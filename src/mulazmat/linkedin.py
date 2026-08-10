"""Client for LinkedIn's public (guest) job-search endpoint.

LinkedIn has no open jobs API. What it does have is the endpoint its own
logged-out jobs page calls for infinite scroll:

    /jobs-guest/jobs/api/seeMoreJobPostings/search

It returns an HTML fragment — a ``<li>`` per posting — which we parse into
:class:`~mulazmat.models.Job` objects. Two consequences worth knowing:

* **It is rate limited.** Hammering it earns HTTP 429 and then a temporary
  block. The client paces itself (see ``request_delay``) and backs off.
* **It is not a contract.** LinkedIn can change the markup at any time; the
  parser is written defensively but can still come up empty if they do.

Scraping LinkedIn is also contrary to their Terms of Service. This module is
here for personal, low-volume job hunting; use it accordingly, and prefer an
official job-board API if you need reliable bulk access.
"""

from __future__ import annotations

import dataclasses
import json
import random
import re
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from .models import Job, SearchQuery

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
JOB_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

#: LinkedIn returns 10 cards per request and stops serving results past ~1000.
PAGE_SIZE = 10
MAX_START = 975

#: Requests in flight at once. Every result needs its own detail page, so doing
#: those one at a time is the difference between seconds and minutes.
MAX_WORKERS = 4

#: Minimum gap between the *start* of any two requests, across all threads.
#: Concurrency alone is not enough to stay under LinkedIn's limit — what it
#: measures is the request rate, so that is what has to be bounded. Widens
#: automatically after a 429 and stays widened for the rest of the run.
MIN_INTERVAL = 0.25
MAX_INTERVAL = 2.0

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}


class _Pacer:
    """Bounds how often requests may start, shared across worker threads.

    Threads reserve their slot under a lock and then sleep outside it, so eight
    workers issue at most one request every ``min_interval`` between them
    rather than eight at once.
    """

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._next_at = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            start_at = max(time.monotonic(), self._next_at)
            self._next_at = start_at + self._min_interval
        delay = start_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    def slow_down(self, factor: float = 2.0) -> float:
        """Widen the gap after a rebuff, and report the new interval."""
        with self._lock:
            self._min_interval = min(self._min_interval * factor, MAX_INTERVAL)
            return self._min_interval

    @property
    def interval(self) -> float:
        return self._min_interval


class LinkedInError(RuntimeError):
    """Base class for search failures."""


class RateLimitedError(LinkedInError):
    """LinkedIn asked us to slow down (HTTP 429) and kept saying so."""


class BlockedError(LinkedInError):
    """LinkedIn refused the request outright (HTTP 403)."""


def build_params(query: SearchQuery, start: int = 0) -> dict[str, str]:
    """Translate a :class:`SearchQuery` into endpoint query parameters."""
    params: dict[str, str] = {"keywords": query.keywords.strip(), "start": str(start)}

    if query.location.strip():
        params["location"] = query.location.strip()
    if query.geo_id:
        params["geoId"] = query.geo_id
    if query.date_posted:
        params["f_TPR"] = query.date_posted
    if query.experience_levels:
        params["f_E"] = ",".join(query.experience_levels)
    if query.job_types:
        params["f_JT"] = ",".join(query.job_types)
    if query.workplace_types:
        params["f_WT"] = ",".join(query.workplace_types)
    if query.sort_by:
        params["sortBy"] = query.sort_by

    return params


def _text(node) -> str:
    return node.get_text(strip=True) if node else ""


def _logo_url(card) -> str:
    """Company logo from a search card.

    LinkedIn lazy-loads these, so the real URL usually sits in
    ``data-delayed-url`` and ``src`` holds a transparent placeholder.
    """
    image = card.select_one("img")
    if not image:
        return ""

    for attribute in ("data-delayed-url", "data-ghost-url", "src"):
        url = (image.get(attribute) or "").strip()
        if url.startswith("http") and "data:image" not in url:
            return url
    return ""


def _job_id(card) -> str:
    """Pull the numeric posting id out of the card's entity urn or link."""
    urn = card.get("data-entity-urn") or ""
    if ":" in urn:
        return urn.rsplit(":", 1)[-1]

    link = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
    href = (link.get("href") if link else "") or ""
    if "/jobs/view/" in href:
        tail = href.split("/jobs/view/", 1)[1].split("?", 1)[0].rstrip("/")
        # Slugged URLs look like "senior-engineer-at-acme-4012345678".
        candidate = tail.rsplit("-", 1)[-1]
        if candidate.isdigit():
            return candidate
        if tail.isdigit():
            return tail
    return ""


def parse_jobs_html(html: str) -> list[Job]:
    """Parse a fragment of search-result cards into :class:`Job` objects."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.base-card, div.base-search-card, li div[data-entity-urn]")

    jobs: list[Job] = []
    seen: set[str] = set()

    for card in cards:
        title = _text(card.select_one("h3.base-search-card__title, h3"))
        if not title:
            continue

        company_node = card.select_one(
            "h4.base-search-card__subtitle a, h4.base-search-card__subtitle, h4"
        )
        link = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
        time_node = card.select_one("time")

        url = (link.get("href") if link else "") or ""
        url = url.split("?", 1)[0]

        company_link = card.select_one("h4.base-search-card__subtitle a")
        company_url = ((company_link.get("href") if company_link else "") or "").split("?", 1)[0]

        job_id = _job_id(card)
        key = job_id or url or f"{title}|{_text(company_node)}"
        if key in seen:
            continue
        seen.add(key)

        jobs.append(
            Job(
                job_id=job_id,
                title=title,
                company=_text(company_node),
                location=_text(card.select_one("span.job-search-card__location")),
                workplace=_text(card.select_one("span.job-search-card__workplace-type")),
                logo_url=_logo_url(card),
                url=url,
                posted_at=(time_node.get("datetime") if time_node else "") or "",
                posted_label=_text(time_node),
                salary=_text(card.select_one("span.job-search-card__salary-info")),
                company_url=company_url,
            )
        )

    return jobs


#: Criteria labels LinkedIn uses on the guest job page -> our field names.
_CRITERIA_FIELDS = {
    "seniority level": "seniority",
    "employment type": "employment_type",
    "job function": "job_function",
    "industries": "industries",
    # Rarely present, but free to read when it is.
    "workplace type": "workplace",
    "remote": "workplace",
}

#: schema.org employmentType codes -> the wording LinkedIn shows.
_EMPLOYMENT_TYPES = {
    "FULL_TIME": "Full-time",
    "PART_TIME": "Part-time",
    "CONTRACTOR": "Contract",
    "TEMPORARY": "Temporary",
    "INTERN": "Internship",
    "VOLUNTEER": "Volunteer",
    "OTHER": "Other",
}

_APPLY_URL_RE = re.compile(r"https?://[^\"'\s<>]+")


#: Button labels LinkedIn renders inside the description block.
_UI_NOISE = re.compile(r"\s*\b(Show more|Show less|See more|See less)\b\s*", re.IGNORECASE)


def _strip_ui_text(text: str) -> str:
    """Drop LinkedIn's own expander labels from scraped description text."""
    return _UI_NOISE.sub(" ", text).strip()


def _clean(text: str, limit: int = 600) -> str:
    """Collapse whitespace and trim to a card-sized snippet."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


#: Containers LinkedIn has used for the "meet the hiring team" block. The
#: guest page usually omits it entirely — it is mostly a logged-in feature — so
#: this casts a wide net and simply finds nothing when there is nothing.
_HIRER_CONTAINERS = (
    "div.message-the-recruiter",
    "section.message-the-recruiter",
    "div.job-details-jobs-unified-top-card__hiring-team",
    "div.hirer-card",
    "[data-testid='hirer-card']",
)


def _parse_hirer(soup: BeautifulSoup) -> dict[str, str]:
    """The named person who posted the job, when the page shows one.

    Name, headline and public profile link only. LinkedIn publishes no email or
    phone number for them, and none is inferred here.
    """
    for selector in _HIRER_CONTAINERS:
        block = soup.select_one(selector)
        if not block:
            continue

        profile = block.select_one("a[href*='/in/']")
        name = _text(block.select_one("h3, h4, .base-main-card__title, .hirer-card__hirer-job-title"))
        # Some layouts put the name only in the profile link's text.
        if not name and profile:
            name = _text(profile)
        if not name:
            continue

        found = {"poster_name": name}
        title = _text(block.select_one("h4, .base-main-card__subtitle, .hirer-card__hirer-headline"))
        if title and title != name:
            found["poster_title"] = title
        if profile:
            found["poster_profile"] = (profile.get("href") or "").split("?", 1)[0]
        return found

    return {}


def parse_json_ld(soup: BeautifulSoup) -> dict[str, str]:
    """Read the schema.org JobPosting block LinkedIn embeds on job pages.

    This is the only place a posting reliably states that it is remote —
    ``jobLocationType: "TELECOMMUTE"`` — since the visible criteria list has no
    workplace row. Anything unparseable is skipped rather than guessed at.
    """
    found: dict[str, str] = {}

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except (TypeError, ValueError):
            continue

        # A page can ship several blocks, or one block holding a list/@graph —
        # pick the JobPosting rather than whichever entry happens to be first.
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            data = data["@graph"]
        if isinstance(data, list):
            entries = [item for item in data if isinstance(item, dict)]
            data = next(
                (item for item in entries if str(item.get("@type", "")) == "JobPosting"),
                entries[0] if entries else None,
            )
        if not isinstance(data, dict):
            continue

        if str(data.get("jobLocationType", "")).upper() == "TELECOMMUTE":
            found["workplace"] = "Remote"

        employment = data.get("employmentType")
        if isinstance(employment, list):
            employment = employment[0] if employment else None
        if isinstance(employment, str):
            label = _EMPLOYMENT_TYPES.get(employment.strip().upper().replace("-", "_"))
            if label:
                found["employment_type"] = label

    return found


def parse_job_details(html: str) -> dict[str, str]:
    """Pull the extra fields off a guest job-detail page.

    Every field is optional — LinkedIn shows different subsets per posting, and
    logged-out pages are the most sparse. Missing simply means "".

    Note that no email address or phone number is ever extracted here. LinkedIn
    does not publish them on job pages, and personal contact details are not
    something this app collects.
    """
    if not html or not html.strip():
        return {}

    soup = BeautifulSoup(html, "html.parser")
    details: dict[str, str] = {}

    # Read this first so the visible page can override it where both exist.
    details.update(parse_json_ld(soup))

    # Prefer the inner markup node: the outer wrapper also contains LinkedIn's
    # own "Show more"/"Show less" buttons, which otherwise land mid-sentence in
    # the text. Stored long so a card can expand to the whole posting.
    body = soup.select_one("div.show-more-less-html__markup, div.description__text")
    if body:
        details["description"] = _clean(_strip_ui_text(body.get_text(" ", strip=True)), 6000)

    for item in soup.select("li.description__job-criteria-item"):
        label = _text(item.select_one("h3, .description__job-criteria-subheader")).lower()
        value = _text(item.select_one("span.description__job-criteria-text, span"))
        field_name = _CRITERIA_FIELDS.get(label.strip())
        if field_name and value:
            details[field_name] = value

    # LinkedIn shows the workplace type as a "flavor" chip on the job page's
    # top card when the posting sets one.
    flavor = _text(
        soup.select_one(
            "span.topcard__flavor--workplace-type, span.job-details-jobs-unified-top-card__workplace-type"
        )
    )
    if flavor:
        details["workplace"] = flavor

    applicants = _text(soup.select_one("span.num-applicants__caption, figcaption"))
    if applicants:
        details["applicants"] = _clean(applicants, 60)

    # LinkedIn hides the external apply target in a commented-out <code> block.
    apply_node = soup.select_one("code#applyUrl")
    if apply_node:
        match = _APPLY_URL_RE.search(apply_node.decode_contents())
        if match:
            details["apply_url"] = match.group(0).replace("&amp;", "&")

    details.update(_parse_hirer(soup))

    return details


class LinkedInClient:
    """Paged, rate-limit-aware reader for the guest job search endpoint."""

    def __init__(
        self,
        session: requests.Session | None = None,
        # Paced between waves, not between individual requests — cheap
        # insurance against a 429 without costing much wall time.
        request_delay: float = 0.25,
        max_retries: int = 3,
        timeout: float = 20.0,
        max_workers: int = MAX_WORKERS,
        min_interval: float = MIN_INTERVAL,
    ) -> None:
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_workers = max(1, max_workers)
        self._pacer = _Pacer(min_interval)
        #: Set once LinkedIn pushes back, so callers can say results are partial.
        self.throttled = False

        # requests.Session is not thread-safe, so each worker thread gets its
        # own. An explicitly passed session is used as-is and pins the client
        # to one worker, which keeps single-threaded callers predictable.
        self._explicit_session = session
        if session is not None:
            session.headers.update(DEFAULT_HEADERS)
            self.max_workers = 1
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:
        """This thread's session, created on first use."""
        if self._explicit_session is not None:
            return self._explicit_session

        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            # Room for every worker in the connection pool, otherwise urllib3
            # discards connections and warns on each request.
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=self.max_workers, pool_maxsize=self.max_workers
            )
            session.mount("https://", adapter)
            self._local.session = session
        return session

    def _map(self, fn, items: list):
        """Run ``fn`` over ``items`` concurrently, keeping the input order."""
        if self.max_workers == 1 or len(items) < 2:
            return [fn(item) for item in items]

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(fn, items))

    def _retry_after(self, response: requests.Response, attempt: int) -> float:
        """How long to wait before retrying, preferring LinkedIn's own answer."""
        header = (response.headers.get("Retry-After") or "").strip()
        if header.isdigit():
            return min(float(header), 30.0)
        return (2**attempt) + random.uniform(0, 1)

    def _get(self, url: str, params: dict[str, str] | None = None) -> str:
        """GET ``url``, retrying with backoff on 429/5xx.

        Returns "" for 400/404, which is how LinkedIn signals "nothing here"
        rather than an actual error.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            self._pacer.wait()
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:  # network hiccup
                last_error = exc
                time.sleep(2**attempt)
                continue

            if response.status_code == 200:
                return response.text
            if response.status_code in (400, 404):
                # LinkedIn's way of saying "no more results past here".
                return ""
            if response.status_code == 403:
                self.throttled = True
                raise BlockedError(
                    "LinkedIn refused the request (HTTP 403). This usually follows a "
                    "burst of traffic and clears on its own after a few minutes. Fewer "
                    "results, and “Fetch full details” off, make it far less likely."
                )
            if response.status_code == 429 or response.status_code >= 500:
                last_error = LinkedInError(f"HTTP {response.status_code}")
                if response.status_code == 429:
                    # Back the whole client off, not just this request — the
                    # other workers are about to hit the same wall.
                    self.throttled = True
                    self._pacer.slow_down()
                time.sleep(self._retry_after(response, attempt))
                continue

            raise LinkedInError(f"Unexpected response from LinkedIn: HTTP {response.status_code}")

        if isinstance(last_error, LinkedInError) and "429" in str(last_error):
            raise RateLimitedError(
                "LinkedIn is rate limiting this search (HTTP 429). Wait a few minutes, "
                "then try fewer results — and with “Fetch full details” off, since that "
                "makes one request per job."
            )
        raise LinkedInError(f"Could not reach LinkedIn: {last_error}")

    def _fetch_page(self, args: tuple[SearchQuery, int]) -> list[Job]:
        query, start = args
        html = self._get(SEARCH_URL, build_params(query, start))
        return parse_jobs_html(html) if html else []

    def iter_jobs(self, query: SearchQuery, limit: int = 100) -> Iterator[Job]:
        """Yield up to ``limit`` unique jobs, paging until LinkedIn runs dry.

        Page offsets are known in advance, so a wave of them is fetched at once
        rather than one at a time. Results are still yielded in LinkedIn's own
        order — only the fetching overlaps.
        """
        seen: set[str] = set()
        yielded = 0
        start = 0

        while yielded < limit and start <= MAX_START:
            remaining = limit - yielded
            wave = min(
                self.max_workers,
                max(1, -(-remaining // PAGE_SIZE)),  # pages still needed
                max(1, (MAX_START - start) // PAGE_SIZE + 1),
            )
            starts = [start + offset * PAGE_SIZE for offset in range(wave)]
            try:
                pages = self._map(self._fetch_page, [(query, s) for s in starts])
            except LinkedInError:
                # Half a page of results beats an error screen. Only the first
                # wave has nothing to show, so only that one propagates.
                if yielded:
                    return
                raise

            new_in_wave = 0
            for page in pages:
                for job in page:
                    key = job.job_id or job.url
                    if key in seen:
                        continue
                    seen.add(key)
                    new_in_wave += 1
                    yielded += 1
                    yield job
                    if yielded >= limit:
                        return

            # A whole wave with nothing new means LinkedIn has run dry.
            if new_in_wave == 0:
                return

            start += wave * PAGE_SIZE
            if self.request_delay:
                time.sleep(self.request_delay)

    def search(
        self,
        query: SearchQuery,
        limit: int = 100,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Job]:
        """Collect up to ``limit`` jobs, reporting progress as they arrive."""
        jobs: list[Job] = []
        for job in self.iter_jobs(query, limit):
            jobs.append(job)
            if on_progress:
                on_progress(len(jobs), limit)
        return jobs

    def workplace_map(self, query: SearchQuery, limit: int = 100) -> dict[str, str]:
        """Ask LinkedIn which of these jobs are Remote, and which are Hybrid.

        Postings almost never state their workplace type anywhere we can read —
        not on the search card, and not in the job page's criteria list. But the
        search endpoint filters on it, so re-running the same query with
        ``f_WT=2`` and ``f_WT=3`` gives an authoritative set of ids for each.

        Costs two extra paginated searches, which is why it is opt-in. Jobs in
        neither set are left unlabelled rather than assumed on-site: a posting
        that never declared a type matches none of the filters.
        """
        labels: dict[str, str] = {}

        for code, label in (("2", "Remote"), ("3", "Hybrid")):
            probe = dataclasses.replace(query, workplace_types=(code,))
            try:
                for job in self.iter_jobs(probe, limit):
                    if job.job_id:
                        labels[job.job_id] = label
            except LinkedInError:
                # A failed probe just means fewer labels, never a failed search.
                break
            time.sleep(self.request_delay)

        return labels

    def fetch_details(self, job: Job) -> Job:
        """Return a copy of ``job`` with the detail-page fields filled in.

        One extra HTTP request per job. Failures are swallowed and the original
        job returned — a missing description should never break the results.
        """
        if not job.job_id:
            return job

        try:
            html = self._get(JOB_DETAIL_URL.format(job_id=job.job_id))
        except LinkedInError:
            return job

        details = parse_job_details(html)
        if not details:
            return job
        return dataclasses.replace(job, **details, enriched=True)

    def enrich(
        self,
        jobs: list[Job],
        limit: int = 25,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Job]:
        """Fetch detail pages for the first ``limit`` jobs, pacing requests.

        This multiplies your request count, so it is opt-in in the UI and
        capped. Jobs past ``limit`` are returned untouched.
        """
        target = min(limit, len(jobs))
        if not target:
            return list(jobs)

        wanted = list(jobs[:target])
        rest = list(jobs[target:])

        if self.max_workers == 1 or target < 2:
            enriched = []
            for index, job in enumerate(wanted, start=1):
                enriched.append(self.fetch_details(job))
                if on_progress:
                    on_progress(index, target)
            return enriched + rest

        results: list[Job] = list(wanted)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self.fetch_details, job): i for i, job in enumerate(wanted)}
            # ``as_completed`` is iterated here, in the calling thread, so
            # ``on_progress`` never runs on a worker. Streamlit calls made off
            # the main thread have no script context and are dropped silently.
            for done, future in enumerate(as_completed(futures), start=1):
                results[futures[future]] = future.result()
                if on_progress:
                    on_progress(done, target)

        return results + rest
