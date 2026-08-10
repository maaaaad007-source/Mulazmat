"""HTML card rendering for job results.

Kept out of ``app.py`` so the markup can be unit tested without a browser.

Everything that came from LinkedIn is escaped before it reaches the page —
job titles and company names are third-party text and must never be trusted as
markup.
"""

from __future__ import annotations

from html import escape

from .models import Job

CARD_CSS = """
<style>
.mz-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
  margin-top: .5rem;
}
.mz-card {
  border: 1px solid rgba(128, 128, 128, .25);
  border-radius: 12px;
  padding: 1rem 1.1rem 1.15rem;
  background: rgba(255, 255, 255, .55);
  display: flex;
  flex-direction: column;
  gap: .55rem;
}
.mz-card:hover { border-color: #0a66c2; }
.mz-card h3 { font-size: 1.02rem; line-height: 1.35; margin: 0; }
.mz-card h3 a { color: #0a66c2; text-decoration: none; }
.mz-card h3 a:hover { text-decoration: underline; }
.mz-company { margin: 0; font-weight: 600; font-size: .92rem; }
.mz-company a { color: inherit; text-decoration: none; }
.mz-company a:hover { text-decoration: underline; }
.mz-meta {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-wrap: wrap; gap: .35rem .9rem;
  font-size: .85rem; opacity: .8;
}
.mz-badges { display: flex; flex-wrap: wrap; gap: .35rem; }
.mz-badge {
  font-size: .74rem; padding: .12rem .55rem; border-radius: 999px;
  background: rgba(10, 102, 194, .12); color: #0a66c2; white-space: nowrap;
}
.mz-desc { font-size: .85rem; line-height: 1.5; opacity: .85; margin: 0; }
.mz-contact {
  margin-top: auto; padding-top: .6rem;
  border-top: 1px dashed rgba(128, 128, 128, .3);
}
.mz-contact__label {
  display: block; font-size: .7rem; letter-spacing: .06em;
  text-transform: uppercase; opacity: .55; margin-bottom: .4rem;
}
.mz-links { display: flex; flex-wrap: wrap; gap: .4rem; }
/* Scoped to .mz-card to outrank Streamlit's own link colouring, which would
   otherwise repaint the primary button's label and kill its contrast. */
.mz-card a.mz-link {
  font-size: .8rem; padding: .25rem .7rem; border-radius: 6px;
  text-decoration: none; border: 1px solid rgba(10, 102, 194, .4); color: #0a66c2;
}
.mz-card a.mz-link:hover { background: rgba(10, 102, 194, .08); text-decoration: none; }
.mz-card a.mz-link--primary {
  background: #0a66c2; color: #fff; border-color: #0a66c2; font-weight: 600;
}
.mz-card a.mz-link--primary:hover { background: #004182; color: #fff; }
.mz-poster { font-size: .8rem; margin: 0 0 .4rem; }
.mz-none { font-size: .78rem; opacity: .6; margin: 0; }
@media (prefers-color-scheme: dark) {
  .mz-card { background: rgba(255, 255, 255, .04); }
  .mz-badge { background: rgba(120, 180, 255, .16); color: #79b8ff; }
  .mz-card h3 a { color: #79b8ff; }
  .mz-card a.mz-link { color: #79b8ff; border-color: rgba(120, 180, 255, .4); }
  .mz-card a.mz-link--primary { background: #0a66c2; color: #fff; }
}
</style>
"""


def _anchor(url: str, label: str, css: str = "") -> str:
    klass = f'class="{css}" ' if css else ""
    return (
        f'<a {klass}href="{escape(url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{escape(label)}</a>'
    )


def _link(url: str, label: str, primary: bool = False) -> str:
    """A pill-styled action link for the contact footer."""
    return _anchor(url, label, "mz-link mz-link--primary" if primary else "mz-link")


def _contact_block(job: Job) -> str:
    """The "Contact & apply" footer.

    Only ever contains links LinkedIn publishes: the apply target, the company
    page, and — when the posting names one — the poster's public profile. There
    are no email addresses or phone numbers in LinkedIn's job data, so there are
    none here either.
    """
    parts = ['<div class="mz-contact"><span class="mz-contact__label">Contact &amp; apply</span>']

    if job.poster_name:
        who = escape(job.poster_name)
        if job.poster_title:
            who += f" · {escape(job.poster_title)}"
        parts.append(f'<p class="mz-poster">Posted by {who}</p>')

    links: list[str] = []
    if job.best_apply_url:
        links.append(_link(job.best_apply_url, "Apply", primary=True))
    if job.company_url:
        links.append(_link(job.company_url, "Company page"))
    if job.poster_profile:
        links.append(_link(job.poster_profile, "Profile"))
    if job.url and job.apply_url:
        # Apply went to an external site — keep the LinkedIn posting reachable.
        links.append(_link(job.url, "On LinkedIn"))

    if links:
        parts.append(f'<div class="mz-links">{"".join(links)}</div>')
    else:
        parts.append('<p class="mz-none">No public contact links on this posting.</p>')

    parts.append("</div>")
    return "".join(parts)


def render_card(job: Job) -> str:
    """One job as an HTML card."""
    label = job.title or "Untitled role"
    # A plain anchor, not _link(): the heading must not look like a button.
    heading = _anchor(job.url, label) if job.url else escape(label)
    parts = [f'<article class="mz-card"><h3>{heading}</h3>']

    if job.company:
        company = _anchor(job.company_url, job.company) if job.company_url else escape(job.company)
        parts.append(f'<p class="mz-company">{company}</p>')

    meta = []
    if job.location:
        meta.append(f"📍 {escape(job.location)}")
    if job.posted_label:
        meta.append(f"🕒 {escape(job.posted_label)}")
    if job.salary:
        meta.append(f"💰 {escape(job.salary)}")
    if job.applicants:
        meta.append(f"👥 {escape(job.applicants)}")
    if meta:
        parts.append(
            '<ul class="mz-meta">' + "".join(f"<li>{item}</li>" for item in meta) + "</ul>"
        )

    if job.badges:
        pills = "".join(f'<span class="mz-badge">{escape(b)}</span>' for b in job.badges)
        parts.append(f'<div class="mz-badges">{pills}</div>')

    if job.description:
        parts.append(f'<p class="mz-desc">{escape(job.description[:280])}…</p>')

    parts.append(_contact_block(job))
    parts.append("</article>")
    return "".join(parts)


def render_cards(jobs: list[Job]) -> str:
    """The full results grid, CSS included."""
    cards = "".join(render_card(job) for job in jobs)
    return f'{CARD_CSS}<div class="mz-grid">{cards}</div>'
