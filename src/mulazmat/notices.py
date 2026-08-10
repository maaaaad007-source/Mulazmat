"""Wording for the "this search was rate limited" banner.

Kept out of ``app.py`` so it can be tested directly: the banner previously
fired on any 429, including ones the backoff recovered from, and told people
their search returned "100 results rather than the 100 asked for".
"""

from __future__ import annotations


def throttle_notice(
    *,
    throttled: bool,
    found: int,
    limit: int,
    missing_details: int = 0,
    detail_count: int = 0,
) -> str:
    """What to tell the user after a throttled search, or "" for nothing.

    A 429 the client recovered from costs the user nothing, so it earns no
    banner. Only an actual shortfall — fewer results than asked for, or
    postings that could not be opened — is worth interrupting for.
    """
    if not throttled:
        return ""

    losses = []
    if found < limit:
        losses.append(f"it stopped at {found} results rather than the {limit} asked for")
    if missing_details:
        losses.append(f"{missing_details} could not be opened for their description")

    if not losses:
        return ""

    advice = (
        " **Fetch full details** is the usual cause — it makes one request per job."
        " Turning it off, or asking for fewer results, avoids this."
        if detail_count
        else " Asking for fewer results avoids this."
    )
    return f"LinkedIn rate limited this search, so {' and '.join(losses)}.{advice}"
