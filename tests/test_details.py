from firststapp.linkedin import parse_job_details

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


JSON_LD_REMOTE = """
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","title":"Product Designer",
 "employmentType":"FULL_TIME","jobLocationType":"TELECOMMUTE",
 "hiringOrganization":{"@type":"Organization","name":"Ordnary"}}
</script>
<div class="description__text">Design products people use daily.</div>
"""

JSON_LD_ONSITE = """
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","employmentType":"PART_TIME"}
</script>
"""


def test_remote_postings_are_detected_from_json_ld():
    # The visible criteria list has no workplace row; TELECOMMUTE is the only
    # place a posting actually says it is remote.
    details = parse_job_details(JSON_LD_REMOTE)
    assert details["workplace"] == "Remote"
    assert details["employment_type"] == "Full-time"
    assert details["description"] == "Design products people use daily."


def test_json_ld_without_telecommute_claims_no_workplace():
    details = parse_job_details(JSON_LD_ONSITE)
    assert "workplace" not in details
    assert details["employment_type"] == "Part-time"


def test_the_visible_criteria_list_wins_over_json_ld():
    details = parse_job_details(JSON_LD_ONSITE + DETAIL_PAGE)
    assert details["employment_type"] == "Full-time"


def test_malformed_json_ld_is_skipped_rather_than_raising():
    html = '<script type="application/ld+json">{not json at all</script>' + DETAIL_PAGE
    assert parse_job_details(html)["seniority"] == "Entry level"


def test_json_ld_arrays_are_handled():
    html = """
    <script type="application/ld+json">
    [{"@type":"WebSite"},{"@type":"JobPosting","jobLocationType":"TELECOMMUTE",
      "employmentType":["CONTRACTOR"]}]
    </script>
    """
    details = parse_job_details(html)
    assert details["workplace"] == "Remote"
    assert details["employment_type"] == "Contract"


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


def test_descriptions_keep_enough_text_for_the_expander():
    # Cards show a short snippet, but "Read full description" needs the whole
    # posting, so the stored text is only capped well beyond a card's worth.
    html = f"<div class='description__text'>{'word ' * 500}</div>"
    description = parse_job_details(html)["description"]
    assert 2000 < len(description) <= 6001


def test_absurdly_long_descriptions_are_still_capped():
    html = f"<div class='description__text'>{'word ' * 4000}</div>"
    description = parse_job_details(html)["description"]
    assert len(description) <= 6001
    assert description.endswith("…")


def test_linkedin_expander_labels_are_stripped_from_the_text():
    html = """
    <div class="description__text"><section class="show-more-less-html">
      <div class="show-more-less-html__markup">We build tools for teams.</div>
      <button class="show-more-less-html__button">Show more</button>
      <button class="show-more-less-html__button">Show less</button>
    </section></div>
    """
    assert parse_job_details(html)["description"] == "We build tools for teams."


HIRER_MODERN = """
<div class="job-details-jobs-unified-top-card__hiring-team">
  <a href="https://www.linkedin.com/in/lotte-jansen?trk=public_jobs">Lotte Jansen</a>
  <div class="hirer-card__hirer-headline">Recruiter at Sequel</div>
</div>
"""

HIRER_LINK_ONLY = """
<div class="hirer-card">
  <a href="https://www.linkedin.com/in/sam-okafor">Sam Okafor</a>
</div>
"""


def test_hiring_contact_is_read_from_the_modern_layout():
    details = parse_job_details(HIRER_MODERN)
    assert details["poster_name"] == "Lotte Jansen"
    assert details["poster_profile"] == "https://www.linkedin.com/in/lotte-jansen"


def test_hiring_contact_falls_back_to_the_profile_links_own_text():
    details = parse_job_details(HIRER_LINK_ONLY)
    assert details["poster_name"] == "Sam Okafor"
    assert details["poster_profile"] == "https://www.linkedin.com/in/sam-okafor"
    assert "poster_title" not in details


def test_no_hiring_block_means_no_contact_person():
    assert "poster_name" not in parse_job_details(JSON_LD_REMOTE)


def test_the_headline_is_not_repeated_as_the_name():
    html = '<div class="hirer-card"><h3>Ada Lovelace</h3><h4>Ada Lovelace</h4></div>'
    details = parse_job_details(html)
    assert details["poster_name"] == "Ada Lovelace"
    assert "poster_title" not in details
