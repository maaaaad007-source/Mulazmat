"""Filter vocabularies used by LinkedIn's guest job-search endpoint.

Each mapping is ``human label -> query-parameter value``. The UI shows the
labels; the client sends the values.
"""

from __future__ import annotations

# f_TPR — "time posted range", in seconds.
DATE_POSTED: dict[str, str] = {
    "Any time": "",
    "Past 24 hours": "r86400",
    "Past week": "r604800",
    "Past month": "r2592000",
}

# f_E — experience level.
EXPERIENCE_LEVELS: dict[str, str] = {
    "Internship": "1",
    "Entry level": "2",
    "Associate": "3",
    "Mid-Senior level": "4",
    "Director": "5",
    "Executive": "6",
}

# f_JT — job type.
JOB_TYPES: dict[str, str] = {
    "Full-time": "F",
    "Part-time": "P",
    "Contract": "C",
    "Temporary": "T",
    "Internship": "I",
    "Volunteer": "V",
    "Other": "O",
}

# f_WT — workplace type.
WORKPLACE_TYPES: dict[str, str] = {
    "On-site": "1",
    "Remote": "2",
    "Hybrid": "3",
}

# sortBy
SORT_OPTIONS: dict[str, str] = {
    "Most relevant": "R",
    "Most recent": "DD",
}


def values_for(labels: list[str] | tuple[str, ...], mapping: dict[str, str]) -> tuple[str, ...]:
    """Translate selected labels into their query-parameter values."""
    return tuple(mapping[label] for label in labels if label in mapping)
