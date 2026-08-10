from mulazmat.cards import (
    card_html,
    contact_html,
    logo_html,
    meta_items,
    meta_row_html,
    title_html,
)
from mulazmat.models import Job

FULL = Job(
    job_id="1",
    title="Senior UX Designer",
    company="Booking.com",
    location="Amsterdam, Netherlands",
    url="https://www.linkedin.com/jobs/view/1",
    posted_label="1 week ago",
    salary="€90,000/yr",
    company_url="https://www.linkedin.com/company/booking",
    description="Design end-to-end flows. " * 20,
    workplace="Remote",
    employment_type="Full-time",
    applicants="42 applicants",
    apply_url="https://careers.booking.example/jobs/1",
    poster_name="Ayesha Khan",
    poster_title="Talent Lead",
    poster_profile="https://www.linkedin.com/in/ayesha",
    enriched=True,
)

BARE = Job(
    job_id="2",
    title="Senior UX Designer",
    company="Globex",
    location="Amsterdam, Netherlands",
    url="https://www.linkedin.com/jobs/view/2",
)


def test_title_block_has_title_company_and_location():
    html = title_html(FULL)
    assert "Senior UX Designer" in html
    assert "Booking.com" in html
    assert "Amsterdam, Netherlands" in html
    assert 'href="https://www.linkedin.com/jobs/view/1"' in html
    assert "mz-card-link" not in html, "the title must not look like a button"


def test_logo_renders_when_the_card_carried_one():
    job = Job(
        job_id="9", title="T", company="Acme", location="Berlin", url="",
        logo_url="https://media.licdn.com/dms/image/acme.png",
    )
    html = logo_html(job)
    assert 'src="https://media.licdn.com/dms/image/acme.png"' in html
    assert 'alt="Acme logo"' in html


def test_logo_falls_back_to_the_company_initial():
    job = Job(job_id="9", title="T", company="ordnary", location="Berlin", url="")
    assert "mz-logo-fallback" in logo_html(job)
    assert ">O<" in logo_html(job)


def test_logo_url_is_escaped():
    job = Job(
        job_id="9", title="T", company="Acme", location="B", url="",
        logo_url='https://x/y.png" onerror="alert(1)',
    )
    assert 'onerror="alert(1)"' not in logo_html(job)


def test_title_block_puts_the_logo_beside_the_text():
    html = title_html(FULL)
    assert "mz-head" in html and "mz-logo-box" in html
    assert html.index("mz-logo-box") < html.index("mz-title")


def test_meta_strip_is_workplace_type_and_age():
    assert meta_items(FULL) == ["Remote", "Full-time", "1 week ago"]
    assert "mz-meta" in meta_row_html(FULL)


def test_meta_strip_omits_facts_we_do_not_have():
    # No workplace, no employment type, no date — nothing to show.
    assert meta_items(BARE) == []
    assert meta_row_html(BARE) == ""


def test_workplace_is_inferred_from_the_location_only_when_stated():
    assert Job(job_id="3", title="T", company="C", location="Remote", url="").workplace_label == (
        "Remote"
    )
    assert Job(
        job_id="4", title="T", company="C", location="Hybrid - Berlin", url=""
    ).workplace_label == "Hybrid"
    # Never guessed: a plain city stays blank rather than claiming "On-site".
    assert Job(job_id="5", title="T", company="C", location="Berlin", url="").workplace_label == ""


def test_contact_block_links_apply_company_and_poster():
    html = contact_html(FULL)
    assert "Contact &amp; apply" in html
    assert 'href="https://careers.booking.example/jobs/1"' in html
    assert 'href="https://www.linkedin.com/company/booking"' in html
    assert 'href="https://www.linkedin.com/in/ayesha"' in html
    assert "Posted by Ayesha Khan · Talent Lead" in html
    assert "On LinkedIn" in html


def test_contact_block_falls_back_to_the_linkedin_url():
    html = contact_html(BARE)
    assert 'href="https://www.linkedin.com/jobs/view/2"' in html
    assert "On LinkedIn" not in html  # would duplicate the Apply link


def test_contact_block_says_so_when_there_is_nothing_to_link():
    bare = Job(job_id="6", title="Analyst", company="X", location="Y", url="")
    assert "No public contact links on this posting." in contact_html(bare)


def test_untrusted_text_is_escaped():
    nasty = Job(
        job_id="7",
        title="<script>alert('xss')</script>",
        company='Evil" onmouseover="alert(1)',
        location="Nowhere",
        url="https://www.linkedin.com/jobs/view/7",
    )
    html = card_html(nasty)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'onmouseover="alert(1)"' not in html


def test_card_html_assembles_every_section():
    html = card_html(FULL)
    assert "mz-title" in html
    assert "mz-meta" in html
    assert "mz-contact-label" in html


def test_description_shows_when_the_posting_has_one():
    # Only enriched jobs carry a description, so in practice this is what
    # "Fetch full details" adds to a card.
    assert "mz-desc" in card_html(FULL)
    assert "mz-desc" not in card_html(FULL, description=False)


def test_unenriched_cards_have_no_description_block():
    assert "mz-desc" not in card_html(BARE)
