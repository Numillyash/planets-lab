"""Synthetic pre/post conflict stage evidence gate; NEVER tests live NuHost."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_conflict_transition_audit import (
    EVIDENCE, POST_STAGE, PRE_STAGE,
    MineConflictTransitionAbstain, audit_isolated_hostile_mine_transition,
)


def f(fid=11, owner=1, *, x=0, y=0, units=100, web=False):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


PRE = (f(11), f(23, 2, x=15))


def audit(*, before=None, after=None, safe=None, **changes):
    before = PRE if before is None else before
    after = (f(23, 2, x=15, units=70),) if after is None else after
    if safe is None:
        owners = (
            sorted({v.owner_id for v in before if not v.is_web})
            if isinstance(before, (tuple, list))
            and all(type(v) is LocatedMinefield for v in before)
            else []
        )
        safe = {
            (o, p): False
            for idx, o in enumerate(owners) for p in owners[idx + 1:]
        }
    args = dict(
        before_fields=before,
        after_fields=after,
        mutual_safe_passage_by_normal_owner_pair=safe,
        max_radius=150,
        turn_number=17,
        before_stage=PRE_STAGE,
        after_stage=POST_STAGE,
        complete_before_roster_provenance_confirmed=True,
        complete_after_roster_provenance_confirmed=True,
        stage_adjacency_and_no_other_mutations_confirmed=True,
        exact_unchanged_diplomacy_and_owner_confirmed=True,
        ordinary_standard_no_protofield_or_custom_rules_confirmed=True,
        independently_authenticated_host_stage_receipts_confirmed=True,
    )
    args.update(changes)
    return audit_isolated_hostile_mine_transition(**args)


def test_isolated_pair_conditional_compatibility_has_no_host_claims():
    result = audit()
    assert result.field_ids == (11, 23)
    assert result.pre_units == (100, 100)
    assert result.post_units == (None, 70)
    assert result.observed_net_unit_change_by_field == (100, 30)
    assert result.outcome == "COMPATIBLE_ONE_ELIMINATED"
    assert result.eliminated_field_id == 11
    assert result.surviving_field_id == 23
    assert result.turn_number == 17
    assert result.evidence == EVIDENCE
    assert not result.actual_host_collision_causally_verified
    assert not result.host_unit_loss_formula_verified
    assert not result.host_order_execution_verified
    assert not result.host_diff_verified
    assert not result.state_mutated


def test_reverse_winner_different_losses_are_both_compatible_not_a_formula():
    a = audit(after=(f(11, units=60),))
    b = audit(after=(f(11, units=90),))
    assert a.outcome == b.outcome == "COMPATIBLE_ONE_ELIMINATED"
    assert (a.observed_net_unit_change_by_field, b.observed_net_unit_change_by_field) == (
        (40, 100), (10, 100),
    )
    assert a.eliminated_field_id == b.eliminated_field_id == 23


def test_both_fields_persist_is_a_conditional_contradiction_not_a_host_bug_claim():
    result = audit(after=(f(11, units=20), f(23, 2, x=15, units=20)))
    assert result.outcome == "CONTRADICTED_BOTH_SURVIVE"
    assert result.eliminated_field_id is None
    assert result.surviving_field_id is None
    assert result.observed_net_unit_change_by_field == (80, 80)
    assert not result.host_diff_verified


def test_one_eliminated_but_survivor_growth_conditional_contradiction():
    # Pre 100 -> post 110; it is still a typed valid ordinary minefield.
    result = audit(after=(f(23, 2, x=15, units=110),))
    assert result.outcome == "CONTRADICTED_SURVIVOR_GROWTH"
    assert result.observed_net_unit_change_by_field == (100, -10)
    assert not result.actual_host_collision_causally_verified


def test_dual_disappearance_and_zero_survivor_loss_are_abstentions():
    with pytest.raises(MineConflictTransitionAbstain, match="both disappeared"):
        audit(after=())
    with pytest.raises(MineConflictTransitionAbstain, match="no observed loss"):
        audit(after=(f(23, 2, x=15),))


def test_unrelated_normal_and_web_fields_must_be_unchanged():
    before = PRE + (f(30, 3, x=500, units=100), f(40, 4, x=1000, web=True))
    after = (f(23, 2, x=15, units=80), before[2], before[3])
    r = audit(before=before, after=after)
    assert r.outcome == "COMPATIBLE_ONE_ELIMINATED"
    assert r.unrelated_field_count == 2
    assert r.pre_field_count == 4
    assert r.post_field_count == 3
    for bad_after in (
        after[:-1],
        (f(23, 2, x=15, units=80), f(30, 3, x=500, units=99), before[3]),
        after + (f(50, 5, x=1500),),
    ):
        with pytest.raises(MineConflictTransitionAbstain, match="unrelated|unknown/new"):
            audit(before=before, after=bad_after)


def test_reversed_source_rosters_return_identical_immutable_summary():
    before = PRE + (f(40, 3, x=1000, units=225),)
    after = (f(23, 2, x=15, units=35), before[2])
    a = audit(before=before, after=after)
    b = audit(before=tuple(reversed(before)), after=list(reversed(after)))
    assert a == b
    assert before[0].mine_units == 100
    with pytest.raises(FrozenInstanceError):
        a.outcome = "REAL_HOST_VERIFIED"


def test_exact_mutual_safe_passage_and_web_do_not_become_false_conflict_witness():
    with pytest.raises(MineConflictTransitionAbstain, match="exactly one"):
        audit(safe={(1, 2): True})
    with pytest.raises(MineConflictTransitionAbstain, match="exactly one"):
        audit(before=(f(11), f(23, 2, x=15, web=True)))


def test_no_overlap_and_tangent_are_not_claimed_conflicts():
    with pytest.raises(MineConflictTransitionAbstain, match="exactly one"):
        audit(before=(f(11), f(23, 2, x=21)))
    with pytest.raises(MineConflictTransitionAbstain, match="tangent"):
        audit(before=(f(11), f(23, 2, x=20)))


def test_multifield_coupling_and_two_separate_conflicts_abstain():
    coupled = (f(11), f(23, 2, x=15), f(31, 3, x=30))
    distinct = PRE + (f(31, 3, x=300), f(42, 4, x=315))
    for before in (coupled, distinct):
        with pytest.raises(MineConflictTransitionAbstain, match="exactly one"):
            audit(before=before)


@pytest.mark.parametrize("after", [
    (f(11, owner=3), f(23, 2, x=15, units=20)),
    (f(11, x=1), f(23, 2, x=15, units=20)),
    (f(11, web=True), f(23, 2, x=15, units=20)),
    (f(23, 2, x=15, units=0),),
    (f(23, 2, x=15, units=22501),),
    (f(23, 2, x=15, units=True),),
    (f(23, 2, x=15, units=20), f(23, 2, x=15, units=20)),
    (f(99, 2, x=15, units=20),),
    "bogus",
])
def test_malformed_or_changed_post_snapshot_abstains(after):
    with pytest.raises(MineConflictTransitionAbstain):
        audit(after=after)


@pytest.mark.parametrize("overrides", [
    {"before_stage": "AFTER"},
    {"after_stage": "BEFORE"},
    {"before_stage": None},
    {"after_stage": 2},
    {"turn_number": 0},
    {"turn_number": True},
    {"turn_number": -2},
    {"max_radius": True},
    {"max_radius": 200},
    {"complete_before_roster_provenance_confirmed": False},
    {"complete_after_roster_provenance_confirmed": None},
    {"stage_adjacency_and_no_other_mutations_confirmed": 1},
    {"exact_unchanged_diplomacy_and_owner_confirmed": False},
    {"ordinary_standard_no_protofield_or_custom_rules_confirmed": False},
    {"independently_authenticated_host_stage_receipts_confirmed": False},
    {"safe": {}},
    {"safe": {(1, 2): 1}},
    {"safe": {(1, 2): False, (2, 3): True}},
    {"before": (f(11, units=0), f(23, 2, x=15))},
    {"before": (f(11), f(11))},
    {"before": (f(11), f(23, 2, x=15, web=1))},
    {"before": None, "after": (f(23, 2, x=15, units=30),), "max_radius": 100,
     "before_stage": PRE_STAGE, "after_stage": POST_STAGE, "turn_number": 17,
     "complete_before_roster_provenance_confirmed": False},
])
def test_unknown_phase_types_owner_snapshot_and_source_cannot_pass(overrides):
    with pytest.raises(MineConflictTransitionAbstain):
        audit(**overrides)


def test_empty_post_does_not_manufacture_a_matched_new_field_id():
    with pytest.raises(MineConflictTransitionAbstain, match="both disappeared"):
        audit(after=[])
