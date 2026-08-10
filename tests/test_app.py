"""End-to-end checks that drive the real Streamlit app in demo mode."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def test_app_starts_with_a_prompt_and_no_results():
    app = _app()
    assert not app.exception
    assert any("press **Search**" in info.value for info in app.info)


def test_search_without_a_title_is_rejected():
    app = _app()
    app.button[0].click().run()
    assert app.error[0].value == "Enter a job title to search."


def test_demo_search_renders_results_and_export():
    app = _app()
    app.text_input[0].set_value("Data Analyst")
    app.selectbox[0].set_value("Pakistan")
    app.toggle[0].set_value(True)
    app.button[0].click().run()

    assert not app.exception
    assert app.dataframe, "expected a results table"

    frame = app.dataframe[0].value
    assert len(frame) > 0
    assert list(frame.columns) == ["Title", "Company", "Location", "Posted", "Salary", "Link"]
    assert frame["Title"].str.contains("Data Analyst").all()
    assert frame["Location"].str.contains("Pakistan|Remote").all()

    assert app.metric[0].label == "Jobs shown"


def test_company_filter_narrows_results_without_researching():
    app = _app()
    app.text_input[0].set_value("Data Analyst")
    app.toggle[0].set_value(True)
    app.button[0].click().run()
    total = len(app.dataframe[0].value)

    # Typing a company re-renders from the cached results; no new search is run.
    app.text_input[1].set_value("careem").run()
    narrowed = app.dataframe[0].value

    assert 0 < len(narrowed) < total
    assert narrowed["Company"].str.lower().str.contains("careem").all()


def test_company_filter_with_no_match_explains_itself():
    app = _app()
    app.text_input[0].set_value("Data Analyst")
    app.toggle[0].set_value(True)
    app.button[0].click().run()

    app.text_input[1].set_value("no-such-company").run()
    assert not app.dataframe
    assert "no-such-company" in app.warning[0].value


def test_country_selectbox_is_alphabetical_and_complete():
    options = _app().selectbox[0].options
    assert options[1:] == sorted(options[1:])
    assert "Pakistan" in options and "Zimbabwe" in options
    assert len(options) > 190


@pytest.mark.parametrize("label", ["Date posted", "Sort by"])
def test_filter_selectboxes_exist(label):
    assert any(box.label == label for box in _app().selectbox)
