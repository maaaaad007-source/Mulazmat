"""The per-posting email drafts.

Pure text in, pure text out — no Streamlit and no network here, so these are
about the writing: who it is addressed to, what of the posting it picks up, and
what it refuses to invent.
"""

from urllib.parse import unquote

import pytest

from mulazmat import email_draft as ed
from mulazmat.email_draft import Sender
from mulazmat.models import Job


def job(**overrides) -> Job:
    fields = dict(
        job_id="4011",
        title="Senior UX Designer",
        company="Northwind Studio",
        location="Amsterdam, Netherlands",
        url="https://www.linkedin.com/jobs/view/4011",
        posted_label="3 days ago",
    )
    fields.update(overrides)
    return Job(**fields)


SUNDUS = Sender(
    name="Sundus",
    headline="Product Designer",
    email="sundus@example.com",
    phone="+31 6 000 000",
    location="Lahore",
    skills=("Figma", "user research", "Kubernetes"),
    pitch="I have spent six years turning research into shipped product.",
)


# --- who it is addressed to ------------------------------------------------


def test_a_named_poster_is_greeted_by_first_name():
    posting = job(poster_name="Sofie de Vries")
    assert ed.greeting(posting) == "Dear Sofie,"
    assert ed.greeting(posting, "Warm") == "Hi Sofie,"


def test_an_initial_is_not_mistaken_for_a_first_name():
    assert ed.greeting(job(poster_name="S. de Vries")) == "Dear S. de Vries,"


def test_without_a_poster_the_company_team_is_addressed():
    assert ed.greeting(job()) == "Dear Northwind Studio Hiring Team,"


def test_without_a_company_either_it_falls_back_to_hiring_manager():
    assert ed.greeting(job(company="")) == "Dear Hiring Manager,"


# --- what it picks up from the posting -------------------------------------


def test_the_body_names_the_role_company_and_when_it_was_posted():
    text = ed.body(job(), SUNDUS)
    assert "Senior UX Designer" in text
    assert "Northwind Studio" in text
    assert "Amsterdam, Netherlands" in text
    assert "advertised on LinkedIn 3 days ago" in text


def test_the_posting_url_is_carried_as_a_reference():
    assert "Posting: https://www.linkedin.com/jobs/view/4011" in ed.body(job(), SUNDUS)


def test_a_remote_role_is_answered_with_where_you_are():
    text = ed.body(job(title="UX Designer (Remote)"), SUNDUS)
    assert "I am based in Lahore and set up to work remotely." in text


def test_a_location_that_only_says_remote_is_not_used_as_a_place():
    # "the role in Remote" is nonsense; the workplace line covers it instead.
    text = ed.body(job(location="Remote"), SUNDUS)
    assert " in Remote" not in text


def test_missing_fields_leave_no_holes_in_the_sentence():
    bare = Job(job_id="1", title="", company="", location="", url="")
    text = ed.body(bare, Sender())

    assert "None" not in text
    assert " ," not in text and " ." not in text
    # Every empty field would otherwise show up as a doubled space, and an
    # untitled posting as "the the role position".
    for paragraph in text.split("\n"):
        assert "  " not in paragraph, paragraph
    assert "I am writing to apply for this role, advertised on LinkedIn." in text


# --- the skills match ------------------------------------------------------


def test_only_skills_the_posting_mentions_are_named():
    posting = job(description="You will run user research and live in Figma all day.")
    assert ed.matched_skills(posting, SUNDUS.skills) == ["Figma", "user research"]

    text = ed.body(posting, SUNDUS)
    assert "The posting calls for Figma and user research" in text
    # Kubernetes is on the CV but not in the posting, so it stays off the letter.
    assert "Kubernetes" not in text


def test_with_no_overlap_the_skills_are_still_stated_plainly():
    text = ed.body(job(description="Nothing in common here."), SUNDUS)
    assert "My background is in Figma, user research and Kubernetes." in text


def test_the_skill_list_is_capped():
    many = Sender(skills=tuple(f"skill{n}" for n in range(10)))
    posting = job(description=" ".join(f"skill{n}" for n in range(10)))
    assert len(ed.matched_skills(posting, many.skills)) == ed.MAX_SKILLS


def test_skills_are_parsed_off_commas_semicolons_and_newlines():
    assert ed.parse_skills("Figma, SQL; CI/CD\n user research ") == (
        "Figma",
        "SQL",
        "CI/CD",  # a slash is part of the skill, not a separator
        "user research",
    )


def test_duplicate_skills_collapse_case_insensitively():
    assert ed.parse_skills("Figma, figma, FIGMA") == ("Figma",)


# --- what it will not write for you ----------------------------------------


def test_the_why_this_company_line_is_left_visibly_blank():
    text = ed.body(job(), Sender(name="Sundus"))
    assert ed.PITCH_PLACEHOLDER in text


def test_a_supplied_pitch_replaces_the_placeholder():
    text = ed.body(job(), SUNDUS)
    assert ed.PITCH_PLACEHOLDER not in text
    assert SUNDUS.pitch in text


def test_no_email_address_is_ever_invented_for_the_recipient():
    # LinkedIn publishes none, so a draft must not contain a guessed address.
    text = ed.body(job(poster_name="Sofie de Vries"), SUNDUS)
    assert "@northwind" not in text.lower()
    # The only address in the letter is the sender's own.
    assert [word for word in text.split() if "@" in word] == ["sundus@example.com"]


def test_the_mailto_leaves_the_recipient_empty_when_we_have_none():
    url = ed.mailto_url("", "Subject line", "Hello")
    assert url.startswith("mailto:?")


# --- signature and subject -------------------------------------------------


def test_the_signature_carries_the_profile_and_contact_details():
    text = ed.body(job(), SUNDUS)
    assert text.rstrip().endswith(ed.DEFAULT_PROFILE)
    assert "sundus@example.com · +31 6 000 000" in text
    assert "Kind regards,\nSundus\nProduct Designer" in text


def test_the_profile_defaults_to_the_owners_and_can_be_replaced():
    assert Sender().profile_url == ed.DEFAULT_PROFILE
    mine = Sender(profile_url="https://www.linkedin.com/in/someone-else")
    assert ed.DEFAULT_PROFILE not in ed.body(job(), mine)


def test_an_unfilled_signature_says_so_rather_than_signing_off_blank():
    assert "[Your name]" in ed.body(job(), Sender())


def test_the_subject_leads_with_the_role():
    assert ed.subject(job(), SUNDUS) == (
        "Application: Senior UX Designer at Northwind Studio — Sundus"
    )


def test_the_subject_survives_a_posting_with_no_title():
    assert ed.subject(job(title=""), Sender()) == "Job application"


# --- tone ------------------------------------------------------------------


@pytest.mark.parametrize("tone", ed.TONES)
def test_every_tone_produces_a_usable_letter(tone):
    text = ed.body(job(), SUNDUS, tone)
    assert text.startswith(("Dear", "Hi"))
    assert "Senior UX Designer" in text
    assert "Sundus" in text


def test_the_tones_actually_differ():
    drafts = {ed.body(job(), SUNDUS, tone) for tone in ed.TONES}
    assert len(drafts) == len(ed.TONES)


def test_short_really_is_short():
    short = ed.body(job(), SUNDUS, "Short")
    full = ed.body(job(), SUNDUS, "Professional")

    # Fewer paragraphs, not merely fewer words: Short drops the pitch, the
    # reference line and the thank-you.
    assert short.count("\n\n") < full.count("\n\n")
    assert len(short) < len(full)
    assert ed.PITCH_PLACEHOLDER not in short
    assert "Posting:" not in short


def test_an_unknown_tone_falls_back_to_the_default():
    assert ed.body(job(), SUNDUS, "Interpretive Dance") == ed.body(job(), SUNDUS, "Professional")


# --- the mailto link -------------------------------------------------------


def test_the_mailto_round_trips_subject_and_body():
    text = ed.body(job(), SUNDUS)
    url = ed.mailto_url("hiring@northwind.example", ed.subject(job(), SUNDUS), text)

    assert url.startswith("mailto:hiring@northwind.example?")
    query = url.split("?", 1)[1]
    encoded_subject, encoded_body = (part.split("=", 1)[1] for part in query.split("&"))
    assert unquote(encoded_subject) == ed.subject(job(), SUNDUS)
    assert unquote(encoded_body) == text


def test_the_mailto_encodes_the_characters_that_would_break_it():
    url = ed.mailto_url("", "A & B", "line one\nline two?yes")
    assert "&" not in url.split("subject=", 1)[1].split("&body=")[0]
    assert "\n" not in url


# --- reading your details out of session state -----------------------------


def test_sender_reads_the_details_panel():
    sender = Sender.from_state(
        {
            "me_name": "  Sundus  ",
            "me_headline": "Product Designer",
            "me_email": "sundus@example.com",
            "me_skills": "Figma, SQL",
            "me_profile": "",
        }
    )
    assert sender.name == "Sundus"
    assert sender.skills == ("Figma", "SQL")
    # A blank profile box falls back rather than signing off with nothing.
    assert sender.profile_url == ed.DEFAULT_PROFILE


def test_a_draft_is_rewritten_when_the_details_change():
    before = Sender(name="Sundus").fingerprint()
    after = Sender(name="Sundus", email="sundus@example.com").fingerprint()
    assert before != after


def test_details_are_usable_only_once_there_is_a_way_to_reply():
    assert not Sender(name="Sundus").is_usable
    assert Sender(name="Sundus", email="sundus@example.com").is_usable
