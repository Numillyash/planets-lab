from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _movement_category,
    _planet_tuples_by_turn,
)
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.movement_topology_diagnostics import (
    _wrapped_planets_near,
    sphere_adjusted_sample,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.validation.movement_geometry import MovementSample


DB = Path("validation/corpus/compiled/v1/corpus.duckdb")
ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")

# Empirically validated wrap period for the one sphere game in the current
# corpus. Keep this diagnostic-only until ordinary Move-Most sensitivity is
# measured independently of the Horwasp ballistic integration.
EFFECTIVE_PERIOD_BY_GAME: dict[int, tuple[int, int]] = {
    591478: (2170, 2170),
}

HORWASP_HULLS = frozenset(range(201, 214))


def _sample(row: dict[str, Any]) -> MovementSample:
    hull_id = int(row["hull_id"]) if row["hull_id"] is not None else None
    return MovementSample(
        turn=int(row["before_embedded_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        gravitonic=hull_id in GRAVITONIC_HULL_IDS if hull_id is not None else False,
        hull_id=hull_id,
    )


def _classify(
    sample: MovementSample,
    *,
    planets: tuple[tuple[int, int, int], ...],
    width: int,
    height: int,
) -> tuple[str, float]:
    adjusted = sphere_adjusted_sample(sample, width=width, height=height)
    wrapped_planets = _wrapped_planets_near(
        (sample.x, sample.y),
        planets,
        width=width,
        height=height,
    )
    category = _movement_category(adjusted, planets=wrapped_planets)
    distance = hypot(adjusted.next_x - adjusted.x, adjusted.next_y - adjusted.y)
    return category, distance


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        columns = [
            item[1]
            for item in con.execute(
                "PRAGMA table_info('movement_post_horwasp_strong_residual')"
            ).fetchall()
        ]
        raw_rows = con.execute(
            "SELECT * FROM movement_post_horwasp_strong_residual "
            "ORDER BY game_id, before_archive_turn, ship_id"
        ).fetchall()
    finally:
        con.close()

    rows = [dict(zip(columns, raw)) for raw in raw_rows]
    print("===== FINAL RESIDUAL SPHERE GEOMETRY AUDIT =====")
    print("final_residual_rows=", len(rows))

    by_game_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game_rows[int(row["game_id"])].append(row)

    totals = Counter()
    by_hull: dict[int, Counter[str]] = defaultdict(Counter)
    by_game: dict[int, Counter[str]] = defaultdict(Counter)
    transitions = Counter()
    examples: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(by_game_rows.items()):
        sphere = game_rows[0].get("sphere")
        raw_width = game_rows[0].get("map_width")
        raw_height = game_rows[0].get("map_height")
        stable = game_rows[0].get("topology_stable")

        if sphere is not True or stable is not True or not raw_width or not raw_height:
            totals["non_sphere_or_unusable_rows"] += len(game_rows)
            print(
                f"game={game_id} rows={len(game_rows)} sphere={sphere!r} "
                f"raw={raw_width}x{raw_height} stable={stable!r} skipped=True"
            )
            continue

        archive_data = (ARCHIVE_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)
        effective_width, effective_height = EFFECTIVE_PERIOD_BY_GAME.get(
            game_id,
            (int(raw_width), int(raw_height)),
        )
        print(
            f"game={game_id} rows={len(game_rows)} sphere=True stable=True "
            f"raw={raw_width}x{raw_height} effective={effective_width}x{effective_height} "
            f"prepared_cache_hit={hit}"
        )

        for row in game_rows:
            totals["sphere_rows"] += 1
            by_game[game_id]["rows"] += 1
            hull_id = int(row["hull_id"]) if row["hull_id"] is not None else -1
            by_hull[hull_id]["rows"] += 1
            sample = _sample(row)
            planets = planets_by_turn.get(int(row["before_archive_turn"]), ())

            raw_category, raw_distance = _classify(
                sample,
                planets=planets,
                width=int(raw_width),
                height=int(raw_height),
            )
            effective_category, effective_distance = _classify(
                sample,
                planets=planets,
                width=effective_width,
                height=effective_height,
            )

            raw_explains = raw_category in GEOMETRY_EXPLAINED_CATEGORIES
            effective_explains = effective_category in GEOMETRY_EXPLAINED_CATEGORIES
            is_horwasp = hull_id in HORWASP_HULLS

            if raw_explains:
                totals["raw_period_explains"] += 1
                by_hull[hull_id]["raw_explains"] += 1
                by_game[game_id]["raw_explains"] += 1
            if effective_explains:
                totals["effective_period_explains"] += 1
                by_hull[hull_id]["effective_explains"] += 1
                by_game[game_id]["effective_explains"] += 1
                if not is_horwasp:
                    totals["effective_period_explains_non_horwasp"] += 1
                    by_hull[hull_id]["effective_explains_non_horwasp"] += 1
            if effective_explains and not raw_explains:
                totals["effective_only_explains"] += 1
                by_hull[hull_id]["effective_only"] += 1
                by_game[game_id]["effective_only"] += 1
                if not is_horwasp:
                    totals["effective_only_explains_non_horwasp"] += 1
            if raw_explains and not effective_explains:
                totals["raw_only_explains"] += 1
                by_hull[hull_id]["raw_only"] += 1
                by_game[game_id]["raw_only"] += 1

            transitions[
                f"{row.get('baseline_category')} -> raw:{raw_category} -> effective:{effective_category}"
            ] += 1

            if effective_explains and len(examples) < 60:
                examples.append(
                    {
                        "game": game_id,
                        "turn": int(row["before_archive_turn"]),
                        "ship": int(row["ship_id"]),
                        "hull": hull_id,
                        "warp": int(row["warp"]),
                        "origin": (int(row["x_before"]), int(row["y_before"])),
                        "observed": (int(row["x_after"]), int(row["y_after"])),
                        "target": (int(row["target_x"]), int(row["target_y"])),
                        "raw_observed_distance": round(float(row["observed_distance"]), 3),
                        "raw_period_distance": round(raw_distance, 3),
                        "effective_period_distance": round(effective_distance, 3),
                        "raw_category": raw_category,
                        "effective_category": effective_category,
                        "effective_only": effective_explains and not raw_explains,
                    }
                )

    print("\n===== TOTAL =====")
    for key in (
        "final_residual_rows",
        "sphere_rows",
        "non_sphere_or_unusable_rows",
        "raw_period_explains",
        "effective_period_explains",
        "effective_period_explains_non_horwasp",
        "effective_only_explains",
        "effective_only_explains_non_horwasp",
        "raw_only_explains",
    ):
        value = len(rows) if key == "final_residual_rows" else totals[key]
        print(f"{key}=", value)

    print("\n===== BY GAME =====")
    for game_id, counts in sorted(by_game.items()):
        print(game_id, dict(counts))

    print("\n===== TOP HULLS BY SPHERE CLOSURE =====")
    print(
        "hull | sphere_rows | raw_explains | effective_explains | "
        "effective_only | raw_only | effective_non_horwasp"
    )
    for hull_id, counts in sorted(
        by_hull.items(), key=lambda item: (-item[1]["effective_explains"], -item[1]["rows"], item[0])
    )[:60]:
        print(
            hull_id,
            counts["rows"],
            counts["raw_explains"],
            counts["effective_explains"],
            counts["effective_only"],
            counts["raw_only"],
            counts["effective_explains_non_horwasp"],
            sep=" | ",
        )

    print("\n===== HULL 46 =====")
    print(dict(by_hull.get(46, Counter())))

    print("\n===== TOP TRANSITIONS =====")
    for key, count in transitions.most_common(40):
        print(count, key)

    print("\n===== EXPLAINED EXAMPLES =====")
    for item in examples:
        print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
