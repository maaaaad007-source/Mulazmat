"""End-to-end checks that drive the real Streamlit app in demo mode.

Widgets are addressed by key rather than position so that moving a control
between the bar and the filters panel does not silently retarget these tests.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _search(app: AppTest, title: str = "UX Designer", view: str = "Cards") -> AppTest:
    app.selectbox(key="title").set_value(title)
    app.checkbox(key="demo_mode").set_value(True)
    app.radio(key="view").set_value(view)
    return app.button(key="search").click().run()


def _html(app: AppTest) -> str:
    return "".join(md.value for md in app.markdown)


def test_app_starts_with_the_intro_and_no_sidebar_widgets():
    app = _app()
    assert not app.exception
    assert "Search LinkedIn job postings" in _html(app)
    assert not app.sidebar.text_input, "the layout must not use a sidebar"


def test_search_without_a_title_is_rejected():
    app = _app()
    app.button(key="search").click().run()
    assert app.error[0].value == "Enter a job title to search."


def test_topbar_carries_title_company_country_search_and_saved():
    app = _app()
    assert app.selectbox(key="title").placeholder == "Job Title"
    assert app.text_input(key="company").placeholder == "Company (Optional)"
    assert app.selectbox(key="country").value is None  # placeholder state
    assert app.button(key="search").label == "Search"
    # Icon-only button: the bookmark glyph lives in `icon`, not the label.
    assert app.button(key="saved_toggle").label == ""


def test_filters_panel_holds_every_filter():
    app = _app()
    keys = {r.key for r in app.radio} | {c.key for c in app.checkbox} | {s.key for s in app.slider}
    assert {"sort", "date_posted", "workplace", "view"} <= keys
    assert {"exp_Internship", "exp_Director", "fetch_details", "demo_mode"} <= keys
    assert "limit" in keys
    assert app.button(key="apply_filters").label == "Apply filters"


def test_demo_search_renders_cards_with_contact_links():
    app = _search(_app())
    assert not app.exception

    html = _html(app)
    assert "Job Results" in html
    assert '<p class="mz-title">' in html
    assert "Contact &amp; apply" in html
    assert "UX Designer" in html
    # One save button per card.
    assert len([b for b in app.button if b.key.startswith("save_")]) > 0


def test_title_box_suggests_common_titles():
    box = _app().selectbox(key="title")
    assert "UX Designer" in box.options
    assert "Data Analyst" in box.options
    assert len(box.options) > 150


def test_a_hand_typed_title_survives_the_rerun():
    # AppTest cannot type into a combobox, so the value is seeded the way
    # Streamlit delivers it — the point is that it stays put and is searchable.
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["title"] = "Underwater Basket Weaver"
    app.session_state["demo_mode"] = True
    app = app.run()

    assert app.selectbox(key="title").value == "Underwater Basket Weaver"
    app = app.button(key="search").click().run()
    assert "Underwater Basket Weaver" in _html(app)


def test_searching_puts_the_title_at_the_top_of_the_suggestions():
    app = _search(_app(), title="Chef")
    assert app.session_state["recent_titles"] == ("Chef",)
    assert app.selectbox(key="title").options[0] == "Chef"


def test_fetch_full_details_adds_the_description():
    app = _app()
    app.checkbox(key="fetch_details").set_value(True).run()
    app = _search(app)

    html = _html(app)
    assert '<p class="mz-desc">' in html
    # The strip fills out too, since employment type comes from the same page.
    assert "Full-time" in html or "Contract" in html


def test_details_are_off_by_default_so_a_search_is_one_request_per_page():
    # The expensive path is opt-in: leaving it off is what keeps a search
    # inside LinkedIn's rate limit.
    app = _app()
    assert app.checkbox(key="fetch_details").value is False
    assert '<p class="mz-desc">' not in _html(_search(app))


def test_the_detail_slider_only_appears_once_details_are_on():
    app = _app()
    assert not [s for s in app.slider if s.key == "detail_count"]
    app.checkbox(key="fetch_details").set_value(True).run()
    assert app.slider(key="detail_count").value is not None


def test_workplace_filter_labels_the_cards():
    # LinkedIn never states workplace on a search card, but filtering to Remote
    # means every result is remote, so the cards can say so.
    app = _app()
    app.radio(key="workplace").set_value("Remote").run()
    app = _search(app)

    assert app.session_state["searched_workplace"] == "Remote"
    assert "Remote" in _html(app)


def test_no_workplace_filter_leaves_the_label_alone():
    app = _search(_app())
    assert app.session_state["searched_workplace"] == ""


def test_country_selection_seeds_the_geo_id():
    app = _app()
    app.selectbox(key="country").set_value("Netherlands").run()
    assert app.text_input(key="geo_id").value == "102890719"

    app.text_input(key="geo_id").set_value("99999999").run()
    assert app.text_input(key="geo_id").value == "99999999"

    app.selectbox(key="country").set_value("Germany").run()
    assert app.text_input(key="geo_id").value == "101282230"


def test_country_without_a_known_geo_id_falls_back_to_free_text():
    app = _app()
    app.selectbox(key="country").set_value("Tuvalu").run()
    assert app.text_input(key="geo_id").value == ""


def test_table_view_renders_a_dataframe_instead_of_cards():
    app = _search(_app(), view="Table")
    assert app.dataframe
    frame = app.dataframe[0].value
    assert list(frame.columns) == [
        "Title", "Company", "Location", "Workplace", "Posted", "Link"
    ]
    # Match the rendered element, not the class name in the stylesheet.
    assert '<p class="mz-title">' not in _html(app)


def test_company_filter_narrows_results_without_researching():
    app = _search(_app(), view="Table")
    total = len(app.dataframe[0].value)

    app.text_input(key="company").set_value("globex").run()
    narrowed = app.dataframe[0].value

    assert 0 < len(narrowed) < total
    assert narrowed["Company"].str.lower().str.contains("globex").all()


def test_company_filter_with_no_match_explains_itself():
    app = _search(_app(), view="Table")
    app.text_input(key="company").set_value("no-such-company").run()
    assert not app.dataframe
    assert "no-such-company" in app.warning[0].value


def test_apply_filters_collapses_the_panel():
    app = _app()
    assert "filters_panel" not in app.session_state

    app = app.button(key="apply_filters").click().run()
    # Remounting the popover under a new key is what makes it come back closed.
    assert app.session_state["filters_panel"] == 1
    assert not app.exception

    app = app.button(key="apply_filters").click().run()
    assert app.session_state["filters_panel"] == 2


def test_saving_a_job_and_filtering_to_saved_only():
    app = _search(_app())
    save_buttons = [b for b in app.button if b.key.startswith("save_")]
    total = len(save_buttons)

    app = save_buttons[0].click().run()
    assert len(app.session_state["saved"]) == 1

    app = app.button(key="saved_toggle").click().run()
    assert "1 Saved Jobs" in _html(app)
    assert len([b for b in app.button if b.key.startswith("save_")]) == 1 < total


def test_saved_view_is_empty_before_anything_is_saved():
    app = _search(_app())
    app = app.button(key="saved_toggle").click().run()
    assert any("No saved jobs yet" in info.value for info in app.info)


def test_unsaving_removes_the_job_again():
    app = _search(_app())
    app = [b for b in app.button if b.key.startswith("save_")][0].click().run()
    assert len(app.session_state["saved"]) == 1

    app = [b for b in app.button if b.key.startswith("save_")][0].click().run()
    assert len(app.session_state["saved"]) == 0


def test_workplace_select_all_sends_no_workplace_filter():
    app = _app()
    assert app.radio(key="workplace").value == "Select all"
    app.radio(key="workplace").set_value("Remote").run()
    assert app.radio(key="workplace").value == "Remote"


def test_descriptions_can_be_expanded_in_place():
    app = _app()
    app.checkbox(key="fetch_details").set_value(True).run()
    app = _search(app)
    toggles = [b for b in app.button if b.key.startswith("desc_")]
    assert toggles, "long postings should offer a toggle"

    app = toggles[0].click().run()
    assert '<p class="mz-desc mz-desc--full">' in _html(app)
    assert any(b.label == "Show less" for b in app.button)
