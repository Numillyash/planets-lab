"""Bounded late PQ mixed calendar: capped wait -> external loss -> build -> fleet moves.

Combine independently fail-closed research slices (#273, #272 boundary
validator, #271 assembly, #276 fleet logistics). NEVER invent a ship
vacancy, accepted winner, combat/recycle, host timing or component credit.
Every mandatory interstage fleet, base, warehouse and PP boundary is
checked; later failure ABSTAINS the entire calendar with no partial
states, receipts or inventory sidecars.
"""
from __future__ import annotations

from dataclasses import dataclass

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.late_pq_capped_no_build_carry import (
    CappedPQCarry, CappedPQNoBuildTurn, CappedPQNoBuildReceipt,
    simulate_soft_capped_pq_no_build_carry,
)
from planets_lab.sim.late_pq_external_loss_multiturn import (
    LatePQExplicitTurn, _check_preturn_external_loss,
)
from planets_lab.sim.late_pq_external_regular_economy import (
    LatePQBase, LatePQContext, LatePQOutcome,
    simulate_late_pq_external_selected_economic_turn,
)
from planets_lab.sim.late_pq_capped_existing_fleet_cargo import (
    CappedFleetCargoTurn, CappedFleetCargoReceipt,
    simulate_capped_pq_existing_ship_cargo_carry,
)

STATUS = "CONDITIONAL_LATE_PQ_WAIT_LOSS_BUILD_FLEET_CALENDAR_NOT_HOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class MixedPQCalendarOutcome:
    status: str
    state: GameState | None = None
    carry_after: CappedPQCarry | None = None
    waiting_turns: tuple[CappedPQNoBuildReceipt, ...] = ()
    external_removed_ship_id: int | None = None
    build: LatePQOutcome | None = None
    fleet_turns: tuple[CappedFleetCargoReceipt, ...] = ()
    reason: str | None = None
    external_ship_loss_independently_verified: bool = False
    pq_winning_base_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    accepted_host_orders_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedPQCalendar(ValueError):
    """A single unknown or extra delta invalidates the entire calendar."""


def simulate_mixed_late_pq_wait_loss_build_fleet_calendar(
    before: GameState, specs: NuStaticSpecs,
    initial: CappedPQCarry,
    wait_plans: tuple[CappedPQNoBuildTurn, ...],
    external_build: LatePQExplicitTurn,
    fleet_plans: tuple[CappedFleetCargoTurn, ...],
    *,
    full_state_and_all_queue_rosters_asserted: bool = False,
    independently_sourced_external_loss_boundary_asserted: bool = False,
    no_other_priority_clones_miners_combat_or_external_changes_asserted: bool = False,
    standard_rules_asserted: bool = False,
    seed: int = 0,
) -> MixedPQCalendarOutcome:
    def abstain(reason: str) -> MixedPQCalendarOutcome:
        return MixedPQCalendarOutcome(
            "ABSTAIN_MIXED_LATE_PQ_WAIT_LOSS_BUILD_FLEET", reason=reason,
        )
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(initial) is not CappedPQCarry
        or type(wait_plans) is not tuple or not 2 <= len(wait_plans) <= 8
        or type(external_build) is not LatePQExplicitTurn
        or type(fleet_plans) is not tuple or not 2 <= len(fleet_plans) <= 6
        or type(seed) is not int
        or full_state_and_all_queue_rosters_asserted is not True
        or independently_sourced_external_loss_boundary_asserted is not True
        or no_other_priority_clones_miners_combat_or_external_changes_asserted is not True
        or standard_rules_asserted is not True
    ):
        return abstain("incomplete externally sourced multi-stage calendar")
    try:
        waited = simulate_soft_capped_pq_no_build_carry(
            before, specs, initial, wait_plans,
            standard_rules_asserted=True,
            complete_owner_planet_base_fleet_and_queue_roster_asserted=True,
            no_priority_clone_mining_stations_or_external_actions_asserted=True,
            default_no_pp_income_or_regular_pp_spend_asserted=True,
            seed=seed,
        )
        if (
            not waited.supported or waited.state is None
            or waited.carry_after != initial
            or len(waited.turns) != len(wait_plans)
            or waited.state.turn != before.turn + len(wait_plans)
            or waited.state.ships != before.ships
            or waited.state.players != before.players
            or waited.state.starbases != before.starbases
        ):
            raise UnsupportedPQCalendar("uncertain capped waiting/economy boundary")

        # Require the selected build queue to be exactly the last wait
        # declaration; callers cannot silently replace the queue while
        # attributing the external loss to a ship-only boundary.
        existing = {row.planet_id: row for row in wait_plans[-1].all_bases}
        entries = external_build.bases
        if (
            type(entries) is not tuple
            or len(entries) != len(existing)
            or any(
                type(row.planet_id) is not int
                or row.planet_id not in existing
                or row.blueprint != existing[row.planet_id].blueprint
                or row.allowed_hull_ids != existing[row.planet_id].allowed_hull_ids
                for row in entries
            )
            or {row.planet_id for row in entries} != set(existing)
        ):
            raise UnsupportedPQCalendar("caller changed queued starbases across ship-only loss")
        prebuild = _check_preturn_external_loss(
            waited.state, external_build, initial.soft_ship_limit,
        )
        if (
            prebuild.turn != waited.state.turn
            or len(prebuild.ships) != initial.soft_ship_limit - 1
            or external_build.selected_ship_id not in range(1, 1000)
        ):
            raise UnsupportedPQCalendar("not exactly one supported soft-cap vacancy")

        stock = dict(initial.all_base_warehouses)
        selected_bases = tuple(
            LatePQBase(
                planet_id=row.planet_id,
                warehouse=stock[row.planet_id],
                blueprint=row.blueprint,
                allowed_hull_ids=(row.allowed_hull_ids
                                  if row.blueprint is not None else None),
            )
            for row in entries
        )
        context = LatePQContext(
            soft_ship_limit=initial.soft_ship_limit,
            selected_planet_id=external_build.selected_planet_id,
            selected_ship_id=external_build.selected_ship_id,
            all_bases=selected_bases,
            player_pp=initial.owner_pp,
            complete_fleet_planets_all_buildable_bases_and_warehouses_asserted=True,
            caller_explicit_random_selected_base_asserted=True,
            no_priority_cloning_mining_stations_or_other_actions_asserted=True,
            default_regular_zero_pp_no_idle_pp_income_asserted=True,
        )
        built = simulate_late_pq_external_selected_economic_turn(
            prebuild, specs, context, placement=external_build.placement,
            standard_rules_asserted=True,
            full_independent_economic_inventory_asserted=True,
            seed=seed + len(wait_plans),
        )
        if (
            not built.supported or built.state is None
            or built.ship_receipt is None
            or built.ship_receipt.ship_id != external_build.selected_ship_id
            or built.selected_base_id != external_build.selected_planet_id
            or built.state.turn != waited.state.turn + 1
            or len(built.state.ships) != initial.soft_ship_limit
            or set(built.state.ships) != (
                set(prebuild.ships) | {external_build.selected_ship_id}
            )
            or built.player_pp_after != initial.owner_pp
            or not built.planet_balances
            or not all(b.resource_balance_exact for b in built.planet_balances)
        ):
            raise UnsupportedPQCalendar("unreconciled restored PQ ship/PP/economy")

        after_build = CappedPQCarry(
            initial.soft_ship_limit,
            built.player_pp_after,
            built.warehouses_after,
        )
        if (
            len(after_build.all_base_warehouses) != len(initial.all_base_warehouses)
            or {p for p, _ in after_build.all_base_warehouses} != set(stock)
            or built.state.starbases != before.starbases
            or built.state.players != before.players
        ):
            raise UnsupportedPQCalendar("unreconciled all-starbase warehouse rollover")

        moving = simulate_capped_pq_existing_ship_cargo_carry(
            built.state, specs, after_build, fleet_plans,
            standard_rules_asserted=True,
            complete_fleet_queue_warehouse_and_owner_pp_asserted=True,
            no_priority_clone_mining_stations_or_external_effects_asserted=True,
            complete_no_encounter_routes_asserted=True,
            seed=seed + len(wait_plans) + 1,
        )
        if (
            not moving.supported or moving.state is None
            or moving.carry_after != after_build
            or len(moving.turns) != len(fleet_plans)
            or moving.state.turn != (
                before.turn + len(wait_plans) + 1 + len(fleet_plans)
            )
            or len(moving.state.ships) != initial.soft_ship_limit
            or moving.state.starbases != before.starbases
            or moving.state.players != before.players
        ):
            raise UnsupportedPQCalendar("uncertain capped fleet after restored ship")
        return MixedPQCalendarOutcome(
            STATUS, state=moving.state, carry_after=after_build,
            waiting_turns=waited.turns,
            external_removed_ship_id=external_build.external_removed_ship_id,
            build=built, fleet_turns=moving.turns,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        return abstain(f"{type(exc).__name__}: {exc}")
