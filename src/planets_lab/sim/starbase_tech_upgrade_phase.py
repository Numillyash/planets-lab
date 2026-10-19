"""Research-only standard starbase technology purchases with explicit orders.

The documented *standard* MegaCredit upgrade schedule is reused here.
This phase is not a NuHost phase-order witness or a substitute for independently
captured orders. A caller must explicitly supply the applicable tech-level cap.
Campaign/custom prices, free tech bonuses, non-premium eligibility, upgrades
submitted by the client, and arbitrary base construction are not inferred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Mapping

from planets_lab.core import GameState
from planets_lab.data.nu_build_cost_calibration import (
    published_standard_tech_upgrade_cost_mc,
)
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import StarbaseTechUpgradeOrder, TurnOrders

TECH_FIELDS = (
    ("tech_hull", "hull"),
    ("tech_engine", "engine"),
    ("tech_beam", "beam"),
    ("tech_torpedo", "torpedo"),
)


class UnsupportedStarbaseTechUpgrade(RuntimeError):
    """Fail-closed unsupported rule context or submitted base upgrade."""


@dataclass(slots=True)
class StarbaseTechUpgradePhase:
    # Caller asserted per-owner level caps (e.g. 7 or 10), not inferred
    # from race, Premium status, homeworld or archive observations.
    max_level_by_player: Mapping[int, int]
    name: str = field(init=False, default="starbase_tech_upgrade")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del rng
        upgrades: list[tuple[int, StarbaseTechUpgradeOrder]] = []
        for player_id in sorted(orders.by_player):
            owner = orders.by_player[player_id]
            for upgrade in owner.starbase_tech_orders:
                upgrades.append((player_id, upgrade))

        # Sort globally; never silently permit multiple competing orders for
        # one starbase, including orders from different players.
        upgrades.sort(key=lambda row: (row[1].planet_id, row[0]))
        seen: set[int] = set()
        events: list[HostEvent] = []
        for player_id, order in upgrades:
            if type(order) is not StarbaseTechUpgradeOrder:
                raise UnsupportedStarbaseTechUpgrade("unsupported tech order type")
            pid = order.planet_id
            if type(pid) is not int or pid <= 0 or pid in seen:
                raise UnsupportedStarbaseTechUpgrade("invalid or duplicate starbase planet id")
            seen.add(pid)
            base = state.starbases.get(pid)
            planet = state.planets.get(pid)
            if base is None or planet is None:
                raise UnsupportedStarbaseTechUpgrade("missing authenticated starbase and planet")
            if base.owner_id != player_id or planet.owner_id != player_id:
                raise UnsupportedStarbaseTechUpgrade("starbase/planet order owner mismatch")
            cap = self.max_level_by_player.get(player_id)
            if type(cap) is not int or not 1 <= cap <= 10:
                raise UnsupportedStarbaseTechUpgrade(
                    "explicit standard-rules tech level cap required for each owner"
                )
            total_cost = 0
            changed: list[tuple[str, int, int]] = []
            for field_name, order_field in TECH_FIELDS:
                start = getattr(base, field_name)
                target = getattr(order, order_field)
                if type(start) is not int or not 1 <= start <= 10:
                    raise UnsupportedStarbaseTechUpgrade("invalid starting tech level")
                if target is None:
                    continue
                if type(target) is not int or not start <= target <= cap:
                    raise UnsupportedStarbaseTechUpgrade(
                        "tech target below current level or above asserted eligibility cap"
                    )
                if target > start:
                    total_cost += published_standard_tech_upgrade_cost_mc(start, target)
                    changed.append((field_name, start, target))
            if not changed:
                raise UnsupportedStarbaseTechUpgrade("no positive tech upgrade in order")
            if type(planet.cargo.megacredits) is not int or (
                planet.cargo.megacredits < total_cost
            ):
                raise UnsupportedStarbaseTechUpgrade(
                    "insufficient planet MegaCredits for selected upgrade placement"
                )
            planet.cargo.megacredits -= total_cost
            for name, _, target in changed:
                setattr(base, name, target)
            details = (
                ("planet_id", str(pid)),
                ("cost_mc", str(total_cost)),
            ) + tuple(
                (name + "_from", str(start)) for name, start, _ in changed
            ) + tuple(
                (name + "_to", str(target)) for name, _, target in changed
            )
            events.append(HostEvent(
                phase=self.name,
                kind="starbase_tech_upgraded_standard_conditional",
                entity_type="starbase", entity_id=pid,
                details=details,
                message="standard pricing hypothesis, not NuHost-executed order",
            ))
        return events
