"""Streamlit Community Cloud's "Manage app" badge is removed.

The badge only exists on a deployed app, so it cannot be exercised by running
the app here. What can be tested is the removal script itself, against a page
that mimics the cloud's markup — including the hashed class names that made a
CSS-only approach fail.
"""

import pathlib
import re

import pytest

playwright = pytest.importorskip("playwright.sync_api")

THEME = pathlib.Path(__file__).resolve().parents[1] / "src" / "firststapp" / "theme.py"
CHROMIUM = "/opt/pw-browsers/chromium"

#: What the cloud renders, as far as this matters: a hashed wrapper, a variant
#: whose classes we have never seen, the documented test id, and a decoy.
CLOUD_LIKE = """
<body>
  <div id="app">real app content</div>
  <div class="_profileContainer_ab12x_53"><a class="_link_ab12x_9">Manage app</a></div>
  <div class="_somethingNew_zz99_7"><button><span>Manage app</span></button></div>
  <div data-testid="manage-app-button">Manage app</div>
  <div id="decoy">Manage app settings for later</div>
</body>
"""


def _removal_script() -> str:
    """The script as actually shipped, pulled out of the theme module."""
    match = re.search(r"<script>(.*?)</script>", THEME.read_text(), re.S)
    assert match, "the badge-hiding script has gone missing from theme.py"
    return match.group(1)


@pytest.fixture(scope="module")
def page():
    if not pathlib.Path(CHROMIUM).exists():  # pragma: no cover - env dependent
        pytest.skip("chromium not available")

    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page()
        page.set_content(CLOUD_LIKE)
        # On a top-level page window.parent is window, so the script runs as-is.
        page.evaluate(_removal_script())
        page.wait_for_timeout(200)
        yield page
        browser.close()


def _visible(page, selector: str) -> bool:
    element = page.locator(selector)
    return element.count() > 0 and element.first.is_visible()


def test_the_hashed_class_badge_is_hidden(page):
    assert not _visible(page, "._profileContainer_ab12x_53")


def test_a_badge_with_class_names_we_have_never_seen_is_still_hidden(page):
    # This is the case CSS could not cover, and why the script matches on text.
    assert not _visible(page, "._somethingNew_zz99_7")


def test_the_documented_test_id_is_hidden(page):
    assert not _visible(page, '[data-testid="manage-app-button"]')


def test_the_app_itself_is_left_alone(page):
    assert _visible(page, "#app")


def test_text_that_merely_mentions_the_badge_is_not_hidden(page):
    assert _visible(page, "#decoy")
