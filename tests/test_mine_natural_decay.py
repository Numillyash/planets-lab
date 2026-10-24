"""Standard mine/web natural-decay formula, scope and atomic ledger tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import isqrt

import pytest

from planets_lab.rules.mine_natural_decay import (
    EVIDENCE,
    MineDecayAbstain,
    MinefieldState,
    simulate_isolated_natural_mine_decay,
)


def field(field_id=1, *, units=100, owner=2, web=False):
    return MinefieldState(field_id=field_id, owner_id=owner, mine_units=units, is_web=web)


def advance(fields, *, nebula=None, turns=1, max_radius=150, **kwargs):
    if nebula is None:
        nebula = {f.field_id: False for f in fields}
    return simulate_isolated_natural_mine_decay(
        fields=fields,
        nebula_intersects_by_field_id=nebula,
        turns=turns,
        max_radius=max_radius,
        isolated_decay_only_confirmed=True,
        standard_density_confirmed=True,
        **kwargs,
    )


def test_documented_normal_and_web_rates_in_open_space():
    report = advance([field(3, units=100), field(1, units=100, web=True)])
    step, = report.turns
    assert [e.field_id for e in step.events] == [1, 3]
    assert [(e.units_before, e.units_after, e.units_lost) for e in step.events] == [
        (100, 94, 6), (100, 94, 6),
    ]
    assert step.units_before == 200
    assert step.units_after == 188
    assert step.natural_units_lost == 12
    assert [f.is_web for f in report.fields_final] == [True, False]
    assert report.evidence == EVIDENCE
    assert report.host_causal_verified is False
    assert report.host_phase_order_verified is False
    assert report.full_host_mine_lifecycle_verified is False


def test_nebula_faster_decay_with_explicit_mixed_context():
    report = advance(
        [field(11, units=100), field(3, units=100, web=True)],
        nebula={3: True, 11: False},
    )
    assert [(e.field_id, e.units_after) for e in report.turns[0].events] == [
        (3, 84), (11, 94),
    ]
    assert report.total_natural_units_lost == 22
    assert report.final_units == 178
    assert report.fields_final[0].is_web


@pytest.mark.parametrize("units,expected", [
    (1, 0), (2, 1), (3, 2), (4, 3),
    (9, 8), (11, 9), (20, 18), (21, 19),
    (100, 94), (400, 379), (22500, 21374),
])
def test_integer_rounding_without_half_ties(units, expected):
    if units == 22500:
        # 22,500 * 0.95 - 1 = 21,374.
        assert expected == 21374
    result = advance([field(units=units)])
    assert result.turns[0].events[0].units_after == expected


def test_integer_sqrt_radius_and_destroyed_field_removed():
    result = advance([field(2, units=1), field(3, units=400)])
    first = result.turns[0]
    exhausted = first.events[0]
    assert exhausted.field_exhausted
    assert exhausted.units_after == 0
    assert exhausted.radius_before == 1
    assert exhausted.radius_after == 0
    assert [f.field_id for f in first.fields_after] == [3]
    assert first.events[1].radius_before == 20
    assert first.events[1].radius_after == isqrt(379) == 19


def test_multiturn_fixed_context_chain_ledger_reconciles_exactly():
    result = advance(
        [field(7, units=400), field(1, units=1, web=True)],
        turns=4,
    )
    assert len(result.turns) == 4
    assert [x.turn_index for x in result.turns] == [1, 2, 3, 4]
    assert result.turns[0].units_before == result.initially_present_units == 401
    assert result.final_units == sum(f.mine_units for f in result.fields_final)
    assert sum(t.natural_units_lost for t in result.turns) == result.total_natural_units_lost
    assert result.initially_present_units == result.final_units + result.total_natural_units_lost
    for left, right in zip(result.turns, result.turns[1:]):
        assert left.fields_after == right.fields_before
        assert left.units_after == right.units_before
    assert len(result.turns[1].events) == 1


def test_input_order_does_not_affect_field_events_or_state():
    a = [field(9, units=22500), field(3, units=100, web=True)]
    b = list(reversed(a))
    assert advance(a) == advance(b)


def test_call_never_mutates_input_and_result_is_immutable():
    f = [field(1, units=100, owner=4, web=True)]
    original = tuple(f)
    outcome = advance(f)
    assert tuple(f) == original
    assert outcome.turns[0].fields_before == original
    assert outcome.fields_final[0].owner_id == 4
    with pytest.raises(FrozenInstanceError):
        outcome.fields_final[0].mine_units = 999


@pytest.mark.parametrize("units", [10, 30, 50, 70, 90])
def test_unverified_exact_half_rounding_explicitly_abstains(units):
    # The rulebook specifies round() but does not define tie behavior.
    with pytest.raises(MineDecayAbstain, match="tie rounding"):
        advance([field(units=units)])


def test_later_turn_half_tie_abstains_atomically_without_partial_result():
    # At turn 1, 11 -> 9; turn 2, 9 -> 8; turn 3, 8 -> 7;
    # other examples can require the tie check only on a later turn.
    with pytest.raises(MineDecayAbstain, match="tie rounding"):
        advance([field(units=12)], turns=8)


@pytest.mark.parametrize("roster", [
    [field(1, units=1), field(1, units=100)],
    [field(True, units=100)],
    [field(0, units=100)],
    [field(1, owner=0)],
    [field(1, units=0)],
    [field(1, units=True)],
    [field(1, units=22501)],
    [MinefieldState(field_id=1, owner_id=2, mine_units=5, is_web=1)],
])
def test_invalid_or_dense_field_roster_abstains_before_simulation(roster):
    with pytest.raises(MineDecayAbstain):
        advance(roster)


@pytest.mark.parametrize("nebula", [
    {}, {1: False, 2: False}, {1: None}, {1: 1}, {1: "false"},
])
def test_missing_extra_or_untyped_nebula_intersection_abstains(nebula):
    with pytest.raises(MineDecayAbstain):
        advance([field(1)], nebula=nebula)


@pytest.mark.parametrize("max_radius", [0, 99, 151, True, None])
def test_unknown_radius_setting_abstains(max_radius):
    with pytest.raises(MineDecayAbstain):
        advance([field()], max_radius=max_radius)


def test_documented_campaign_100_ly_cap_is_explicit_not_silent():
    normal = advance([field(units=10000)], max_radius=100)
    assert normal.fields_final[0].mine_units == 9499
    with pytest.raises(MineDecayAbstain):
        advance([field(units=10001)], max_radius=100)


@pytest.mark.parametrize("turns", [0, 13, -1, True, 1.5])
def test_out_of_scope_number_of_turns_abstains(turns):
    with pytest.raises(MineDecayAbstain):
        advance([field()], turns=turns)


def test_unconfirmed_interactions_and_dense_rules_fail_closed():
    kwargs = {
        "fields": (field(),),
        "nebula_intersects_by_field_id": {1: False},
    }
    with pytest.raises(MineDecayAbstain, match="not excluded"):
        simulate_isolated_natural_mine_decay(
            **kwargs,
            isolated_decay_only_confirmed=False,
            standard_density_confirmed=True,
        )
    with pytest.raises(MineDecayAbstain, match="dense"):
        simulate_isolated_natural_mine_decay(
            **kwargs,
            isolated_decay_only_confirmed=True,
            standard_density_confirmed=False,
        )


def test_empty_complete_roster_is_noop_but_unknown_context_does_not_promote():
    a = advance([], nebula={}, turns=3)
    assert a.final_units == a.initially_present_units == 0
    assert len(a.turns) == 3
    assert all(t.events == () for t in a.turns)
    with pytest.raises(MineDecayAbstain):
        advance([], nebula={1: True})


def test_unknown_roster_type_is_rejected_not_assumed_empty():
    with pytest.raises(MineDecayAbstain):
        simulate_isolated_natural_mine_decay(
            fields=None,
            nebula_intersects_by_field_id={},
            isolated_decay_only_confirmed=True,
            standard_density_confirmed=True,
        )
