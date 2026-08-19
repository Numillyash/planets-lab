from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _movement_category,
    _planet_tuples_by_turn,
    _warp_well_destination,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.validation.movement_geometry import host_major_minor_destination


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _candidate_without_above_nominal_guard(sample, planets):
    """Reproduce ordinary geometry but test warp wells before above-nominal rejection.

    This is an audit-only candidate. It intentionally reuses the production
    host-major/minor projection and warp-well resolver, changing only ordering.
    """

    if sample.warp <= 0:
        return None, None, False

    origin = (sample.x, sample.y)
    target = (sample.target_x, sample.target_y)
    observed = sample.observed_destination
    nominal = sample.nominal_max_distance

    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    target_distance_sq = dx * dx + dy * dy

    if target_distance_sq <= nominal * nominal:
        expected = target
        branch = "reachable"
    else:
        expected = host_major_minor_destination(sample)
        branch = "partial"

    well, ambiguous = _warp_well_destination(
        sample=sample,
        endpoint=expected,
        planets=planets,
    )
    if ambiguous:
        return branch, None, True
    if well is None:
        return branch, None, False
    return branch, well, False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether post-Horwasp residual movement rows are ordinary warp-well "
            "arrivals hidden by the current above_nominal early return."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                hull_id,
                observed_distance,
                horwasp_candidate_kind,
                horwasp_category
            FROM movement_post_horwasp_strong_residual
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    print("compiled_residual_rows=", len(rows))
    print("games=", sorted(by_game))

    totals = Counter()
    by_hull = Counter()
    by_game_count = Counter()
    by_baseline = Counter()
    by_kind = Counter()
    examples: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        prepared_path = PREPARED_DIR / f"game-{game_id}.pickle"
        archive_data = archive_path.read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_path,
        )
        records = prepared.snapshots
        entities = _entity_map(records)
        planets_by_turn = _planet_tuples_by_turn(entities)
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }

        local = Counter()
        for (
            _gid,
            before_turn,
            after_turn,
            ship_id,
            hull_id,
            db_observed_distance,
            horwasp_kind,
            horwasp_category,
        ) in by_game[game_id]:
            totals["rows"] += 1
            transition = transition_by_key.get((int(before_turn), int(after_turn), int(ship_id)))
            if transition is None:
                totals["missing_transition"] += 1
                continue
            sample = _sample_from_transition(transition, entities)
            if sample is None:
                totals["missing_sample"] += 1
                continue

            planets = planets_by_turn.get(int(before_turn), ())
            baseline = _movement_category(sample, planets=planets)
            branch, well, ambiguous = _candidate_without_above_nominal_guard(sample, planets)

            if ambiguous:
                totals["candidate_ambiguous"] += 1
                continue
            if well is None:
                continue

            totals["candidate_has_warp_well"] += 1
            observed = sample.observed_destination
            if observed != well:
                continue

            totals["candidate_observed_matches_warp_well"] += 1
            local["matches"] += 1
            hid = int(hull_id) if hull_id is not None else -1
            by_hull[hid] += 1
            by_game_count[game_id] += 1
            by_baseline[baseline] += 1
            by_kind[(str(horwasp_kind or "none"), str(horwasp_category or "none"))] += 1

            if baseline == "above_nominal":
                totals["above_nominal_hidden_warp_well"] += 1
                local["above_nominal"] += 1
            else:
                totals["other_baseline_warp_well_match"] += 1

            if len(examples) < args.examples:
                examples.append({
                    "game": game_id,
                    "turn": int(before_turn),
                    "ship": int(ship_id),
                    "hull": hid,
                    "warp": sample.warp,
                    "origin": (sample.x, sample.y),
                    "waypoint": (sample.target_x, sample.target_y),
                    "observed": observed,
                    "observed_distance": round(float(db_observed_distance), 3),
                    "nominal": sample.nominal_max_distance,
                    "baseline": baseline,
                    "candidate_branch": branch,
                    "candidate_planet": well,
                    "horwasp_kind": str(horwasp_kind or "none"),
                    "horwasp_category": str(horwasp_category or "none"),
                })

        print(
            f"game={game_id} prepared_cache_hit={hit} residual={len(by_game[game_id])} "
            f"warp_well_matches={local['matches']} above_nominal={local['above_nominal']}"
        )

    print("\n===== TOTAL =====")
    for key in (
        "rows",
        "missing_transition",
        "missing_sample",
        "candidate_ambiguous",
        "candidate_has_warp_well",
        "candidate_observed_matches_warp_well",
        "above_nominal_hidden_warp_well",
        "other_baseline_warp_well_match",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== BY CURRENT BASELINE =====")
    for key, count in by_baseline.most_common():
        print(key, count)

    print("\n===== TOP HULLS =====")
    for hull_id, count in by_hull.most_common(50):
        print(hull_id, count)

    print("\n===== BY GAME =====")
    for game_id, count in by_game_count.most_common():
        print(game_id, count)

    print("\n===== HORWASP LABELS =====")
    for key, count in by_kind.most_common():
        print(key, count)

    print("\n===== EXAMPLES =====")
    for row in examples:
        print(row)

    print("\nNOTE: this audit changes only classifier ordering.")
    print("It reuses the current eligible-planet set, host-major/minor projection, and warp-well resolver.")
    print("A large above_nominal_hidden_warp_well count therefore indicates a pipeline ordering bug, not a new movement formula.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
