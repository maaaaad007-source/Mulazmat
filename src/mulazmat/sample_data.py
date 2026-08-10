"""Offline sample results.

Demo mode lets you click through the whole UI — filters, table, CSV export —
without touching LinkedIn. Useful for development, for screenshots, and for
checking the app still runs when LinkedIn is rate limiting you.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from urllib.parse import quote

from .models import Job, SearchQuery

# Each company carries its own location, so demo results never read
# "London, Germany" just because Germany was the country searched.
_COMPANIES = (
    ("Northwind Studio", "Amsterdam, North Holland, Netherlands"),
    ("Acme Analytics", "Remote"),
    ("Globex Health", "London, United Kingdom"),
    ("Initech", "Berlin, Germany"),
    ("Umbrella Retail", "Toronto, Ontario, Canada"),
    ("Hooli", "San Francisco, CA, United States"),
    ("Stark Industries", "Dubai, United Arab Emirates"),
    ("Vandelay Interactive", "Utrecht, Netherlands"),
    ("Soylent Foods", "Singapore"),
    ("Wayne Digital", "Sydney, NSW, Australia"),
)

_SENIORITY = ("Junior", "", "Senior", "Lead", "Principal")
_ARRANGEMENT = ("On-site", "Hybrid", "Remote")
#: f_WT values back to labels, so a demo search filtered to Remote does not
#: hand back cards labelled On-site.
_WORKPLACE_BY_CODE = {"1": "On-site", "2": "Remote", "3": "Hybrid"}


def _demo_logo(company: str) -> str:
    """An inline SVG monogram, so demo cards exercise the <img> path offline."""
    hue = sum(ord(c) for c in company) % 360
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'>"
        f"<rect width='40' height='40' rx='6' fill='hsl({hue},55%,88%)'/>"
        f"<text x='20' y='27' font-family='sans-serif' font-size='20' font-weight='700' "
        f"text-anchor='middle' fill='hsl({hue},45%,38%)'>{company[:1].upper()}</text></svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)


def sample_jobs(
    query: SearchQuery,
    limit: int = 40,
    enriched: bool = False,
    detect_workplace: bool = False,
) -> list[Job]:
    """Deterministic fake results shaped by the user's query.

    ``enriched`` mirrors "Fetch full details" and ``detect_workplace`` mirrors
    the workplace probe: without them the jobs carry only what a real search
    card gives you, so demo mode shows the same sparser cards a live search
    would.
    """
    # Echoed back exactly as typed — .title() would turn "UX designer" into
    # "Ux Designer".
    title = query.keywords.strip() or "Software Engineer"
    today = date.today()

    jobs: list[Job] = []
    for index in range(min(limit, 40)):
        company, location = _COMPANIES[index % len(_COMPANIES)]
        seniority = _SENIORITY[index % len(_SENIORITY)]
        arrangement = _ARRANGEMENT[index % len(_ARRANGEMENT)]
        if len(query.workplace_types) == 1:
            arrangement = _WORKPLACE_BY_CODE.get(query.workplace_types[0], arrangement)
        posted = today - timedelta(days=index % 21)

        full_title = f"{seniority} {title}".strip()
        digest = hashlib.sha1(f"{full_title}{company}{index}".encode()).hexdigest()[:10]
        job_id = str(int(digest, 16) % 9_000_000_000 + 1_000_000_000)

        jobs.append(
            Job(
                job_id=job_id,
                title=full_title,
                company=company,
                location=location,
                url=f"https://www.linkedin.com/jobs/view/{job_id}",
                posted_at=posted.isoformat(),
                posted_label=("today" if index % 21 == 0 else f"{index % 21} days ago"),
                salary="" if index % 3 else "€5,500 - 7,000/mo",
                company_url=f"https://www.linkedin.com/company/{company.split()[0].lower()}",
                logo_url=_demo_logo(company) if index % 3 else "",
                source="demo",
                description=(
                    f"We are hiring a {full_title.lower()} to join {company}. "
                    "You will shape the work end to end, partner with teams across "
                    "the business, and help turn a messy problem into something "
                    "people can actually use."
                )
                if enriched
                else "",
                workplace=arrangement if (enriched or detect_workplace) else "",
                seniority=("Entry level" if index % 2 else "Mid-Senior level") if enriched else "",
                employment_type=("Contract" if index % 5 == 0 else "Full-time") if enriched else "",
                job_function="Analyst" if enriched else "",
                industries="Information Technology & Services" if enriched else "",
                applicants=f"{(index * 7) % 90 + 5} applicants" if enriched else "",
                apply_url=(
                    f"https://careers.{company.split()[0].lower()}.example/jobs/{job_id}"
                    if enriched and index % 3 == 0
                    else ""
                ),
                poster_name=("Sofie de Vries" if enriched and index % 4 == 0 else ""),
                poster_title=("Talent Acquisition Lead" if enriched and index % 4 == 0 else ""),
                poster_profile=(
                    "https://www.linkedin.com/in/sofie-de-vries-demo"
                    if enriched and index % 4 == 0
                    else ""
                ),
                enriched=enriched,
            )
        )

    return jobs
