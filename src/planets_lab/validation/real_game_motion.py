from __future__ import annotations

from math import hypot

from planets_lab.validation.movement_geometry import MovementSample, candidate_scores
from planets_lab.validation.real_game import RealGameTransition

SPECIAL_MISSION_IDS = frozenset({6, 7})


def _mission_id(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def partial_samples(
    transitions: tuple[RealGameTransition, ...],
) -> tuple[MovementSample, ...]:
    result: list[MovementSample] = []
    for transition in transitions:
        before = transition.before.import_state()
        after = transition.after.import_state()
        player_id = transition.before.stream.source_player_slot_id
        common = set(before.ships).intersection(after.ships)
        for ship_id in sorted(common):
            ship = before.ships[ship_id]
            next_ship = after.ships[ship_id]
            if ship.owner_id != player_id or next_ship.owner_id != player_id:
                continue
            mission_id = _mission_id(ship.mission)
            if mission_id in SPECIAL_MISSION_IDS:
                continue
            if ship.friendly_code.strip().lower() == "hyp" or ship.warp <= 0:
                continue
            tx = ship.waypoint_x if ship.waypoint_x is not None else ship.x
            ty = ship.waypoint_y if ship.waypoint_y is not None else ship.y
            nominal = ship.warp * ship.warp
            if hypot(tx - ship.x, ty - ship.y) <= nominal:
                continue
            observed = hypot(next_ship.x - ship.x, next_ship.y - ship.y)
            if observed > nominal + 1.5:
                continue
            result.append(
                MovementSample(
                    game_id=before.game_id,
                    player_slot_id=player_id,
                    turn=before.turn,
                    ship_id=ship.id,
                    hull_id=ship.hull_id,
                    mission=mission_id,
                    damage=ship.damage,
                    friendly_code=ship.friendly_code,
                    x=ship.x,
                    y=ship.y,
                    target_x=tx,
                    target_y=ty,
                    warp=ship.warp,
                    next_x=next_ship.x,
                    next_y=next_ship.y,
                )
            )
    return tuple(result)


def summarize_motion(transitions: tuple[RealGameTransition, ...]) -> dict[str, object]:
    pairs = appeared = disappeared = moved = stationary = special = normal = 0
    reachable = reachable_matches = above_nominal = 0
    for transition in transitions:
        before = transition.before.import_state()
        after = transition.after.import_state()
        player_id = transition.before.stream.source_player_slot_id
        before_ids = {s.id for s in before.ships.values() if s.owner_id == player_id}
        after_ids = {s.id for s in after.ships.values() if s.owner_id == player_id}
        appeared += len(after_ids - before_ids)
        disappeared += len(before_ids - after_ids)
        for ship_id in sorted(before_ids.intersection(after_ids)):
            pairs += 1
            ship = before.ships[ship_id]
            next_ship = after.ships[ship_id]
            if (ship.x, ship.y) == (next_ship.x, next_ship.y):
                stationary += 1
            else:
                moved += 1
            mission_id = _mission_id(ship.mission)
            if mission_id in SPECIAL_MISSION_IDS or ship.friendly_code.strip().lower() == "hyp":
                special += 1
                continue
            normal += 1
            if ship.warp <= 0:
                continue
            tx = ship.waypoint_x if ship.waypoint_x is not None else ship.x
            ty = ship.waypoint_y if ship.waypoint_y is not None else ship.y
            nominal = ship.warp * ship.warp
            observed = hypot(next_ship.x - ship.x, next_ship.y - ship.y)
            if observed > nominal + 1.5:
                above_nominal += 1
                continue
            if hypot(tx - ship.x, ty - ship.y) <= nominal:
                reachable += 1
                if (next_ship.x, next_ship.y) == (tx, ty):
                    reachable_matches += 1
    samples = partial_samples(transitions)
    return {
        "transitions": len(transitions),
        "source_ship_pairs": pairs,
        "source_ships_appeared": appeared,
        "source_ships_disappeared": disappeared,
        "moved": moved,
        "stationary": stationary,
        "special_cases": special,
        "ordinary_cases": normal,
        "reachable_cases": reachable,
        "reachable_matches": reachable_matches,
        "partial_cases": len(samples),
        "rounding_scores": candidate_scores(samples),
        "excluded_above_nominal": above_nominal,
    }
