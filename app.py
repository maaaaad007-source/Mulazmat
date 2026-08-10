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
from mulazmat.linkedin import LinkedInClient, LinkedInError  # noqa: E402
from mulazmat.models import Job, SearchQuery  # noqa: E402
from mulazmat.sample_data import sample_jobs  # noqa: E402

st.set_page_config(page_title="Mulazmat — LinkedIn Job Search", page_icon="💼", layout="wide")


@st.cache_data(ttl=600, show_spinner=False)
def _cached_search(cache_key: tuple, query_fields: dict, limit: int, demo: bool) -> list[dict]:
    """Run a search and cache it for 10 minutes.

    Keyed on ``cache_key`` (which excludes the company filter, since that is
    applied locally) so changing only the company name reuses the same results.
    """
    query = SearchQuery(**query_fields)
    if demo:
        return [job.to_dict() for job in sample_jobs(query, limit)]

    progress = st.progress(0.0, text="Searching LinkedIn…")

    def on_progress(found: int, target: int) -> None:
        progress.progress(min(found / target, 1.0), text=f"Found {found} of up to {target} jobs…")

    try:
        jobs = LinkedInClient().search(query, limit=limit, on_progress=on_progress)
    finally:
        progress.empty()

    return [job.to_dict() for job in jobs]


def _sidebar() -> tuple[SearchQuery, int, bool, bool]:
    with st.sidebar:
        st.header("Search")

        title = st.text_input(
            "Job title *",
            placeholder="e.g. Data Analyst",
            help="Required. Matched against the posting's title and description.",
        )
        company = st.text_input(
            "Company (optional)",
            placeholder="e.g. Systems Limited",
            help="Filters the results after they come back from LinkedIn.",
        )

        country = st.selectbox(
            "Country",
            options=countries.country_options(),
            index=0,
            help="Alphabetical — start typing to jump to a country.",
        )
        city = st.text_input("City / region (optional)", placeholder="e.g. Lahore")

        st.divider()
        st.subheader("Filters")

        date_label = st.selectbox("Date posted", list(filters.DATE_POSTED))
        sort_label = st.selectbox("Sort by", list(filters.SORT_OPTIONS))
        workplace = st.multiselect("Workplace", list(filters.WORKPLACE_TYPES))
        job_types = st.multiselect("Job type", list(filters.JOB_TYPES))
        experience = st.multiselect("Experience level", list(filters.EXPERIENCE_LEVELS))

        limit = st.slider(
            "Max results",
            min_value=25,
            max_value=500,
            value=100,
            step=25,
            help="LinkedIn serves ~10 per request and stops around 1000. "
            "Larger numbers take longer and risk rate limiting.",
        )

        st.divider()
        demo = st.toggle(
            "Demo mode (no network)",
            value=False,
            help="Show sample results so you can try the UI without querying LinkedIn.",
        )

        geo_id = countries.geo_id_for(country)
        with st.expander("Advanced"):
            geo_id = st.text_input(
                "LinkedIn geoId",
                value=geo_id,
                help="Auto-filled for supported countries; blank means the country "
                "name is sent as free text instead. Override if results look off.",
            ).strip()

        run = st.button("Search", type="primary", use_container_width=True)

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
    return query, limit, demo, run


def _render_results(jobs: list[Job], query: SearchQuery) -> None:
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

    st.download_button(
        "Download CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=f"mulazmat-{query.keywords.strip().replace(' ', '-').lower() or 'jobs'}.csv",
        mime="text/csv",
    )


st.title("💼 Mulazmat")
st.caption("Search LinkedIn job postings by title, company and country.")

query, limit, demo, run = _sidebar()

if run:
    if not query.keywords.strip():
        st.error("Enter a job title to search.")
    else:
        st.session_state.pop("results", None)
        try:
            raw = _cached_search(query.cache_key(), query.__dict__.copy(), limit, demo)
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
    _render_results([Job(**row) for row in st.session_state["results"]], stored)
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

        LinkedIn has no public jobs API, so this reads the same endpoint its
        logged-out jobs page uses. It is rate limited: keep searches modest, and
        expect the occasional "slow down" message.
        """
    )
