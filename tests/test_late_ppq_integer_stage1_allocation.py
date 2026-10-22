"""Bounded, caller-asserted late PPQ integer-share selector contract."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.core import GameState, Planet, Player, Ship, Starbase
from planets_lab.sim.late_ppq_integer_stage1_allocation import (
    STATUS, PPQRegularBase, PPQStage1Context,
    quote_integral_ppq_regular_stage1,
)


def scenario():
    # 12 of 20 currently owned planets belong to owner1, 8 to owner2.
    # Missing one slot at soft cap 20 => PPQ allocates ten: 6 + 4.
    game = GameState(game_id=900001, turn=8)
    game.players = {i: Player(id=i) for i in (1, 2)}
    for pid in range(1, 21):
        owner = 1 if pid <= 12 else 2
        game.planets[pid] = Planet(id=pid, owner_id=owner, x=pid * 10, y=100)
        game.starbases[pid] = Starbase(planet_id=pid, owner_id=owner)
    for sid in range(1, 20):
        game.ships[sid] = Ship(id=sid, owner_id=1, hull_id=7, x=100, y=100)
    bases = []
    for pid in range(1, 21):
        # Owner 1 has seven queued, first six get RB1..RB6.
        # Owner 2 has five queued; RB1..RB4 beat an untagged heavy hull.
        queued = pid <= 7 or 13 <= pid <= 17
        code = (
            f"RB{pid}" if 1 <= pid <= 7
            else f"rb{pid - 12}" if 13 <= pid <= 16
            else None
        )
        if pid == 7:
            code = "RB9"
        bases.append(PPQRegularBase(
            pid, queued, 1000 if pid == 17 else 100 if queued else None,
            code,
        ))
    ctx = PPQStage1Context(
        soft_ship_limit=20, all_bases=tuple(bases),
        full_planet_fleet_and_base_roster_asserted=True,
        complete_queued_hulls_rb_codes_and_eligible_bases_asserted=True,
        no_mining_stations_priorities_clones_or_other_host_actions_asserted=True,
        regular_subphase_after_priorities_asserted=True,
        default_ppq_stage1_owned_planet_share_rule_asserted=True,
    )
    game.validate()
    return game, ctx


def test_exact_owned_share_exhausts_stage1_without_lottery():
    game, ctx = scenario()
    original = deepcopy((game, ctx))
    result = quote_integral_ppq_regular_stage1(game, ctx)
    assert result == quote_integral_ppq_regular_stage1(game, ctx)
    assert result.supported and result.status == STATUS
    assert result.allocated_regular_slots == 10
    assert result.owned_planet_counts == ((1, 12), (2, 8))
    assert result.guaranteed_slots_by_owner == ((1, 6), (2, 4))
    assert result.selected_base_ids_by_owner == (
        (1, (1, 2, 3, 4, 5, 6)), (2, (13, 14, 15, 16)),
    )
    assert result.lowest_available_ship_id_pool == tuple(range(20, 30))
    assert not result.server_selection_verified
    assert not result.server_ship_id_assignment_verified
    assert not result.server_accepted_orders_verified
    assert not result.nuhost_stage_placement_verified
    assert not result.independent_host_parity_verified
    assert (game, ctx) == original


def test_selection_is_independent_of_input_roster_order_and_idle_bases():
    game, ctx = scenario()
    original = quote_integral_ppq_regular_stage1(game, ctx)
    scrambled = replace(ctx, all_bases=tuple(reversed(ctx.all_bases)))
    assert quote_integral_ppq_regular_stage1(game, scrambled) == original
    assert len(original.selected_base_ids_by_owner[0][1]) == 6
    assert 7 not in original.selected_base_ids_by_owner[0][1]
    assert 17 not in original.selected_base_ids_by_owner[1][1]


def test_no_rb_code_uses_heaviest_hull_without_random_boundary():
    game, ctx = scenario()
    rows = list(ctx.all_bases)
    rows[4] = replace(rows[4], rb_code=None, hull_mass_kt=101)
    rows[5] = replace(rows[5], rb_code=None, hull_mass_kt=100)
    rows[6] = replace(rows[6], rb_code=None, hull_mass_kt=99)
    ctx = replace(ctx, all_bases=tuple(rows))
    result = quote_integral_ppq_regular_stage1(game, ctx)
    assert result.supported
    assert result.selected_base_ids_by_owner[0][1] == (1, 2, 3, 4, 5, 6)


@pytest.mark.parametrize("case", (
    "missing_roster", "duplicate_base", "wrong_base_owner",
    "fractional_planet_share", "unknown_owner", "unowned_all",
    "insufficient_queue", "rb_boundary_tie", "hull_boundary_tie",
    "invalid_rb", "bool_hull", "missing_mass", "idle_with_code",
    "invalid_soft_limit", "soft_limit_already_reached",
    "unthrottled_queue", "moving_ship", "custom_metadata",
    "no_complete_world", "no_hull_and_rb_certification",
    "no_exclusion_other_actions", "not_after_priority",
    "no_stage1_rule", "bool_ship_id", "out_of_range_ship_id",
))
def test_unsupported_selection_never_returns_partial_allocation(case):
    game, ctx = scenario()
    rows = list(ctx.all_bases)
    if case == "missing_roster":
        rows.pop()
    elif case == "duplicate_base":
        rows[0] = rows[1]
    elif case == "wrong_base_owner":
        game.starbases[5].owner_id = 2
    elif case == "fractional_planet_share":
        game.planets[20].owner_id = 1
    elif case == "unknown_owner":
        game.planets[20].owner_id = 999
    elif case == "unowned_all":
        for p in game.planets.values():
            p.owner_id = None
    elif case == "insufficient_queue":
        rows[0] = PPQRegularBase(1, False)
    elif case == "rb_boundary_tie":
        rows[5] = replace(rows[5], rb_code="rb5")
        rows[6] = replace(rows[6], rb_code="RB5")
    elif case == "hull_boundary_tie":
        for index in range(7):
            rows[index] = replace(rows[index], rb_code=None, hull_mass_kt=100)
    elif case == "invalid_rb":
        rows[0] = replace(rows[0], rb_code="RB0")
    elif case == "bool_hull":
        rows[0] = replace(rows[0], hull_mass_kt=True)
    elif case == "missing_mass":
        rows[0] = replace(rows[0], hull_mass_kt=None)
    elif case == "idle_with_code":
        rows[11] = replace(rows[11], rb_code="rb1")
    elif case == "invalid_soft_limit":
        ctx = replace(ctx, soft_ship_limit=True)
    elif case == "soft_limit_already_reached":
        ctx = replace(ctx, soft_ship_limit=19)
    elif case == "unthrottled_queue":
        for i in range(len(rows)):
            if i not in (0, 12): rows[i] = PPQRegularBase(i + 1, False)
    elif case == "moving_ship":
        game.ships[1].warp = 8
    elif case == "custom_metadata":
        game.metadata["mod"] = True
    elif case == "no_complete_world":
        ctx = replace(ctx, full_planet_fleet_and_base_roster_asserted=False)
    elif case == "no_hull_and_rb_certification":
        ctx = replace(ctx, complete_queued_hulls_rb_codes_and_eligible_bases_asserted=False)
    elif case == "no_exclusion_other_actions":
        ctx = replace(ctx, no_mining_stations_priorities_clones_or_other_host_actions_asserted=False)
    elif case == "not_after_priority":
        ctx = replace(ctx, regular_subphase_after_priorities_asserted=False)
    elif case == "no_stage1_rule":
        ctx = replace(ctx, default_ppq_stage1_owned_planet_share_rule_asserted=False)
    elif case == "bool_ship_id":
        game.ships[True] = Ship(id=True, owner_id=1, hull_id=7, x=0, y=0)
    elif case == "out_of_range_ship_id":
        game.ships[1000] = Ship(id=1000, owner_id=1, hull_id=7, x=0, y=0)
    if tuple(rows) != ctx.all_bases:
        ctx = replace(ctx, all_bases=tuple(rows))
    frozen = deepcopy((game, ctx))
    result = quote_integral_ppq_regular_stage1(game, ctx)
    assert not result.supported
    assert result.status.startswith("ABSTAIN")
    assert result.allocated_regular_slots == 0
    assert result.owned_planet_counts == ()
    assert result.guaranteed_slots_by_owner == ()
    assert result.selected_base_ids_by_owner == ()
    assert result.lowest_available_ship_id_pool == ()
    assert (game, ctx) == frozen
