"""Synthetic-only overlap graph and hostility scopes, not a Host conflict solver."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_overlap_candidate_graph import (
    EVIDENCE, MineOverlapAbstain, classify_conditional_mine_overlaps,
)


def f(fid=1, owner=1, *, x=0, y=0, units=100, web=False):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


def go(*, fields=None, safe=None, max_radius=150, **overrides):
    fields = (f(), f(2, 2, x=15)) if fields is None else fields
    if safe is None:
        owners = sorted({item.owner_id for item in fields if not item.is_web})
        safe = {
            (owner, other): False
            for i, owner in enumerate(owners)
            for other in owners[i+1:]
        }
    args = dict(
        fields=fields,
        mutual_safe_passage_by_normal_owner_pair=safe,
        max_radius=max_radius,
        complete_phase_current_field_roster_confirmed=True,
        exact_centers_units_and_types_confirmed=True,
        exact_mutual_diplomacy_confirmed=True,
        ordinary_no_protofield_or_custom_interactions_confirmed=True,
        no_intervening_host_field_mutations_confirmed=True,
    )
    args.update(overrides)
    return classify_conditional_mine_overlaps(**args)


def test_two_hostile_normal_fields_are_candidate_only_not_destroyed():
    result = go()
    assert result.total_fields == 2
    assert result.total_pairs_examined == 1
    assert result.conflict_candidate_pairs == 1
    assert result.isolated_conflict_pair_components == 1
    assert result.coupled_multifield_components == 0
    a = result.assessments[0]
    assert a.classification == "HOSTILE_NORMAL_OVERLAP_CANDIDATE"
    assert a.candidate_host_conflict is True
    assert (a.first_field_id, a.second_field_id) == (1, 2)
    assert a.mine_units_destroyed is None and not a.field_destroyed
    assert result.components[0].field_ids == (1, 2)
    assert result.components[0].candidate_edges == ((1, 2),)
    assert result.components[0].category == "ISOLATED_PAIR"
    assert result.evidence == EVIDENCE
    assert result.host_mine_units_destroyed is None
    assert not result.host_conflicts_resolved
    assert not result.actual_field_roster_mutated
    assert not result.host_diff_verified


def test_disjoint_and_exact_tangent_abstain():
    assert go(fields=(f(), f(2, 2, x=21))).assessments[0].classification == "DISJOINT"
    with pytest.raises(MineOverlapAbstain, match="tangent"):
        go(fields=(f(), f(2, 2, x=20)))


def test_safe_passage_explicit_even_when_fields_overlap():
    r = go(safe={(1, 2): True})
    assert r.assessments[0].classification == "MUTUAL_SAFE_PASSAGE_NONDESTRUCTIVE"
    assert not r.assessments[0].candidate_host_conflict
    assert r.components == ()


def test_same_owner_overlapping_does_not_qualify_hostile():
    r = go(fields=(f(), f(2, 1, x=15)), safe={})
    assert r.assessments[0].classification == "SAME_OWNER_NONDESTRUCTIVE"
    assert r.conflict_candidate_pairs == 0


@pytest.mark.parametrize("f1,f2", [
    (f(1, 1, web=True), f(2, 2, x=15)),
    (f(1, 1), f(2, 2, x=15, web=True)),
    (f(1, 1, web=True), f(2, 2, x=15, web=True)),
])
def test_any_web_overlap_is_non_destructive(f1, f2):
    r = go(fields=(f1, f2), safe={})
    assert r.assessments[0].classification == "WEB_NONDESTRUCTIVE"
    assert r.components == ()
    assert r.conflict_candidate_pairs == 0


def test_cross_type_tangency_still_refuses_unwitnessed_geometric_boundary():
    with pytest.raises(MineOverlapAbstain, match="tangent"):
        go(fields=(f(web=True), f(2, 2, x=20, web=True)), safe={})


def test_three_field_chain_is_coupled_not_two_independent_host_solutions():
    fields = (f(30, 3, x=30), f(10, 1, x=0), f(20, 2, x=15))
    r = go(fields=fields)
    assert r.conflict_candidate_pairs == 2
    assert r.isolated_conflict_pair_components == 0
    assert r.coupled_multifield_components == 1
    comp = r.components[0]
    assert comp.field_ids == (10, 20, 30)
    assert comp.candidate_edges == ((10, 20), (20, 30))
    assert comp.category == "COUPLED_MULTIFIELD"
    assert not comp.host_resolution_verified
    assert [(a.first_field_id, a.second_field_id) for a in r.assessments] == [
        (10, 20), (10, 30), (20, 30),
    ]
    assert r.assessments[1].classification == "DISJOINT"


def test_two_isolated_components_are_separate_and_order_invariant():
    fields = (f(21, 3, x=200), f(20, 2, x=15),
              f(10, 1), f(22, 4, x=215))
    r = go(fields=fields)
    r2 = go(fields=list(reversed(fields)))
    assert r == r2
    assert r.conflict_candidate_pairs == 2
    assert r.isolated_conflict_pair_components == 2
    assert [x.field_ids for x in r.components] == [(10, 20), (21, 22)]


def test_safe_passage_transitive_assumption_is_not_made():
    fields = (f(1, 1), f(2, 2, x=12), f(3, 3, x=14))
    safe = {(1, 2): True, (1, 3): False, (2, 3): True}
    r = go(fields=fields, safe=safe)
    assert r.conflict_candidate_pairs == 1
    assert r.components[0].candidate_edges == ((1, 3),)


def test_100_ly_and_150_ly_caps_typed():
    assert go(fields=(f(units=10000),), safe={}, max_radius=100).total_fields == 1
    with pytest.raises(MineOverlapAbstain, match="field"):
        go(fields=(f(units=10001),), safe={}, max_radius=100)
    r = go(fields=(f(units=22500),), safe={}, max_radius=150)
    assert r.total_fields == 1


def test_no_fields_empty_graph_and_single_field_no_pair():
    empty = go(fields=(), safe={})
    assert empty.total_fields == 0
    assert empty.total_pairs_examined == 0
    assert empty.components == ()
    one = go(fields=(f(),), safe={})
    assert one.total_pairs_examined == 0 and one.components == ()


def test_graph_immutable_and_input_unchanged():
    original = [f(), f(2, 2, x=15)]
    r = go(fields=original)
    assert original[0].mine_units == original[1].mine_units == 100
    with pytest.raises(FrozenInstanceError):
        r.total_fields = 11
    with pytest.raises(FrozenInstanceError):
        r.components[0].field_ids = (9,)


@pytest.mark.parametrize("bad", [
    {"complete_phase_current_field_roster_confirmed": False},
    {"exact_centers_units_and_types_confirmed": False},
    {"exact_mutual_diplomacy_confirmed": 1},
    {"ordinary_no_protofield_or_custom_interactions_confirmed": None},
    {"no_intervening_host_field_mutations_confirmed": False},
    {"max_radius": True},
    {"max_radius": 101},
    {"fields": (f(fid=True),)},
    {"fields": (f(owner=True),)},
    {"fields": (f(web=1),)},
    {"fields": (f(units=0),)},
    {"fields": (f(units=22501),)},
    {"fields": (f(x=True),)},
    {"fields": (f(1), f(1))},
    {"fields": "not-a-roster"},
    {"safe": {}},  # two different normal owners require explicit relation
    {"safe": {(1, 2): None}},
    {"safe": {(1, 2): 1}},
    {"safe": {(1, 2): False, (1, 3): True}},
    {"safe": {(True, 2): False}},
    {"safe": {(2, 1): False}},
])
def test_source_ambiguity_and_false_facts_raise_atomic_abstain(bad):
    with pytest.raises(MineOverlapAbstain):
        go(**bad)


def test_bound_128_fields_without_inventing_host_limit():
    roster = tuple(f(i, 1, x=i*300) for i in range(1, 129))
    r = go(fields=roster, safe={})
    assert r.total_pairs_examined == 128 * 127 // 2
    with pytest.raises(MineOverlapAbstain, match="bounded"):
        go(fields=roster + (f(129, 1, x=50000),), safe={})
