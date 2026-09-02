"""Remember **Your details** between visits.

Streamlit's session state lasts exactly as long as the browser tab. That is
fine for a search, which you redo anyway, and wrong for your own name and
email, which you would otherwise retype every time you came back.

So the details are kept in a cookie, in your own browser:

* **Writing** goes through a zero-height component that sets ``document.cookie``
  on the parent page — the same trick the Manage-app badge removal uses.
* **Reading** goes through ``st.context.cookies``, which is the request's
  cookies, so the values are already there on the first run of a new session.

Nothing is sent anywhere. The cookie is your details, in your browser, readable
only by this app's own domain — there is no server side to this app beyond the
LinkedIn requests, and those never carry it.

The pure functions here take state and cookies as arguments so they can be
tested without a running app; :func:`load` and :func:`save` are the thin
Streamlit-facing wrappers.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, MutableMapping
from urllib.parse import quote, unquote

#: Cookie name. Namespaced so it cannot collide with Streamlit's own.
COOKIE = "mz_details"

#: The session-state keys the details panel writes. Only these are stored, so a
#: future field is opted in deliberately rather than swept up by accident.
FIELDS = (
    "me_name",
    "me_headline",
    "me_email",
    "me_phone",
    "me_location",
    "me_profile",
    "me_skills",
    "me_pitch",
)

#: A year. Long enough to be "remembered", short enough to eventually lapse.
MAX_AGE = 60 * 60 * 24 * 365

#: Per field, to keep the whole cookie comfortably inside the ~4KB browsers
#: allow. The pitch is the only field that could approach it.
MAX_FIELD = 500


def encode(state: Mapping[str, Any]) -> str:
    """The details as JSON, or ``""`` when there is nothing worth keeping."""
    values = {}
    for field in FIELDS:
        value = str(state.get(field) or "").strip()
        if value:
            values[field] = value[:MAX_FIELD]
    return json.dumps(values, separators=(",", ":"), sort_keys=True) if values else ""


def decode(raw: str) -> dict[str, str]:
    """Parse a stored cookie back into details.

    Deliberately forgiving: a cookie can be truncated, hand-edited or left over
    from an older version of the app, and none of that should be an error the
    user sees. Anything unrecognised is dropped.
    """
    if not raw:
        return {}
    try:
        data = json.loads(unquote(raw))
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        key: value[:MAX_FIELD]
        for key, value in data.items()
        if key in FIELDS and isinstance(value, str) and value.strip()
    }


def restore(state: MutableMapping[str, Any], cookies: Mapping[str, str]) -> int:
    """Seed session state from the cookie. Returns how many fields were set.

    Runs once per session, and never overwrites a value already in state — a
    widget the user has touched this run outranks what the browser remembered.
    """
    if state.get("_details_loaded"):
        return 0
    state["_details_loaded"] = True

    restored = 0
    for key, value in decode(cookies.get(COOKIE, "")).items():
        if not str(state.get(key) or ""):
            state[key] = value
            restored += 1
    return restored


def script(payload: str) -> str:
    """The JS that writes — or, given ``""``, clears — the cookie."""
    value = quote(payload, safe="")
    # json.dumps for the literals: the payload is user text and must not be
    # able to end the string it sits in.
    return f"""
    <script>
    try {{
      const doc = (window.parent && window.parent.document) || document;
      const value = {json.dumps(value)};
      const age = value ? {MAX_AGE} : 0;
      doc.cookie = {json.dumps(COOKIE)} + "=" + value +
        ";path=/;max-age=" + age + ";samesite=lax";
    }} catch (err) {{ /* cookies blocked: the details just will not persist */ }}
    </script>
    """


def load() -> None:
    """Restore the details for this session, if the browser remembers any."""
    import streamlit as st

    try:
        cookies = st.context.cookies or {}
    except Exception:  # noqa: BLE001 — no context (tests, bare mode): carry on
        cookies = {}
    restore(st.session_state, cookies)


def save() -> None:
    """Write the details back to the browser, but only when they changed.

    Re-rendering the component on every run would mean an iframe per rerun for
    no gain, so the last payload written is remembered in session state.
    """
    import streamlit as st
    import streamlit.components.v1 as components

    payload = encode(st.session_state)
    if st.session_state.get("_details_saved") == payload:
        return
    st.session_state["_details_saved"] = payload
    components.html(script(payload), height=0)
