"""Adversarial geometry and provenance tests for candidate-only mine laying."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minelaying_conversion import quote_standard_starship_minelaying
from planets_lab.rules.minefield_placement_candidate import (
    EVIDENCE, LocatedMinefield, MinefieldPlacementAbstain,
    Point, StarClusterCore, quote_minefield_placement_candidate,
)


def ammo(*, count=1, family="mark_8_photon", mission="LAY_MINES", max_radius=150):
    return quote_standard_starship_minelaying(
        torpedo_family=family,
        torpedoes_held=count,
        drop_code="ALL",
        mission=mission,
        standard_torpedo_catalog_confirmed=True,
        ordinary_no_custom_modifiers_confirmed=True,
        mission_and_tubes_eligible_confirmed=True,
        web_permission_confirmed=(mission == "LAY_WEB_MINES"),
        robot_fourfold_bonus_confirmed=False,
        robot_field_owner_is_self_confirmed=True,
        max_radius=max_radius,
    )


def field(fid, owner, x, y, units, web=False):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


def select(*, fields=(), cores=(), pos=Point(0, 0), owner=1,
           quote=None, max_radius=150, **changes):
    args = dict(
        quote=quote if quote is not None else ammo(),
        mine_layer_position=pos,
        target_owner_id=owner,
        fields=fields,
        cluster_cores=cores,
        max_radius=max_radius,
        complete_current_field_roster_confirmed=True,
        exact_position_and_radius_source_confirmed=True,
        target_owner_and_quote_mission_consistent_confirmed=True,
        full_star_cluster_core_geometry_confirmed=True,
        isolated_pre_lay_snapshot_confirmed=True,
    )
    args.update(changes)
    return quote_minefield_placement_candidate(**args)


def test_nearest_compatible_field_inside_expands_even_when_another_covers_ship():
    fields = (field(22, 1, 0, 0, 400), field(11, 1, 10, 0, 25))
    r = select(fields=fields, pos=Point(10, 0))
    assert r.decision == "EXPAND_CANDIDATE"
    assert r.matching_nearest_field_id == r.expansion_candidate_field_id == 11
    assert r.prospective_units_if_uncontested == 125
    assert r.prospective_radius_if_uncontested == 11
    assert r.center == Point(10, 0)
    assert fields[1].mine_units == 25
    assert not r.field_roster_mutated and not r.field_created_or_expanded


def test_outside_nearest_creates_candidate_even_inside_more_distant_field():
    fields = (field(3, 1, 0, 0, 400), field(2, 1, 10, 0, 1))
    r = select(fields=fields, pos=Point(8, 0))
    assert r.decision == "NEW_CANDIDATE"
    assert r.matching_nearest_field_id == 2
    assert r.expansion_candidate_field_id is None
    assert r.center == Point(8, 0)
    assert r.prospective_units_if_uncontested == 100


def test_exact_squared_distance_tie_selects_lowest_id_before_inside_test():
    # Same squared distance; low-ID field does not cover, other does.
    fields = (field(7, 1, 0, 10, 225), field(2, 1, 10, 0, 1))
    r = select(fields=fields, pos=Point(0, 0))
    assert r.matching_nearest_field_id == 2
    assert r.decision == "NEW_CANDIDATE"
    assert r.distance_squared_to_nearest == 100


def test_owner_and_web_filter_before_distance_and_tie():
    fields = (
        field(1, 2, 0, 0, 200),
        field(2, 1, 0, 0, 200, web=True),
        field(4, 1, 10, 0, 100),
    )
    r = select(fields=fields, pos=Point(0, 0))
    assert r.matching_nearest_field_id == 4
    assert r.decision == "EXPAND_CANDIDATE"
    w = select(fields=fields, pos=Point(0, 0), quote=ammo(mission="LAY_WEB_MINES"))
    assert w.matching_nearest_field_id == 2
    assert w.decision == "EXPAND_CANDIDATE"


def test_inclusive_integer_radius_boundary_and_one_step_outside():
    f = (field(2, 1, 0, 0, 99),)
    assert select(fields=f, pos=Point(9, 0)).decision == "EXPAND_CANDIDATE"
    assert select(fields=f, pos=Point(10, 0)).decision == "NEW_CANDIDATE"
    f2 = (field(2, 1, 0, 0, 100),)
    assert select(fields=f2, pos=Point(10, 0)).decision == "EXPAND_CANDIDATE"


def test_no_field_and_no_ammo_do_not_allocate_ids():
    r = select()
    assert r.decision == "NEW_CANDIDATE"
    assert r.created_field_id is None
    assert r.prospective_radius_if_uncontested == 10
    z = select(quote=ammo(count=0), fields=(field(2, 1, 0, 0, 300),))
    assert z.decision == "NO_UNITS"
    assert z.center is None and z.matching_nearest_field_id is None
    assert z.raw_unallocated_units == 0


def test_exact_cluster_core_plus_ten_exclusion_abstains_including_contact():
    # Proposed radius 10 + 10 LY buffer + core radius 5 = 25.
    for x in (0, 24, 25):
        with pytest.raises(MinefieldPlacementAbstain, match="cluster"):
            select(cores=(StarClusterCore(Point(x, 0), 5),))
    good = select(cores=(StarClusterCore(Point(26, 0), 5),))
    assert good.decision == "NEW_CANDIDATE"


def test_expansion_uses_original_center_to_check_cluster_and_max_capacity():
    fields = (field(8, 1, 0, 0, 100),)
    with pytest.raises(MinefieldPlacementAbstain, match="cluster"):
        select(fields=fields, cores=(StarClusterCore(Point(24, 0), 0),))
    assert select(fields=fields, cores=(StarClusterCore(Point(31, 0), 0),)).decision == "EXPAND_CANDIDATE"
    with pytest.raises(MinefieldPlacementAbstain, match="overcapacity"):
        select(fields=(field(8, 1, 0, 0, 22500),))


def test_reduced_radius_100_is_consistent_with_independent_quote():
    r = select(quote=ammo(max_radius=100), max_radius=100)
    assert r.max_radius == 100
    with pytest.raises(MinefieldPlacementAbstain, match="radius"):
        select(quote=ammo(max_radius=100), max_radius=150)


def test_determinism_and_immutability_of_selection_and_source():
    fields = [field(50, 1, 0, 0, 64), field(40, 1, 30, 0, 64)]
    r = select(fields=fields)
    assert r == select(fields=list(reversed(fields)))
    assert r.evidence == EVIDENCE and not r.host_causal_verified
    assert r.created_field_id is None and not r.host_order_accepted_verified
    with pytest.raises(FrozenInstanceError):
        r.decision = "REAL"
    assert fields[0].mine_units == 64


@pytest.mark.parametrize("overrides", [
    {"complete_current_field_roster_confirmed": False},
    {"exact_position_and_radius_source_confirmed": False},
    {"target_owner_and_quote_mission_consistent_confirmed": False},
    {"full_star_cluster_core_geometry_confirmed": False},
    {"isolated_pre_lay_snapshot_confirmed": False},
    {"mine_layer_position": Point(True, 1)},
    {"mine_layer_position": (0, 0)},
    {"target_owner_id": True},
    {"target_owner_id": -1},
    {"fields": None},
    {"fields": (field(1, 1, 0, 0, 10), field(1, 2, 3, 4, 10))},
    {"fields": (field(1, 1, 0, 0, 0),)},
    {"fields": (field(1, 1, 0, 0, 22501),)},
    {"fields": (field(1, 1, 0, 0, 1, web=1),)},
    {"fields": (field(True, 1, 0, 0, 1),)},
    {"cluster_cores": None},
    {"cluster_cores": (StarClusterCore(Point(0, 0), True),)},
    {"cluster_cores": (StarClusterCore(Point(0, 0), -1),)},
    {"max_radius": True},
    {"max_radius": 200},
])
def test_invalid_or_unwitnessed_source_abstains(overrides):
    with pytest.raises(MinefieldPlacementAbstain):
        select(**overrides)


def test_soft_limit_refuses_new_creation_but_allows_geometric_expand_quote():
    fields = tuple(field(i, 1, i * 200, 0, 25) for i in range(1, 501))
    with pytest.raises(MinefieldPlacementAbstain, match="soft"):
        select(fields=fields, pos=Point(0, 0))
    assert select(fields=fields, pos=Point(200, 0)).decision == "EXPAND_CANDIDATE"
