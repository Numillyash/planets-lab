from __future__ import annotations

import sys

from planets_lab.validation.movement_geometry import projection_candidates
from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion import _mission_id, partial_samples


def _brief(ship, after=None) -> str:
    end = None if after is None else (after.x, after.y)
    return (
        f"id={ship.id} owner={ship.owner_id} hull={ship.hull_id} mission={_mission_id(ship.mission)} "
        f"m1={ship.mission1_target_id} m2={ship.mission2_target_id} warp={ship.warp} "
        f"damage={ship.damage} fuel={ship.cargo.neutronium} "
        f"target={(ship.waypoint_x, ship.waypoint_y)} end={end}"
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m planets_lab.validation.real_game_motion_context_cli DATASET.jsonl", file=sys.stderr)
        return 2

    transitions = consecutive_transitions(load_jsonl(sys.argv[1]))
    by_key = {
        (t.before.game_id, t.before.stream.source_player_slot_id, t.before.turn): t
        for t in transitions
    }
    residuals = [
        s for s in partial_samples(transitions)
        if projection_candidates(s)["host_major_minor"] != s.observed_destination
    ]

    print("===== REAL GAME MOTION RESIDUAL CONTEXT =====")
    print(f"residual cases               {len(residuals)}")

    for sample in residuals:
        transition = by_key[(sample.game_id, sample.player_slot_id, sample.turn)]
        before = transition.before.import_state()
        after = transition.after.import_state()
        ship = before.ships[sample.ship_id]
        next_ship = after.ships[sample.ship_id]
        player = before.players.get(sample.player_slot_id)
        expected = projection_candidates(sample)["host_major_minor"]
        origin = (ship.x, ship.y)
        observed = (next_ship.x, next_ship.y)

        print()
        print(
            f"turn={sample.turn} player={sample.player_slot_id} race={None if player is None else player.race_id} "
            f"ship={sample.ship_id} expected={expected} observed={observed}"
        )
        print(f"  before: {_brief(ship, next_ship)}")
        print(
            f"  after: damage={next_ship.damage} warp={next_ship.warp} fuel={next_ship.cargo.neutronium} "
            f"mission={_mission_id(next_ship.mission)} target={(next_ship.waypoint_x, next_ship.waypoint_y)}"
        )

        peers = [s for s in before.ships.values() if s.id != ship.id and (s.x, s.y) == origin]
        same_end = []
        mission6 = []
        for other in peers:
            other_after = after.ships.get(other.id)
            if other_after is not None and (other_after.x, other_after.y) == observed:
                same_end.append((other, other_after))
            if _mission_id(other.mission) == 6 and sample.ship_id in {other.mission1_target_id, other.mission2_target_id}:
                mission6.append((other, other_after))

        print(f"  peers_before={len(peers)} same_end={len(same_end)} mission6_targeting={len(mission6)}")
        for other, other_after in same_end:
            print(f"    same-end: {_brief(other, other_after)}")
        for other, other_after in mission6:
            print(f"    mission6-target: {_brief(other, other_after)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
