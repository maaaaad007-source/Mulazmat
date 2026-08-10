from mulazmat.linkedin import LinkedInClient, LinkedInError, build_params, parse_jobs_html
from mulazmat.models import Job, SearchQuery

# Trimmed-down copy of a real search-result fragment.
FRAGMENT = """
<li>
  <div class="base-card relative job-search-card"
       data-entity-urn="urn:li:jobPosting:4012345678">
    <a class="base-card__full-link"
       href="https://www.linkedin.com/jobs/view/data-analyst-at-acme-4012345678?refId=xyz"></a>
    <h3 class="base-search-card__title"> Data Analyst </h3>
    <h4 class="base-search-card__subtitle">
      <a class="hidden-nested-link" href="https://www.linkedin.com/company/acme?trk=x">Acme</a>
    </h4>
    <span class="job-search-card__location">Amsterdam, North Holland, Netherlands</span>
    <span class="job-search-card__salary-info"> €6,500/mo </span>
    <time class="job-search-card__listdate" datetime="2026-08-01">1 week ago</time>
  </div>
</li>
<li>
  <div class="base-card" data-entity-urn="urn:li:jobPosting:4099999999">
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/4099999999"></a>
    <h3 class="base-search-card__title">Senior Data Analyst</h3>
    <h4 class="base-search-card__subtitle">Globex</h4>
    <span class="job-search-card__location">Remote</span>
  </div>
</li>
"""


def test_parses_cards():
    jobs = parse_jobs_html(FRAGMENT)
    assert len(jobs) == 2

    first = jobs[0]
    assert first.job_id == "4012345678"
    assert first.title == "Data Analyst"
    assert first.company == "Acme"
    assert first.location == "Amsterdam, North Holland, Netherlands"
    assert first.salary == "€6,500/mo"
    assert first.posted_at == "2026-08-01"
    assert first.posted_label == "1 week ago"
    # Tracking params are stripped from both links.
    assert first.url == "https://www.linkedin.com/jobs/view/data-analyst-at-acme-4012345678"
    assert first.company_url == "https://www.linkedin.com/company/acme"


def test_parses_card_without_optional_fields():
    second = parse_jobs_html(FRAGMENT)[1]
    assert second.job_id == "4099999999"
    assert second.company == "Globex"
    assert second.salary == ""
    assert second.posted_at == ""


def test_duplicate_cards_are_dropped():
    assert len(parse_jobs_html(FRAGMENT + FRAGMENT)) == 2


def test_empty_html_yields_nothing():
    assert parse_jobs_html("") == []
    assert parse_jobs_html("<ul></ul>") == []


def test_build_params_minimal_query():
    params = build_params(SearchQuery(keywords="data analyst"))
    assert params["keywords"] == "data analyst"
    assert params["start"] == "0"
    assert "f_TPR" not in params
    assert "geoId" not in params


def test_build_params_full_query():
    query = SearchQuery(
        keywords="data analyst",
        location="Netherlands",
        geo_id="102890719",
        date_posted="r604800",
        experience_levels=("2", "3"),
        job_types=("F",),
        workplace_types=("2", "3"),
        sort_by="DD",
    )
    params = build_params(query, start=20)

    assert params["start"] == "20"
    assert params["location"] == "Netherlands"
    assert params["geoId"] == "102890719"
    assert params["f_TPR"] == "r604800"
    assert params["f_E"] == "2,3"
    assert params["f_JT"] == "F"
    assert params["f_WT"] == "2,3"
    assert params["sortBy"] == "DD"


def test_company_filter_ignores_case_and_blanks():
    job = parse_jobs_html(FRAGMENT)[0]
    assert job.matches_company("acme")
    assert job.matches_company("  ")
    assert not job.matches_company("globex")


class _FakeClient(LinkedInClient):
    """Records which workplace filter each probe used, and answers from a map."""

    def __init__(self, by_code, fail_on=None):
        super().__init__(request_delay=0)
        self.by_code = by_code
        self.fail_on = fail_on
        self.codes_seen = []

    def iter_jobs(self, query, limit=100):
        code = query.workplace_types[0]
        self.codes_seen.append(code)
        if code == self.fail_on:
            raise LinkedInError("probe failed")
        for job_id in self.by_code.get(code, ()):
            yield Job(job_id=job_id, title="t", company="c", location="l", url="")


def test_workplace_map_labels_remote_and_hybrid_from_linkedins_own_filters():
    client = _FakeClient({"2": ["1", "2"], "3": ["3"]})
    assert client.workplace_map(SearchQuery(keywords="x")) == {
        "1": "Remote",
        "2": "Remote",
        "3": "Hybrid",
    }
    assert client.codes_seen == ["2", "3"]


def test_jobs_in_neither_probe_stay_unlabelled():
    # A posting that never declared a workplace type matches no filter, so it
    # is left blank rather than assumed on-site.
    client = _FakeClient({"2": ["1"]})
    assert "99" not in client.workplace_map(SearchQuery(keywords="x"))


def test_a_failed_probe_degrades_instead_of_breaking_the_search():
    client = _FakeClient({"2": ["1"]}, fail_on="2")
    assert client.workplace_map(SearchQuery(keywords="x")) == {}


def test_the_probe_never_reuses_the_users_own_workplace_filter():
    client = _FakeClient({"2": ["1"], "3": []})
    client.workplace_map(SearchQuery(keywords="x", workplace_types=("1",)))
    assert client.codes_seen == ["2", "3"]
