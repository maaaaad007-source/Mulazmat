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

from .models import Job


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
        return (
            f'<img class="mz-logo-img" src="{escape(job.logo_url, quote=True)}" '
            f'alt="{escape(job.company)} logo" loading="lazy" '
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


def card_html(job: Job, description: bool = True) -> str:
    """Everything on a card except the save button, which must be a widget.

    The description only exists on jobs that went through detail enrichment, so
    in practice it appears exactly when "Fetch full details" is on.
    """
    body = [title_html(job), meta_row_html(job)]
    if description and job.description:
        body.append(f'<p class="mz-desc">{escape(job.description[:220])}…</p>')
    body.append(contact_html(job))
    return "".join(body)


def render_grid(jobs: list[Job], saved: set[str], columns: int = 2) -> str | None:
    """Draw the cards two-up and return the id of any save button clicked.

    The heart has to be a real Streamlit button (HTML cannot call back into
    Python), so each card is a keyed container with the button floated into its
    top-right corner by CSS.
    """
    clicked: str | None = None

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
                st.markdown(card_html(job), unsafe_allow_html=True)

    return clicked
