"""Default late PQ / PPQ PP price, complete roster and one explicit pb1."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.classic_uncontested_priority_pbp import PriorityShipOrder
from planets_lab.sim.late_pq_ppq_priority_admission import (
    STATUS, MODES, LatePriorityBase, LatePriorityContext,
    default_pq_ppq_priority_cost, quote_single_late_priority,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from test_classic_standard_pointer_economy_turn import context as base_context


def fixture(mode="PRODUCTION_PQ"):
    game, specs, _, queued = base_context(existing=8)
    request = PriorityShipOrder(
        blueprint=queued[10].blueprint,
        warehouse=StandardComponentWarehouse(),
        allowed_hull_ids=frozenset({7}),
    )
    state = LatePriorityContext(
        mode=mode, soft_ship_limit=8,
        player_pp=((1, 3), (2, 0)),
        all_bases=(
            LatePriorityBase(10, "pb1", request),
            LatePriorityBase(20, None, None),
            LatePriorityBase(30, None, None),
        ),
        complete_fleet_base_and_player_roster_asserted=True,
        complete_priority_point_balances_asserted=True,
        no_other_priority_or_regular_builds_in_phase_asserted=True,
        default_priority_cost_rule_asserted=True,
    )
    return game, specs, state


@pytest.mark.parametrize("mass,cost", [
    (1,2),(49,2),(50,2),(51,3),(60,3),
    (100,3),(101,4),(1000,21),(1001,21),(1970,21),
])
def test_default_pq_ppq_priority_bill_1_plus_ceil_50kt_capped_at_21(mass,cost):
    assert default_pq_ppq_priority_cost(mass) == cost


@pytest.mark.parametrize("mass", [0, -1, True, 10.0, None, "100"])
def test_priority_quote_rejects_non_positive_or_untyped_mass(mass):
    assert default_pq_ppq_priority_cost(mass) is None


@pytest.mark.parametrize("mode", MODES)
def test_unique_pb1_above_soft_limit_is_conditional_admission(mode):
    game, specs, ctx = fixture(mode)
    initial = deepcopy((game, specs, ctx))
    out = quote_single_late_priority(game, specs, ctx)
    assert out == quote_single_late_priority(game, specs, ctx)
    assert out.status == STATUS and out.supported
    assert out.base_planet_id == 10 and out.proposed_ship_id == 9
    assert out.owner_id == 1 and out.hull_mass == 50
    assert out.priority_point_cost == 2
    assert out.pp_after == ((1, 1), (2, 0))
    assert not out.server_selected_priority_slot_verified
    assert not out.server_accepted_order_verified
    assert not out.ship_id_independently_verified
    assert not out.host_phase_order_verified
    assert (game, specs, ctx) == initial


def test_known_high_mass_can_spend_pp_through_soft_cap_under_programmatic_max():
    game, specs, ctx = fixture()
    specs.hulls[7] = replace(specs.hulls[7], mass=1970)
    ctx = replace(ctx, player_pp=((1, 21), (2, 0)))
    out = quote_single_late_priority(game, specs, ctx)
    assert out.supported
    assert out.priority_point_cost == 21 and out.pp_after == ((1, 0), (2, 0))


@pytest.mark.parametrize("bad", (
    "unknown_mode", "custom_priority_cost", "no_source_assert",
    "no_pp_assert", "other_phase_actions",
    "missing_base", "duplicate_base", "phantom_base",
    "missing_owner", "duplicate_owner", "negative_pp", "boolean_pp",
    "insufficient_pp", "missing_design", "missing_priority",
    "two_priorities", "pb2_not_admitted", "clone",
    "normal_queued_base", "wrong_base_owner", "before_soft_limit",
    "invalid_soft_limit", "hard_999_full", "unknown_hull",
    "bool_hull_mass", "special_metadata", "active_ion",
))
def test_unknown_priority_scope_abstains_no_partial_bill(bad):
    game, specs, ctx = fixture()
    bases = list(ctx.all_bases)
    if bad == "unknown_mode": ctx = replace(ctx, mode="CLASSIC_PBP")
    elif bad == "custom_priority_cost": ctx = replace(ctx, default_priority_cost_rule_asserted=False)
    elif bad == "no_source_assert": ctx = replace(ctx, complete_fleet_base_and_player_roster_asserted=False)
    elif bad == "no_pp_assert": ctx = replace(ctx, complete_priority_point_balances_asserted=False)
    elif bad == "other_phase_actions": ctx = replace(ctx, no_other_priority_or_regular_builds_in_phase_asserted=False)
    elif bad == "missing_base": bases.pop()
    elif bad == "duplicate_base": bases[2] = bases[0]
    elif bad == "phantom_base": bases[2] = replace(bases[2], planet_id=999)
    elif bad == "missing_owner": ctx = replace(ctx, player_pp=((1,3),))
    elif bad == "duplicate_owner": ctx = replace(ctx, player_pp=((1,3),(1,3)))
    elif bad == "negative_pp": ctx = replace(ctx, player_pp=((1,-1),(2,0)))
    elif bad == "boolean_pp": ctx = replace(ctx, player_pp=((1,True),(2,0)))
    elif bad == "insufficient_pp": ctx = replace(ctx, player_pp=((1,1),(2,0)))
    elif bad == "missing_design": bases[0] = replace(bases[0], order=None)
    elif bad == "missing_priority": bases[0] = replace(bases[0], priority_code=None)
    elif bad == "two_priorities": bases[1] = replace(bases[1], priority_code="pb1", order=bases[0].order)
    elif bad == "pb2_not_admitted": bases[0] = replace(bases[0], priority_code="pb2")
    elif bad == "clone": bases[0] = replace(bases[0], cloning=True)
    elif bad == "normal_queued_base": bases[1] = replace(bases[1], order=bases[0].order)
    elif bad == "wrong_base_owner": game.starbases[10].owner_id = 2
    elif bad == "before_soft_limit": ctx = replace(ctx, soft_ship_limit=10)
    elif bad == "invalid_soft_limit": ctx = replace(ctx, soft_ship_limit=True)
    elif bad == "hard_999_full":
        from planets_lab.core import Ship
        for ident in range(9,1000):
            game.ships[ident] = Ship(id=ident, owner_id=1, hull_id=7, x=100, y=100)
    elif bad == "unknown_hull": specs.hulls.pop(7)
    elif bad == "bool_hull_mass": specs.hulls[7] = replace(specs.hulls[7], mass=True)
    elif bad == "special_metadata": game.metadata["custom"] = True
    elif bad == "active_ion":
        game.metadata["ion_storm_on"] = 1
    if tuple(bases) != ctx.all_bases: ctx = replace(ctx, all_bases=tuple(bases))
    frozen = deepcopy((game, specs, ctx))
    out = quote_single_late_priority(game, specs, ctx)
    assert not out.supported
    assert out.status == "ABSTAIN_LATE_PQ_PPQ_PRIORITY_QUOTE"
    assert out.proposed_ship_id is None and out.pp_after == ()
    assert (game, specs, ctx) == frozen
