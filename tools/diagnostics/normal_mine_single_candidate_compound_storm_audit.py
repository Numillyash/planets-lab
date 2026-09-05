from __future__ import annotations

from math import hypot

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import (
    _resolved_storm_offset,
    _storm_clusters,
    _storm_consensus_by_turn,
)
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.rules.ion_storm import integer_drag_delta, local_voltage
from planets_lab.sim.normal_movement import project_toward_waypoint

from normal_mine_single_candidate_immunity_repair_audit import (
    BEFORE_TURN,
    GAME_ID,
    PREPARED_DIR,
    RAW_DIR,
    SHIP_ID,
    _load_row,
    _planned_vector,
    _sample,
)


def _rounded_point(point: tuple[int, int]) -> tuple[int, int]:
    return int(point[0]), int(point[1])


def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])


def _storm_snapshot(
    *,
    turn: int,
    storms: tuple,
    origin: tuple[int, int],
) -> dict[str, object]:
    offset, status = _resolved_storm_offset(storms, x=origin[0], y=origin[1])
    clusters: list[dict[str, object]] = []
    effective_x, effective_y = origin
    for root, circles in _storm_clusters(storms):
        voltage = local_voltage(circles, effective_x, effective_y)
        drag = integer_drag_delta(root.warp, root.heading)
        active = 150.0 <= voltage < 400.0
        clusters.append(
            {
                "root_id": root.id,
                "warp": root.warp,
                "heading": round(root.heading, 6),
                "local_voltage_at_evaluation_point": round(voltage, 6),
                "drag_delta": drag,
                "active_class4_or_5_drag": active,
                "evaluation_point": (effective_x, effective_y),
            }
        )
        if active:
            effective_x += drag[0]
            effective_y += drag[1]
    return {
        "archive_turn": turn,
        "storm_count": len(storms),
        "resolved_offset": offset,
        "resolved_status": status,
        "clusters": clusters,
    }


def main() -> int:
    row = _load_row()
    archive_path = RAW_DIR / f"game-{GAME_ID}.zip"
    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=GAME_ID,
        cache_path=PREPARED_DIR / f"game-{GAME_ID}.pickle",
    )

    sample = _sample(row)
    raw_topology = extract_map_topology(archive_data)
    topology = effective_sphere_topology(game_id=GAME_ID, topology=raw_topology)
    effective_sample = sample
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        effective_sample = sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )

    planned_vector, planned_distance, target_distance = _planned_vector(
        effective_sample,
        float(row["nominal_max_distance"] or 0.0),
    )
    origin = (effective_sample.x, effective_sample.y)
    target = (effective_sample.target_x, effective_sample.target_y)
    observed = (effective_sample.next_x, effective_sample.next_y)

    mine_only_distance = max(0.0, planned_distance - 10.0)
    mine_only_endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=mine_only_distance,
    )

    regular_endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=planned_distance,
    )

    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(
        prepared.snapshots
    )
    before_turn = int(row["before_archive_turn"])
    after_turn = int(row["after_archive_turn"])

    print("===== NORMAL-MINE SINGLE CANDIDATE COMPOUND ION-STORM AUDIT =====")
    print("game=", GAME_ID)
    print("turn=", BEFORE_TURN)
    print("ship=", SHIP_ID)
    print("prepared_cache_hit=", cache_hit)
    print("origin=", origin)
    print("target=", target)
    print("observed_endpoint=", observed)
    print("target_distance=", round(target_distance, 6))
    print("planned_distance=", round(planned_distance, 6))
    print("regular_endpoint=", regular_endpoint)
    print("mine_only_distance_minus_10=", round(mine_only_distance, 6))
    print("mine_only_endpoint=", mine_only_endpoint)
    print("mine_only_to_observed_delta=", (observed[0] - mine_only_endpoint[0], observed[1] - mine_only_endpoint[1]))
    print("mine_only_to_observed_distance=", round(_distance(mine_only_endpoint, observed), 6))

    print("\n===== STORM CONSENSUS STATUS =====")
    print("before_turn_in_conflict_set=", before_turn in storm_conflict_turns)
    print("after_turn_in_conflict_set=", after_turn in storm_conflict_turns)
    print("before_turn_in_invalid_set=", before_turn in storm_invalid_turns)
    print("after_turn_in_invalid_set=", after_turn in storm_invalid_turns)

    snapshots: list[dict[str, object]] = []
    for turn in (before_turn, after_turn):
        storms = tuple(storms_by_turn.get(turn, ()))
        snapshot = _storm_snapshot(turn=turn, storms=storms, origin=origin)
        snapshots.append(snapshot)
        print(f"\n===== STORM SNAPSHOT T{turn} =====")
        print("storm_count=", snapshot["storm_count"])
        print("resolved_status=", snapshot["resolved_status"])
        print("resolved_offset=", snapshot["resolved_offset"])
        for cluster in snapshot["clusters"]:
            print(cluster)

    print("\n===== COMPOUND ENDPOINT CANDIDATES =====")
    any_exact = False
    for snapshot in snapshots:
        offset = snapshot["resolved_offset"]
        if not isinstance(offset, tuple) or len(offset) != 2:
            print({
                "archive_turn": snapshot["archive_turn"],
                "status": snapshot["resolved_status"],
                "candidate_available": False,
            })
            continue
        dx, dy = int(offset[0]), int(offset[1])
        pure_storm_endpoint = (regular_endpoint[0] + dx, regular_endpoint[1] + dy)
        mine_then_storm_endpoint = (mine_only_endpoint[0] + dx, mine_only_endpoint[1] + dy)
        storm_then_mine_endpoint = project_toward_waypoint(
            x=origin[0] + dx,
            y=origin[1] + dy,
            target_x=target[0] + dx,
            target_y=target[1] + dy,
            distance=mine_only_distance,
        )
        pure_exact = pure_storm_endpoint == observed
        mine_storm_exact = mine_then_storm_endpoint == observed
        storm_mine_exact = storm_then_mine_endpoint == observed
        any_exact = any_exact or pure_exact or mine_storm_exact or storm_mine_exact
        print({
            "archive_turn": snapshot["archive_turn"],
            "resolved_offset": (dx, dy),
            "pure_storm_endpoint": pure_storm_endpoint,
            "pure_storm_matches_observed": pure_exact,
            "mine_then_storm_endpoint": mine_then_storm_endpoint,
            "mine_then_storm_matches_observed": mine_storm_exact,
            "storm_then_mine_endpoint": storm_then_mine_endpoint,
            "storm_then_mine_matches_observed": storm_mine_exact,
        })

    print("\n===== VECTOR CONSISTENCY =====")
    route_dx, route_dy = planned_vector
    observed_vector = _vector(origin, observed, topology)
    print("planned_vector=", (round(route_dx, 6), round(route_dy, 6)))
    print("observed_vector=", observed_vector)
    print("mine_only_plus_required_delta=", (
        mine_only_endpoint[0] + (observed[0] - mine_only_endpoint[0]),
        mine_only_endpoint[1] + (observed[1] - mine_only_endpoint[1]),
    ))

    print("\n===== SUMMARY =====")
    print("any_compound_endpoint_exact=", any_exact)
    print("required_post_mine_delta=", (observed[0] - mine_only_endpoint[0], observed[1] - mine_only_endpoint[1]))
    print("required_post_mine_delta_distance=", round(_distance(mine_only_endpoint, observed), 6))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This is an evidence-only compound-order diagnostic. It reuses the already corpus-verified ion-storm "
        "consensus and integer drag helpers, but it does not promote a mine+storm production label from one row. "
        "An exact combined endpoint is evidence that two independently supported effects compose geometrically; "
        "Host phase ordering still requires independent transitions before production semantics are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
