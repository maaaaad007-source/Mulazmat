"""Email drafts, written per posting.

Every card can produce an email addressed to whoever is behind that specific
posting — the named poster when the job page gave us one, the company's hiring
team when it did not. The text is assembled from two sides: what the posting
says (role, company, location, workplace, when it went up, what it asks for)
and what you told the app about yourself once, under **Filters → Your details**.

Two honest limits, both structural:

* **LinkedIn publishes no email addresses.** Not on a search card, not on a
  guest job page. So the draft is written for you, and the "To" box is yours to
  fill in — from the company's careers page, the posting itself, or a reply on
  LinkedIn. Nothing here guesses ``first.last@company.com``.
* **Your own profile is not read either.** ``linkedin.com/in/...`` is behind a
  sign-in wall for anything automated, so the details used to tailor a draft are
  the ones you type into the panel. The profile URL is carried through to the
  signature so the reader can go and look.

Everything in this module is pure text: no Streamlit, no network. The widgets
live in :mod:`firststapp.cards`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from .models import Job

#: Seeded into the details panel so the signature has something real in it from
#: the first draft. Overwrite it in the UI like any other field.
DEFAULT_PROFILE = "https://www.linkedin.com/in/sunduslive"

#: Draft registers. Order matters — the first is the default.
TONES = ("Professional", "Warm", "Short")

#: The one thing the app will not write for you. A sentence about why *this*
#: employer is the part a recruiter can tell was generated, so it is left
#: visibly blank rather than filled with something bland.
PITCH_PLACEHOLDER = "[One or two sentences on why this company in particular.]"

#: How many skills a draft will name before it starts sounding like a CV dump.
MAX_SKILLS = 4

_SKILL_SPLIT = re.compile(r"[,;\n]+")

_SIGNOFF = {"Professional": "Kind regards,", "Warm": "Best wishes,", "Short": "Thanks,"}


def parse_skills(text: str) -> tuple[str, ...]:
    """Split a free-text skills box into individual skills.

    Commas, semicolons and newlines all separate; slashes do not, so "CI/CD"
    survives. Duplicates are dropped case-insensitively, first spelling wins.
    """
    seen: dict[str, str] = {}
    for chunk in _SKILL_SPLIT.split(text or ""):
        skill = chunk.strip(" \t.-")
        if skill and skill.lower() not in seen:
            seen[skill.lower()] = skill
    return tuple(seen.values())


def join_list(items: Sequence[str]) -> str:
    """``["a", "b", "c"]`` → ``"a, b and c"``."""
    values = [item for item in items if item]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + " and " + values[-1]


@dataclass(frozen=True)
class Sender:
    """You — the details a draft is written from.

    Held as a value object so a draft can be regenerated whenever any of it
    changes, and so the text functions stay testable without Streamlit.
    """

    name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    profile_url: str = DEFAULT_PROFILE
    skills: tuple[str, ...] = ()
    pitch: str = ""

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> "Sender":
        """Read the ``me_*`` keys the details panel writes."""

        def text(key: str) -> str:
            return str(state.get(key) or "").strip()

        return cls(
            name=text("me_name"),
            headline=text("me_headline"),
            email=text("me_email"),
            phone=text("me_phone"),
            location=text("me_location"),
            profile_url=text("me_profile") or DEFAULT_PROFILE,
            skills=parse_skills(text("me_skills")),
            pitch=text("me_pitch"),
        )

    def fingerprint(self) -> tuple[Any, ...]:
        """Identity of the details, so an edit can re-write open drafts."""
        return (
            self.name,
            self.headline,
            self.email,
            self.phone,
            self.location,
            self.profile_url,
            self.skills,
            self.pitch,
        )

    @property
    def is_usable(self) -> bool:
        """Enough filled in that a draft does not read as a form letter."""
        return bool(self.name and (self.email or self.phone))


def first_name(full_name: str) -> str:
    """"Sofie de Vries" → "Sofie". Falls back to the whole name.

    A one-character token is an initial rather than a name, and "Dear S," is
    worse than the full string.
    """
    token = (full_name or "").strip().split(" ")[0].strip(".,")
    return token if len(token) > 1 else (full_name or "").strip()


def greeting(job: Job, tone: str = "Professional") -> str:
    """Address the person if the posting named one, the team if it did not."""
    warm = tone in {"Warm", "Short"}
    if job.poster_name:
        who = first_name(job.poster_name)
        return f"Hi {who}," if warm else f"Dear {who},"
    if job.company:
        return f"Hi {job.company} team," if warm else f"Dear {job.company} Hiring Team,"
    return "Hi there," if warm else "Dear Hiring Manager,"


def matched_skills(job: Job, skills: Sequence[str], limit: int = MAX_SKILLS) -> list[str]:
    """Your skills that this posting actually mentions.

    A plain substring match against the title and description. It is deliberately
    dumb: naming a skill the posting never asked for is the thing that makes a
    letter read as mass-produced, so the bar is "the words are in the posting".
    """
    haystack = f"{job.title} {job.description}".lower()
    return [skill for skill in skills if skill and skill.lower() in haystack][:limit]


def _where(job: Job) -> str:
    location = (job.location or "").strip()
    # "the role in Remote" is nonsense, and repeating the company is noise.
    if not location or location.lower() in {"remote", "hybrid", (job.company or "").lower()}:
        return ""
    return f" in {location}"


def _opening(job: Job, tone: str) -> str:
    # A posting with no title still has to make a sentence — "the the role
    # position" is what naive interpolation gives you.
    role = f"the {job.title} role" if job.title else "this role"
    at = f" at {job.company}" if job.company else ""
    when = f" {job.posted_label}" if job.posted_label else ""

    if tone == "Warm":
        return (
            f"I came across {role}{at}{_where(job)} on LinkedIn{when}, "
            "and I would very much like to be considered for it."
        )
    if tone == "Short":
        return f"I would like to apply for {role}{at}, which I saw on LinkedIn{when}."
    return (
        f"I am writing to apply for {role}{at}{_where(job)}, advertised on LinkedIn{when}."
    )


def _fit(job: Job, sender: Sender) -> str:
    """The paragraph that ties your background to this specific posting."""
    parts: list[str] = []

    matched = matched_skills(job, sender.skills)
    if matched:
        parts.append(
            f"The posting calls for {join_list(matched)}, which is where most of my work has been."
        )
    elif sender.skills:
        parts.append(f"My background is in {join_list(list(sender.skills)[:MAX_SKILLS])}.")

    workplace = job.workplace_label
    if sender.location and workplace == "Remote":
        parts.append(f"I am based in {sender.location} and set up to work remotely.")
    elif sender.location and workplace:
        parts.append(f"I am based in {sender.location}.")

    return " ".join(parts)


def _closing(sender: Sender, tone: str) -> str:
    profile = f" My full background is on LinkedIn: {sender.profile_url}." if sender.profile_url else ""
    if tone == "Short":
        return f"My CV is attached.{profile}".strip()
    if tone == "Warm":
        return (
            f"I have attached my CV.{profile} "
            "I would love to talk it through if you think there is a fit."
        )
    return (
        f"I have attached my CV.{profile} "
        "I would welcome the chance to discuss the role at your convenience."
    )


def signature(sender: Sender, tone: str = "Professional") -> str:
    lines = [_SIGNOFF.get(tone, _SIGNOFF["Professional"]), sender.name or "[Your name]"]
    if tone != "Short" and sender.headline:
        lines.append(sender.headline)
    contact = " · ".join(value for value in (sender.email, sender.phone) if value)
    if contact:
        lines.append(contact)
    if sender.profile_url:
        lines.append(sender.profile_url)
    return "\n".join(lines)


def subject(job: Job, sender: Sender) -> str:
    """What lands in the recipient's inbox list — role first, then who."""
    role = job.title.strip() if job.title else ""
    line = f"Application: {role}" if role else "Job application"
    if job.company and role:
        line += f" at {job.company}"
    if sender.name:
        line += f" — {sender.name}"
    return line


def body(job: Job, sender: Sender, tone: str = "Professional") -> str:
    """The draft itself: paragraphs, blank-line separated, ready to send."""
    if tone not in TONES:
        tone = TONES[0]

    paragraphs = [greeting(job, tone), _opening(job, tone)]

    if tone != "Short":
        paragraphs.append(sender.pitch or PITCH_PLACEHOLDER)

    paragraphs.append(_fit(job, sender))
    paragraphs.append(_closing(sender, tone))

    if tone == "Professional":
        paragraphs.append("Thank you for your time and consideration.")
    if tone != "Short" and job.url:
        # A reference line: employers often run several openings at once.
        paragraphs.append(f"Posting: {job.url}")

    paragraphs.append(signature(sender, tone))
    return "\n\n".join(part for part in paragraphs if part)


def mailto_url(to: str, subject_line: str, message: str) -> str:
    """A ``mailto:`` the browser can hand to the default mail client.

    An empty ``to`` is fine and normal here — LinkedIn gives us no address, so
    the link opens a compose window with everything but the recipient filled in.
    """
    address = quote((to or "").strip(), safe="@;,")
    query = f"subject={quote(subject_line or '')}&body={quote(message or '')}"
    return f"mailto:{address}?{query}"
