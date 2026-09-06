from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_damage_context import _race_map, max_warp_from_damage
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
DEFAULT_RAW_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")

# Five route-matched Four Fingers cases that remain after removing cases where
# both tower and target independently reach the observed endpoint.
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


def _label_row(
    connection: duckdb.DuckDBPyConnection,
    *,
    game_id: int,
    turn: int,
    ship_id: int,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        SELECT *
        FROM movement_context_labels
        WHERE game_id = ?
          AND before_archive_turn = ?
          AND ship_id = ?
        ORDER BY after_archive_turn
        LIMIT 1
        """,
        [game_id, turn, ship_id],
    )
    return _dict_row(cursor, cursor.fetchone())


def _owner_raw(
    ship_groups: Mapping[tuple[int, int], tuple[Any, ...]],
    *,
    turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _effective_damage_projection(
    row: Mapping[str, Any] | None,
    *,
    raw: Mapping[str, Any] | None,
    race_id: int | None,
) -> dict[str, Any]:
    if row is None or raw is None:
        return {
            "damage": None,
            "supplies": None,
            "race_id": race_id,
            "damage_max_warp": None,
            "damage_projected_endpoint": None,
            "damage_projection_exact": None,
        }

    damage = _intish(raw.get("damage"))
    supplies = _intish(raw.get("supplies"))
    effective_warp = max_warp_from_damage(damage, race_id)
    projected: tuple[int, int] | None = None

    required = (
        "before_embedded_turn",
        "ship_id",
        "x_before",
        "y_before",
        "target_x",
        "target_y",
        "x_after",
        "y_after",
    )
    if effective_warp is not None and all(row.get(key) is not None for key in required):
        sample = MovementSample(
            turn=int(row["before_embedded_turn"]),
            ship_id=int(row["ship_id"]),
            x=int(row["x_before"]),
            y=int(row["y_before"]),
            target_x=int(row["target_x"]),
            target_y=int(row["target_y"]),
            warp=int(effective_warp),
            next_x=int(row["x_after"]),
            next_y=int(row["y_after"]),
            gravitonic=row.get("is_gravitonic_hull") is True,
            game_id=int(row["game_id"]),
            hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
        )
        projected = host_major_minor_destination(sample)

    observed = None
    if row.get("x_after") is not None and row.get("y_after") is not None:
        observed = (int(row["x_after"]), int(row["y_after"]))

    return {
        "damage": damage,
        "supplies": supplies,
        "race_id": race_id,
        "damage_max_warp": effective_warp,
        "damage_projected_endpoint": projected,
        "damage_projection_exact": projected == observed if projected is not None and observed is not None else None,
    }


def _compact_movement(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = (
        "intent_class",
        "hull_id",
        "x_before",
        "y_before",
        "x_after",
        "y_after",
        "target_x",
        "target_y",
        "warp",
        "observed_distance",
        "target_distance",
        "nominal_max_distance",
        "warp_wells_enabled",
        "eligible_warp_well_planets",
        "is_gravitonic_hull",
        "baseline_category",
        "baseline_explained",
        "observed_tow_target_match",
        "storm_context_status",
        "external_context_category",
        "external_context_explained",
        "post_external_residual",
    )
    return {key: row.get(key) for key in keys}


def _compact_labels(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = (
        "label_issue",
        "chunnel_category",
        "chunnel_explained",
        "horwasp_category",
        "horwasp_strong_explained",
        "mine_category",
        "mine_damage_hits",
        "mine_slowdown_hits",
        "mine_strong_explained",
        "fuel_proration_category",
        "fuel_proration_explained",
        "post_fuel_proration_residual",
    )
    return {key: row.get(key) for key in keys}


def run(*, database: Path, raw_dir: Path, prepared_dir: Path) -> int:
    connection = duckdb.connect(str(database), read_only=True)
    prepared_by_game: dict[int, tuple[Any, Mapping[tuple[int, int], tuple[Any, ...]], dict[int, int]]] = {}
    try:
        print("===== REMAINING FOUR-FINGERS CONTEXT AUDIT =====")
        for game_id, turn, tower_id, target_id in CASES:
            if game_id not in prepared_by_game:
                archive = (raw_dir / f"game-{game_id}.zip").read_bytes()
                prepared, cache_hit = load_or_build_prepared_game_cache(
                    archive,
                    game_id=game_id,
                    cache_path=prepared_dir / f"game-{game_id}.pickle",
                )
                ship_groups = group_perspective_records(prepared.snapshots, "ship")
                races = _race_map(prepared.snapshots)
                prepared_by_game[game_id] = (prepared, ship_groups, races)
                print({"game": game_id, "prepared_cache_hit": cache_hit})

            _prepared, ship_groups, races = prepared_by_game[game_id]
            print()
            print(f"===== GAME {game_id} TURN {turn} TOWER {tower_id} TARGET {target_id} =====")

            for role, ship_id in (("tower", tower_id), ("target", target_id)):
                movement = _movement_row(
                    connection,
                    game_id=game_id,
                    turn=turn,
                    ship_id=ship_id,
                )
                labels = None
                if movement is not None and movement.get("post_external_residual") is True:
                    labels = _label_row(
                        connection,
                        game_id=game_id,
                        turn=turn,
                        ship_id=ship_id,
                    )
                owner_id, raw = _owner_raw(
                    ship_groups,
                    turn=turn,
                    ship_id=ship_id,
                )
                damage = _effective_damage_projection(
                    movement,
                    raw=raw,
                    race_id=races.get(owner_id) if owner_id is not None else None,
                )
                factual = {
                    "owner_id": owner_id,
                    "mission": _intish(raw.get("mission")) if raw is not None else None,
                    "mission1target": _intish(raw.get("mission1target")) if raw is not None else None,
                    "fuel": _intish(raw.get("neutronium")) if raw is not None else None,
                    "damage": damage["damage"],
                    "supplies": damage["supplies"],
                    "race_id": damage["race_id"],
                    "damage_max_warp": damage["damage_max_warp"],
                    "damage_projected_endpoint": damage["damage_projected_endpoint"],
                    "damage_projection_exact": damage["damage_projection_exact"],
                }
                print({
                    "role": role,
                    "ship_id": ship_id,
                    "movement": _compact_movement(movement),
                    "labels": _compact_labels(labels),
                    "factual_context": factual,
                })
    finally:
        connection.close()

    print()
    print("===== INTERPRETATION =====")
    print("baseline/external categories are prior movement-layer explanations; they are stronger than a fresh Tow guess.")
    print("damage_projection_exact is diagnostic only unless the strict damage guards are also satisfied; supplies >=5 can permit repair and must stay fail-closed.")
    print("observed_tow_target_match is route evidence and must not be used as an independent explanation of a Four Fingers contradiction.")
    print("L2 labels are shown only for post-external residual rows and can identify Chunnel/Horwasp/mine/fuel explanations already verified by the corpus pipeline.")
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
