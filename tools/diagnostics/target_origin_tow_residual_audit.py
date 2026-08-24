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
from planets_lab.corpus.movement_differential import _entity_map, _intish, _resolved_value
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


def _resolved_int(entity: Any, field: str) -> int | None:
    if entity is None:
        return None
    try:
        return _intish(_resolved_value(entity, field))
    except KeyError:
        return None


def _warp_bucket(warp: int | None) -> str:
    if warp is None:
        return "warp_unknown"
    if warp <= 0:
        return "warp0"
    if warp <= 3:
        return "warp1-3"
    if warp <= 6:
        return "warp4-6"
    if warp <= 9:
        return "warp7-9"
    return "warp>9"


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
                warp,
                baseline_category,
                x_before,
                y_before,
                x_after,
                y_after
            FROM movement_post_mine_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND target_x = x_before
              AND target_y = y_before
              AND (x_after <> x_before OR y_after <> y_before)
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== TARGET-ORIGIN TOW RESIDUAL AUDIT =====")
    print("residual_view= movement_post_mine_strong_residual")
    print("candidate_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    convention = MovementMissionConvention()
    totals = Counter()
    warp_counts = Counter()
    baseline_counts = Counter()
    visible_match_count = Counter()
    comover_count = Counter()
    post_warp_counts = Counter()
    by_game_count = Counter()
    by_hull_count = Counter()
    multi_by_game = Counter()
    multi_by_hull = Counter()
    post_warp0_by_game = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")

        print(
            f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}"
        )

        for row in by_game[game_id]:
            (
                _gid,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                warp,
                baseline_category,
                x_before,
                y_before,
                x_after,
                y_after,
            ) = row

            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp) if warp is not None else None
            origin = (int(x_before), int(y_before))
            observed = (int(x_after), int(y_after))

            totals["rows"] += 1
            warp_counts[_warp_bucket(warp)] += 1
            baseline_counts[str(baseline_category)] += 1
            by_game_count[game_id] += 1
            by_hull_count[hull_id] += 1

            candidate_after = entities.get(("ship", after_turn, ship_id))
            after_warp = _resolved_int(candidate_after, "warp")
            after_target = (
                _resolved_int(candidate_after, "targetx"),
                _resolved_int(candidate_after, "targety"),
            )
            post_warp_counts[_warp_bucket(after_warp)] += 1
            if after_warp == 0:
                totals["post_warp0"] += 1
                post_warp0_by_game[game_id] += 1

            colocated_ids = sorted(
                entity_id
                for kind, turn, entity_id in entities
                if kind == "ship"
                and turn == before_turn
                and entity_id != ship_id
                and _xy(entities.get(("ship", before_turn, entity_id))) == origin
            )

            co_movers: list[int] = []
            hidden_or_unresolved_comovers: list[int] = []
            visible_non_tow_comovers: list[int] = []
            visible_tow_targeters: list[int] = []
            visible_matching_towers: list[int] = []
            visible_tow_other_destination: list[int] = []

            for other_id in colocated_ids:
                other_after = entities.get(("ship", after_turn, other_id))
                other_after_xy = _xy(other_after)
                same_destination = other_after_xy == observed
                if same_destination:
                    co_movers.append(other_id)

                group = ship_groups.get((before_turn, other_id), ())
                _, owner = _owner_record(group)
                if owner is None:
                    if same_destination:
                        hidden_or_unresolved_comovers.append(other_id)
                    continue

                intent = _classify_owner_record(owner, convention=convention)
                targets_candidate = intent == TOW_ATTEMPT and _target_id(owner.raw) == ship_id
                if targets_candidate:
                    visible_tow_targeters.append(other_id)
                    if same_destination:
                        visible_matching_towers.append(other_id)
                    else:
                        visible_tow_other_destination.append(other_id)
                elif same_destination:
                    visible_non_tow_comovers.append(other_id)

            comover_count[len(co_movers)] += 1
            visible_match_count[len(visible_matching_towers)] += 1

            if co_movers:
                totals["has_same_origin_destination_comover"] += 1
            if hidden_or_unresolved_comovers:
                totals["has_hidden_or_unresolved_comover"] += 1
            if visible_non_tow_comovers:
                totals["has_visible_non_tow_comover"] += 1
            if visible_tow_targeters:
                totals["has_visible_tow_targeter"] += 1
            if visible_tow_other_destination:
                totals["visible_tow_targeter_other_destination"] += 1
            if len(visible_matching_towers) == 1:
                totals["single_visible_matching_tower"] += 1
            if len(visible_matching_towers) > 1:
                totals["route_equivalent_multiple_visible_towers"] += 1
                multi_by_game[game_id] += 1
                multi_by_hull[hull_id] += 1
            if visible_matching_towers:
                totals["any_visible_matching_tower"] += 1
            if after_warp == 0 and visible_matching_towers:
                totals["post_warp0_with_visible_matching_tower"] += 1
            if after_warp == 0 and len(visible_matching_towers) > 1:
                totals["post_warp0_with_multiple_visible_towers"] += 1
            if after_warp == 0 and co_movers:
                totals["post_warp0_with_comover"] += 1
            if after_warp == 0 and hidden_or_unresolved_comovers and not visible_matching_towers:
                totals["post_warp0_hidden_comover_without_visible_tow"] += 1
            if after_warp == 0 and visible_non_tow_comovers and not visible_matching_towers:
                totals["post_warp0_visible_non_tow_comover_without_visible_tow"] += 1
            if after_warp == 0 and not co_movers:
                totals["post_warp0_without_comover"] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "warp_before": warp,
                "warp_after": after_warp,
                "baseline": str(baseline_category),
                "origin": origin,
                "observed": observed,
                "after_target": after_target,
                "co_movers": co_movers,
                "visible_tow_targeters": visible_tow_targeters,
                "visible_matching_towers": visible_matching_towers,
                "visible_tow_other_destination": visible_tow_other_destination,
                "hidden_or_unresolved_comovers": hidden_or_unresolved_comovers,
                "visible_non_tow_comovers": visible_non_tow_comovers,
            }

            if len(visible_matching_towers) > 1 and len(examples["multiple_visible"]) < 40:
                examples["multiple_visible"].append(detail)
            elif len(visible_matching_towers) == 1 and len(examples["single_visible"]) < 20:
                examples["single_visible"].append(detail)
            elif after_warp == 0 and hidden_or_unresolved_comovers and len(examples["hidden_warp0"]) < 30:
                examples["hidden_warp0"].append(detail)
            elif after_warp == 0 and visible_non_tow_comovers and len(examples["non_tow_warp0"]) < 30:
                examples["non_tow_warp0"].append(detail)
            elif after_warp == 0 and not co_movers and len(examples["no_comover_warp0"]) < 30:
                examples["no_comover_warp0"].append(detail)

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "post_warp0",
        "has_same_origin_destination_comover",
        "has_hidden_or_unresolved_comover",
        "has_visible_non_tow_comover",
        "has_visible_tow_targeter",
        "visible_tow_targeter_other_destination",
        "any_visible_matching_tower",
        "single_visible_matching_tower",
        "route_equivalent_multiple_visible_towers",
        "post_warp0_with_visible_matching_tower",
        "post_warp0_with_multiple_visible_towers",
        "post_warp0_with_comover",
        "post_warp0_hidden_comover_without_visible_tow",
        "post_warp0_visible_non_tow_comover_without_visible_tow",
        "post_warp0_without_comover",
    ):
        print(f"{key}=", totals[key])

    print("\n===== BEFORE WARP BUCKET =====")
    for key, count in warp_counts.most_common():
        print(key, count)

    print("\n===== AFTER WARP BUCKET =====")
    for key, count in post_warp_counts.most_common():
        print(key, count)

    print("\n===== BASELINE CATEGORY =====")
    for key, count in baseline_counts.most_common():
        print(key, count)

    print("\n===== SAME-DESTINATION CO-MOVER COUNT =====")
    for key, count in sorted(comover_count.items()):
        print(key, count)

    print("\n===== VISIBLE MATCHING TOWER COUNT =====")
    for key, count in sorted(visible_match_count.items()):
        print(key, count)

    print("\n===== MULTIPLE VISIBLE MATCHES BY GAME =====")
    for game_id, count in multi_by_game.most_common():
        print(game_id, count)

    print("\n===== MULTIPLE VISIBLE MATCHES BY HULL =====")
    for hull_id, count in multi_by_hull.most_common():
        print(hull_id, count)

    print("\n===== TARGET-ORIGIN ROWS BY GAME =====")
    for game_id, count in by_game_count.most_common():
        print(game_id, count)

    print("\n===== TARGET-ORIGIN ROWS BY HULL =====")
    for hull_id, count in by_hull_count.most_common(40):
        print(hull_id, count)

    print("\n===== POST-WARP0 BY GAME =====")
    for game_id, count in post_warp0_by_game.most_common():
        print(game_id, count)

    for bucket, title in (
        ("multiple_visible", "ROUTE-EQUIVALENT MULTIPLE VISIBLE TOW EXAMPLES"),
        ("single_visible", "UNEXPECTED SINGLE VISIBLE MATCH EXAMPLES"),
        ("hidden_warp0", "POST-WARP0 HIDDEN/UNRESOLVED CO-MOVER EXAMPLES"),
        ("non_tow_warp0", "POST-WARP0 VISIBLE NON-TOW CO-MOVER EXAMPLES"),
        ("no_comover_warp0", "POST-WARP0 WITHOUT CO-MOVER EXAMPLES"),
    ):
        print(f"\n===== {title} =====")
        for detail in examples[bucket]:
            print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "A successful tow moves the target with the tower and leaves the target at warp 0. "
        "Multiple owner-visible matching towers are route-equivalent movement evidence even "
        "when tower identity is ambiguous, because every counted match shares the observed "
        "start and destination. Hidden/unresolved or visible non-tow co-movers remain leads, "
        "not proof of tow. Do not promote them without a stronger differential."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
