"""Mulazmat — search LinkedIn job postings from a Streamlit UI.

Run with:  streamlit run app.py

Layout is a horizontal search bar (title, company, country, search, filters,
saved) over a two-up grid of result cards. There is no sidebar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mulazmat import countries, filters, theme  # noqa: E402
from mulazmat.cards import render_grid  # noqa: E402
from mulazmat.linkedin import LinkedInClient, LinkedInError  # noqa: E402
from mulazmat.models import Job, SearchQuery  # noqa: E402
from mulazmat.sample_data import sample_jobs  # noqa: E402

st.set_page_config(
    page_title="Mulazmat — LinkedIn Job Search",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(theme.STYLES, unsafe_allow_html=True)

WORKPLACE_CHOICES = ["Select all", *filters.WORKPLACE_TYPES]


@st.cache_data(ttl=600, show_spinner=False)
def _cached_search(
    cache_key: tuple, query_fields: dict, limit: int, demo: bool, detail_count: int
) -> list[dict]:
    """Run a search and cache it for 10 minutes.

    Keyed on ``cache_key`` (which excludes the company filter, since that is
    applied locally) so changing only the company name reuses the same results.
    """
    query = SearchQuery(**query_fields)
    if demo:
        return [job.to_dict() for job in sample_jobs(query, limit)]

    client = LinkedInClient()
    progress = st.progress(0.0, text="Searching LinkedIn…")

    def on_progress(found: int, target: int) -> None:
        progress.progress(min(found / target, 1.0), text=f"Found {found} of up to {target} jobs…")

    try:
        jobs = client.search(query, limit=limit, on_progress=on_progress)

        if detail_count and jobs:

            def on_detail(done: int, target: int) -> None:
                progress.progress(
                    min(done / target, 1.0), text=f"Fetching details {done}/{target}…"
                )

            jobs = client.enrich(jobs, limit=detail_count, on_progress=on_detail)
    finally:
        progress.empty()

    return [job.to_dict() for job in jobs]


def _filters_panel() -> None:
    """The dropdown behind the Filters button.

    Widgets write straight to session state via their keys, so nothing needs to
    be returned; "Apply filters" only exists to close the panel and rerun.

    LinkedIn's guest endpoint returns no facet counts, so the options here are
    unnumbered — a count would have to be invented.
    """
    st.markdown('<p class="mz-fgroup">Sort by</p>', unsafe_allow_html=True)
    st.radio("Sort by", list(filters.SORT_OPTIONS), key="sort", label_visibility="collapsed")

    st.markdown('<p class="mz-fgroup">Date posted</p>', unsafe_allow_html=True)
    st.radio(
        "Date posted", list(filters.DATE_POSTED), key="date_posted", label_visibility="collapsed"
    )

    st.markdown('<p class="mz-fgroup">Workplace</p>', unsafe_allow_html=True)
    st.radio("Workplace", WORKPLACE_CHOICES, key="workplace", label_visibility="collapsed")

    st.markdown('<p class="mz-fgroup">Experience level</p>', unsafe_allow_html=True)
    for label in filters.EXPERIENCE_LEVELS:
        st.checkbox(label, key=f"exp_{label}")

    st.markdown('<p class="mz-fgroup">Max results</p>', unsafe_allow_html=True)
    st.slider(
        "Max results",
        key="limit",
        min_value=25,
        max_value=500,
        value=100,
        step=25,
        label_visibility="collapsed",
        help="LinkedIn serves ~10 per request and stops around 1000.",
    )

    st.markdown('<p class="mz-fgroup">View as</p>', unsafe_allow_html=True)
    st.radio("View as", ["Cards", "Table"], key="view", label_visibility="collapsed")

    st.checkbox(
        "Fetch full details",
        key="fetch_details",
        help="Opens each posting for its description, applicant count and apply link. "
        "One extra request per job — slower, and more likely to hit the rate limit.",
    )
    if st.session_state.get("fetch_details"):
        st.slider("Details for first N jobs", key="detail_count", min_value=5, max_value=50, step=5)
    st.checkbox("Demo mode (no network)", key="demo_mode", help="Sample results, no LinkedIn call.")

    st.markdown('<p class="mz-fgroup">Advanced</p>', unsafe_allow_html=True)
    st.text_input(
        "LinkedIn geoId",
        key="geo_id",
        placeholder="LinkedIn geoId",
        label_visibility="collapsed",
        help="Auto-filled for supported countries; blank sends the country name as "
        "free text instead. Override if results look off.",
    )

    if st.button("Apply filters", key="apply_filters", width="stretch"):
        # Remount the popover so it comes back collapsed.
        st.session_state["filters_panel"] = st.session_state.get("filters_panel", 0) + 1
        st.rerun()


def _topbar() -> bool:
    """Draw the search bar. Returns True when Search was pressed."""
    with st.container(key="topbar"):
        # Ratios chosen so every control stretches to fill its column and the
        # row ends flush with the cards below.
        logo, title, company, country, search, filt, saved = st.columns(
            [0.55, 3.1, 3.1, 2.6, 1.9, 1.7, 0.45],
            vertical_alignment="center",
            gap="small",
        )

        logo.markdown(theme.LOGO, unsafe_allow_html=True)
        title.text_input(
            "Job title", key="title", placeholder="Job Title", label_visibility="collapsed"
        )
        company.text_input(
            "Company", key="company", placeholder="Company (Optional)", label_visibility="collapsed"
        )

        picked = country.selectbox(
            "Country",
            options=sorted(countries.COUNTRIES),
            key="country",
            index=None,
            placeholder="Country",
            label_visibility="collapsed",
        )
        # A keyed widget ignores ``value=`` after its first render, so the geoId
        # is re-seeded when the country changes. Overrides survive until then.
        if st.session_state.get("_geo_country") != picked:
            st.session_state["_geo_country"] = picked
            st.session_state["geo_id"] = countries.geo_id_for(picked or "")

        run = search.button("Search", key="search", width="stretch")

        # Streamlit has no API to close a popover, but remounting the element
        # renders it closed — so "Apply filters" bumps this counter and the new
        # key gives us a fresh, collapsed panel. Widget state is unaffected;
        # each control inside keeps its own key.
        panel = st.session_state.get("filters_panel", 0)
        with filt.popover("Filters", key=f"filters_{panel}", width="stretch"):
            _filters_panel()

        showing = st.session_state.get("show_saved", False)
        if saved.button(
            "",
            key="saved_toggle",
            icon=":material/bookmark:",
            help="Show all jobs" if showing else "Show saved jobs",
            type="primary" if showing else "secondary",
            width="stretch",
        ):
            st.session_state["show_saved"] = not showing
            st.rerun()

    return run


def _query_from_state() -> SearchQuery:
    state = st.session_state
    country = state.get("country") or ""
    workplace = state.get("workplace", "Select all")
    experience = [label for label in filters.EXPERIENCE_LEVELS if state.get(f"exp_{label}")]

    return SearchQuery(
        keywords=state.get("title", ""),
        location=countries.location_string(country or countries.ANYWHERE),
        geo_id=(state.get("geo_id") or "").strip(),
        company=state.get("company", ""),
        date_posted=filters.DATE_POSTED[state.get("date_posted", "Any time")],
        experience_levels=filters.values_for(experience, filters.EXPERIENCE_LEVELS),
        job_types=(),
        workplace_types=(
            ()
            if workplace == "Select all"
            else filters.values_for([workplace], filters.WORKPLACE_TYPES)
        ),
        sort_by=filters.SORT_OPTIONS[state.get("sort", "Most relevant")],
    )


def _render_table(frame: pd.DataFrame) -> None:
    display = frame[["title", "company", "location", "posted_label", "salary", "url"]].rename(
        columns={
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "posted_label": "Posted",
            "salary": "Salary",
            "url": "Link",
        }
    )
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config={"Link": st.column_config.LinkColumn("Link", display_text="Open")},
    )


def _render_results(jobs: list[Job], query: SearchQuery) -> None:
    state = st.session_state
    saved: set[str] = state.setdefault("saved", set())
    showing_saved = state.get("show_saved", False)

    filtered = [job for job in jobs if job.matches_company(query.company)]
    if showing_saved:
        filtered = [job for job in filtered if job.job_id in saved]

    if not filtered:
        if showing_saved:
            st.info("No saved jobs yet — tap the ♡ on a card to save it.")
        elif jobs and query.company:
            st.warning(
                f"{len(jobs)} jobs found, but none from a company matching "
                f"“{query.company}”. Try a shorter company name."
            )
        else:
            st.warning("No jobs matched. Try a broader title, or widen the date filter.")
        return

    heading = "Saved Jobs" if showing_saved else "Job Results"
    st.markdown(
        f'<p class="mz-count">{len(filtered)} {heading}</p>',
        unsafe_allow_html=True,
    )

    if state.get("view", "Cards") == "Cards":
        clicked = render_grid(filtered, saved)
        if clicked:
            saved.symmetric_difference_update({clicked})
            st.rerun()
    else:
        _render_table(pd.DataFrame([job.to_dict() for job in filtered]))

    st.divider()
    st.download_button(
        "Download CSV",
        data=pd.DataFrame([job.to_dict() for job in filtered]).to_csv(index=False).encode("utf-8"),
        file_name=f"mulazmat-{query.keywords.strip().replace(' ', '-').lower() or 'jobs'}.csv",
        mime="text/csv",
    )


run = _topbar()
query = _query_from_state()

if run:
    if not query.keywords.strip():
        st.error("Enter a job title to search.")
    else:
        st.session_state.pop("results", None)
        st.session_state["show_saved"] = False
        try:
            raw = _cached_search(
                query.cache_key(),
                query.__dict__.copy(),
                st.session_state.get("limit", 100),
                st.session_state.get("demo_mode", False),
                st.session_state.get("detail_count", 0)
                if st.session_state.get("fetch_details")
                else 0,
            )
        except LinkedInError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 — surface anything else to the user
            st.error(f"Search failed: {exc}")
        else:
            st.session_state["results"] = raw
            st.session_state["demo"] = st.session_state.get("demo_mode", False)

if "results" in st.session_state:
    if st.session_state.get("demo"):
        st.info("Demo mode — these are sample results, not live LinkedIn data.")
    _render_results([Job(**row) for row in st.session_state["results"]], query)
else:
    st.markdown(
        """
        #### Search LinkedIn job postings

        Enter a **job title**, optionally a **company** and a **country**, then press
        **Search**. Everything else — sort, date posted, workplace, experience level,
        card or table view — lives behind **Filters**.

        Use the bookmark on any card to save it, and the bookmark in the bar to
        show only saved jobs.

        LinkedIn publishes no recruiter emails or phone numbers on job postings, so
        neither does this app. **Contact & apply** links the real apply page, the
        company's LinkedIn page, and — when a posting names one — the public profile
        of whoever posted it.

        LinkedIn has no public jobs API, so this reads the same endpoint its
        logged-out jobs page uses. It is rate limited: keep searches modest, and
        expect the occasional "slow down" message.
        """
    )
