"""Your details, remembered between visits.

The cookie itself is a browser thing, so what is tested here is the part that
can be got wrong in Python: what goes into it, what is trusted coming back out,
and the rule that a value already in state is never overwritten.
"""

import json
from urllib.parse import quote

from firststapp import details_store as store

FILLED = {
    "me_name": "Sundus",
    "me_email": "sundus@example.com",
    "me_skills": "Figma, user research",
    "me_profile": "https://www.linkedin.com/in/sunduslive",
}


def cookie(state: dict) -> dict:
    """What the browser would hand back after storing ``state``."""
    return {store.COOKIE: quote(store.encode(state), safe="")}


# --- what gets written -----------------------------------------------------


def test_the_details_round_trip():
    assert store.decode(store.encode(FILLED)) == FILLED


def test_a_url_encoded_cookie_round_trips_too():
    # Which is how it actually comes back: JSON has commas and quotes in it.
    assert store.decode(cookie(FILLED)[store.COOKIE]) == FILLED


def test_nothing_filled_in_means_nothing_stored():
    assert store.encode({}) == ""
    assert store.encode({"me_name": "   "}) == ""


def test_only_the_details_are_stored():
    payload = store.encode({**FILLED, "title": "UX Designer", "saved": {"123"}})
    assert set(json.loads(payload)) == set(FILLED)


def test_values_are_trimmed_and_capped():
    payload = json.loads(store.encode({"me_pitch": "  " + "x" * 900 + "  "}))
    assert payload["me_pitch"] == "x" * store.MAX_FIELD


# --- what is trusted coming back -------------------------------------------


def test_a_damaged_cookie_is_ignored_rather_than_raised():
    for raw in ("", "not json", "[1, 2, 3]", '{"me_name": ', '{"me_name": 42}'):
        assert store.decode(raw) == {}


def test_keys_we_do_not_recognise_are_dropped():
    raw = json.dumps({"me_name": "Sundus", "admin": True, "results": "..."})
    assert store.decode(raw) == {"me_name": "Sundus"}


def test_an_empty_field_in_the_cookie_is_not_restored():
    assert store.decode(json.dumps({"me_name": "  "})) == {}


# --- restoring into a session ----------------------------------------------


def test_details_are_restored_into_a_fresh_session():
    state: dict = {}
    assert store.restore(state, cookie(FILLED)) == len(FILLED)
    assert state["me_name"] == "Sundus"
    assert state["me_email"] == "sundus@example.com"


def test_restoring_happens_once_per_session():
    state: dict = {}
    store.restore(state, cookie(FILLED))
    state["me_name"] = "Someone else"

    # A second run must not undo an edit made after the first.
    assert store.restore(state, cookie(FILLED)) == 0
    assert state["me_name"] == "Someone else"


def test_a_value_already_in_state_wins_over_the_cookie():
    state = {"me_name": "Typed just now"}
    store.restore(state, cookie(FILLED))
    assert state["me_name"] == "Typed just now"
    # The rest still comes back.
    assert state["me_email"] == "sundus@example.com"


def test_no_cookie_at_all_is_not_an_error():
    state: dict = {}
    assert store.restore(state, {}) == 0


# --- the script that does the writing --------------------------------------


def test_the_script_writes_the_cookie_with_a_lifetime():
    js = store.script(store.encode(FILLED))
    assert store.COOKIE in js
    assert str(store.MAX_AGE) in js
    assert "samesite=lax" in js


def test_clearing_the_details_expires_the_cookie():
    js = store.script("")
    assert 'const value = "";' in js
    assert "age = value ?" in js  # empty value → max-age 0 → the browser forgets


def test_the_payload_cannot_break_out_of_the_script():
    nasty = {"me_name": '</script><script>alert(1)</script>'}
    js = store.script(store.encode(nasty))
    assert "</script><script>" not in js
    assert "alert(1)" not in js
