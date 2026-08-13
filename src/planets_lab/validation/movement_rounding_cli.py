from __future__ import annotations

import csv
import sys

from planets_lab.validation.movement_geometry import (
    MovementSample,
    candidate_scores,
    continuous_partial_destination,
    group_candidate_scores,
    projection_candidates,
)


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "t"}


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def _parse_game_id(value: str | None) -> int | str | None:
    if value is None or value.strip() == "":
        return None
    cleaned = value.strip()
    try:
        return int(cleaned)
    except ValueError:
        return cleaned


def _print_scores(label: str, scores: dict[str, tuple[int, int]]) -> None:
    print(label)
    for mode, (matches, total) in scores.items():
        print("  {:8s}: {}/{}".format(mode, matches, total))


def main() -> int:
    reader = csv.DictReader(sys.stdin)
    samples = [
        MovementSample(
            turn=int(row["turn"]),
            ship_id=int(row["ship_id"]),
            x=int(row["x"]),
            y=int(row["y"]),
            target_x=int(row["target_x"]),
            target_y=int(row["target_y"]),
            warp=int(row["warp"]),
            next_x=int(row["next_x"]),
            next_y=int(row["next_y"]),
            gravitonic=_parse_bool(row.get("gravitonic")),
            game_id=_parse_game_id(row.get("game_id")),
            player_slot_id=_parse_optional_int(row.get("player_slot_id")),
            hull_id=_parse_optional_int(row.get("hull_id")),
            mission=_parse_optional_int(row.get("mission")),
            damage=_parse_optional_int(row.get("damage")),
            friendly_code=(row.get("friendly_code") or ""),
        )
        for row in reader
    ]

    print("===== MOVEMENT ROUNDING CANDIDATES =====")
    print("samples:", len(samples))
    _print_scores("all samples", candidate_scores(samples))

    for attribute in ("game_id", "player_slot_id", "mission"):
        groups = group_candidate_scores(samples, attribute=attribute)
        if len(groups) <= 1 and next(iter(groups), None) is None:
            continue

        print()
        print("===== BY {} =====".format(attribute.upper()))
        for key in sorted(groups, key=lambda item: (item is None, str(item))):
            _print_scores("{}={}".format(attribute, key), groups[key])

    undamaged = [
        sample
        for sample in samples
        if sample.damage is not None and sample.damage < 20
    ]
    damaged = [
        sample
        for sample in samples
        if sample.damage is not None and sample.damage >= 20
    ]

    if undamaged or damaged:
        print()
        print("===== BY DAMAGE CLASS =====")
        if undamaged:
            _print_scores("damage<20", candidate_scores(undamaged))
        if damaged:
            _print_scores("damage>=20", candidate_scores(damaged))

    print()
    print("===== DISCRIMINATING SAMPLES =====")

    for sample in samples:
        candidates = projection_candidates(sample)
        if len(set(candidates.values())) <= 1:
            continue

        raw_x, raw_y = continuous_partial_destination(sample)
        context = (
            "game={} player={} turn={} ship={} hull={} mission={} damage={} "
            "observed=({}, {}) observed_dist={:.6f} raw=({:.6f}, {:.6f}) "
            "nominal={} candidates={}"
        ).format(
            sample.game_id,
            sample.player_slot_id,
            sample.turn,
            sample.ship_id,
            sample.hull_id,
            sample.mission,
            sample.damage,
            sample.next_x,
            sample.next_y,
            sample.observed_distance,
            raw_x,
            raw_y,
            sample.nominal_max_distance,
            candidates,
        )
        print(context)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
