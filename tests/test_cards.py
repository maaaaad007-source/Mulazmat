from mulazmat.cards import render_card, render_cards
from mulazmat.models import Job

FULL = Job(
    job_id="1",
    title="Data Analyst",
    company="Acme",
    location="Lahore, Pakistan",
    url="https://www.linkedin.com/jobs/view/1",
    posted_label="2 days ago",
    salary="PKR 300,000/mo",
    company_url="https://www.linkedin.com/company/acme",
    description="Own reporting and dashboards. " * 20,
    seniority="Entry level",
    employment_type="Full-time",
    applicants="42 applicants",
    apply_url="https://careers.acme.example/jobs/1",
    poster_name="Ayesha Khan",
    poster_title="Talent Lead",
    poster_profile="https://www.linkedin.com/in/ayesha",
    enriched=True,
)

BARE = Job(
    job_id="2",
    title="Data Analyst",
    company="Globex",
    location="Remote",
    url="https://www.linkedin.com/jobs/view/2",
)


def test_card_shows_the_core_fields():
    html = render_card(FULL)
    assert "Data Analyst" in html
    assert "Acme" in html
    assert "Lahore, Pakistan" in html
    assert "2 days ago" in html
    assert "PKR 300,000/mo" in html
    assert "42 applicants" in html


def test_card_contact_block_links_apply_company_and_poster():
    html = render_card(FULL)
    assert "Contact &amp; apply" in html
    # Apply points at the external careers page, not the LinkedIn mirror.
    assert 'href="https://careers.acme.example/jobs/1"' in html
    assert 'href="https://www.linkedin.com/company/acme"' in html
    assert 'href="https://www.linkedin.com/in/ayesha"' in html
    assert "Posted by Ayesha Khan · Talent Lead" in html
    # The LinkedIn posting stays reachable when apply goes elsewhere.
    assert "On LinkedIn" in html


def test_card_falls_back_to_the_linkedin_url_when_there_is_no_apply_url():
    html = render_card(BARE)
    assert 'href="https://www.linkedin.com/jobs/view/2"' in html
    assert "On LinkedIn" not in html  # would duplicate the Apply link


def test_card_says_so_when_there_is_nothing_to_link():
    html = render_card(Job(job_id="3", title="Analyst", company="X", location="Y", url=""))
    assert "No public contact links on this posting." in html


def test_title_is_a_plain_heading_link_not_a_pill_button():
    html = render_card(FULL)
    heading = html.split("</h3>")[0]
    assert "mz-link" not in heading, "the title must not pick up button styling"
    assert 'href="https://www.linkedin.com/jobs/view/1"' in heading


def test_badges_only_render_when_present():
    assert "Full-time" in render_card(FULL)
    assert "mz-badge" not in render_card(BARE)


def test_untrusted_text_is_escaped():
    nasty = Job(
        job_id="4",
        title="<script>alert('xss')</script>",
        company='Evil" onmouseover="alert(1)',
        location="Nowhere",
        url="https://www.linkedin.com/jobs/view/4",
    )
    html = render_card(nasty)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'onmouseover="alert(1)"' not in html


def test_grid_includes_styles_and_one_article_per_job():
    html = render_cards([FULL, BARE])
    assert "<style>" in html
    assert 'class="mz-grid"' in html
    assert html.count("<article") == 2


def test_empty_result_set_still_produces_valid_markup():
    html = render_cards([])
    assert 'class="mz-grid"' in html
    assert "<article" not in html
