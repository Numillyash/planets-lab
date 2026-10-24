"""Synthetic-only full-roster isolated mine decay and PRE/POST web boundary audit."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_decay_web_phase_audit import (
    MineDecayPhaseAuditAbstain,
    SOURCE_SYNTHETIC, SOURCE_EXTERNAL,
    audit_conditional_natural_decay_web_phase_pair,
)


def field(fid=3, *, owner=5, x=0, y=0, units=100, web=True):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


def run(*, before=None, after=None, nebula=None, position=Point(0, 0), **kwargs):
    before = (field(), field(5, owner=6, x=100, units=400, web=False)) if before is None else before
    after = (field(units=94), field(5, owner=6, x=100, units=379, web=False)) if after is None else after
    nebula = {3: False, 5: False} if nebula is None else nebula
    params = dict(
        fields_before_decay=before,
        fields_after_decay=after,
        nebula_intersects_by_field_id=nebula,
        selected_web_field_id=3,
        ship_position=position,
        max_radius=150,
        source_kind=SOURCE_SYNTHETIC,
        complete_before_and_after_field_rosters_confirmed=True,
        phase_adjacent_natural_decay_only_confirmed=True,
        exact_static_centers_owners_types_confirmed=True,
        exact_per_field_nebula_membership_confirmed=True,
        ordinary_density_and_no_special_host_modifiers_confirmed=True,
    )
    params.update(kwargs)
    return audit_conditional_natural_decay_web_phase_pair(**params)


def test_exact_full_roster_delta_and_safe_pre_post_geometry():
    result = run()
    assert result.conditional_arithmetic_outcome == "EXACT_MATCH"
    assert result.geometry_outcome == "PHASE_PAIR_CLASSIFIED"
    assert result.pre_web_geometry_class == "INSIDE_CONFIRMED"
    assert result.post_web_geometry_class == "INSIDE_CONFIRMED"
    assert result.total_units_before == 500
    assert result.total_units_expected_after == result.total_units_observed_after == 473
    assert result.total_units_expected_natural_loss == 27
    assert [f.field_id for f in result.field_deltas] == [3, 5]
    assert [f.expected_units_after for f in result.field_deltas] == [94, 379]
    assert all(f.matches_conditional_formula for f in result.field_deltas)
    assert not result.source_phase_authenticated
    assert not result.actual_host_decay_verified
    assert not result.actual_web_sweep_verified
    assert not result.actual_web_drain_verified
    assert not result.host_diff_verified
    assert not result.source_or_host_state_mutated


def test_pre_inside_post_edge_abstain_is_not_claimed_as_drain():
    result = run(position=Point(10, 0))
    assert result.conditional_arithmetic_outcome == "EXACT_MATCH"
    assert result.pre_web_geometry_class == "INSIDE_CONFIRMED"
    assert result.post_web_geometry_class == "EDGE_ABSTAIN"
    assert result.geometry_outcome == "EDGE_ABSTAIN"
    assert not result.actual_web_drain_verified


def test_full_roster_contains_nebula_and_exact_field_exhaustion():
    before = (field(units=1), field(5, owner=6, x=100, units=100, web=False))
    after = (field(5, owner=6, x=100, units=84, web=False),)
    result = run(before=before, after=after, nebula={3: False, 5: True})
    assert result.conditional_arithmetic_outcome == "EXACT_MATCH"
    assert result.field_deltas[0].expected_units_after == 0
    assert result.field_deltas[1].expected_units_after == 84
    assert result.pre_web_geometry_class == "INSIDE_CONFIRMED"
    assert result.post_web_geometry_class is None
    assert result.geometry_outcome == "FIELD_EXHAUSTED"
    assert result.total_units_before == 101
    assert result.total_units_expected_after == 84


def test_wrong_post_decay_units_are_conditional_mismatch_not_a_host_failure():
    after = (field(units=95), field(5, owner=6, x=100, units=379, web=False))
    result = run(after=after, source_kind=SOURCE_EXTERNAL)
    assert result.source_kind == SOURCE_EXTERNAL
    assert result.conditional_arithmetic_outcome == "SOURCE_MISMATCH"
    assert result.total_units_observed_after == 474
    assert result.total_units_expected_after == 473
    assert not result.field_deltas[0].matches_conditional_formula
    assert result.field_deltas[1].matches_conditional_formula
    assert result.pre_web_geometry_class is None
    assert result.post_web_geometry_class is None
    assert result.geometry_outcome == "NOT_EVALUATED_MISMATCH"
    assert not result.actual_host_decay_verified
    assert not result.source_phase_authenticated


def test_missing_expected_live_field_is_arithmetic_mismatch_not_fabricated_exhaustion():
    result = run(after=(field(5, owner=6, x=100, units=379, web=False),))
    assert result.conditional_arithmetic_outcome == "SOURCE_MISMATCH"
    assert result.field_deltas[0].observed_units_after == 0
    assert result.field_deltas[0].expected_units_after == 94
    assert result.pre_web_geometry_class is None


def test_original_order_and_input_objects_are_unchanged():
    before = [field(5, owner=6, x=100, units=400, web=False), field()]
    after = [field(5, owner=6, x=100, units=379, web=False), field(units=94)]
    r1 = run(before=before, after=after)
    r2 = run(before=list(reversed(before)), after=list(reversed(after)))
    assert r1 == r2
    assert before[0].mine_units == 400 and after[0].mine_units == 379
    with pytest.raises(FrozenInstanceError):
        r1.conditional_arithmetic_outcome = "HOST_VERIFIED"


def test_empty_roster_cannot_claim_selected_web_field():
    with pytest.raises(MineDecayPhaseAuditAbstain, match="selected"):
        run(before=(), after=(), nebula={})


def test_missing_web_or_nonweb_target_abstains():
    before = (field(3, web=False),)
    with pytest.raises(MineDecayPhaseAuditAbstain, match="web field"):
        run(before=before, after=(field(3, web=False, units=94),),
            nebula={3: False})


def test_half_tie_rounding_abstains_before_any_geometry():
    with pytest.raises(MineDecayPhaseAuditAbstain, match="tie rounding"):
        run(before=(field(units=10),), after=(field(units=9),),
            nebula={3: False})


def test_external_phase_assertion_does_not_authenticate_any_snapshot():
    r = run(source_kind=SOURCE_EXTERNAL)
    assert r.conditional_arithmetic_outcome == "EXACT_MATCH"
    assert r.source_kind == SOURCE_EXTERNAL
    assert r.source_phase_authenticated is False
    assert r.host_diff_verified is False


@pytest.mark.parametrize("changes", [
    {"source_kind": "PUBLIC_T_MINUS_1_TO_T"},
    {"source_kind": "HOST_ACTUAL_VERIFIED"},
    {"source_kind": None},
    {"source_kind": True},
    {"selected_web_field_id": True},
    {"selected_web_field_id": 0},
    {"selected_web_field_id": 42},
    {"ship_position": Point(True, 0)},
    {"ship_position": (0, 0)},
    {"ship_position": Point(1_000_001, 0)},
    {"max_radius": 101},
    {"max_radius": True},
    {"fields_before_decay": None},
    {"fields_after_decay": None},
    {"fields_before_decay": (field(), field())},
    {"fields_after_decay": (field(units=94), field(units=94))},
    {"fields_before_decay": (field(fid=True),)},
    {"fields_before_decay": (field(owner=True),)},
    {"fields_before_decay": (field(units=True),)},
    {"fields_before_decay": (field(web=1),)},
    {"fields_before_decay": (field(units=22501),)},
    {"fields_before_decay": (field(x=True),)},
    {"fields_after_decay": (field(fid=9),)},
    {"fields_after_decay": (field(owner=6, units=94),)},
    {"fields_after_decay": (field(x=1, units=94),)},
    {"fields_after_decay": (field(web=False, units=94),)},
    {"nebula_intersects_by_field_id": {3: False}},
    {"nebula_intersects_by_field_id": {3: False, 5: 1}},
    {"nebula_intersects_by_field_id": {3: False, 5: False, 6: True}},
    {"nebula_intersects_by_field_id": None},
    {"complete_before_and_after_field_rosters_confirmed": False},
    {"complete_before_and_after_field_rosters_confirmed": 1},
    {"phase_adjacent_natural_decay_only_confirmed": False},
    {"exact_static_centers_owners_types_confirmed": None},
    {"exact_per_field_nebula_membership_confirmed": False},
    {"ordinary_density_and_no_special_host_modifiers_confirmed": False},
])
def test_ambiguous_source_or_changed_identity_atomic_abstain(changes):
    with pytest.raises(MineDecayPhaseAuditAbstain):
        run(**changes)


def test_source_kind_and_full_roster_require_all_other_phases_excluded():
    # A turn-pair containing lay/sweep/combat is not a decay phase boundary.
    for kind in (SOURCE_SYNTHETIC, SOURCE_EXTERNAL):
        with pytest.raises(MineDecayPhaseAuditAbstain, match="isolated phase"):
            run(source_kind=kind,
                phase_adjacent_natural_decay_only_confirmed=False)
