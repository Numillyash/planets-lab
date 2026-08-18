from __future__ import annotations

import json
from math import hypot
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "red_mite_game_591478.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def axis_delta(a: float, b: float, period: float) -> float:
    return ((b - a + period / 2) % period) - period / 2


def distance(a: list[int], b: list[int], period: float) -> float:
    return hypot(axis_delta(a[0], b[0], period), axis_delta(a[1], b[1], period))


def test_red_mite_identity_boundary_matches_raw_turn() -> None:
    data = load_fixture()
    events = data["events"]

    assert events["329"]["mite_raw_turn"] == events["329"]["tracking_start"]
    assert events["206"]["mite_raw_turn"] == events["206"]["tracking_start"]
    for mite in events["380"]["mites"]:
        assert mite["mite_raw_turn"] == events["380"]["tracking_start"]


def test_clean_tracking_starts_point_at_current_target() -> None:
    data = load_fixture()
    events = data["events"]

    for key in ("329", "206"):
        row = events[key]["start"]
        assert row["mite_wp"] == row["target_xy"]

    for mite in events["380"]["mites"]:
        row = mite["rows"][0]
        assert row["mite_wp"] == row["target_xy"]


def test_329_exact_contact_requires_game_scoped_period_2170() -> None:
    data = load_fixture()
    period = data["period"]
    row = data["events"]["329"]["termination"]

    assert period == 2170
    assert row["mite_xy"] != row["target_xy"]
    assert distance(row["mite_xy"], row["target_xy"], period) == pytest.approx(0.0)


def assert_normal_fallback_navigation(event: dict, period: float, moving_rows: list[dict]) -> None:
    anchor = event["anchor"]
    previous = event["termination"]

    for current in moving_rows:
        assert current["same_identity"] is True
        assert current["mite_wp"] == anchor

        previous_distance = distance(previous["mite_xy"], anchor, period)
        current_distance = distance(current["mite_xy"], anchor, period)
        step = distance(previous["mite_xy"], current["mite_xy"], period)
        expected_step = min(previous["mite_warp"] ** 2, previous_distance)
        progress = previous_distance - current_distance

        assert step == pytest.approx(expected_step, abs=1.5)
        assert progress == pytest.approx(step, abs=0.02)
        assert current_distance <= previous_distance + 1e-9

        previous = current


def test_329_fallback_navigation_reaches_predecessor_coordinate() -> None:
    data = load_fixture()
    event = data["events"]["329"]

    assert event["termination"]["mite_wp"] == event["anchor"]
    assert_normal_fallback_navigation(event, data["period"], event["fallback"][:4])

    arrival = event["fallback"][3]
    stopped = event["fallback"][4]
    assert arrival["mite_xy"] == event["anchor"]
    assert arrival["mite_wp"] == arrival["mite_xy"]
    assert stopped["mite_warp"] == 0
    assert stopped["mite_wp"] == stopped["mite_xy"]


def test_206_uses_same_fallback_law_before_identity_disappears() -> None:
    data = load_fixture()
    event = data["events"]["206"]

    assert event["termination"]["mite_wp"] == event["anchor"]
    assert event["termination"]["target_cloak"] is False
    assert event["termination"]["target_transfer_target_id"] == 452
    assert event["termination"]["target_planet_id"] == 452

    assert_normal_fallback_navigation(event, data["period"], event["fallback"])
    assert event["first_absent_turn"] == 70
    assert distance(event["fallback"][-1]["mite_xy"], event["anchor"], data["period"]) == pytest.approx(100.0)


def test_clear_state_is_not_immediate_destruction() -> None:
    data = load_fixture()

    for key in ("329", "206"):
        first_clear = data["events"][key]["fallback"][0]
        assert first_clear["same_identity"] is True
        assert first_clear["mite_mission"] == 0
        assert first_clear["mite_m1"] == 0


def test_380_cloak_branch_switches_to_self_waypoint_instead_of_fallback_flight() -> None:
    data = load_fixture()
    event = data["events"]["380"]
    anchor = event["anchor"]

    for mite in event["mites"]:
        start, cloak_onset, self_waypoint, clear = mite["rows"]

        assert start["mite_wp"] == start["target_xy"]
        assert cloak_onset["target_cloak"] is True
        assert cloak_onset["target_xy"] == anchor
        assert cloak_onset["mite_wp"] == anchor

        assert self_waypoint["target_cloak"] is True
        assert self_waypoint["mite_wp"] == self_waypoint["mite_xy"]
        assert self_waypoint["mite_wp"] != anchor

        assert clear["mite_mission"] == 0
        assert clear["mite_m1"] == 0
        assert clear["mite_warp"] == 0
        assert clear["mite_wp"] == clear["mite_xy"]
