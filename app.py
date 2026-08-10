"""Mulazmat — search LinkedIn job postings from a Streamlit UI.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mulazmat import countries, filters  # noqa: E402
from mulazmat.cards import render_cards  # noqa: E402
from mulazmat.linkedin import LinkedInClient, LinkedInError  # noqa: E402
from mulazmat.models import Job, SearchQuery  # noqa: E402
from mulazmat.sample_data import sample_jobs  # noqa: E402

st.set_page_config(page_title="Mulazmat — LinkedIn Job Search", page_icon="💼", layout="wide")


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


def _sidebar() -> tuple[SearchQuery, int, bool, bool, str, int]:
    with st.sidebar:
        st.header("Search")

        title = st.text_input(
            "Job title *",
            key="title",
            placeholder="e.g. Data Analyst",
            help="Required. Matched against the posting's title and description.",
        )
        company = st.text_input(
            "Company (optional)",
            key="company",
            placeholder="e.g. Systems Limited",
            help="Filters the results after they come back from LinkedIn.",
        )

        country = st.selectbox(
            "Country",
            key="country",
            options=countries.country_options(),
            index=0,
            help="Alphabetical — start typing to jump to a country.",
        )
        city = st.text_input("City / region (optional)", key="city", placeholder="e.g. Lahore")

        st.divider()
        st.subheader("Filters")

        date_label = st.selectbox("Date posted", list(filters.DATE_POSTED), key="date_posted")
        sort_label = st.selectbox("Sort by", list(filters.SORT_OPTIONS), key="sort")
        workplace = st.multiselect("Workplace", list(filters.WORKPLACE_TYPES), key="workplace")
        job_types = st.multiselect("Job type", list(filters.JOB_TYPES), key="job_types")
        experience = st.multiselect("Experience level", list(filters.EXPERIENCE_LEVELS), key="experience")

        limit = st.slider(
            "Max results",
            key="limit",
            min_value=25,
            max_value=500,
            value=100,
            step=25,
            help="LinkedIn serves ~10 per request and stops around 1000. "
            "Larger numbers take longer and risk rate limiting.",
        )

        st.divider()
        st.subheader("Display")

        view = st.radio("View as", ["Cards", "Table"], key="view", horizontal=True)

        fetch_details = st.toggle(
            "Fetch full details",
            key="fetch_details",
            value=False,
            help="Opens each posting for its description, seniority, employment type, "
            "applicant count and apply link. One extra request per job — slower, and "
            "much more likely to hit LinkedIn's rate limit.",
        )
        detail_count = 0
        if fetch_details:
            detail_count = st.slider(
                "Details for first N jobs", key="detail_count", min_value=5, max_value=50, value=15, step=5
            )

        demo = st.toggle(
            "Demo mode (no network)",
            key="demo_mode",
            value=False,
            help="Show sample results so you can try the UI without querying LinkedIn.",
        )

        # A keyed widget ignores ``value=`` after its first render, so the geoId
        # is re-seeded explicitly whenever the country changes. Manual overrides
        # survive until then.
        if st.session_state.get("_geo_country") != country:
            st.session_state["_geo_country"] = country
            st.session_state["geo_id"] = countries.geo_id_for(country)

        with st.expander("Advanced"):
            geo_id = st.text_input(
                "LinkedIn geoId",
                key="geo_id",
                help="Auto-filled for supported countries; blank means the country "
                "name is sent as free text instead. Override if results look off.",
            ).strip()

        run = st.button("Search", key="search", type="primary", use_container_width=True)

    query = SearchQuery(
        keywords=title,
        location=countries.location_string(country, city),
        geo_id=geo_id,
        company=company,
        date_posted=filters.DATE_POSTED[date_label],
        experience_levels=filters.values_for(experience, filters.EXPERIENCE_LEVELS),
        job_types=filters.values_for(job_types, filters.JOB_TYPES),
        workplace_types=filters.values_for(workplace, filters.WORKPLACE_TYPES),
        sort_by=filters.SORT_OPTIONS[sort_label],
    )
    return query, limit, demo, run, view, detail_count


def _render_results(jobs: list[Job], query: SearchQuery, view: str = "Cards") -> None:
    filtered = [job for job in jobs if job.matches_company(query.company)]

    if not filtered:
        if jobs and query.company:
            st.warning(
                f"{len(jobs)} jobs found, but none from a company matching "
                f"“{query.company}”. Try a shorter company name."
            )
        else:
            st.warning("No jobs matched. Try a broader title, or widen the date filter.")
        return

    left, mid, right = st.columns(3)
    left.metric("Jobs shown", len(filtered))
    mid.metric("Companies", len({job.company for job in filtered if job.company}))
    if query.company:
        right.metric("Filtered out", len(jobs) - len(filtered))

    frame = pd.DataFrame([job.to_dict() for job in filtered])

    if view == "Cards":
        st.markdown(render_cards(filtered), unsafe_allow_html=True)
    else:
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
            use_container_width=True,
            hide_index=True,
            column_config={"Link": st.column_config.LinkColumn("Link", display_text="Open")},
        )

    st.divider()

    st.download_button(
        "Download CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=f"mulazmat-{query.keywords.strip().replace(' ', '-').lower() or 'jobs'}.csv",
        mime="text/csv",
    )


st.title("💼 Mulazmat")
st.caption("Search LinkedIn job postings by title, company and country.")

query, limit, demo, run, view, detail_count = _sidebar()

if run:
    if not query.keywords.strip():
        st.error("Enter a job title to search.")
    else:
        st.session_state.pop("results", None)
        try:
            raw = _cached_search(
                query.cache_key(), query.__dict__.copy(), limit, demo, detail_count
            )
        except LinkedInError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 — surface anything else to the user
            st.error(f"Search failed: {exc}")
        else:
            st.session_state["results"] = raw
            st.session_state["query"] = query
            st.session_state["demo"] = demo

if "results" in st.session_state:
    stored: SearchQuery = st.session_state["query"]
    # Re-apply the company filter live, so editing it does not re-hit LinkedIn.
    stored.company = query.company
    if st.session_state.get("demo"):
        st.info("Demo mode — these are sample results, not live LinkedIn data.")
    _render_results([Job(**row) for row in st.session_state["results"]], stored, view)
else:
    st.info("Enter a job title in the sidebar and press **Search** to begin.")
    st.markdown(
        """
        **How it works**

        - **Job title** is required and is what LinkedIn actually searches on.
        - **Company** is optional and is applied to the results after they arrive,
          so you can change it without running a new search.
        - **Country** is the full alphabetical list — click and start typing to
          filter it.
        - **Cards** show each role with its apply link and company page. Turn on
          **Fetch full details** for the description, seniority and applicant
          count too — at the cost of one extra request per job.

        LinkedIn job postings contain no recruiter emails or phone numbers, so
        neither does this app. "Contact & apply" links to the real apply page,
        the company's LinkedIn page, and — when a posting names one — the public
        profile of the person who posted it.

        LinkedIn has no public jobs API, so this reads the same endpoint its
        logged-out jobs page uses. It is rate limited: keep searches modest, and
        expect the occasional "slow down" message.
        """
    )
