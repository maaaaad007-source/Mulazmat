"""Filters that can be applied to results already on screen."""

from datetime import date

from firststapp.arrange import arrange, needs_refetch, sort_jobs, within_window
from firststapp.models import Job, SearchQuery

TODAY = date(2026, 8, 10)


def _job(job_id: str, posted: str = "", company: str = "Acme") -> Job:
    return Job(
        job_id=job_id,
        title="Role",
        company=company,
        location="Amsterdam",
        url="",
        posted_at=posted,
    )


# --- sorting -----------------------------------------------------------------


def test_most_recent_puts_the_newest_first():
    jobs = [_job("old", "2026-07-01"), _job("new", "2026-08-09"), _job("mid", "2026-08-01")]
    assert [job.job_id for job in sort_jobs(jobs, "DD")] == ["new", "mid", "old"]


def test_most_relevant_leaves_linkedins_own_order_alone():
    # Relevance is LinkedIn's ranking; it cannot be recomputed here.
    jobs = [_job("b", "2026-07-01"), _job("a", "2026-08-09")]
    assert [job.job_id for job in sort_jobs(jobs, "R")] == ["b", "a"]


def test_undated_postings_sort_last_rather_than_oldest():
    jobs = [_job("undated"), _job("dated", "2026-01-01")]
    assert [job.job_id for job in sort_jobs(jobs, "DD")] == ["dated", "undated"]


def test_sorting_does_not_mutate_the_input():
    jobs = [_job("b", "2026-07-01"), _job("a", "2026-08-09")]
    sort_jobs(jobs, "DD")
    assert [job.job_id for job in jobs] == ["b", "a"]


# --- date window -------------------------------------------------------------


def test_the_past_week_window_keeps_only_that_week():
    jobs = [_job("today", "2026-08-10"), _job("6d", "2026-08-04"), _job("3w", "2026-07-20")]
    kept = within_window(jobs, "r604800", today=TODAY)
    assert [job.job_id for job in kept] == ["today", "6d"]


def test_any_time_keeps_everything():
    jobs = [_job("a", "2020-01-01"), _job("b")]
    assert len(within_window(jobs, "", today=TODAY)) == 2


def test_an_undated_posting_cannot_satisfy_a_date_window():
    # "Posted in the last 24 hours" is an assertion, and an unknown date
    # cannot support it.
    assert within_window([_job("undated")], "r86400", today=TODAY) == []


def test_a_nonsense_window_is_ignored_rather_than_emptying_the_page():
    jobs = [_job("a", "2026-08-10")]
    assert within_window(jobs, "banana", today=TODAY) == jobs


# --- the whole pipeline ------------------------------------------------------


def test_arrange_applies_company_date_sort_and_limit_together():
    jobs = [
        _job("acme-old", "2026-06-01"),
        _job("globex", "2026-08-09", company="Globex"),
        _job("acme-new", "2026-08-09"),
        _job("acme-mid", "2026-08-06"),
    ]
    query = SearchQuery(keywords="x", company="acme", date_posted="r604800", sort_by="DD")

    shown = arrange(jobs, query, limit=2, today=TODAY)
    assert [job.job_id for job in shown] == ["acme-new", "acme-mid"]


def test_arrange_with_no_filters_returns_everything_in_order():
    jobs = [_job("a"), _job("b"), _job("c")]
    assert arrange(jobs, SearchQuery(keywords="x"), today=TODAY) == jobs


# --- when LinkedIn has to be asked again -------------------------------------


def test_sorting_and_dates_never_need_a_new_search():
    base = SearchQuery(keywords="x")
    assert not needs_refetch(base, SearchQuery(keywords="x", sort_by="DD"))
    assert not needs_refetch(base, SearchQuery(keywords="x", date_posted="r86400"))
    assert not needs_refetch(base, SearchQuery(keywords="x", company="acme"))


def test_workplace_and_experience_do_need_a_new_search():
    # A search card carries neither, so there is nothing here to filter on.
    base = SearchQuery(keywords="x")
    assert needs_refetch(base, SearchQuery(keywords="x", workplace_types=("2",)))
    assert needs_refetch(base, SearchQuery(keywords="x", experience_levels=("2",)))


def test_changing_the_query_itself_needs_a_new_search():
    base = SearchQuery(keywords="x")
    assert needs_refetch(base, SearchQuery(keywords="y"))
    assert needs_refetch(base, SearchQuery(keywords="x", location="Sweden"))
    assert needs_refetch(base, SearchQuery(keywords="x", geo_id="123"))


def test_the_first_search_always_fetches():
    assert needs_refetch(None, SearchQuery(keywords="x"))
