"""Offline sample results.

Demo mode lets you click through the whole UI — filters, table, CSV export —
without touching LinkedIn. Useful for development, for screenshots, and for
checking the app still runs when LinkedIn is rate limiting you.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from .models import Job, SearchQuery

# Each company carries its own real-looking location, so demo results never
# read "London, Pakistan" just because Pakistan was the country searched.
_COMPANIES = (
    ("Systems Limited", "Lahore, Pakistan"),
    ("Netsol Technologies", "Lahore, Pakistan"),
    ("Careem", "Karachi, Pakistan"),
    ("Acme Analytics", "Remote"),
    ("Globex Health", "London, United Kingdom"),
    ("Initech", "Berlin, Germany"),
    ("Umbrella Retail", "Toronto, Canada"),
    ("Hooli", "San Francisco, CA, United States"),
    ("Stark Industries", "Dubai, United Arab Emirates"),
    ("Booking.com", "Amsterdam, Netherlands"),
)

_SENIORITY = ("Junior", "", "Senior", "Lead", "Principal")
_ARRANGEMENT = ("On-site", "Hybrid", "Remote")


def sample_jobs(query: SearchQuery, limit: int = 40) -> list[Job]:
    """Deterministic fake results shaped by the user's query."""
    title = query.keywords.strip() or "Software Engineer"
    today = date.today()

    jobs: list[Job] = []
    for index in range(min(limit, 40)):
        company, location = _COMPANIES[index % len(_COMPANIES)]
        seniority = _SENIORITY[index % len(_SENIORITY)]
        arrangement = _ARRANGEMENT[index % len(_ARRANGEMENT)]
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
                salary="" if index % 3 else "PKR 250,000 - 400,000/mo",
                company_url=f"https://www.linkedin.com/company/{company.split()[0].lower()}",
                source="demo",
                description=(
                    f"We are hiring a {full_title.lower()} to join {company}. "
                    "You will own reporting, build dashboards, and partner with "
                    "product and finance teams to turn messy data into decisions."
                ),
                workplace=arrangement,
                seniority=("Entry level" if index % 2 else "Mid-Senior level"),
                employment_type=("Contract" if index % 5 == 0 else "Full-time"),
                job_function="Analyst",
                industries="Information Technology & Services",
                applicants=f"{(index * 7) % 90 + 5} applicants",
                apply_url=(
                    f"https://careers.{company.split()[0].lower()}.example/jobs/{job_id}"
                    if index % 3 == 0
                    else ""
                ),
                poster_name=("Ayesha Khan" if index % 4 == 0 else ""),
                poster_title=("Talent Acquisition Lead" if index % 4 == 0 else ""),
                poster_profile=(
                    "https://www.linkedin.com/in/ayesha-khan-demo" if index % 4 == 0 else ""
                ),
                enriched=True,
            )
        )

    return jobs
