from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from planets_lab.core import GameState, Ship
from planets_lab.data import NuStaticSpecs
from planets_lab.rules import max_nominal_distance
from planets_lab.sim.movement_classifier import classify_movement_intents


class UnsupportedTowTopology(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TowAttemptResult:
    tower_ship_id: int
    target_ship_id: int | None
    locked: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TowResolution:
    attempts: tuple[TowAttemptResult, ...]

    @property
    def successful(self) -> tuple[TowAttemptResult, ...]:
        return tuple(item for item in self.attempts if item.locked)


def _engine_count(ship: Ship, specs: NuStaticSpecs) -> int:
    hull = specs.hulls.get(ship.hull_id)
    if hull is None:
        raise ValueError(f"missing hull spec {ship.hull_id} for ship {ship.id}")
    return hull.engine_count


def target_breaks_tow(target: Ship, tower: Ship, specs: NuStaticSpecs, *, gravitonic_hull_ids: frozenset[int] = frozenset()) -> bool:
    if target.cargo.neutronium <= 25:
        return False
    if _engine_count(target, specs) < 2:
        return False
    tx = target.waypoint_x if target.waypoint_x is not None else target.x
    ty = target.waypoint_y if target.waypoint_y is not None else target.y
    if hypot(tx - target.x, ty - target.y) <= target.warp * target.warp:
        return False
    target_speed = max_nominal_distance(target.warp, gravitonic=target.hull_id in gravitonic_hull_ids)
    tower_speed = max_nominal_distance(tower.warp, gravitonic=tower.hull_id in gravitonic_hull_ids)
    return target_speed >= tower_speed


def resolve_tow_locks(state: GameState, specs: NuStaticSpecs, *, tow_attempt_ship_ids: frozenset[int] | None = None, gravitonic_hull_ids: frozenset[int] = frozenset(), allow_single_engine_tow: bool = False) -> TowResolution:
    if tow_attempt_ship_ids is None:
        tow_attempt_ship_ids = classify_movement_intents(state).tow_attempt_ship_ids

    unknown = tow_attempt_ship_ids.difference(state.ships)
    if unknown:
        raise ValueError(f"tow attempts reference unknown ships: {sorted(unknown)}")

    targeted_towers = {state.ships[sid].mission1_target_id for sid in tow_attempt_ship_ids if state.ships[sid].mission1_target_id in tow_attempt_ship_ids}
    if targeted_towers:
        raise UnsupportedTowTopology(f"tow chains/cycles are not implemented: {sorted(targeted_towers)}")

    locked_targets: set[int] = set()
    results: list[TowAttemptResult] = []
    for tower_id in sorted(tow_attempt_ship_ids):
        tower = state.ships[tower_id]
        target_id = tower.mission1_target_id
        if target_id is None or target_id == tower_id or target_id not in state.ships:
            results.append(TowAttemptResult(tower_id, target_id, False, "invalid_target"))
            continue
        target = state.ships[target_id]
        if _engine_count(tower, specs) < 2 and not allow_single_engine_tow:
            results.append(TowAttemptResult(tower_id, target_id, False, "insufficient_engines"))
            continue
        if tower.cargo.neutronium <= 0:
            results.append(TowAttemptResult(tower_id, target_id, False, "no_fuel"))
            continue
        if (tower.x, tower.y) != (target.x, target.y):
            results.append(TowAttemptResult(tower_id, target_id, False, "target_not_colocated"))
            continue
        if target_id in locked_targets:
            results.append(TowAttemptResult(tower_id, target_id, False, "tow_contest_lost"))
            continue
        if target_breaks_tow(target, tower, specs, gravitonic_hull_ids=gravitonic_hull_ids):
            results.append(TowAttemptResult(tower_id, target_id, False, "target_broke_lock"))
            continue
        locked_targets.add(target_id)
        results.append(TowAttemptResult(tower_id, target_id, True))
    return TowResolution(tuple(results))
