"""Fetching runs in parallel, without disturbing order or correctness."""

import threading
import time

import requests

from mulazmat.linkedin import (
    MAX_INTERVAL,
    PAGE_SIZE,
    LinkedInClient,
    LinkedInError,
    RateLimitedError,
    _Pacer,
)
from mulazmat.models import Job, SearchQuery


def _card(job_id: int) -> str:
    return f"""
    <div class="base-card" data-entity-urn="urn:li:jobPosting:{job_id}">
      <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/{job_id}"></a>
      <h3 class="base-search-card__title">Role {job_id}</h3>
      <h4 class="base-search-card__subtitle">Company {job_id}</h4>
    </div>
    """


class _SlowClient(LinkedInClient):
    """Answers every request after ``latency``, tracking peak concurrency."""

    def __init__(self, pages: int = 5, latency: float = 0.05, **kwargs):
        super().__init__(**kwargs)
        self.pages = pages
        self.latency = latency
        self.in_flight = 0
        self.peak = 0
        self.calls: list[str] = []
        self._lock = threading.Lock()

    def _get(self, url: str, params: dict | None = None) -> str:
        with self._lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
            self.calls.append(url)
        try:
            time.sleep(self.latency)
            if params and "start" in params:
                start = int(params["start"])
                if start >= self.pages * PAGE_SIZE:
                    return ""
                first = start + 1
                return "".join(_card(first + i) for i in range(PAGE_SIZE))
            return "<div class='description__text'>Full posting text.</div>"
        finally:
            with self._lock:
                self.in_flight -= 1


def _jobs(count: int) -> list[Job]:
    return [
        Job(job_id=str(i), title=f"Role {i}", company="C", location="L", url="")
        for i in range(count)
    ]


def test_enrichment_runs_in_parallel():
    client = _SlowClient(latency=0.05, max_workers=8)
    jobs = _jobs(16)

    started = time.monotonic()
    client.enrich(jobs, limit=len(jobs))
    elapsed = time.monotonic() - started

    # Sequentially this is 16 × 50ms = 0.8s; in parallel it is a fraction.
    assert elapsed < 0.4, f"enrichment did not overlap requests ({elapsed:.2f}s)"
    assert client.peak > 1


def test_enrichment_keeps_the_results_in_order():
    client = _SlowClient(latency=0.01, max_workers=8)
    jobs = _jobs(20)

    enriched = client.enrich(jobs, limit=len(jobs))
    assert [job.job_id for job in enriched] == [job.job_id for job in jobs]
    assert all(job.description for job in enriched)


def test_enrichment_past_the_limit_leaves_jobs_untouched():
    client = _SlowClient(latency=0.01, max_workers=4)
    jobs = _jobs(10)

    enriched = client.enrich(jobs, limit=4)
    assert all(job.description for job in enriched[:4])
    assert not any(job.description for job in enriched[4:])
    assert [job.job_id for job in enriched] == [job.job_id for job in jobs]


def test_progress_is_reported_once_per_job():
    client = _SlowClient(latency=0.01, max_workers=8)
    seen: list[int] = []
    client.enrich(_jobs(12), limit=12, on_progress=lambda done, total: seen.append(done))

    assert len(seen) == 12
    assert max(seen) == 12


def test_progress_is_reported_on_the_calling_thread():
    # Streamlit APIs are only valid on the thread running the script, so a
    # progress callback must never be invoked from a pool worker.
    client = _SlowClient(latency=0.01, max_workers=4)
    caller = threading.current_thread().ident
    threads: list[int] = []

    client.enrich(
        _jobs(8), limit=8, on_progress=lambda *_: threads.append(threading.current_thread().ident)
    )

    assert threads and set(threads) == {caller}


def test_search_pages_are_fetched_in_parallel_but_yielded_in_order():
    client = _SlowClient(pages=5, latency=0.05, max_workers=8)

    started = time.monotonic()
    jobs = client.search(SearchQuery(keywords="x"), limit=50)
    elapsed = time.monotonic() - started

    assert [job.job_id for job in jobs] == [str(i) for i in range(1, 51)]
    # Five pages sequentially would be 5 × 50ms plus pacing; in one wave it is ~50ms.
    assert elapsed < 0.25, f"pages were not fetched concurrently ({elapsed:.2f}s)"


def test_search_stops_once_linkedin_runs_dry():
    client = _SlowClient(pages=2, latency=0.0, max_workers=8)
    jobs = client.search(SearchQuery(keywords="x"), limit=200)

    assert len(jobs) == 20  # two pages of ten, then nothing
    assert len(client.calls) < 30, "should stop rather than page to the cap"


def test_a_caller_supplied_session_pins_the_client_to_one_worker():
    # requests.Session is not thread-safe, so a shared one must not be used
    # from several threads at once.
    session = requests.Session()
    client = LinkedInClient(session=session, max_workers=8)

    assert client.max_workers == 1
    assert client.session is session


def test_each_thread_gets_its_own_session():
    client = LinkedInClient(max_workers=4)
    # Hold the objects, not their ids: a collected session's address can be
    # handed straight back to the next allocation.
    seen: list[requests.Session] = []
    lock = threading.Lock()

    def grab() -> None:
        session = client.session
        with lock:
            seen.append(session)

    threads = [threading.Thread(target=grab) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len({id(session) for session in seen}) == 4


def test_one_failing_detail_page_does_not_sink_the_batch():
    class _Flaky(_SlowClient):
        def _get(self, url: str, params: dict | None = None) -> str:
            if "jobPosting/3" in url:
                raise LinkedInError("boom")
            return super()._get(url, params)

    client = _Flaky(latency=0.0, max_workers=4)
    enriched = client.enrich(_jobs(6), limit=6)

    assert [job.job_id for job in enriched] == [str(i) for i in range(6)]
    assert not enriched[3].description  # the failure kept its original job
    assert enriched[0].description


class _Response:
    def __init__(self, status_code: int, headers: dict | None = None, text: str = "ok"):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class _Rebuffed(LinkedInClient):
    """Answers with 429 for the first ``fails`` requests, then normally."""

    def __init__(self, fails: int, headers: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.fails = fails
        self.headers = headers or {}
        self.seen = 0
        self.slept: list[float] = []
        self._lock = threading.Lock()

    @property
    def session(self):
        client = self

        class _S:
            @staticmethod
            def get(url, params=None, timeout=None):
                with client._lock:
                    client.seen += 1
                    n = client.seen
                return (
                    _Response(429, client.headers)
                    if n <= client.fails
                    else _Response(200, text="<div class='description__text'>Text.</div>")
                )

        return _S()


def test_requests_are_paced_apart_even_with_many_workers():
    # Concurrency alone does not bound the request *rate*, which is what
    # LinkedIn actually measures.
    pacer = _Pacer(0.05)
    started: list[float] = []
    lock = threading.Lock()

    def go() -> None:
        pacer.wait()
        with lock:
            started.append(time.monotonic())

    threads = [threading.Thread(target=go) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    started.sort()
    gaps = [b - a for a, b in zip(started, started[1:])]
    assert all(gap >= 0.04 for gap in gaps), gaps


def test_a_429_widens_the_gap_for_the_rest_of_the_run():
    client = _Rebuffed(fails=1, min_interval=0.01, max_workers=1)
    before = client._pacer.interval

    client._get("https://example.test/x")

    assert client.throttled
    assert client._pacer.interval > before


def test_backing_off_is_capped():
    pacer = _Pacer(1.0)
    for _ in range(10):
        pacer.slow_down()
    assert pacer.interval == MAX_INTERVAL


def test_retry_after_is_honoured_when_linkedin_sends_one():
    client = _Rebuffed(fails=1, headers={"Retry-After": "3"}, min_interval=0.01, max_workers=1)
    assert client._retry_after(_Response(429, {"Retry-After": "3"}), attempt=0) == 3.0
    # Absurd values are clamped rather than trusted.
    assert client._retry_after(_Response(429, {"Retry-After": "9999"}), attempt=0) == 30.0
    # A non-numeric header falls back to exponential backoff.
    assert client._retry_after(_Response(429, {"Retry-After": "later"}), attempt=1) >= 2.0


def test_rate_limiting_partway_through_keeps_the_results_so_far():
    class _DiesAfterOneWave(_SlowClient):
        def _fetch_page(self, args):
            query, start = args
            if start >= PAGE_SIZE * 4:
                raise RateLimitedError("slow down")
            return super()._fetch_page(args)

    client = _DiesAfterOneWave(pages=20, latency=0.0, max_workers=4)
    jobs = client.search(SearchQuery(keywords="x"), limit=100)

    # Four pages made it; the error did not throw the lot away.
    assert len(jobs) == 40


def test_rate_limiting_on_the_very_first_wave_still_raises():
    class _DiesImmediately(_SlowClient):
        def _fetch_page(self, args):
            raise RateLimitedError("slow down")

    client = _DiesImmediately(latency=0.0, max_workers=4)
    try:
        client.search(SearchQuery(keywords="x"), limit=100)
    except RateLimitedError:
        pass
    else:
        raise AssertionError("with nothing to show, the error must surface")
