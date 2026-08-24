from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_context import (
    TOW_ATTEMPT,
    MovementMissionConvention,
    _classify_owner_record,
)
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_residual_context import _owner_record, _xy
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _target_id(raw: Any) -> int | None:
    if not hasattr(raw, "get"):
        return None
    return _intish(raw.get("mission1target", raw.get("mission1_target_id")))


def _visible_tow_route_matches(
    *,
    entities: Any,
    ship_groups: Any,
    pairs: set[tuple[int, int]],
) -> dict[tuple[int, int, int], tuple[int, ...]]:
    """Discover owner-visible route-equivalent Tow matches independently of L1 labels."""

    convention = MovementMissionConvention()
    matches: dict[tuple[int, int, int], set[int]] = defaultdict(set)

    for before_turn, after_turn in sorted(pairs):
        tower_ids = sorted(
            entity_id
            for kind, turn, entity_id in entities
            if kind == "ship" and turn == before_turn
        )
        for tower_id in tower_ids:
            group = ship_groups.get((before_turn, tower_id), ())
            _, owner = _owner_record(group)
            if owner is None:
                continue
            if _classify_owner_record(owner, convention=convention) != TOW_ATTEMPT:
                continue

            target_id = _target_id(owner.raw)
            if target_id is None or target_id <= 0 or target_id == tower_id:
                continue

            tower_before = _xy(entities.get(("ship", before_turn, tower_id)))
            target_before = _xy(entities.get(("ship", before_turn, target_id)))
            tower_after = _xy(entities.get(("ship", after_turn, tower_id)))
            target_after = _xy(entities.get(("ship", after_turn, target_id)))
            if None in (tower_before, target_before, tower_after, target_after):
                continue
            if tower_before != target_before:
                continue
            if tower_after != target_after:
                continue
            if tower_after == tower_before:
                continue

            matches[(before_turn, after_turn, target_id)].add(tower_id)

    return {
        key: tuple(sorted(towers))
        for key, towers in matches.items()
        if towers
    }


def _stage(
    *,
    chunnel_explained: bool,
    horwasp_strong_explained: bool,
    mine_strong_explained: bool,
    post_mine_strong_residual: bool,
) -> str:
    if chunnel_explained:
        return "chunnel_explained"
    if horwasp_strong_explained:
        return "horwasp_strong_explained"
    if mine_strong_explained:
        return "mine_strong_explained"
    if post_mine_strong_residual:
        return "post_mine_strong_residual"
    return "other"


def main() -> int:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                hull_id,
                baseline_category,
                chunnel_explained,
                horwasp_strong_explained,
                mine_strong_explained,
                post_mine_strong_residual
            FROM movement_labeled_residual
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== GLOBAL ROUTE-EQUIVALENT TOW DIFFERENTIAL AUDIT =====")
    print("source_view= movement_labeled_residual")
    print("external_residual_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    match_count = Counter()
    stage_counts = Counter()
    by_game_counts = Counter()
    by_hull_counts = Counter()
    baseline_counts = Counter()
    examples: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        pairs = {(int(row[1]), int(row[2])) for row in by_game[game_id]}
        matches = _visible_tow_route_matches(
            entities=entities,
            ship_groups=ship_groups,
            pairs=pairs,
        )

        print(
            f"prepared game={game_id} cache_hit={cache_hit} "
            f"rows={len(by_game[game_id])} route_match_keys={len(matches)}"
        )

        for row in by_game[game_id]:
            (
                _gid,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                baseline_category,
                chunnel_explained,
                horwasp_strong_explained,
                mine_strong_explained,
                post_mine_strong_residual,
            ) = row
            key = (int(before_turn), int(after_turn), int(ship_id))
            towers = matches.get(key, ())
            match_count[len(towers)] += 1
            if not towers:
                continue

            totals["any_visible_matching_tower"] += 1
            if len(towers) == 1:
                totals["single_visible_matching_tower"] += 1
                continue

            totals["route_equivalent_multiple_visible_towers"] += 1
            stage = _stage(
                chunnel_explained=bool(chunnel_explained),
                horwasp_strong_explained=bool(horwasp_strong_explained),
                mine_strong_explained=bool(mine_strong_explained),
                post_mine_strong_residual=bool(post_mine_strong_residual),
            )
            stage_counts[stage] += 1
            by_game_counts[game_id] += 1
            if hull_id is not None:
                by_hull_counts[int(hull_id)] += 1
            baseline_counts[str(baseline_category)] += 1

            if len(examples) < 40:
                examples.append(
                    {
                        "game": game_id,
                        "turn": int(before_turn),
                        "ship": int(ship_id),
                        "hull": int(hull_id) if hull_id is not None else None,
                        "baseline": str(baseline_category),
                        "matching_tower_count": len(towers),
                        "matching_towers": list(towers),
                        "downstream_stage": stage,
                    }
                )

    print("\n===== GLOBAL MATCH ACCOUNTING =====")
    print("any_visible_matching_tower=", totals["any_visible_matching_tower"])
    print("single_visible_matching_tower=", totals["single_visible_matching_tower"])
    print(
        "route_equivalent_multiple_visible_towers=",
        totals["route_equivalent_multiple_visible_towers"],
    )

    print("\n===== MATCH COUNT DISTRIBUTION =====")
    for count, rows_count in sorted(match_count.items()):
        print(count, rows_count)

    print("\n===== MULTIPLE MATCHES BY CURRENT DOWNSTREAM STAGE =====")
    for stage, count in stage_counts.most_common():
        print(stage, count)

    print("\n===== MULTIPLE MATCHES BY GAME =====")
    for game_id, count in by_game_counts.most_common():
        print(game_id, count)

    print("\n===== MULTIPLE MATCHES BY HULL =====")
    for hull_id, count in by_hull_counts.most_common():
        print(hull_id, count)

    print("\n===== MULTIPLE MATCHES BY BASELINE =====")
    for baseline, count in baseline_counts.most_common():
        print(baseline, count)

    print("\n===== ROUTE-EQUIVALENT MULTIPLE EXAMPLES =====")
    for example in examples:
        print(example)

    multiple = totals["route_equivalent_multiple_visible_towers"]
    print("\n===== EXPECTED ACCOUNTING DELTA =====")
    print("external_context_explained_delta=", multiple)
    print("post_external_residual_delta=", -multiple)
    print("chunnel_explained_delta=", -stage_counts["chunnel_explained"])
    print(
        "horwasp_strong_explained_delta=",
        -stage_counts["horwasp_strong_explained"],
    )
    print("mine_strong_explained_delta=", -stage_counts["mine_strong_explained"])
    print(
        "post_mine_strong_residual_delta=",
        -stage_counts["post_mine_strong_residual"],
    )

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "A non-zero multiple-match set is route-equivalent movement evidence only because "
        "every counted owner-visible Tow tower is colocated with the target before movement "
        "and shares its observed non-stationary destination. Tower identity remains ambiguous. "
        "single_visible_matching_tower should be zero in the old external residual; if it is "
        "not zero, stop and investigate the existing L1 detector before accepting a delta."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
