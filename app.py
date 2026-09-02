"""firstSTAPP — search LinkedIn job postings from a Streamlit UI.

Run with:  streamlit run app.py

Layout is a horizontal search bar (title, company, country, search, filters,
saved) over a two-up grid of result cards. There is no sidebar.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from firststapp import countries, details_store, filters, job_titles, theme  # noqa: E402
from firststapp.arrange import arrange, needs_refetch  # noqa: E402
from firststapp.cards import render_grid  # noqa: E402
from firststapp.email_draft import DEFAULT_PROFILE  # noqa: E402
from firststapp.linkedin import LinkedInClient, LinkedInError  # noqa: E402
from firststapp.models import Job, SearchQuery  # noqa: E402
from firststapp.sample_data import sample_jobs  # noqa: E402

st.set_page_config(
    page_title="firstSTAPP",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(theme.STYLES, unsafe_allow_html=True)
theme.hide_cloud_badge()

WORKPLACE_CHOICES = ["Select all", *filters.WORKPLACE_TYPES]

# Your details, as remembered by this browser. Must run before the default
# below, so a saved profile wins over the seeded one.
details_store.load()

# Seeded once so the first email draft already signs off with a real profile
# link. Editable like any other field, and the edit sticks.
st.session_state.setdefault("me_profile", DEFAULT_PROFILE)


@st.cache_data(ttl=600, show_spinner=False)
def _cached_search(
    cache_key: tuple,
    query_fields: dict,
    limit: int,
    demo: bool,
    detail_count: int,
    detect_workplace: bool,
) -> list[dict]:
    """Run a search and cache it for 10 minutes.

    Keyed on ``cache_key`` (which excludes the company filter, since that is
    applied locally) so changing only the company name reuses the same results.
    """
    query = SearchQuery(**query_fields)
    if demo:
        return [
            job.to_dict()
            for job in sample_jobs(query, limit, bool(detail_count), detect_workplace)
        ]

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

        if detect_workplace and jobs and not query.workplace_types:
            progress.progress(0.0, text="Checking which roles are remote or hybrid…")
            labels = client.workplace_map(query, limit)
            jobs = [
                dataclasses.replace(job, workplace=job.workplace or labels.get(job.job_id, ""))
                for job in jobs
            ]
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
    st.checkbox(
        "Detect workplace type",
        key="detect_workplace",
        help="Labels each result Remote or Hybrid by re-running your search through "
        "LinkedIn's own workplace filters — the only reliable source, since postings "
        "rarely state it anywhere readable. Costs two extra searches.",
    )
    st.checkbox("Demo mode (no network)", key="demo_mode", help="Sample results, no LinkedIn call.")

    st.markdown('<p class="mz-fgroup">Your details</p>', unsafe_allow_html=True)
    # Feeds every "Write email" draft. Collapsed by default because it is filled
    # in once and then forgotten about, unlike the filters above it.
    #
    # These are typed rather than read off your LinkedIn profile: profile pages
    # are behind a sign-in wall for anything automated, so there is nothing to
    # fetch. The profile URL is carried into the signature so the reader can go
    # and look for themselves.
    with st.expander("Used in email drafts"):
        st.text_input("Your name", key="me_name", placeholder="Your name")
        st.text_input(
            "Headline", key="me_headline", placeholder="e.g. Senior UX Designer, Amsterdam"
        )
        st.text_input("Your email", key="me_email", placeholder="you@example.com")
        st.text_input("Phone (optional)", key="me_phone", placeholder="+00 000 000 000")
        st.text_input("Based in (optional)", key="me_location", placeholder="City, country")
        st.text_input("LinkedIn profile", key="me_profile")
        st.text_area(
            "Key skills",
            key="me_skills",
            placeholder="Figma, user research, design systems",
            height=70,
            help="Comma separated. A draft names the ones the posting itself mentions.",
        )
        st.text_area(
            "Short pitch (optional)",
            key="me_pitch",
            placeholder="A sentence or two about you, reused in every draft.",
            height=80,
            help="Left blank, drafts carry a visible placeholder instead — the "
            "why-this-company line is the one worth writing yourself.",
        )
        st.caption("Remembered in this browser, so you only fill this in once.")

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
        # Sorting, the date window and a smaller result count are all applied
        # to the cards already on screen — no request needed. Only a filter
        # LinkedIn itself has to act on sends us back for a new set.
        st.session_state["apply_filters_pressed"] = True
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
        # A combobox rather than a text input: it suggests common titles as you
        # type, but ``accept_new_options`` means anything else can still be
        # typed straight in.
        title.selectbox(
            "Job title",
            options=job_titles.suggestions(
                st.session_state.get("recent_titles", ()),
                current=st.session_state.get("title"),
            ),
            key="title",
            index=None,
            accept_new_options=True,
            placeholder="Job Title",
            label_visibility="collapsed",
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
        keywords=state.get("title") or "",
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
    display = frame[["title", "company", "location", "workplace", "posted_label", "url"]].rename(
        columns={
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "workplace": "Workplace",
            "posted_label": "Posted",
            "url": "Link",
        }
    )
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config={"Link": st.column_config.LinkColumn("Link", display_text="Open")},
    )


def _render_results(jobs: list[Job], query: SearchQuery, fetched: int = 0) -> None:
    state = st.session_state
    saved: set[str] = state.setdefault("saved", set())
    showing_saved = state.get("show_saved", False)

    # ``jobs`` arrives already arranged — company, date window, sort and count
    # were applied by firststapp.arrange.
    filtered = [job for job in jobs if job.job_id in saved] if showing_saved else list(jobs)

    if not filtered:
        if showing_saved:
            st.info("No saved jobs yet — tap the ♡ on a card to save it.")
        elif fetched and query.company:
            st.warning(
                f"{fetched} jobs found, but none from a company matching "
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
        file_name=f"firststapp-{query.keywords.strip().replace(' ', '-').lower() or 'jobs'}.csv",
        mime="text/csv",
    )


run = _topbar()
query = _query_from_state()

# Applying filters re-arranges what is on screen. It only goes back to LinkedIn
# when a filter LinkedIn itself has to act on changed, or when more results are
# wanted than were fetched.
if st.session_state.pop("apply_filters_pressed", False) and query.keywords.strip():
    wants_more = st.session_state.get("fetched_limit", 0) < st.session_state.get("limit", 100)
    run = run or needs_refetch(st.session_state.get("fetched_with"), query) or wants_more

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
                bool(st.session_state.get("detect_workplace")),
            )
        except LinkedInError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 — surface anything else to the user
            st.error(f"Search failed: {exc}")
        else:
            st.session_state["results"] = raw
            st.session_state["demo"] = st.session_state.get("demo_mode", False)
            # Remember what this set was fetched with, so a later Apply filters
            # can tell a re-arrange from a genuine re-search.
            st.session_state["fetched_with"] = query
            st.session_state["fetched_limit"] = st.session_state.get("limit", 100)
            st.session_state["recent_titles"] = job_titles.remember(
                st.session_state.get("recent_titles", ()), query.keywords
            )
            # Filtering by workplace means every result is of that kind, even
            # though the posting itself never says so. Remember what was asked
            # for so the cards can label it.
            asked = st.session_state.get("workplace", "Select all")
            st.session_state["searched_workplace"] = "" if asked == "Select all" else asked

if "results" in st.session_state:
    if st.session_state.get("demo"):
        st.info("Demo mode — these are sample results, not live LinkedIn data.")
    workplace = st.session_state.get("searched_workplace", "")
    jobs = [Job(**row) for row in st.session_state["results"]]
    if workplace:
        jobs = [dataclasses.replace(job, workplace=job.workplace or workplace) for job in jobs]
    # Sort order, date window, company and count are applied here, on every
    # run, so changing them re-arranges what is on screen instantly.
    _render_results(
        arrange(jobs, query, st.session_state.get("limit", 100)), query, fetched=len(jobs)
    )
else:
    st.markdown(theme.IDLE_GIF, unsafe_allow_html=True)

# Last, so it sees the details exactly as the widgets left them this run.
details_store.save()
