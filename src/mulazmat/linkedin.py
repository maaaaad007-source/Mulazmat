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

import random
import time
from collections.abc import Callable, Iterator

import requests
from bs4 import BeautifulSoup

from .models import Job, SearchQuery

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

#: LinkedIn returns 10 cards per request and stops serving results past ~1000.
PAGE_SIZE = 10
MAX_START = 975

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}


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
                url=url,
                posted_at=(time_node.get("datetime") if time_node else "") or "",
                posted_label=_text(time_node),
                salary=_text(card.select_one("span.job-search-card__salary-info")),
                company_url=company_url,
            )
        )

    return jobs


class LinkedInClient:
    """Paged, rate-limit-aware reader for the guest job search endpoint."""

    def __init__(
        self,
        session: requests.Session | None = None,
        request_delay: float = 1.5,
        max_retries: int = 3,
        timeout: float = 20.0,
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout

    def _fetch_page(self, query: SearchQuery, start: int) -> str:
        """Fetch one page of cards, retrying with backoff on 429/5xx."""
        params = build_params(query, start)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(SEARCH_URL, params=params, timeout=self.timeout)
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
                raise BlockedError(
                    "LinkedIn refused the request (HTTP 403). It usually clears on its "
                    "own after a while; searching less often helps."
                )
            if response.status_code == 429 or response.status_code >= 500:
                last_error = LinkedInError(f"HTTP {response.status_code}")
                time.sleep((2**attempt) + random.uniform(0, 1))
                continue

            raise LinkedInError(f"Unexpected response from LinkedIn: HTTP {response.status_code}")

        if isinstance(last_error, LinkedInError) and "429" in str(last_error):
            raise RateLimitedError(
                "LinkedIn is rate limiting this search (HTTP 429). Wait a few minutes, "
                "or ask for fewer results."
            )
        raise LinkedInError(f"Could not reach LinkedIn: {last_error}")

    def iter_jobs(self, query: SearchQuery, limit: int = 100) -> Iterator[Job]:
        """Yield up to ``limit`` unique jobs, paging until LinkedIn runs dry."""
        seen: set[str] = set()
        yielded = 0
        empty_pages = 0
        start = 0

        while yielded < limit and start <= MAX_START:
            html = self._fetch_page(query, start)
            page = parse_jobs_html(html) if html else []

            new_on_page = 0
            for job in page:
                key = job.job_id or job.url
                if key in seen:
                    continue
                seen.add(key)
                new_on_page += 1
                yielded += 1
                yield job
                if yielded >= limit:
                    return

            # Two consecutive pages with nothing new means we have it all.
            empty_pages = empty_pages + 1 if new_on_page == 0 else 0
            if empty_pages >= 2:
                return

            start += PAGE_SIZE
            if yielded < limit and start <= MAX_START:
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
