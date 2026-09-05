from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_damage_context import _race_map, max_warp_from_damage
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _load_rows() -> list[dict[str, Any]]:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "after_archive_turn",
            "ship_id",
            "hull_id",
            "warp",
            "observed_distance",
            "nominal_max_distance",
            "mine_damage_hits",
            "mine_slowdown_hits",
        ]
        rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM movement_labeled_residual
            WHERE mine_strong_explained = true
              AND mine_category = 'normal_mine_hit_nearest_damage'
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in rows]


def _target(raw: dict[str, Any]) -> tuple[int | None, int | None]:
    return (
        _intish(raw.get("targetx", raw.get("waypointx"))),
        _intish(raw.get("targety", raw.get("waypointy"))),
    )


def _state_category(
    *,
    before_warp: int | None,
    after_warp: int | None,
    post_damage_limit: int | None,
) -> str:
    if after_warp is None:
        return "after_warp_missing"
    if after_warp == 0:
        return "warp_zero"
    if before_warp is not None and after_warp == before_warp:
        if post_damage_limit is not None and after_warp == post_damage_limit:
            return "unchanged_equals_post_damage_limit"
        return "unchanged_warp"
    if post_damage_limit is not None and after_warp == post_damage_limit:
        return "changed_to_post_damage_limit"
    return "changed_other"


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    rows = _load_rows()
    print("===== NORMAL-MINE POST-TURN WARP STATE CROSS-CASE AUDIT =====")
    print("production_normal_mine_rows=", len(rows))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals = Counter()
    examples: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races = _race_map(prepared.snapshots)
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])

            owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or before_owner is None:
                totals["before_owner_missing"] += 1
                continue
            if after_owner_id != owner_id or after_owner is None:
                totals["after_owner_missing"] += 1
                continue
            totals["owner_ready"] += 1

            before_raw = dict(before_owner.raw)
            after_raw = dict(after_owner.raw)
            race_id = races.get(owner_id)

            before_warp = _intish(before_raw.get("warp"))
            after_warp = _intish(after_raw.get("warp"))
            before_damage = _intish(before_raw.get("damage"))
            after_damage = _intish(after_raw.get("damage"))
            before_supplies = _intish(before_raw.get("supplies"))
            after_supplies = _intish(after_raw.get("supplies"))
            before_target = _target(before_raw)
            after_target = _target(after_raw)
            post_damage_limit = max_warp_from_damage(after_damage, race_id)

            category = _state_category(
                before_warp=before_warp,
                after_warp=after_warp,
                post_damage_limit=post_damage_limit,
            )
            totals[category] += 1
            if before_target == after_target:
                totals["waypoint_preserved"] += 1
            else:
                totals["waypoint_changed"] += 1
            if post_damage_limit is not None and after_warp == post_damage_limit:
                totals["after_warp_equals_post_damage_limit"] += 1
            if before_warp is not None and after_warp is not None and after_warp < before_warp:
                totals["after_warp_lower_than_before"] += 1

            nominal = float(row["nominal_max_distance"] or 0.0)
            observed = float(row["observed_distance"] or 0.0)
            lost = nominal - observed

            example = {
                "game_id": game_id,
                "before_turn": before_turn,
                "ship_id": ship_id,
                "hull_id": row["hull_id"],
                "mine_damage_hits": row["mine_damage_hits"],
                "mine_slowdown_hits": row["mine_slowdown_hits"],
                "nominal_max_distance": round(nominal, 3),
                "observed_distance": round(observed, 3),
                "lost_distance_from_nominal": round(lost, 3),
                "race_id": race_id,
                "before_warp": before_warp,
                "after_warp": after_warp,
                "before_damage": before_damage,
                "after_damage": after_damage,
                "post_damage_max_warp": post_damage_limit,
                "before_supplies": before_supplies,
                "after_supplies": after_supplies,
                "waypoint_preserved": before_target == after_target,
                "state_category": category,
            }
            examples.append(example)

    print("\n===== SUMMARY =====")
    for key in (
        "owner_ready",
        "before_owner_missing",
        "after_owner_missing",
        "changed_to_post_damage_limit",
        "unchanged_equals_post_damage_limit",
        "unchanged_warp",
        "warp_zero",
        "changed_other",
        "after_warp_equals_post_damage_limit",
        "after_warp_lower_than_before",
        "waypoint_preserved",
        "waypoint_changed",
    ):
        print(f"{key}=", totals[key])

    print("\n===== ROWS =====")
    for example in examples:
        print(example)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic treats the after-turn warp and waypoint only as observational state. "
        "Its purpose is to determine whether damage-compatible post-turn warp reduction is common "
        "among already production-closed normal-mine transitions that still exhibit the ordinary "
        "approximately-10-LY-per-hit movement signature. A common pattern would reject using the "
        "target case's after_warp=4 as evidence for same-turn damage-limited continuation. No labels, "
        "schemas, corpus accounting, or Host semantics are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
