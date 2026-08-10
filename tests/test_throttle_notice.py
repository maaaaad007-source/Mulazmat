"""The rate-limit banner only appears when the results are actually poorer.

A 429 that the backoff recovered from costs the user nothing, and saying
"100 results rather than the 100 asked for" is worse than saying nothing.
"""

from mulazmat.notices import throttle_notice


def test_a_recovered_rate_limit_says_nothing():
    # Everything asked for arrived, with every description — the 429 cost the
    # user nothing, so there is nothing to report.
    assert throttle_notice(throttled=True, found=100, limit=100) == ""


def test_nothing_is_said_when_nothing_was_throttled():
    assert throttle_notice(throttled=False, found=12, limit=100) == ""


def test_a_short_result_set_reports_the_real_numbers():
    notice = throttle_notice(throttled=True, found=37, limit=100)
    assert "37 results rather than the 100 asked for" in notice
    assert "100 results rather than the 100" not in notice


def test_missing_descriptions_are_reported_even_when_the_count_is_whole():
    notice = throttle_notice(
        throttled=True, found=100, limit=100, missing_details=9, detail_count=25
    )
    assert "9 could not be opened for their description" in notice
    assert "stopped at" not in notice


def test_both_losses_are_reported_together():
    notice = throttle_notice(
        throttled=True, found=60, limit=100, missing_details=4, detail_count=25
    )
    assert "stopped at 60 results" in notice
    assert "4 could not be opened" in notice
    assert " and " in notice


def test_the_advice_names_the_details_toggle_only_when_it_was_on():
    with_details = throttle_notice(throttled=True, found=10, limit=100, detail_count=25)
    without = throttle_notice(throttled=True, found=10, limit=100, detail_count=0)

    assert "Fetch full details" in with_details
    assert "Fetch full details" not in without
    assert "fewer results" in without
