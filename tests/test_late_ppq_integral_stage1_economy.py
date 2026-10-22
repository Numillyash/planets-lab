"""Late PPQ exact integer Stage-1 slots + all-base warehouse/economy."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_ppq_integral_stage1_economy import (
    STATUS, PLACEMENTS, PPQWarehouseBase, PPQIntegralEconomicContext,
    simulate_integral_ppq_stage1_economic_turn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
from test_late_ppq_integer_stage1_allocation import scenario
from test_standard_ship_component_quote import pre


def fixture():
    game, quota = scenario()
    prototype, base, specs, blueprint = pre()
    for pid, planet in game.planets.items():
        planet.cargo = deepcopy(prototype.cargo)
        game.starbases[pid] = replace(
            base, planet_id=pid, owner_id=planet.owner_id,
        )
    queue_rows = []
    for row in quota.all_bases:
        if row.queued:
            queue_rows.append(replace(
                row, hull_mass_kt=specs.hulls[7].mass,
            ))
        else:
            queue_rows.append(row)
    quota = replace(quota, all_bases=tuple(queue_rows))
    selected = tuple(range(1, 7)) + tuple(range(13, 17))
    assignments = dict(zip(selected, range(20, 30), strict=True))
    roster = tuple(
        PPQWarehouseBase(
            planet_id=row.planet_id,
            warehouse=StandardComponentWarehouse(),
            blueprint=blueprint if row.queued else None,
            allowed_hull_ids=frozenset({7}) if row.queued else None,
            asserted_ship_id=assignments.get(row.planet_id),
        )
        for row in quota.all_bases
    )
    context = PPQIntegralEconomicContext(
        stage1=quota,
        all_base_warehouses=roster,
        player_pp=((1, 17), (2, 19)),
        complete_warehouse_hull_rights_and_ship_id_assignment_asserted=True,
        default_zero_pp_regular_build_and_no_pp_income_asserted=True,
        no_external_ship_planet_base_or_combat_effects_asserted=True,
    )
    return game, specs, context


def run(game, specs, ctx, **changes):
    kw = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_independent_planetary_inventory_asserted=True,
    )
    kw.update(changes)
    return simulate_integral_ppq_stage1_economic_turn(game, specs, ctx, **kw)


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_ten_regular_ships_cross_soft_cap_with_bom_economy_and_unchanged_pp(placement):
    game, specs, ctx = fixture()
    frozen = deepcopy((game, specs, ctx))
    r = run(game, specs, ctx, placement=placement)
    assert r.supported and r.status == STATUS
    assert r == run(game, specs, ctx, placement=placement)
    assert game.turn + 1 == r.state.turn
    assert len(game.ships) == 19
    assert len(r.state.ships) == 29 > ctx.stage1.soft_ship_limit
    assert set(r.state.ships) == set(game.ships) | set(range(20, 30))
    assert len(r.ship_receipts) == 10
    assert all(x.purchased.megacredits == 260 for x in r.ship_receipts)
    assert len(r.planet_balances) == 20
    assert all(x.resource_balance_exact for x in r.planet_balances)
    assert r.selected_bases_by_owner == (
        (1, tuple(range(1, 7))), (2, tuple(range(13, 17))),
    )
    assert r.player_pp_after == ((1, 17), (2, 19))
    assert len(r.base_warehouses_after) == 20
    assert r.state.starbases == game.starbases
    assert not r.selected_set_independently_verified
    assert not r.base_to_ship_id_assignment_verified
    assert not r.accepted_order_independently_verified
    assert not r.nuhost_execution_verified
    assert not r.nuhost_phase_placement_verified
    assert not r.independent_host_parity_verified
    assert (game, specs, ctx) == frozen


def test_permuting_proposed_ship_ids_changes_owner_assignment_not_selected_set():
    game, specs, ctx = fixture()
    rows = list(ctx.all_base_warehouses)
    rows[0] = replace(rows[0], asserted_ship_id=29)
    rows[15] = replace(rows[15], asserted_ship_id=20)
    ctx = replace(ctx, all_base_warehouses=tuple(rows))
    r = run(game, specs, ctx)
    assert r.supported
    assert r.state.ships[20].owner_id == 2
    assert r.state.ships[29].owner_id == 1
    assert r.selected_bases_by_owner[0][1] == tuple(range(1, 7))
    assert not r.base_to_ship_id_assignment_verified


def test_stored_components_prevent_material_debit_but_not_other_bases_builds():
    game, specs, ctx = fixture()
    full = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    rows = list(ctx.all_base_warehouses)
    rows[0] = replace(rows[0], warehouse=full)
    ctx = replace(ctx, all_base_warehouses=tuple(rows))
    for key in ("megacredits", "duranium", "tritanium", "molybdenum"):
        setattr(game.planets[1].cargo, key, 0)
    r = run(game, specs, ctx)
    assert r.supported
    receipt = next(x for x in r.ship_receipts if x.starbase_planet_id == 1)
    assert all(getattr(receipt.purchased, k) == 0 for k in (
        "megacredits", "duranium", "tritanium", "molybdenum",
    ))
    assert dict(r.base_warehouses_after)[1].hulls == ((7, 0),)


@pytest.mark.parametrize("case", (
    "missing_base", "duplicate_base", "missing_pp", "duplicate_pp",
    "bool_pp", "missing_stock", "unknown_idle_component",
    "unknown_unselected_component", "missing_selected_ship_id",
    "duplicate_ship_id", "id_not_lowest", "id_on_unselected",
    "unselected_warehouse_modified", "unselected_hull_rights_absent",
    "unselected_blueprint_mass_mismatch", "selected_hull_not_permitted",
    "bad_ship_blueprint", "one_base_unaffordable", "missing_resource",
    "fractional_quota", "rb_boundary_tie", "unknown_owner",
    "wrong_owner", "moving_ship", "custom_metadata", "no_complete_inventory",
    "nondefault_regular_pp", "outside_scope", "wrong_placement",
    "boolean_seed", "lost_stage1_claim",
))
def test_invalid_late_stage1_bom_and_sidecar_abstains_atomically(case):
    game, specs, ctx = fixture()
    rows = list(ctx.all_base_warehouses)
    quota = ctx.stage1
    opts = {}
    if case == "missing_base":
        rows.pop()
    elif case == "duplicate_base":
        rows[1] = rows[0]
    elif case == "missing_pp":
        ctx = replace(ctx, player_pp=((1, 17),))
    elif case == "duplicate_pp":
        ctx = replace(ctx, player_pp=((1, 17), (1, 19)))
    elif case == "bool_pp":
        ctx = replace(ctx, player_pp=((1, True), (2, 19)))
    elif case == "missing_stock":
        rows[5] = replace(rows[5], warehouse=None)
    elif case == "unknown_idle_component":
        rows[19] = replace(rows[19], warehouse=StandardComponentWarehouse(hulls=((999, 1),)))
    elif case == "unknown_unselected_component":
        rows[6] = replace(rows[6], warehouse=StandardComponentWarehouse(engines=((999, 1),)))
    elif case == "missing_selected_ship_id":
        rows[0] = replace(rows[0], asserted_ship_id=None)
    elif case == "duplicate_ship_id":
        rows[1] = replace(rows[1], asserted_ship_id=20)
    elif case == "id_not_lowest":
        rows[0] = replace(rows[0], asserted_ship_id=99)
    elif case == "id_on_unselected":
        rows[6] = replace(rows[6], asserted_ship_id=99)
    elif case == "unselected_warehouse_modified":
        rows[6] = replace(rows[6], warehouse=StandardComponentWarehouse(hulls=((7, -1),)))
    elif case == "unselected_hull_rights_absent":
        rows[6] = replace(rows[6], allowed_hull_ids=None)
    elif case == "unselected_blueprint_mass_mismatch":
        candidates = list(quota.all_bases)
        candidates[6] = replace(candidates[6], hull_mass_kt=100)
        quota = replace(quota, all_bases=tuple(candidates))
    elif case == "selected_hull_not_permitted":
        rows[0] = replace(rows[0], allowed_hull_ids=frozenset({8}))
    elif case == "bad_ship_blueprint":
        rows[0] = replace(rows[0], blueprint=None)
    elif case == "one_base_unaffordable":
        game.planets[2].cargo.megacredits = 0
    elif case == "missing_resource":
        game.planets[2].cargo.duranium = 0
    elif case == "fractional_quota":
        game.planets[20].owner_id = 1
    elif case == "rb_boundary_tie":
        candidates = list(quota.all_bases)
        candidates[5] = replace(candidates[5], rb_code="rb5")
        candidates[6] = replace(candidates[6], rb_code="RB5")
        quota = replace(quota, all_bases=tuple(candidates))
    elif case == "unknown_owner":
        game.planets[20].owner_id = 999
    elif case == "wrong_owner":
        game.starbases[20].owner_id = 1
    elif case == "moving_ship":
        game.ships[1].warp = 8
    elif case == "custom_metadata":
        game.metadata["custom"] = True
    elif case == "no_complete_inventory":
        opts["complete_independent_planetary_inventory_asserted"] = False
    elif case == "nondefault_regular_pp":
        ctx = replace(ctx, default_zero_pp_regular_build_and_no_pp_income_asserted=False)
    elif case == "outside_scope":
        ctx = replace(ctx, no_external_ship_planet_base_or_combat_effects_asserted=False)
    elif case == "wrong_placement":
        opts["placement"] = "verified_NuHost_phase"
    elif case == "boolean_seed":
        opts["seed"] = True
    elif case == "lost_stage1_claim":
        quota = replace(quota, regular_subphase_after_priorities_asserted=False)
    if tuple(rows) != ctx.all_base_warehouses:
        ctx = replace(ctx, all_base_warehouses=tuple(rows))
    if quota != ctx.stage1:
        ctx = replace(ctx, stage1=quota)
    frozen = deepcopy((game, specs, ctx))
    out = run(game, specs, ctx, **opts)
    assert not out.supported
    assert out.state is None
    assert out.ship_receipts == () and out.player_pp_after == ()
    assert out.base_warehouses_after == () and out.planet_balances == ()
    assert out.economic_events == () and out.selected_bases_by_owner == ()
    assert (game, specs, ctx) == frozen


@pytest.mark.parametrize("bad", (
    "extra_mc", "invented_mineral", "missing_economy_event",
    "new_ship_crew", "phantom_ship",
))
def test_forged_engine_output_cannot_pass_complete_late_ppq_ledger(monkeypatch, bad):
    import planets_lab.sim.late_ppq_integral_stage1_economy as module
    original = module.HostEngine.step

    def forged(self, state, orders, *, seed=0):
        after, events = original(self, state, orders, seed=seed)
        after = deepcopy(after)
        if bad == "extra_mc":
            after.planets[19].cargo.megacredits += 1
        elif bad == "invented_mineral":
            after.planets[19].ground_duranium.amount += 1
        elif bad == "missing_economy_event":
            events = tuple(e for e in events if e.phase != "mineral_mining")
        elif bad == "new_ship_crew":
            after.ships[20].crew += 1
        elif bad == "phantom_ship":
            from planets_lab.core import Ship
            after.ships[77] = Ship(id=77, owner_id=1, hull_id=7, x=100, y=100)
        return after, events

    monkeypatch.setattr(module.HostEngine, "step", forged)
    game, specs, ctx = fixture()
    out = run(game, specs, ctx)
    assert not out.supported and out.state is None
    assert out.player_pp_after == () and out.ship_receipts == ()
