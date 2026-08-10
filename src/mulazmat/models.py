"""Data structures shared by the search client and the Streamlit UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Job:
    """A single job posting."""

    job_id: str
    title: str
    company: str
    location: str
    url: str
    posted_at: str = ""
    posted_label: str = ""
    salary: str = ""
    company_url: str = ""
    source: str = "linkedin"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def matches_company(self, needle: str) -> bool:
        """Case-insensitive substring match against the company name."""
        needle = (needle or "").strip().lower()
        if not needle:
            return True
        return needle in self.company.lower()


@dataclass
class SearchQuery:
    """Everything the user can ask for on the search form.

    ``company`` is applied client-side to the results rather than being sent to
    LinkedIn, because the guest search endpoint filters by numeric company id
    (which we cannot resolve from a free-text name).
    """

    keywords: str
    location: str = ""
    geo_id: str = ""
    company: str = ""
    date_posted: str = ""
    experience_levels: tuple[str, ...] = ()
    job_types: tuple[str, ...] = ()
    workplace_types: tuple[str, ...] = ()
    sort_by: str = "R"

    def __post_init__(self) -> None:
        # Normalise the multi-selects so the query is hashable and cacheable.
        self.experience_levels = tuple(self.experience_levels)
        self.job_types = tuple(self.job_types)
        self.workplace_types = tuple(self.workplace_types)

    def cache_key(self) -> tuple[Any, ...]:
        """Identity of the *remote* request — company is excluded on purpose."""
        return (
            self.keywords.strip().lower(),
            self.location.strip().lower(),
            self.geo_id,
            self.date_posted,
            tuple(sorted(self.experience_levels)),
            tuple(sorted(self.job_types)),
            tuple(sorted(self.workplace_types)),
            self.sort_by,
        )
