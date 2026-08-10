from mulazmat import job_titles


def test_curated_list_is_unique_case_insensitively():
    lowered = [t.lower() for t in job_titles.TITLES]
    assert len(lowered) == len(set(lowered))


def test_titles_are_stripped_and_non_empty():
    assert all(t == t.strip() and t for t in job_titles.TITLES)


def test_suggestions_are_alphabetical_when_there_is_no_history():
    out = job_titles.suggestions()
    assert out == sorted(out, key=str.lower)
    assert "UX Designer" in out
    assert "Data Analyst" in out


def test_recent_searches_lead_the_list_and_are_not_repeated():
    out = job_titles.suggestions(("Data Analyst", "Chef"))
    assert out[:2] == ["Data Analyst", "Chef"]
    assert out.count("Data Analyst") == 1
    assert out.count("Chef") == 1


def test_current_value_is_always_an_option():
    # The widget rebuilds its options every rerun and drops any value missing
    # from them — that silently discarded titles typed by hand.
    out = job_titles.suggestions(current="Underwater Basket Weaver")
    assert out[0] == "Underwater Basket Weaver"


def test_current_value_already_known_is_not_duplicated():
    out = job_titles.suggestions(("Chef",), current="Chef")
    assert out[0] == "Chef"
    assert out.count("Chef") == 1


def test_blank_current_and_recent_entries_are_ignored():
    out = job_titles.suggestions(("", "   "), current="")
    assert out == sorted(job_titles.TITLES, key=str.lower)


def test_remember_moves_a_title_to_the_front():
    assert job_titles.remember(("Chef", "Nurse"), "Nurse") == ("Nurse", "Chef")


def test_remember_ignores_blank_titles():
    assert job_titles.remember(("Chef",), "   ") == ("Chef",)


def test_remember_is_case_insensitive_about_duplicates():
    assert job_titles.remember(("Chef",), "chef") == ("chef",)


def test_remember_caps_the_history():
    recent: tuple[str, ...] = ()
    for i in range(job_titles.MAX_RECENT + 5):
        recent = job_titles.remember(recent, f"Role {i}")

    assert len(recent) == job_titles.MAX_RECENT
    assert recent[0] == f"Role {job_titles.MAX_RECENT + 4}"  # newest first
