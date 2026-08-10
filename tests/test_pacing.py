"""Requests stay sequential and paced.

An earlier attempt at speed fired eight requests at once with no gap and was
rate limited immediately. These tests pin the shape that works: one request at
a time, a deliberate pause between them, and no pause after the last one.
"""

import threading
import time

from mulazmat.linkedin import REQUEST_DELAY, PAGE_SIZE, LinkedInClient
from mulazmat.models import Job, SearchQuery


def _card(job_id: int) -> str:
    return f"""
    <div class="base-card" data-entity-urn="urn:li:jobPosting:{job_id}">
      <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/{job_id}"></a>
      <h3 class="base-search-card__title">Role {job_id}</h3>
      <h4 class="base-search-card__subtitle">Company {job_id}</h4>
    </div>
    """


class _Recorder(LinkedInClient):
    """Records when each request starts, and how many overlap."""

    def __init__(self, pages: int = 3, latency: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.pages = pages
        self.latency = latency
        self.starts: list[float] = []
        self.in_flight = 0
        self.peak = 0
        self._lock = threading.Lock()

    def _get(self, url: str, params: dict | None = None) -> str:
        with self._lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
            self.starts.append(time.monotonic())
        try:
            time.sleep(self.latency)
            if params and "start" in params:
                start = int(params["start"])
                if start >= self.pages * PAGE_SIZE:
                    return ""
                return "".join(_card(start + 1 + i) for i in range(PAGE_SIZE))
            return "<div class='description__text'>Posting text.</div>"
        finally:
            with self._lock:
                self.in_flight -= 1


def _jobs(count: int) -> list[Job]:
    return [
        Job(job_id=str(i), title="Role", company="C", location="L", url="")
        for i in range(count)
    ]


def test_the_default_delay_is_the_documented_one():
    assert LinkedInClient().request_delay == REQUEST_DELAY


def test_requests_never_overlap():
    # The dial to turn for speed is the delay, never concurrency: firing
    # several at once is what earned an immediate 429.
    client = _Recorder(pages=3, request_delay=0.0)
    client.enrich(_jobs(5), limit=5)
    client.search(SearchQuery(keywords="x"), limit=30)

    assert client.peak == 1


def test_a_gap_is_left_between_enrichment_requests():
    client = _Recorder(request_delay=0.05)
    client.enrich(_jobs(4), limit=4)

    gaps = [b - a for a, b in zip(client.starts, client.starts[1:])]
    assert len(gaps) == 3
    assert all(gap >= 0.04 for gap in gaps), gaps


def test_no_time_is_wasted_after_the_final_request():
    client = _Recorder(request_delay=0.3)

    started = time.monotonic()
    client.enrich(_jobs(2), limit=2)
    elapsed = time.monotonic() - started

    # Two requests means one gap between them, not two.
    assert elapsed < 0.6, f"looks like it idled after the last request ({elapsed:.2f}s)"


def test_the_workplace_probe_does_not_idle_after_its_last_pass():
    client = _Recorder(pages=1, request_delay=0.3)

    started = time.monotonic()
    client.workplace_map(SearchQuery(keywords="x"), limit=10)
    elapsed = time.monotonic() - started

    # Two probes, so one gap between them — plus each probe's own paging.
    assert elapsed < 1.2, f"idled after the final probe ({elapsed:.2f}s)"


def test_paging_stops_without_a_trailing_pause():
    client = _Recorder(pages=2, request_delay=0.3)

    started = time.monotonic()
    jobs = client.search(SearchQuery(keywords="x"), limit=100)
    elapsed = time.monotonic() - started

    assert len(jobs) == 20
    # Pages fetched: two with results, then the empties that end it. Whatever
    # that count is, it must not pay a delay after the final one.
    assert elapsed < len(client.starts) * 0.3, f"{elapsed:.2f}s for {len(client.starts)} requests"
