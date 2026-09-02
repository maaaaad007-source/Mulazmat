"""Result cards.

The markup-producing helpers are kept pure so they can be unit tested; only
:func:`render_grid` touches Streamlit.

Everything that came from LinkedIn is escaped before it reaches the page — job
titles and company names are third-party text and must never be trusted as
markup.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from . import email_draft
from .email_draft import Sender
from .models import Job

#: Logo edge length, in px. Mirrored in the stylesheet and pinned on the <img>
#: itself so a large source image can never blow out the card.
LOGO_PX = 56

#: How much description a card shows before the expander takes over.
SNIPPET_CHARS = 200


def _anchor(url: str, label: str, css: str = "") -> str:
    klass = f'class="{css}" ' if css else ""
    return (
        f'<a {klass}href="{escape(url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{escape(label)}</a>'
    )


def logo_html(job: Job) -> str:
    """Company logo, falling back to the company's initial.

    The URL comes off the search card itself, so showing it costs no extra
    request. A monogram stands in when a company has no logo, which keeps every
    card the same shape.
    """
    if job.logo_url:
        # Size is pinned on the element itself — width/height attributes plus an
        # inline style — not only in the stylesheet. Logos arrive at whatever
        # resolution the company uploaded, and if the class-based rules do not
        # reach the image it renders at full size and swallows the card.
        return (
            f'<img class="mz-logo-img" src="{escape(job.logo_url, quote=True)}" '
            f'alt="{escape(job.company)} logo" loading="lazy" '
            f'width="{LOGO_PX}" height="{LOGO_PX}" '
            f'style="width:{LOGO_PX}px;height:{LOGO_PX}px;object-fit:contain;flex:none" '
            f'onerror="this.style.display=\'none\'">'
        )
    return f'<span class="mz-logo-fallback">{escape(job.initial)}</span>'


def title_html(job: Job) -> str:
    """Logo, job title, company and location — the top third of a card."""
    label = job.title or "Untitled role"
    heading = _anchor(job.url, label) if job.url else escape(label)

    text = [f'<p class="mz-title">{heading}</p>']
    if job.company:
        company = _anchor(job.company_url, job.company) if job.company_url else escape(job.company)
        text.append(f'<p class="mz-sub">{company}</p>')
    if job.location:
        text.append(f'<p class="mz-sub mz-sub--muted">{escape(job.location)}</p>')

    return (
        f'<div class="mz-head">'
        f'<div class="mz-logo-box">{logo_html(job)}</div>'
        f'<div class="mz-head-text">{"".join(text)}</div>'
        f"</div>"
    )


def meta_items(job: Job) -> list[str]:
    """The workplace / job-type / posted strip.

    Only facts we actually have — a posting that does not tell us its
    employment type simply gets a shorter strip rather than a guessed one.
    """
    values = (job.workplace_label, job.employment_type, job.posted_label)
    return [value for value in values if value]


def meta_row_html(job: Job) -> str:
    items = meta_items(job)
    if not items:
        return ""
    # Spreading a lone value across the full width just looks like a mistake,
    # so a single-item strip stays left-aligned.
    css = "mz-meta" if len(items) > 1 else "mz-meta mz-meta--single"
    cells = "".join(f"<span>{escape(item)}</span>" for item in items)
    return f'<div class="{css}">{cells}</div>'


def contact_html(job: Job) -> str:
    """The "Contact & apply" footer.

    Only ever contains links LinkedIn publishes: the apply target, the company
    page, and — when the posting names one — the poster's public profile. There
    are no email addresses or phone numbers in LinkedIn's job data, so there are
    none here either.
    """
    parts = ['<p class="mz-contact-label">Contact &amp; apply</p>']

    if job.poster_name:
        who = escape(job.poster_name)
        if job.poster_title:
            who += f" · {escape(job.poster_title)}"
        parts.append(f'<p class="mz-poster">Posted by {who}</p>')

    links: list[str] = []
    if job.best_apply_url:
        links.append(_anchor(job.best_apply_url, "Apply", "mz-card-link"))
    if job.company_url:
        links.append(_anchor(job.company_url, "Company page", "mz-card-link"))
    if job.poster_profile:
        links.append(_anchor(job.poster_profile, "Profile", "mz-card-link"))
    if job.url and job.apply_url:
        # Apply went to an external site — keep the LinkedIn posting reachable.
        links.append(_anchor(job.url, "On LinkedIn", "mz-card-link"))

    if links:
        parts.append(f'<div class="mz-links">{"".join(links)}</div>')
    else:
        parts.append('<p class="mz-none">No public contact links on this posting.</p>')

    return "".join(parts)


def upper_html(job: Job, description: bool = True, expanded: bool = False) -> str:
    """Everything above the toggle: logo, title, meta strip, description.

    ``expanded`` swaps the snippet for the whole posting in place, rather than
    repeating the snippet with the full text underneath it.
    """
    body = [title_html(job), meta_row_html(job)]
    if description and job.description:
        text = job.description.strip() if expanded else snippet(job)
        css = "mz-desc mz-desc--full" if expanded else "mz-desc"
        body.append(f'<p class="{css}">{escape(text)}</p>')
    return "".join(body)


def card_html(job: Job, description: bool = True) -> str:
    """The whole card except the widgets (save button, description expander).

    The description only exists on jobs that went through detail enrichment, so
    in practice it appears exactly when "Fetch full details" is on.
    """
    return upper_html(job, description) + contact_html(job)


def snippet(job: Job) -> str:
    """The short description shown before the card is expanded."""
    text = job.description.strip()
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"


def has_more(job: Job) -> bool:
    """True when the posting has more description than the card is showing."""
    return len(job.description.strip()) > SNIPPET_CHARS


def _toggle_expanded(job_id: str) -> None:
    """Flip a card between snippet and full description.

    Runs as a button callback so the change lands before the script re-runs —
    toggling inside the run would leave the description already rendered from
    the previous state.
    """
    expanded: set[str] = st.session_state.setdefault("expanded", set())
    expanded.symmetric_difference_update({job_id})


def _toggle_email(job_id: str) -> None:
    """Open or close a card's email draft. A callback, for the same reason."""
    open_drafts: set[str] = st.session_state.setdefault("emailing", set())
    open_drafts.symmetric_difference_update({job_id})


def _regenerate(job_id: str) -> None:
    """Throw away hand edits and rewrite the draft from the current details."""
    st.session_state.pop(f"draft_{job_id}", None)


def _render_email_panel(job: Job, sender: Sender) -> None:
    """The draft editor, opened inside the card it belongs to.

    Subject and body are seeded into session state *before* the widgets are
    created, which is the only way to refill a keyed widget — a keyed text box
    ignores ``value=`` after its first render. They are only reseeded when the
    tone or your own details change, so hand edits survive a rerun.
    """
    job_id = job.job_id
    subject_key, body_key, stamp_key = f"subj_{job_id}", f"body_{job_id}", f"draft_{job_id}"

    # Its own container so the panel's spacing can be tightened without
    # disturbing the card around it — the gap lives on the vertical block, and
    # the card's own block is shared with the title, description and footer.
    with st.container(key=f"draftbox_{job_id}"):
        st.markdown('<p class="mz-draft-label">Email draft</p>', unsafe_allow_html=True)

        tone = st.radio(
            "Tone",
            list(email_draft.TONES),
            key=f"tone_{job_id}",
            horizontal=True,
            label_visibility="collapsed",
        )

        stamp = (tone, sender.fingerprint())
        if st.session_state.get(stamp_key) != stamp:
            st.session_state[stamp_key] = stamp
            st.session_state[subject_key] = email_draft.subject(job, sender)
            st.session_state[body_key] = email_draft.body(job, sender, tone)

        if not sender.is_usable:
            st.caption("Add your name and contact details under Filters → Your details.")

        # LinkedIn publishes no email address for a posting, so this is the one
        # field the app genuinely cannot fill in. Left empty, the mailto still
        # opens a compose window — just without a recipient.
        to = st.text_input(
            "To",
            key=f"to_{job_id}",
            placeholder="To — name@company.com (LinkedIn does not publish one)",
            label_visibility="collapsed",
        )
        st.text_input("Subject", key=subject_key, placeholder="Subject", label_visibility="collapsed")
        st.text_area("Message", key=body_key, height=300, label_visibility="collapsed")

        # Read back from state rather than from the return values, so the links
        # carry any edit made during this run.
        message = st.session_state.get(body_key, "")
        line = st.session_state.get(subject_key, "")

        st.link_button(
            "Open in email app",
            email_draft.mailto_url(to, line, message),
            key=f"mailto_{job_id}",
            width="stretch",
        )
        if job.poster_profile:
            # No address? The person who posted it is still reachable where they
            # posted it.
            st.link_button(
                "Message on LinkedIn",
                job.poster_profile,
                key=f"liprofile_{job_id}",
                width="stretch",
            )

        # Webmail ignores mailto:, so give that half of the world something to
        # copy — st.code brings its own copy button.
        with st.expander("Copy as plain text"):
            # wrap_lines, or a letter reads as one clipped line per paragraph.
            st.code(f"Subject: {line}\n\n{message}", language=None, wrap_lines=True)

        st.button(
            "Start over",
            key=f"regen_{job_id}",
            on_click=_regenerate,
            args=(job_id,),
            help="Rewrite this draft from the posting and your details, "
            "discarding any edits.",
        )


def render_grid(jobs: list[Job], saved: set[str], columns: int = 2) -> str | None:
    """Draw the cards two-up and return the id of any save button clicked.

    The save control has to be a real Streamlit button (HTML cannot call back
    into Python), so each card is a keyed container with the button floated into
    its top-right corner by CSS.
    """
    clicked: str | None = None
    expanded: set[str] = st.session_state.setdefault("expanded", set())
    emailing: set[str] = st.session_state.setdefault("emailing", set())
    sender = Sender.from_state(st.session_state)

    for row_start in range(0, len(jobs), columns):
        row = jobs[row_start : row_start + columns]
        for column, job in zip(st.columns(columns, gap="medium"), row):
            with column, st.container(border=True, key=f"card_{job.job_id or row_start}"):
                is_saved = job.job_id in saved
                if st.button(
                    "",
                    key=f"save_{job.job_id or row_start}",
                    icon=":material/bookmark:" if is_saved else ":material/bookmark_border:",
                    help="Remove from saved" if is_saved else "Save this job",
                    type="primary" if is_saved else "secondary",
                ):
                    clicked = job.job_id
                # Rendered in two halves so the toggle can sit with the
                # description rather than below the Apply buttons.
                is_open = job.job_id in expanded
                st.markdown(upper_html(job, expanded=is_open), unsafe_allow_html=True)

                # The whole posting in place, without a trip to LinkedIn. Only
                # offered when there is more than the snippet already shows.
                if has_more(job):
                    st.button(
                        "Show less" if is_open else "Read full description",
                        key=f"desc_{job.job_id or row_start}",
                        on_click=_toggle_expanded,
                        args=(job.job_id,),
                    )

                st.markdown(contact_html(job), unsafe_allow_html=True)

                # An email has to be written per posting, so the control lives
                # with the posting rather than anywhere central.
                drafting = job.job_id in emailing

                def _email_button() -> None:
                    st.button(
                        "Close draft" if drafting else "Write email",
                        key=f"email_{job.job_id or row_start}",
                        on_click=_toggle_email,
                        args=(job.job_id,),
                        help=f"Draft an email about this role to {job.poster_name}"
                        if job.poster_name
                        else "Draft an email about this role",
                    )

                if drafting:
                    # Wrapped only while open, purely so the stylesheet can hold
                    # it back — an open draft already has a filled action of its
                    # own, and two competing for the eye is one too many.
                    with st.container(key=f"emailopen_{job.job_id or row_start}"):
                        _email_button()
                    _render_email_panel(job, sender)
                else:
                    _email_button()

    return clicked
