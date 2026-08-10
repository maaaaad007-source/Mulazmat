from mulazmat.linkedin import parse_job_details

DETAIL_PAGE = """
<section class="core-section-container">
  <div class="description__text">
    <section class="show-more-less-html">
      <div class="show-more-less-html__markup">
        We are hiring a Data Analyst.   You will own reporting
        and build dashboards.
      </div>
    </section>
  </div>
  <figcaption class="num-applicants__caption">Over 200 applicants</figcaption>
  <ul class="description__job-criteria-list">
    <li class="description__job-criteria-item">
      <h3 class="description__job-criteria-subheader">Seniority level</h3>
      <span class="description__job-criteria-text">Entry level</span>
    </li>
    <li class="description__job-criteria-item">
      <h3 class="description__job-criteria-subheader">Employment type</h3>
      <span class="description__job-criteria-text">Full-time</span>
    </li>
    <li class="description__job-criteria-item">
      <h3 class="description__job-criteria-subheader">Job function</h3>
      <span class="description__job-criteria-text">Analyst</span>
    </li>
    <li class="description__job-criteria-item">
      <h3 class="description__job-criteria-subheader">Industries</h3>
      <span class="description__job-criteria-text">IT Services</span>
    </li>
  </ul>
  <code id="applyUrl" style="display:none"><!--"https://careers.acme.example/apply?id=7&amp;src=li"--></code>
  <div class="message-the-recruiter">
    <h3 class="base-main-card__title">Ayesha Khan</h3>
    <h4 class="base-main-card__subtitle">Talent Acquisition Lead</h4>
    <a href="https://www.linkedin.com/in/ayesha-khan?trk=public_jobs">Message</a>
  </div>
</section>
"""


def test_parses_description_and_collapses_whitespace():
    details = parse_job_details(DETAIL_PAGE)
    assert details["description"].startswith("We are hiring a Data Analyst.")
    assert "  " not in details["description"]


def test_parses_all_four_criteria():
    details = parse_job_details(DETAIL_PAGE)
    assert details["seniority"] == "Entry level"
    assert details["employment_type"] == "Full-time"
    assert details["job_function"] == "Analyst"
    assert details["industries"] == "IT Services"


def test_parses_applicant_count():
    assert parse_job_details(DETAIL_PAGE)["applicants"] == "Over 200 applicants"


def test_extracts_commented_out_apply_url_and_unescapes_it():
    assert (
        parse_job_details(DETAIL_PAGE)["apply_url"]
        == "https://careers.acme.example/apply?id=7&src=li"
    )


def test_extracts_poster_name_title_and_profile():
    details = parse_job_details(DETAIL_PAGE)
    assert details["poster_name"] == "Ayesha Khan"
    assert details["poster_title"] == "Talent Acquisition Lead"
    assert details["poster_profile"] == "https://www.linkedin.com/in/ayesha-khan"


def test_missing_sections_are_simply_absent():
    details = parse_job_details("<div class='description__text'>Just a description.</div>")
    assert details["description"] == "Just a description."
    assert "seniority" not in details
    assert "apply_url" not in details
    assert "poster_name" not in details


def test_blank_input_yields_no_details():
    assert parse_job_details("") == {}
    assert parse_job_details("   ") == {}


def test_long_descriptions_are_trimmed_for_the_card():
    html = f"<div class='description__text'>{'word ' * 500}</div>"
    description = parse_job_details(html)["description"]
    assert len(description) <= 601
    assert description.endswith("…")
