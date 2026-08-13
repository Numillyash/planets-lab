from __future__ import annotations

from collections import Counter
from math import hypot

from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id
from planets_lab.validation.movement_geometry import projection_candidates
from planets_lab.validation.real_game import RealGameTransition
from planets_lab.validation.real_game_motion import SPECIAL_MISSION_IDS, _mission_id, _sample

def _well_destination(before, sample, endpoint: tuple[int, int]) -> tuple[int, int] | None:
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

def diagnose(transitions: tuple[RealGameTransition, ...], row_limit: int = 30) -> dict[str, object]:
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
            sample = _sample(before, ship, next_ship, mission_id)
            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = (sample.next_x, sample.next_y)
            nominal = sample.warp * sample.warp
            target_distance = hypot(target[0] - origin[0], target[1] - origin[1])
            observed_distance = hypot(observed[0] - origin[0], observed[1] - origin[1])
            if observed_distance > nominal + 1.5:
                categories["above_nominal"] += 1
                continue
            if target_distance <= nominal:
                if observed == target:
                    categories["reachable_exact"] += 1
                    continue
                well = _well_destination(before, sample, target)
                if well is not None and observed == well:
                    categories["reachable_warp_well"] += 1
                    continue
                category = "reachable_stayed" if observed == origin else "reachable_other"
            else:
                nearest = projection_candidates(sample)["nearest"]
                if observed == nearest:
                    categories["partial_nearest"] += 1
                    continue
                well = _well_destination(before, sample, nearest)
                if well is not None and observed == well:
                    categories["partial_nearest_warp_well"] += 1
                    continue
                category = "partial_stayed" if observed == origin else "partial_other"
            categories[category] += 1
            if len(rows) < row_limit:
                rows.append({
                    "category": category, "turn": before.turn, "player": player_id,
                    "ship": ship.id, "hull": ship.hull_id, "warp": ship.warp,
                    "damage": ship.damage, "fuel": ship.cargo.neutronium,
                    "origin": origin, "target": target, "observed": observed,
                    "target_distance": round(target_distance, 3),
                    "observed_distance": round(observed_distance, 3),
                })
    return {"categories": dict(sorted(categories.items())), "rows": tuple(rows)}
