from __future__ import annotations

from tools.diagnostics.combat_host_matching_fc_hwm_audit import (
    _hwm_observation,
    _matching_fc_kind,
    _site_position,
)


def test_matching_fc_kind_is_exact_case_sensitive() -> None:
    assert _matching_fc_kind("abc", "abc") == "ordinary_exact_match"
    assert _matching_fc_kind("abc", "Abc") == "not_matching"


def test_matching_fc_kind_recognizes_documented_ship_exceptions_case_insensitively() -> None:
    for value in ("MKT", "mkt", "NtP", "Lfm"):
        assert _matching_fc_kind(value, value) == "documented_ship_exception"


def test_hwm_observation_requires_bird_for_nonexception_match() -> None:
    assert _hwm_observation(
        matching_fc_kind="ordinary_exact_match",
        left_race_id=1,
        right_race_id=2,
        left_start_shield=100,
        right_start_shield=100,
        site_first_ship_vcr=True,
    ) == "nonbird_nonexception_matching_vcr"


def test_hwm_observation_detects_unshielded_bird_opponent_on_first_site_vcr() -> None:
    assert _hwm_observation(
        matching_fc_kind="ordinary_exact_match",
        left_race_id=3,
        right_race_id=2,
        left_start_shield=100,
        right_start_shield=0,
        site_first_ship_vcr=True,
    ) == "bird_enemy_unshielded_first_site"


def test_hwm_observation_does_not_confuse_prior_combat_with_clean_first_site_signal() -> None:
    assert _hwm_observation(
        matching_fc_kind="ordinary_exact_match",
        left_race_id=3,
        right_race_id=2,
        left_start_shield=100,
        right_start_shield=0,
        site_first_ship_vcr=False,
    ) == "bird_enemy_unshielded_after_prior_site_vcr"


def test_documented_ship_exception_is_not_labeled_hwm() -> None:
    assert _hwm_observation(
        matching_fc_kind="documented_ship_exception",
        left_race_id=3,
        right_race_id=2,
        left_start_shield=100,
        right_start_shield=0,
        site_first_ship_vcr=True,
    ) == "documented_ship_fc_exception"


def test_site_position_is_one_based() -> None:
    assert _site_position([8, 4, 10], 8) == {
        "site_ship_vcr_ids": [4, 8, 10],
        "site_ship_vcr_count": 3,
        "site_ship_vcr_index": 2,
        "site_first_ship_vcr": False,
        "site_prior_ship_vcr_count": 1,
    }
