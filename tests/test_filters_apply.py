"""Applying filters actually re-runs the search.

"Apply filters" used to only close the panel, so changing sort order, dates or
anything else appeared to do nothing until Search was pressed again.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from firststapp import filters
from firststapp.linkedin import build_params
from firststapp.models import SearchQuery

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _searched(app: AppTest, title: str = "UX Designer") -> AppTest:
    app.selectbox(key="title").set_value(title)
    app.checkbox(key="demo_mode").set_value(True)
    return app.button(key="search").click().run()


def _fetched(app: AppTest) -> int:
    """How many jobs were actually retrieved from LinkedIn."""
    # AppTest's session_state has no .get(), so check membership first.
    return len(app.session_state["results"]) if "results" in app.session_state else 0


def _shown(app: AppTest) -> int:
    """How many cards are on screen after arranging."""
    return len([b for b in app.button if b.key.startswith("save_")])


def test_apply_filters_rearranges_without_searching_again():
    app = _searched(_app())
    assert _fetched(app) == 40 and _shown(app) == 40

    app.slider(key="limit").set_value(25).run()
    app = app.button(key="apply_filters").click().run()

    assert _shown(app) == 25, "the cards on screen should have been trimmed"
    assert _fetched(app) == 40, "trimming the count should not re-fetch anything"


def test_apply_filters_still_collapses_the_panel():
    app = _searched(_app())
    assert "filters_panel" not in app.session_state  # untouched until first use

    app = app.button(key="apply_filters").click().run()
    assert app.session_state["filters_panel"] == 1


def test_applying_filters_before_any_search_does_not_error():
    # Someone setting filters up first should not be scolded for it.
    app = _app()
    app = app.button(key="apply_filters").click().run()

    assert not app.error
    assert "results" not in app.session_state


def test_sort_order_reaches_the_query():
    app = _app()
    app.radio(key="sort").set_value("Most recent").run()
    assert app.session_state["sort"] == "Most recent"
    assert filters.SORT_OPTIONS["Most recent"] == "DD"


def test_sort_order_reaches_linkedin_as_a_parameter():
    recent = SearchQuery(keywords="x", sort_by=filters.SORT_OPTIONS["Most recent"])
    relevant = SearchQuery(keywords="x", sort_by=filters.SORT_OPTIONS["Most relevant"])

    assert build_params(recent)["sortBy"] == "DD"
    assert build_params(relevant)["sortBy"] == "R"


def test_sort_order_is_part_of_the_cache_key():
    # Otherwise a re-search would hand back the previous order from cache.
    recent = SearchQuery(keywords="x", sort_by="DD")
    relevant = SearchQuery(keywords="x", sort_by="R")
    assert recent.cache_key() != relevant.cache_key()


def test_every_filter_is_part_of_the_cache_key():
    base = SearchQuery(keywords="x")
    variations = [
        SearchQuery(keywords="x", date_posted="r86400"),
        SearchQuery(keywords="x", experience_levels=("2",)),
        SearchQuery(keywords="x", workplace_types=("2",)),
        SearchQuery(keywords="x", geo_id="123"),
        SearchQuery(keywords="x", location="Sweden"),
    ]
    for variant in variations:
        assert variant.cache_key() != base.cache_key()
