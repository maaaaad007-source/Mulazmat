"""End-to-end checks that drive the real Streamlit app in demo mode.

Widgets are addressed by key rather than position so that adding a control to
the sidebar does not silently retarget these tests.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _demo_search(app: AppTest, title: str = "Data Analyst", view: str = "Cards") -> AppTest:
    app.text_input(key="title").set_value(title)
    app.toggle(key="demo_mode").set_value(True)
    app.radio(key="view").set_value(view)
    return app.button(key="search").click().run()


def test_app_starts_with_a_prompt_and_no_results():
    app = _app()
    assert not app.exception
    assert any("press **Search**" in info.value for info in app.info)


def test_search_without_a_title_is_rejected():
    app = _app()
    app.button(key="search").click().run()
    assert app.error[0].value == "Enter a job title to search."


def test_demo_search_renders_cards_by_default():
    app = _demo_search(_app())
    assert not app.exception

    html = "".join(md.value for md in app.markdown)
    assert 'class="mz-grid"' in html
    assert html.count("<article") > 0
    assert "Data Analyst" in html
    assert app.metric[0].label == "Jobs shown"


def test_cards_carry_contact_and_apply_links():
    html = "".join(md.value for md in _demo_search(_app()).markdown)
    assert "Contact &amp; apply" in html
    assert "linkedin.com/company/" in html
    assert ">Apply<" in html


def test_table_view_renders_a_dataframe_instead():
    app = _demo_search(_app(), view="Table")
    assert app.dataframe, "expected a results table"

    frame = app.dataframe[0].value
    assert len(frame) > 0
    assert list(frame.columns) == ["Title", "Company", "Location", "Posted", "Salary", "Link"]
    assert frame["Title"].str.contains("Data Analyst").all()
    assert 'class="mz-grid"' not in "".join(md.value for md in app.markdown)


def test_company_filter_narrows_results_without_researching():
    app = _demo_search(_app(), view="Table")
    total = len(app.dataframe[0].value)

    # Typing a company re-renders from the cached results; no new search is run.
    app.text_input(key="company").set_value("careem").run()
    narrowed = app.dataframe[0].value

    assert 0 < len(narrowed) < total
    assert narrowed["Company"].str.lower().str.contains("careem").all()


def test_company_filter_with_no_match_explains_itself():
    app = _demo_search(_app(), view="Table")

    app.text_input(key="company").set_value("no-such-company").run()
    assert not app.dataframe
    assert "no-such-company" in app.warning[0].value


def test_country_selectbox_is_alphabetical_and_complete():
    options = _app().selectbox(key="country").options
    assert options[1:] == sorted(options[1:])
    assert "Pakistan" in options and "Zimbabwe" in options
    assert len(options) > 190


def test_detail_count_slider_only_appears_when_enrichment_is_on():
    app = _app()
    assert not [s for s in app.slider if s.key == "detail_count"]

    app.toggle(key="fetch_details").set_value(True).run()
    assert app.slider(key="detail_count").value == 15


def test_geo_id_autofills_per_country_and_keeps_manual_overrides():
    app = _app()
    assert app.text_input(key="geo_id").value == ""  # "Anywhere" has none

    app.selectbox(key="country").set_value("United States").run()
    assert app.text_input(key="geo_id").value == "103644278"

    # A hand-typed id sticks while the country is unchanged...
    app.text_input(key="geo_id").set_value("99999999").run()
    assert app.text_input(key="geo_id").value == "99999999"

    # ...and is re-seeded when the country changes.
    app.selectbox(key="country").set_value("Pakistan").run()
    assert app.text_input(key="geo_id").value == "101022442"


def test_country_without_a_known_geo_id_falls_back_to_free_text():
    app = _app()
    app.selectbox(key="country").set_value("Tuvalu").run()
    assert app.text_input(key="geo_id").value == ""


def test_selected_country_flows_into_the_search():
    app = _app()
    app.text_input(key="title").set_value("Data Analyst")
    app.selectbox(key="country").set_value("Pakistan")
    app.toggle(key="demo_mode").set_value(True)
    app.button(key="search").click().run()

    assert app.text_input(key="geo_id").value == "101022442"
    assert "Pakistan" in "".join(md.value for md in app.markdown)
