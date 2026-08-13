from __future__ import annotations

import math
import sys
from collections.abc import Mapping

from planets_lab.validation.movement_geometry import projection_candidates
from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion import partial_samples


def _number(raw: Mapping[str, object], key: str) -> float | None:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _integer(raw: Mapping[str, object], key: str) -> int | None:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _storm_summary(storm: Mapping[str, object], x: int, y: int) -> dict[str, object]:
    sx = _number(storm, "x")
    sy = _number(storm, "y")
    radius = _number(storm, "radius")
    warp = _number(storm, "warp")
    voltage = _number(storm, "voltage")
    heading = _number(storm, "heading")
    center_distance = None
    inside = None
    if sx is not None and sy is not None:
        center_distance = math.hypot(x - sx, y - sy)
        if radius is not None:
            inside = center_distance <= radius
    drag_distance = None if warp is None else 0.75 * warp * warp
    return {
        "id": _integer(storm, "id"),
        "x": sx,
        "y": sy,
        "radius": radius,
        "voltage": voltage,
        "warp": warp,
        "heading": heading,
        "isgrowing": storm.get("isgrowing"),
        "center_distance": None if center_distance is None else round(center_distance, 3),
        "inside": inside,
        "class4_or_5_candidate": None if voltage is None else voltage >= 150,
        "documented_drag_distance": None if drag_distance is None else round(drag_distance, 3),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: python -m planets_lab.validation.real_game_motion_storm_cli DATASET.jsonl",
            file=sys.stderr,
        )
        return 2

    batches = load_jsonl(sys.argv[1])
    transitions = consecutive_transitions(batches)
    by_key = {
        (t.before.game_id, t.before.stream.source_player_slot_id, t.before.turn): t
        for t in transitions
    }
    residuals = [
        sample
        for sample in partial_samples(transitions)
        if projection_candidates(sample)["host_major_minor"] != sample.observed_destination
    ]

    print("===== REAL GAME ION STORM RESIDUAL CONTEXT =====")
    print(f"records                      {len(batches)}")
    print(f"transitions                  {len(transitions)}")
    print(f"residual cases               {len(residuals)}")

    for sample in residuals:
        transition = by_key[(sample.game_id, sample.player_slot_id, sample.turn)]
        expected = projection_candidates(sample)["host_major_minor"]
        observed = sample.observed_destination
        rx = observed[0] - expected[0]
        ry = observed[1] - expected[1]
        residual_distance = math.hypot(rx, ry)
        residual_angle = math.degrees(math.atan2(ry, rx)) % 360.0

        print()
        print(
            f"turn={sample.turn} player={sample.player_slot_id} ship={sample.ship_id} "
            f"origin=({sample.x},{sample.y}) expected={expected} observed={observed}"
        )
        print(
            f"  residual=({rx:+d},{ry:+d}) distance={residual_distance:.3f} "
            f"xy_angle={residual_angle:.3f}"
        )
        print(f"  ionstorms_before={len(transition.before.ionstorms)}")

        summaries = [
            _storm_summary(storm, sample.x, sample.y)
            for storm in transition.before.ionstorms
        ]
        covering = [item for item in summaries if item["inside"] is True]
        print(f"  covering_storms={len(covering)}")
        for item in covering:
            print(f"    {item}")
        if not covering:
            for item in summaries:
                print(f"    nearby/context: {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
