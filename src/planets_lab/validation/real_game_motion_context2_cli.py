from __future__ import annotations

import sys
from math import hypot

from planets_lab.validation.movement_geometry import projection_candidates
from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion import _mission_id, partial_samples


def _nearby_planets(state, point, radius=3.0):
    rows = []
    for planet in state.planets.values():
        d = hypot(point[0] - planet.x, point[1] - planet.y)
        if d <= radius:
            rows.append((planet.id, planet.x, planet.y, round(d, 3), planet.id in state.starbases))
    return tuple(sorted(rows))


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    transitions = consecutive_transitions(load_jsonl(sys.argv[1]))
    by_key = {(t.before.game_id, t.before.stream.source_player_slot_id, t.before.turn): t for t in transitions}
    residuals = [s for s in partial_samples(transitions) if projection_candidates(s)["host_major_minor"] != s.observed_destination]
    print("===== REAL GAME MOTION RESIDUAL CONTEXT V2 =====")
    print(f"residual cases               {len(residuals)}")
    for sample in residuals:
        t = by_key[(sample.game_id, sample.player_slot_id, sample.turn)]
        before = t.before.import_state()
        after = t.after.import_state()
        ship = before.ships[sample.ship_id]
        next_ship = after.ships[sample.ship_id]
        player = before.players.get(sample.player_slot_id)
        expected = projection_candidates(sample)["host_major_minor"]
        observed = (next_ship.x, next_ship.y)
        print()
        print(f"turn={sample.turn} player={sample.player_slot_id} race={None if player is None else player.race_id} ship={sample.ship_id} hull={ship.hull_id}")
        print(f"  expected={expected} observed={observed}")
        print(f"  before damage={ship.damage} warp={ship.warp} fuel={ship.cargo.neutronium} supplies={ship.cargo.supplies} mission={_mission_id(ship.mission)} target={(ship.waypoint_x, ship.waypoint_y)}")
        print(f"  after  damage={next_ship.damage} warp={next_ship.warp} fuel={next_ship.cargo.neutronium} supplies={next_ship.cargo.supplies} mission={_mission_id(next_ship.mission)} target={(next_ship.waypoint_x, next_ship.waypoint_y)}")
        print(f"  planets_near_expected={_nearby_planets(before, expected)}")
        print(f"  planets_near_observed={_nearby_planets(before, observed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
