"""Data structures shared by the search client and the Streamlit UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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

    # Filled in only when detail enrichment is switched on — see
    # ``LinkedInClient.fetch_details``. All optional; LinkedIn omits most of
    # them on most postings.
    description: str = ""
    workplace: str = ""
    seniority: str = ""
    employment_type: str = ""
    job_function: str = ""
    industries: str = ""
    applicants: str = ""
    apply_url: str = ""
    poster_name: str = ""
    poster_title: str = ""
    poster_profile: str = ""
    enriched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def best_apply_url(self) -> str:
        """Where "Apply" should point: the external URL if we have one."""
        return self.apply_url or self.url

    @property
    def workplace_label(self) -> str:
        """On-site / Remote / Hybrid, if the posting actually says so.

        LinkedIn does not return a workplace field on search cards, so this
        reads the location text and stays empty when it cannot tell — a guess
        here would be worse than a blank.
        """
        if self.workplace:
            return self.workplace
        location = self.location.lower()
        if "hybrid" in location:
            return "Hybrid"
        if "remote" in location:
            return "Remote"
        return ""

    @property
    def badges(self) -> tuple[str, ...]:
        """Short labels shown as pills on the card."""
        values = (self.employment_type, self.seniority, self.job_function)
        return tuple(value for value in values if value)

    def has_contact_links(self) -> bool:
        """True when we have anything real to put under "Contact & apply"."""
        return bool(self.best_apply_url or self.company_url or self.poster_profile)

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
