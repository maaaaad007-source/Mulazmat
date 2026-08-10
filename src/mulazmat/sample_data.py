"""Offline sample results.

Demo mode lets you click through the whole UI — filters, table, CSV export —
without touching LinkedIn. Useful for development, for screenshots, and for
checking the app still runs when LinkedIn is rate limiting you.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from .models import Job, SearchQuery

_COMPANIES = (
    ("Systems Limited", "Lahore"),
    ("Netsol Technologies", "Lahore"),
    ("Careem", "Karachi"),
    ("Acme Analytics", "Remote"),
    ("Globex Health", "London"),
    ("Initech", "Berlin"),
    ("Umbrella Retail", "Toronto"),
    ("Hooli", "San Francisco, CA"),
    ("Stark Industries", "Dubai"),
    ("Wayne Digital", "Amsterdam"),
)

_SENIORITY = ("Junior", "", "Senior", "Lead", "Principal")
_ARRANGEMENT = ("On-site", "Hybrid", "Remote")


def sample_jobs(query: SearchQuery, limit: int = 40) -> list[Job]:
    """Deterministic fake results shaped by the user's query."""
    title = query.keywords.strip() or "Software Engineer"
    country = query.location.strip() or "Pakistan"
    today = date.today()

    jobs: list[Job] = []
    for index in range(min(limit, 40)):
        company, city = _COMPANIES[index % len(_COMPANIES)]
        seniority = _SENIORITY[index % len(_SENIORITY)]
        arrangement = _ARRANGEMENT[index % len(_ARRANGEMENT)]
        posted = today - timedelta(days=index % 21)

        full_title = f"{seniority} {title}".strip()
        digest = hashlib.sha1(f"{full_title}{company}{index}".encode()).hexdigest()[:10]
        job_id = str(int(digest, 16) % 9_000_000_000 + 1_000_000_000)

        jobs.append(
            Job(
                job_id=job_id,
                title=f"{full_title} ({arrangement})",
                company=company,
                location=city if city == "Remote" else f"{city}, {country}",
                url=f"https://www.linkedin.com/jobs/view/{job_id}",
                posted_at=posted.isoformat(),
                posted_label=("today" if index % 21 == 0 else f"{index % 21} days ago"),
                salary="",
                company_url="",
                source="demo",
            )
        )

    return jobs
