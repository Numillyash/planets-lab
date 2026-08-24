from __future__ import annotations

import json
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_context import (
    TOW_ATTEMPT,
    MovementMissionConvention,
    _classify_owner_record,
)
from planets_lab.corpus.movement_differential import _entity_map, _intish, _resolved_value
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import (
    _owner_record,
    _resolved_storm_offset,
    _storm_consensus_by_turn,
    _xy,
)
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_storm_context import _classic_constant_storm_offset
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
MANIFEST = Path("validation/corpus/manifests/accounts-recent-finished.jsonl")
HORWASP_HULL_IDS = frozenset(range(201, 214))


def _manifest_storm_modes() -> dict[int, bool]:
    result: dict[int, bool] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        game_id = row.get("game_id")
        settings = row.get("settings")
        if isinstance(game_id, int) and isinstance(settings, Mapping):
            mode = settings.get("nuionstorms")
            if isinstance(mode, bool):
                result[game_id] = mode
    return result


def _owner_id(entity: Any) -> int | None:
    if entity is None:
        return None
    try:
        return _intish(_resolved_value(entity, "ownerid"))
    except KeyError:
        try:
            return _intish(_resolved_value(entity, "owner"))
        except KeyError:
            return None


def _target_id(raw: Mapping[str, Any]) -> int | None:
    return _intish(raw.get("mission1target", raw.get("mission1_target_id")))


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
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                baseline_category
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp = 0
              AND target_x = x_before
              AND target_y = y_before
              AND (x_after <> x_before OR y_after <> y_before)
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== WARP-ZERO EXTERNAL MOVEMENT CONTEXT AUDIT =====")
    print("candidate_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    storm_modes = _manifest_storm_modes()
    totals = Counter()
    by_hull = Counter()
    by_game_count = Counter()
    displacement = Counter()
    co_mover_count = Counter()
    candidate_mission = Counter()
    tower_visibility = Counter()
    explicit_tow_hulls = Counter()
    explicit_tow_games = Counter()
    hidden_comover_hulls = Counter()
    hidden_comover_games = Counter()
    wrapped_storm_hulls = Counter()
    wrapped_storm_games = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    convention = MovementMissionConvention()

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        records = prepared.snapshots
        entities = _entity_map(records)
        ship_groups = group_perspective_records(records, "ship")
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(records)
        nuionstorms = storm_modes.get(game_id)

        print(
            f"prepared game={game_id} cache_hit={hit} rows={len(by_game[game_id])} "
            f"storm_mode={nuionstorms} raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )

        for row in by_game[game_id]:
            (
                _gid,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                x_before,
                y_before,
                x_after,
                y_after,
                _target_x,
                _target_y,
                baseline_category,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            origin = (int(x_before), int(y_before))
            observed = (int(x_after), int(y_after))
            observed_vector = _vector(origin, observed, topology)

            totals["rows"] += 1
            by_hull[hull_id] += 1
            by_game_count[game_id] += 1
            displacement[observed_vector] += 1

            candidate_group = ship_groups.get((before_turn, ship_id), ())
            candidate_owner_id, candidate_owner = _owner_record(candidate_group)
            if candidate_owner is None:
                candidate_mission["owner_record_missing"] += 1
            else:
                intent = _classify_owner_record(candidate_owner, convention=convention)
                candidate_mission[str(intent)] += 1

            co_movers: list[int] = []
            explicit_towers: list[int] = []
            hidden_or_unresolved_comovers: list[int] = []
            visible_non_tow_comovers: list[int] = []

            ship_ids = sorted(
                entity_id
                for kind, turn, entity_id in entities
                if kind == "ship" and turn == before_turn and entity_id != ship_id
            )
            for other_id in ship_ids:
                before_entity = entities.get(("ship", before_turn, other_id))
                after_entity = entities.get(("ship", after_turn, other_id))
                if _xy(before_entity) != origin or _xy(after_entity) != observed:
                    continue

                co_movers.append(other_id)
                group = ship_groups.get((before_turn, other_id), ())
                other_owner_id, other_owner = _owner_record(group)
                if other_owner is None:
                    hidden_or_unresolved_comovers.append(other_id)
                    tower_visibility["co_mover_owner_record_missing"] += 1
                    continue

                intent = _classify_owner_record(other_owner, convention=convention)
                if intent == TOW_ATTEMPT and _target_id(other_owner.raw) == ship_id:
                    explicit_towers.append(other_id)
                    tower_visibility["visible_explicit_tower_targets_candidate"] += 1
                else:
                    visible_non_tow_comovers.append(other_id)
                    tower_visibility["visible_comover_not_explicit_tower"] += 1

                candidate_entity = entities.get(("ship", before_turn, ship_id))
                if (
                    candidate_owner_id is not None
                    and other_owner_id is not None
                    and candidate_owner_id != other_owner_id
                ):
                    tower_visibility["co_mover_different_owner"] += 1

            co_mover_count[len(co_movers)] += 1
            if co_movers:
                totals["has_colocated_same_destination_comover"] += 1
            if len(co_movers) == 1:
                totals["single_colocated_same_destination_comover"] += 1
            if explicit_towers:
                totals["visible_explicit_tow_target_match"] += 1
                explicit_tow_hulls[hull_id] += 1
                explicit_tow_games[game_id] += 1
            if hidden_or_unresolved_comovers:
                totals["has_hidden_or_unresolved_comover"] += 1
                hidden_comover_hulls[hull_id] += 1
                hidden_comover_games[game_id] += 1
            if visible_non_tow_comovers:
                totals["has_visible_non_tow_comover"] += 1

            storm_status = "not_checked"
            storm_vector_match = False
            if after_turn in storm_conflicts:
                storm_status = "conflict"
            elif after_turn in storm_invalid:
                storm_status = "invalid"
            elif nuionstorms is None:
                storm_status = "mode_unknown"
            else:
                storms = storms_by_turn.get(after_turn, ())
                if nuionstorms:
                    offset, storm_status = _resolved_storm_offset(
                        storms,
                        x=origin[0],
                        y=origin[1],
                    )
                else:
                    offset, storm_status = _classic_constant_storm_offset(
                        storms,
                        x=origin[0],
                        y=origin[1],
                    )
                if offset is not None and offset != (0, 0):
                    storm_vector_match = tuple(offset) == tuple(observed_vector)
                    if storm_vector_match:
                        totals["effective_topology_storm_vector_match"] += 1
                        wrapped_storm_hulls[hull_id] += 1
                        wrapped_storm_games[game_id] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "baseline": str(baseline_category),
                "origin": origin,
                "observed": observed,
                "observed_vector": observed_vector,
                "distance": round(hypot(*observed_vector), 3),
                "co_movers": co_movers,
                "explicit_towers": explicit_towers,
                "hidden_or_unresolved_comovers": hidden_or_unresolved_comovers,
                "visible_non_tow_comovers": visible_non_tow_comovers,
                "storm_status": storm_status,
                "storm_vector_match": storm_vector_match,
            }

            if explicit_towers and len(examples["explicit_tow"]) < 30:
                examples["explicit_tow"].append(detail)
            elif hidden_or_unresolved_comovers and len(examples["hidden_comover"]) < 30:
                examples["hidden_comover"].append(detail)
            elif storm_vector_match and len(examples["storm"]) < 30:
                examples["storm"].append(detail)
            elif len(examples["unexplained"]) < 30:
                examples["unexplained"].append(detail)

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "has_colocated_same_destination_comover",
        "single_colocated_same_destination_comover",
        "visible_explicit_tow_target_match",
        "has_hidden_or_unresolved_comover",
        "has_visible_non_tow_comover",
        "effective_topology_storm_vector_match",
    ):
        print(f"{key}=", totals[key])

    print("\n===== CO-MOVER COUNT =====")
    for key, count in sorted(co_mover_count.items()):
        print(key, count)

    print("\n===== HULL COUNTS =====")
    for hull_id, count in by_hull.most_common(40):
        print(hull_id, count)

    print("\n===== GAME COUNTS =====")
    for game_id, count in by_game_count.most_common():
        print(game_id, count)

    print("\n===== CANDIDATE OWNER INTENT =====")
    for key, count in candidate_mission.most_common():
        print(key, count)

    print("\n===== TOWER / CO-MOVER VISIBILITY =====")
    for key, count in tower_visibility.most_common():
        print(key, count)

    print("\n===== VISIBLE EXPLICIT TOW MATCH BY HULL =====")
    for hull_id, count in explicit_tow_hulls.most_common():
        print(hull_id, count)
    print("visible_explicit_tow_games=", sorted(explicit_tow_games))

    print("\n===== HIDDEN/UNRESOLVED CO-MOVER BY HULL =====")
    for hull_id, count in hidden_comover_hulls.most_common():
        print(hull_id, count)
    print("hidden_or_unresolved_comover_games=", sorted(hidden_comover_games))

    print("\n===== EFFECTIVE-TOPOLOGY STORM VECTOR MATCH BY HULL =====")
    for hull_id, count in wrapped_storm_hulls.most_common():
        print(hull_id, count)
    print("storm_vector_match_games=", sorted(wrapped_storm_games))

    print("\n===== TOP OBSERVED VECTORS =====")
    for vector, count in displacement.most_common(30):
        print(vector, count, "distance=", round(hypot(*vector), 3))

    for bucket, title in (
        ("explicit_tow", "VISIBLE EXPLICIT TOW EXAMPLES"),
        ("hidden_comover", "HIDDEN/UNRESOLVED CO-MOVER EXAMPLES"),
        ("storm", "EFFECTIVE-TOPOLOGY STORM VECTOR EXAMPLES"),
        ("unexplained", "OTHER UNEXPLAINED EXAMPLES"),
    ):
        print(f"\n===== {title} =====")
        for detail in examples[bucket]:
            print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "A colocated ship with the same destination is evidence of shared external motion, "
        "not proof of tow by itself. Visible explicit tow targeting is stronger; a hidden or "
        "unresolved co-mover is a lead for private/enemy tow context. Effective-topology storm "
        "vector matching tests whether a residual is only a coordinate-wrap miss in the current "
        "storm layer. Promote no rule from vector coincidence alone."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
