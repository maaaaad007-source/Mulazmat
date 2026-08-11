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


def test_the_idle_state_is_a_gif_not_a_wall_of_text():
    app = _app()
    assert not app.exception

    html = _html(app)
    assert 'class="mz-idle"' in html
    assert "giphy.com" in html
    assert "Search LinkedIn job postings" not in html
    assert not app.sidebar.text_input, "the layout must not use a sidebar"


def test_the_gif_gives_way_to_results():
    html = _html(_search(_app()))
    assert 'class="mz-idle"' not in html
    assert "Job Results" in html


def test_streamlit_clouds_manage_app_badge_is_hidden():
    from mulazmat import theme

    assert '[data-testid="manage-app-button"]' in theme.STYLES
    assert '[class*="_profileContainer"]' in theme.STYLES


def test_the_browser_tab_is_named_oolazim():
    source = Path(APP).read_text()
    assert 'page_title="oolazim"' in source


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


def test_fetch_full_details_puts_a_description_on_the_cards():
    app = _app()
    app.checkbox(key="fetch_details").set_value(True).run()
    app = _search(app)

    html = _html(app)
    assert '<p class="mz-desc">' in html
    # And the strip fills out, because employment type comes from the same place.
    assert "Full-time" in html or "Contract" in html


def test_without_enrichment_cards_carry_no_description():
    html = _html(_search(_app()))
    assert '<p class="mz-desc">' not in html


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


def _write_email(app: AppTest) -> AppTest:
    """Open the first card's draft."""
    return [b for b in app.button if b.key.startswith("email_")][0].click().run()


def test_every_card_offers_to_write_an_email():
    app = _search(_app())
    cards = len([b for b in app.button if b.key.startswith("save_")])
    assert len([b for b in app.button if b.key.startswith("email_")]) == cards


def test_writing_an_email_fills_in_a_draft_about_that_posting():
    app = _search(_app(), title="UX Designer")
    app = _write_email(app)
    assert not app.exception

    subject = [i for i in app.text_input if i.key.startswith("subj_")][0]
    body = [a for a in app.text_area if a.key.startswith("body_")][0]

    assert "UX Designer" in subject.value
    assert "UX Designer" in body.value
    # Addressed to the company on that card, and signed with the profile.
    assert "Northwind Studio" in body.value
    assert "linkedin.com/in/sunduslive" in body.value


def test_the_draft_only_opens_on_the_card_you_clicked():
    app = _write_email(_search(_app()))
    assert len([a for a in app.text_area if a.key.startswith("body_")]) == 1
    assert len(app.session_state["emailing"]) == 1


def test_your_details_are_written_into_the_draft():
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["me_name"] = "Sundus"
    app.session_state["me_email"] = "sundus@example.com"
    app.session_state["me_skills"] = "user research, Figma"
    app = _write_email(_search(app.run()))

    body = [a for a in app.text_area if a.key.startswith("body_")][0].value
    assert body.rstrip().endswith("https://www.linkedin.com/in/sunduslive")
    assert "sundus@example.com" in body
    assert "Sundus" in body


def test_the_details_panel_seeds_the_owners_profile():
    app = _app()
    assert app.text_input(key="me_profile").value == "https://www.linkedin.com/in/sunduslive"
    assert {"me_name", "me_email", "me_headline"} <= {i.key for i in app.text_input}
    assert {"me_skills", "me_pitch"} <= {a.key for a in app.text_area}


def test_the_draft_can_be_edited_and_survives_a_rerun():
    app = _write_email(_search(_app()))
    body = [a for a in app.text_area if a.key.startswith("body_")][0]
    app = body.set_value("My own words entirely.").run()

    assert [a for a in app.text_area if a.key.startswith("body_")][0].value == (
        "My own words entirely."
    )


def test_regenerate_throws_hand_edits_away():
    app = _write_email(_search(_app()))
    key = [a for a in app.text_area if a.key.startswith("body_")][0].key
    app = app.text_area(key=key).set_value("scratch that").run()

    app = [b for b in app.button if b.key.startswith("regen_")][0].click().run()
    assert app.text_area(key=key).value != "scratch that"
    assert "Job Results" in _html(app)


def test_changing_tone_rewrites_the_draft():
    app = _write_email(_search(_app()))
    tone = [r for r in app.radio if r.key.startswith("tone_")][0]
    assert tone.value == "Professional"
    before = [a for a in app.text_area if a.key.startswith("body_")][0].value

    app = tone.set_value("Short").run()
    after = [a for a in app.text_area if a.key.startswith("body_")][0].value
    assert after != before
    assert len(after) < len(before)


def test_closing_the_draft_puts_the_card_back():
    app = _write_email(_search(_app()))
    app = [b for b in app.button if b.key.startswith("email_")][0].click().run()
    assert not [a for a in app.text_area if a.key.startswith("body_")]
    assert not app.session_state["emailing"]


def test_the_recipient_box_starts_empty_because_linkedin_publishes_none():
    app = _write_email(_search(_app()))
    to = [i for i in app.text_input if i.key.startswith("to_")][0]
    assert to.value == ""
    assert "LinkedIn does not publish one" in to.placeholder


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


def test_detail_slider_only_appears_when_enrichment_is_on():
    app = _app()
    assert not [s for s in app.slider if s.key == "detail_count"]
    app.checkbox(key="fetch_details").set_value(True).run()
    assert app.slider(key="detail_count").value is not None
