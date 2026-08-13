from __future__ import annotations

from collections import Counter
from math import hypot

from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id
from planets_lab.validation.movement_geometry import MovementSample, projection_candidates
from planets_lab.validation.real_game import RealGameTransition
from planets_lab.validation.real_game_motion import SPECIAL_MISSION_IDS, _mission_id


EXPLAINED_CATEGORIES = frozenset(
    {
        "reachable_exact",
        "reachable_warp_well",
        "partial_nearest",
        "partial_nearest_warp_well",
        "reachable_stayed_no_fuel",
        "partial_stayed_no_fuel",
        "warp_zero",
    }
)


def _make_sample(before, ship, next_ship, mission_id: int | None) -> MovementSample:
    target_x = ship.waypoint_x if ship.waypoint_x is not None else ship.x
    target_y = ship.waypoint_y if ship.waypoint_y is not None else ship.y
    return MovementSample(
        game_id=before.game_id,
        player_slot_id=ship.owner_id,
        turn=before.turn,
        ship_id=ship.id,
        hull_id=ship.hull_id,
        mission=mission_id,
        damage=ship.damage,
        friendly_code=ship.friendly_code,
        x=ship.x,
        y=ship.y,
        target_x=target_x,
        target_y=target_y,
        warp=ship.warp,
        next_x=next_ship.x,
        next_y=next_ship.y,
    )


def _well_destination(
    before,
    sample: MovementSample,
    endpoint: tuple[int, int],
) -> tuple[int, int] | None:
    planets = tuple((planet.id, planet.x, planet.y) for planet in before.planets.values())
    try:
        planet_id = warp_well_planet_id(
            origin_x=sample.x,
            origin_y=sample.y,
            end_x=endpoint[0],
            end_y=endpoint[1],
            movement_warp=sample.warp,
            planets=planets,
        )
    except WarpWellAmbiguityError:
        return None
    if planet_id is None:
        return None
    planet = before.planets[planet_id]
    return planet.x, planet.y


def _unresolved_category(
    *,
    reachable: bool,
    origin: tuple[int, int],
    observed: tuple[int, int],
    observed_distance: float,
    nominal: int,
    fuel: int,
) -> str:
    prefix = "reachable" if reachable else "partial"
    if observed == origin:
        return f"{prefix}_stayed_no_fuel" if fuel <= 0 else f"{prefix}_stayed_with_fuel"
    if observed_distance < nominal - 1.5:
        return f"{prefix}_shorter_than_nominal"
    return f"{prefix}_other"


def diagnose(
    transitions: tuple[RealGameTransition, ...],
    row_limit: int = 50,
) -> dict[str, object]:
    categories: Counter[str] = Counter()
    rows: list[dict[str, object]] = []

    for transition in transitions:
        before = transition.before.import_state()
        after = transition.after.import_state()
        player_id = transition.before.stream.source_player_slot_id

        for ship_id in sorted(set(before.ships).intersection(after.ships)):
            ship = before.ships[ship_id]
            next_ship = after.ships[ship_id]
            if ship.owner_id != player_id or next_ship.owner_id != player_id:
                continue

            mission_id = _mission_id(ship.mission)
            if mission_id in SPECIAL_MISSION_IDS or ship.friendly_code.strip().lower() == "hyp":
                continue
            if ship.warp <= 0:
                categories["warp_zero"] += 1
                continue

            sample = _make_sample(before, ship, next_ship, mission_id)
            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = (sample.next_x, sample.next_y)
            nominal = sample.warp * sample.warp
            target_distance = hypot(target[0] - origin[0], target[1] - origin[1])
            observed_distance = hypot(observed[0] - origin[0], observed[1] - origin[1])
            fuel = ship.cargo.neutronium

            category: str | None = None
            expected: tuple[int, int] | None = None

            if observed_distance > nominal + 1.5:
                category = "above_nominal"
            elif target_distance <= nominal:
                expected = target
                if observed == target:
                    categories["reachable_exact"] += 1
                    continue
                well = _well_destination(before, sample, target)
                if well is not None and observed == well:
                    categories["reachable_warp_well"] += 1
                    continue
                category = _unresolved_category(
                    reachable=True,
                    origin=origin,
                    observed=observed,
                    observed_distance=observed_distance,
                    nominal=nominal,
                    fuel=fuel,
                )
            else:
                nearest = projection_candidates(sample)["nearest"]
                expected = nearest
                if observed == nearest:
                    categories["partial_nearest"] += 1
                    continue
                well = _well_destination(before, sample, nearest)
                if well is not None and observed == well:
                    categories["partial_nearest_warp_well"] += 1
                    continue
                category = _unresolved_category(
                    reachable=False,
                    origin=origin,
                    observed=observed,
                    observed_distance=observed_distance,
                    nominal=nominal,
                    fuel=fuel,
                )

            categories[category] += 1
            if len(rows) < row_limit and category not in EXPLAINED_CATEGORIES:
                rows.append(
                    {
                        "category": category,
                        "turn": before.turn,
                        "player": player_id,
                        "ship": ship.id,
                        "hull": ship.hull_id,
                        "mission": mission_id,
                        "friendly_code": ship.friendly_code,
                        "warp": ship.warp,
                        "damage": ship.damage,
                        "fuel": fuel,
                        "origin": origin,
                        "target": target,
                        "expected": expected,
                        "observed": observed,
                        "target_distance": round(target_distance, 3),
                        "observed_distance": round(observed_distance, 3),
                    }
                )

    explained = sum(value for key, value in categories.items() if key in EXPLAINED_CATEGORIES)
    total = sum(categories.values())
    unresolved = total - explained
    return {
        "categories": dict(sorted(categories.items())),
        "rows": tuple(rows),
        "total": total,
        "explained": explained,
        "unresolved": unresolved,
    }
