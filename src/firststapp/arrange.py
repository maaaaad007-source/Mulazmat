"""Re-arranging results that have already been fetched.

Some filters can be applied to the cards on screen, with no request at all:
sorting, the date window, the company name, and trimming to fewer results. The
search card carries the date and company, so all of that is just local work.

Others cannot. A search card says nothing about workplace type or experience
level, so those have to be handed to LinkedIn as query parameters and the
search re-run — there is no data here to filter on.

:func:`needs_refetch` is where that line is drawn.
"""

from __future__ import annotations

from datetime import date, timedelta

from .models import Job, SearchQuery

#: Query fields that only LinkedIn can act on. Changing any of them means the
#: results on screen are the wrong set, not merely the wrong order.
SERVER_SIDE_FIELDS = (
    "keywords",
    "location",
    "geo_id",
    "workplace_types",
    "experience_levels",
    "job_types",
)


def needs_refetch(previous: SearchQuery | None, current: SearchQuery) -> bool:
    """True when the change requires asking LinkedIn again."""
    if previous is None:
        return True
    return any(
        getattr(previous, field) != getattr(current, field) for field in SERVER_SIDE_FIELDS
    )


def _posted_on(job: Job) -> str:
    """The posting's date as ``YYYY-MM-DD``, or "" when it has none."""
    return (job.posted_at or "").strip()[:10]


def within_window(jobs: list[Job], seconds: str, today: date | None = None) -> list[Job]:
    """Keep postings inside LinkedIn's ``f_TPR`` window.

    ``seconds`` is LinkedIn's own wording — "r604800" for a week. A posting
    with no date is dropped while a window is active: the filter asserts
    "posted within X", and that cannot be asserted about an unknown date.
    """
    if not seconds:
        return list(jobs)

    try:
        span = int(str(seconds).lstrip("r"))
    except ValueError:
        return list(jobs)

    cutoff = ((today or date.today()) - timedelta(seconds=span)).isoformat()
    return [job for job in jobs if _posted_on(job) and _posted_on(job) >= cutoff]


def sort_jobs(jobs: list[Job], sort_by: str) -> list[Job]:
    """Newest first for "DD"; LinkedIn's own relevance order otherwise.

    Relevance is the order they arrived in, so it cannot be recomputed here —
    it is simply left alone.
    """
    if sort_by != "DD":
        return list(jobs)

    # Dateless postings sort last rather than being treated as very old. With
    # reverse=True the "has a date" flag must be True for dated postings, so
    # they come first — inverting it floats the dateless ones to the top.
    return sorted(jobs, key=lambda job: (_posted_on(job) != "", _posted_on(job)), reverse=True)


def arrange(
    jobs: list[Job],
    query: SearchQuery,
    limit: int | None = None,
    today: date | None = None,
) -> list[Job]:
    """Apply every filter that does not need LinkedIn, in display order."""
    shown = [job for job in jobs if job.matches_company(query.company)]
    shown = within_window(shown, query.date_posted, today)
    shown = sort_jobs(shown, query.sort_by)
    if limit is not None:
        shown = shown[:limit]
    return shown
