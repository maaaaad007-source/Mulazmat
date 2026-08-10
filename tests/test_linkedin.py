from mulazmat.linkedin import build_params, parse_jobs_html
from mulazmat.models import SearchQuery

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
    <span class="job-search-card__location">Lahore, Punjab, Pakistan</span>
    <span class="job-search-card__salary-info"> PKR 200,000/mo </span>
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
    assert first.location == "Lahore, Punjab, Pakistan"
    assert first.salary == "PKR 200,000/mo"
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
        location="Pakistan",
        geo_id="101022442",
        date_posted="r604800",
        experience_levels=("2", "3"),
        job_types=("F",),
        workplace_types=("2", "3"),
        sort_by="DD",
    )
    params = build_params(query, start=20)

    assert params["start"] == "20"
    assert params["location"] == "Pakistan"
    assert params["geoId"] == "101022442"
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
