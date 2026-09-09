from __future__ import annotations

from planets_lab.rules.combat.eligibility import (
    harmonic_weapon_modulation_applies,
    matching_ship_friendly_code_blocks_combat,
)


def test_nonmatching_ship_friendly_codes_do_not_trigger_matching_block() -> None:
    assert matching_ship_friendly_code_blocks_combat(
        left_friendly_code="abc",
        right_friendly_code="Abc",
        left_race_id=1,
        right_race_id=2,
        left_harmonic_weapon_modulation_enabled=False,
        right_harmonic_weapon_modulation_enabled=False,
    ) is False


def test_exact_matching_normal_ship_friendly_code_blocks_combat() -> None:
    assert matching_ship_friendly_code_blocks_combat(
        left_friendly_code="abc",
        right_friendly_code="abc",
        left_race_id=1,
        right_race_id=2,
        left_harmonic_weapon_modulation_enabled=False,
        right_harmonic_weapon_modulation_enabled=False,
    ) is True


def test_documented_ship_friendly_code_exceptions_do_not_block() -> None:
    for friendly_code in ("MKT", "mkt", "NtP", "lfm"):
        assert matching_ship_friendly_code_blocks_combat(
            left_friendly_code=friendly_code,
            right_friendly_code=friendly_code,
            left_race_id=1,
            right_race_id=2,
            left_harmonic_weapon_modulation_enabled=False,
            right_harmonic_weapon_modulation_enabled=False,
        ) is False


def test_enabled_bird_hwm_overrides_exact_matching_fc_suppression() -> None:
    assert matching_ship_friendly_code_blocks_combat(
        left_friendly_code="abc",
        right_friendly_code="abc",
        left_race_id=3,
        right_race_id=2,
        left_harmonic_weapon_modulation_enabled=True,
        right_harmonic_weapon_modulation_enabled=False,
    ) is False


def test_matching_fc_fails_closed_for_bird_with_unknown_hwm_state() -> None:
    assert matching_ship_friendly_code_blocks_combat(
        left_friendly_code="abc",
        right_friendly_code="abc",
        left_race_id=3,
        right_race_id=2,
        left_harmonic_weapon_modulation_enabled=None,
        right_harmonic_weapon_modulation_enabled=False,
    ) is None


def test_nonbird_unknown_hwm_field_is_irrelevant_when_race_is_known() -> None:
    assert matching_ship_friendly_code_blocks_combat(
        left_friendly_code="abc",
        right_friendly_code="abc",
        left_race_id=1,
        right_race_id=2,
        left_harmonic_weapon_modulation_enabled=None,
        right_harmonic_weapon_modulation_enabled=None,
    ) is True


def test_unknown_race_and_unknown_hwm_state_fail_closed() -> None:
    assert matching_ship_friendly_code_blocks_combat(
        left_friendly_code="abc",
        right_friendly_code="abc",
        left_race_id=None,
        right_race_id=2,
        left_harmonic_weapon_modulation_enabled=None,
        right_harmonic_weapon_modulation_enabled=False,
    ) is None


def test_hwm_trigger_requires_bird_exact_match_and_enabled_state() -> None:
    assert harmonic_weapon_modulation_applies(
        bird_race_id=3,
        harmonic_weapon_modulation_enabled=True,
        bird_friendly_code="abc",
        opponent_friendly_code="abc",
    ) is True
    assert harmonic_weapon_modulation_applies(
        bird_race_id=3,
        harmonic_weapon_modulation_enabled=True,
        bird_friendly_code="abc",
        opponent_friendly_code="Abc",
    ) is False
    assert harmonic_weapon_modulation_applies(
        bird_race_id=2,
        harmonic_weapon_modulation_enabled=True,
        bird_friendly_code="abc",
        opponent_friendly_code="abc",
    ) is False


def test_hwm_trigger_fails_closed_when_effective_state_unknown() -> None:
    assert harmonic_weapon_modulation_applies(
        bird_race_id=3,
        harmonic_weapon_modulation_enabled=None,
        bird_friendly_code="abc",
        opponent_friendly_code="abc",
    ) is None
