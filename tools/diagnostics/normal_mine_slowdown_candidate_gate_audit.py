from __future__ import annotations

from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_mine_context import (
    build_mine_evidence_context,
    nearest_damage_quantum,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"

# Runtime-derived target rows whose route is exposed to owner-different normal mines
# and whose planned-distance deficit is within 1.5 ly of 10*N.
CANDIDATES = (
    (360690, 155, 447, 23, 3),
    (511506, 23, 160, 17, 2),
)


def _load_row(game_id: int, turn: int, ship_id: int) -> dict[str, Any] | None:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "after_archive_turn",
            "ship_id",
            "hull_id",
            "warp",
            "x_before",
            "y_before",
            "x_after",
            "y_after",
            "target_x",
            "target_y",
            "observed_distance",
            "nominal_max_distance",
        ]
        rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM {RESIDUAL_VIEW}
            WHERE game_id = ? AND before_archive_turn = ? AND ship_id = ?
            """,
            [game_id, turn, ship_id],
        ).fetchall()
    finally:
        con.close()
    if len(rows) != 1:
        return None
    return dict(zip(names, rows[0]))


def _safe_ship_state(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return {
        "damage": _intish(raw.get("damage")),
        "supplies": _intish(raw.get("supplies")),
        "fuel": _intish(raw.get("neutronium")),
        "mass": _intish(raw.get("mass")),
        "friendlycode": raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None,
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    print("===== NORMAL-MINE SLOWDOWN CANDIDATE GATE AUDIT =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("candidate_count_expected=", len(CANDIDATES))
    print("documented_not_slowed_hull_tech_threshold= 7")

    found = 0
    tech_eligible = 0

    for game_id, turn, ship_id, expected_hull, implied_hits in CANDIDATES:
        print(f"\n===== game={game_id} turn={turn} ship={ship_id} =====")
        row = _load_row(game_id, turn, ship_id)
        if row is None:
            print("candidate_row= missing_or_ambiguous")
            continue
        found += 1

        archive_path = RAW_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")

        before_turn = int(row["before_archive_turn"])
        after_turn = int(row["after_archive_turn"])
        owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
        after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))

        hull_id = int(row["hull_id"]) if row["hull_id"] is not None else None
        hull = context.specs.hulls.get(hull_id) if hull_id is not None else None
        hull_tech = hull.tech_level if hull is not None else None
        hull_mass = hull.mass if hull is not None else None
        eligible = hull_tech is not None and hull_tech < 7
        if eligible:
            tech_eligible += 1

        planned_distance = min(
            hypot(int(row["target_x"]) - int(row["x_before"]), int(row["target_y"]) - int(row["y_before"])),
            float(row["nominal_max_distance"] or 0.0),
        )
        observed_distance = float(row["observed_distance"] or 0.0)
        deficit = planned_distance - observed_distance

        enemy_normal_fields = [
            field
            for field in context.fields(after_turn)
            if not field.is_web
            and field.owner_id is not None
            and field.owner_id > 0
            and owner_id is not None
            and field.owner_id != owner_id
        ]

        before_raw = owner.raw if owner is not None else None
        after_raw = after_owner.raw if after_owner is not None and after_owner_id == owner_id else None
        before_damage = _intish(before_raw.get("damage")) if before_raw is not None else None
        after_damage = _intish(after_raw.get("damage")) if after_raw is not None else None
        damage_delta = (
            after_damage - before_damage
            if before_damage is not None and after_damage is not None
            else None
        )
        quantum = nearest_damage_quantum(hull_mass, web=False)

        print("prepared_cache_hit=", cache_hit)
        print("expected_hull=", expected_hull)
        print("hull_id=", hull_id)
        print("hull_tech=", hull_tech)
        print("hull_mass=", hull_mass)
        print("slowdown_tech_eligible=", eligible)
        print("implied_slowdown_hits=", implied_hits)
        print("planned_distance=", round(planned_distance, 3))
        print("observed_distance=", round(observed_distance, 3))
        print("deficit=", round(deficit, 3))
        print("normal_mine_damage_quantum=", quantum)
        print("owner_id=", owner_id)
        print("enemy_normal_field_count=", len(enemy_normal_fields))
        print("enemy_normal_field_ids=", [field.field_id for field in enemy_normal_fields])
        print("enemy_normal_field_owners=", sorted({field.owner_id for field in enemy_normal_fields}))
        print("before_state=", _safe_ship_state(before_raw))
        print("after_state_observational=", _safe_ship_state(after_raw))
        print("observed_damage_delta=", damage_delta)
        if quantum is not None and damage_delta is not None and damage_delta > 0:
            print("damage_delta_multiple_of_quantum=", damage_delta % quantum == 0)
            print("observed_damage_hits_if_exact=", damage_delta // quantum if damage_delta % quantum == 0 else None)
        else:
            print("damage_delta_multiple_of_quantum=", False)
            print("observed_damage_hits_if_exact=", None)

    print("\n===== SUMMARY =====")
    print("candidate_rows_found=", found)
    print("tech_eligible_candidates=", tech_eligible)
    print("tech_ineligible_candidates=", found - tech_eligible)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Hull tech is the first hard gate: documented normal-mine slowdown does not apply at tech 7+. "
        "For tech<7 candidates, owner-different field presence is still only an upper bound: historical "
        "Safe Passage / minefield friendly-code immunity, exact route-field intersection, mine-hit RNG, "
        "and repair must be resolved before attributing a mine hit. after_state is observational because "
        "editable cargo/orders in historical next-turn snapshots need not equal the immediate post-Host state."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
