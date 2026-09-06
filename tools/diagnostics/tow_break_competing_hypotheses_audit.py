from __future__ import annotations

import argparse
import sys
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_chunnel_context import _effective_sample
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
)
from planets_lab.corpus.movement_fuel_context import (
    classify_strict_fuel_proration_transition,
    extract_static_specs,
)
from planets_lab.corpus.movement_mine_context import (
    build_mine_evidence_context,
    classify_strong_mine_hit_transition,
)
from planets_lab.corpus.movement_residual_context import (
    _owner_record,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
DEFAULT_RAW_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")

# The five route-matched cases that remained after independent nominal-route
# disambiguation. This audit deliberately tests competing *independent movement*
# explanations even though the compiled L1 pipeline previously consumed the
# target as observed_tow_target_match.
CASES: tuple[tuple[int, int, int, int], ...] = (
    (360690, 112, 54, 473),
    (511506, 92, 436, 358),
    (591478, 15, 161, 203),
    (591478, 87, 288, 503),
    (620694, 34, 20, 102),
)


def _dict_row(cursor: duckdb.DuckDBPyConnection, row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    columns = [item[0] for item in cursor.description]
    return dict(zip(columns, row))


def _movement_row(
    connection: duckdb.DuckDBPyConnection,
    *,
    game_id: int,
    turn: int,
    ship_id: int,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        SELECT *
        FROM movement_transitions
        WHERE game_id = ?
          AND before_archive_turn = ?
          AND ship_id = ?
        ORDER BY after_archive_turn
        LIMIT 1
        """,
        [game_id, turn, ship_id],
    )
    return _dict_row(cursor, cursor.fetchone())


def _sample(row: Mapping[str, Any] | None) -> MovementSample | None:
    if row is None:
        return None
    required = (
        "before_embedded_turn",
        "ship_id",
        "x_before",
        "y_before",
        "target_x",
        "target_y",
        "warp",
        "x_after",
        "y_after",
    )
    if any(row.get(key) is None for key in required):
        return None
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
        gravitonic=row.get("is_gravitonic_hull") is True,
        game_id=int(row["game_id"]) if row.get("game_id") is not None else None,
        hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
    )


def _owner_raw(
    ship_groups: Mapping[tuple[int, int], tuple[Any, ...]],
    *,
    turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _after_owner_raw(
    ship_groups: Mapping[tuple[int, int], tuple[Any, ...]],
    *,
    turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _long_waypoint_variants(sample: MovementSample | None) -> dict[str, Any]:
    if sample is None:
        return {
            "target_distance": None,
            "documented_long_threshold": None,
            "documented_long": None,
            "effective_speed_threshold_alt": None,
            "effective_speed_long_alt": None,
        }
    distance = hypot(sample.target_x - sample.x, sample.target_y - sample.y)
    documented = float(sample.warp * sample.warp)
    effective = documented * (2.0 if sample.gravitonic else 1.0)
    return {
        "target_distance": distance,
        "documented_long_threshold": documented,
        "documented_long": distance > documented + 1e-9,
        "effective_speed_threshold_alt": effective,
        "effective_speed_long_alt": distance > effective + 1e-9,
    }


def _speed(sample: MovementSample | None) -> float | None:
    if sample is None:
        return None
    return float(sample.warp * sample.warp) * (2.0 if sample.gravitonic else 1.0)


def _direct_context(
    *,
    game_id: int,
    row: Mapping[str, Any] | None,
    sample: MovementSample | None,
    owner_id: int | None,
    raw: Mapping[str, Any] | None,
    ship_groups: Mapping[tuple[int, int], tuple[Any, ...]],
    races: Mapping[int, int],
    planets_by_turn: Mapping[int, tuple[tuple[int, int, int], ...]],
    storms_by_turn: Mapping[int, tuple[Any, ...]],
    storm_conflicts: frozenset[int],
    storm_invalid: frozenset[int],
    mine_context: Any,
    specs: Any,
) -> dict[str, Any]:
    if row is None or sample is None or raw is None or owner_id is None or owner_id <= 0:
        return {
            "storm_category": None,
            "storm_status": "inputs_unavailable",
            "mine_category": None,
            "mine_damage_hits": None,
            "mine_slowdown_hits": None,
            "strict_fuel_category": None,
        }

    before_turn = int(row["before_archive_turn"])
    after_turn = int(row["after_archive_turn"])
    effective = _effective_sample(sample)

    if after_turn in storm_conflicts:
        storm_category = None
        storm_status = "storm_consensus_conflict"
    elif after_turn in storm_invalid:
        storm_category = None
        storm_status = "storm_context_invalid"
    else:
        storm_category, storm_status = _storm_expected_category(
            effective,
            storms=storms_by_turn.get(after_turn, ()),
            planets=planets_by_turn.get(before_turn, ()),
        )

    mine = classify_strong_mine_hit_transition(
        context=mine_context,
        before_turn=before_turn,
        after_turn=after_turn,
        ship_id=sample.ship_id,
        owner_id=owner_id,
        before_raw=raw,
        sample=sample,
    )

    fuel = classify_strict_fuel_proration_transition(
        effective,
        before_raw=raw,
        race_id=races.get(owner_id),
        specs=specs,
    )

    return {
        "storm_category": storm_category,
        "storm_status": storm_status,
        "mine_category": mine.category if mine is not None else None,
        "mine_damage_hits": mine.damage_hits if mine is not None else None,
        "mine_slowdown_hits": mine.slowdown_hits if mine is not None else None,
        "strict_fuel_category": fuel.category if fuel is not None else None,
    }


def run(*, database: Path, raw_dir: Path, prepared_dir: Path) -> int:
    connection = duckdb.connect(str(database), read_only=True)
    by_game: dict[int, dict[str, Any]] = {}
    try:
        print("===== TOW BREAK COMPETING HYPOTHESES AUDIT =====")
        for game_id, turn, tower_id, target_id in CASES:
            if game_id not in by_game:
                archive = (raw_dir / f"game-{game_id}.zip").read_bytes()
                prepared, cache_hit = load_or_build_prepared_game_cache(
                    archive,
                    game_id=game_id,
                    cache_path=prepared_dir / f"game-{game_id}.pickle",
                )
                entities = _entity_map(prepared.snapshots)
                ship_groups = group_perspective_records(prepared.snapshots, "ship")
                from planets_lab.corpus.movement_damage_context import _race_map

                races = _race_map(prepared.snapshots)
                planets_by_turn = _planet_tuples_by_turn(entities)
                storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(
                    prepared.snapshots
                )
                specs = extract_static_specs(archive)
                mine_context = build_mine_evidence_context(
                    game_id=game_id,
                    archive_data=archive,
                    snapshots=prepared.snapshots,
                )
                by_game[game_id] = {
                    "ship_groups": ship_groups,
                    "races": races,
                    "planets_by_turn": planets_by_turn,
                    "storms_by_turn": storms_by_turn,
                    "storm_conflicts": storm_conflicts,
                    "storm_invalid": storm_invalid,
                    "specs": specs,
                    "mine_context": mine_context,
                }
                print({"game": game_id, "prepared_cache_hit": cache_hit})

            context = by_game[game_id]
            tower_row = _movement_row(connection, game_id=game_id, turn=turn, ship_id=tower_id)
            target_row = _movement_row(connection, game_id=game_id, turn=turn, ship_id=target_id)
            tower_sample = _sample(tower_row)
            target_sample = _sample(target_row)
            tower_owner, tower_raw = _owner_raw(
                context["ship_groups"], turn=turn, ship_id=tower_id
            )
            target_owner, target_raw = _owner_raw(
                context["ship_groups"], turn=turn, ship_id=target_id
            )
            after_turn = int(target_row["after_archive_turn"]) if target_row is not None else turn + 1
            after_target_owner, after_target_raw = _after_owner_raw(
                context["ship_groups"], turn=after_turn, ship_id=target_id
            )

            tower_direct = _direct_context(
                game_id=game_id,
                row=tower_row,
                sample=tower_sample,
                owner_id=tower_owner,
                raw=tower_raw,
                ship_groups=context["ship_groups"],
                races=context["races"],
                planets_by_turn=context["planets_by_turn"],
                storms_by_turn=context["storms_by_turn"],
                storm_conflicts=context["storm_conflicts"],
                storm_invalid=context["storm_invalid"],
                mine_context=context["mine_context"],
                specs=context["specs"],
            )
            target_direct = _direct_context(
                game_id=game_id,
                row=target_row,
                sample=target_sample,
                owner_id=target_owner,
                raw=target_raw,
                ship_groups=context["ship_groups"],
                races=context["races"],
                planets_by_turn=context["planets_by_turn"],
                storms_by_turn=context["storms_by_turn"],
                storm_conflicts=context["storm_conflicts"],
                storm_invalid=context["storm_invalid"],
                mine_context=context["mine_context"],
                specs=context["specs"],
            )

            target_hull = (
                context["specs"].hulls.get(target_sample.hull_id)
                if target_sample is not None and target_sample.hull_id is not None
                else None
            )
            tower_hull = (
                context["specs"].hulls.get(tower_sample.hull_id)
                if tower_sample is not None and tower_sample.hull_id is not None
                else None
            )
            long_variants = _long_waypoint_variants(target_sample)
            target_fuel = _intish(target_raw.get("neutronium")) if target_raw is not None else None
            target_speed = _speed(target_sample)
            tower_speed = _speed(tower_sample)
            documented_four_fingers = (
                target_fuel is not None
                and target_fuel > 25
                and target_hull is not None
                and target_hull.engine_count >= 2
                and long_variants["documented_long"] is True
                and target_speed is not None
                and tower_speed is not None
                and target_speed >= tower_speed
            )
            alt_effective_long_four_fingers = (
                target_fuel is not None
                and target_fuel > 25
                and target_hull is not None
                and target_hull.engine_count >= 2
                and long_variants["effective_speed_long_alt"] is True
                and target_speed is not None
                and tower_speed is not None
                and target_speed >= tower_speed
            )

            print()
            print(f"===== GAME {game_id} TURN {turn} TOWER {tower_id} TARGET {target_id} =====")
            print({
                "same_owner": tower_owner is not None and tower_owner == target_owner,
                "tower": {
                    "owner_id": tower_owner,
                    "hull_id": tower_sample.hull_id if tower_sample is not None else None,
                    "hull_name": tower_hull.name if tower_hull is not None else None,
                    "engine_count": tower_hull.engine_count if tower_hull is not None else None,
                    "warp": tower_sample.warp if tower_sample is not None else None,
                    "gravitonic": tower_sample.gravitonic if tower_sample is not None else None,
                    "speed_ly": tower_speed,
                    "direct_context": tower_direct,
                },
                "target": {
                    "owner_id": target_owner,
                    "hull_id": target_sample.hull_id if target_sample is not None else None,
                    "hull_name": target_hull.name if target_hull is not None else None,
                    "engine_count": target_hull.engine_count if target_hull is not None else None,
                    "warp": target_sample.warp if target_sample is not None else None,
                    "gravitonic": target_sample.gravitonic if target_sample is not None else None,
                    "speed_ly": target_speed,
                    "fuel_at_before_snapshot": target_fuel,
                    **long_variants,
                    "documented_four_fingers": documented_four_fingers,
                    "effective_speed_long_alt_four_fingers": alt_effective_long_four_fingers,
                    "direct_context": target_direct,
                    "after_owner_same": after_target_owner == target_owner,
                    "after_warp_supporting_only": (
                        _intish(after_target_raw.get("warp"))
                        if after_target_raw is not None
                        else None
                    ),
                    "after_damage": (
                        _intish(after_target_raw.get("damage"))
                        if after_target_raw is not None
                        else None
                    ),
                },
            })
    finally:
        connection.close()

    print()
    print("===== INTERPRETATION =====")
    print("documented_four_fingers uses the current documented long-waypoint test: distance > warp^2; Gravitonic modifies only the speed comparison.")
    print("effective_speed_long_alt_four_fingers is a diagnostic counterfactual only: it asks whether using effective max movement for the long-waypoint threshold would remove a contradiction. It is not promoted as a rule without corpus support.")
    print("direct_context deliberately re-runs storm, strict mine-hit and strict fuel-proration evidence even when L1 previously consumed the row as observed_tow_target_match.")
    print("A direct mine/storm/fuel match can explain route-equivalence without proving Tow succeeded. Absence of a strict match does not prove Tow succeeded because those evidence layers are intentionally fail-closed.")
    print("Historical after-warp is supporting only; Time Machine next-snapshot navigation fields remain editable and are not treated as a Host phase boundary.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=DEFAULT_PREPARED_DIR)
    args = parser.parse_args()
    raise SystemExit(
        run(
            database=args.database,
            raw_dir=args.raw_dir,
            prepared_dir=args.prepared_dir,
        )
    )


if __name__ == "__main__":
    main()
