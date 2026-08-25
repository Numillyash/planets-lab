from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_damage_context import _race_map, _same_owner_identity_after
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_fuel_context import extract_static_specs
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
HORWASP_HULL_IDS = frozenset(range(201, 214))
PRIVATEER_RACE_ID = 5
SPECIAL_MISSION_ID = 9


def _ratio_bucket(distance: float, nominal: float) -> str:
    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (
        ("~0.5x", 0.5),
        ("~1.0x", 1.0),
        ("~1.5x", 1.5),
        ("~2.0x", 2.0),
        ("~3.0x", 3.0),
    ):
        if abs(ratio - target) <= 0.08:
            return label
    if ratio < 0.5:
        return "<0.5x"
    if ratio < 1.0:
        return "0.5-1.0x"
    if ratio < 1.5:
        return "1.0-1.5x"
    if ratio < 2.0:
        return "1.5-2.0x"
    if ratio < 3.0:
        return "2.0-3.0x"
    return ">3.0x"


def _target_relation(row: Mapping[str, Any]) -> str:
    origin = (int(row["x_before"]), int(row["y_before"]))
    observed = (int(row["x_after"]), int(row["y_after"]))
    target = (int(row["target_x"]), int(row["target_y"]))
    if observed == origin and target == origin:
        return "observed=origin,target=origin"
    if observed == origin:
        return "observed=origin"
    if target == origin:
        return "target=origin"
    if observed == target:
        return "observed=target"
    return "observed=other"


def _direction_bucket(row: Mapping[str, Any]) -> str:
    odx = int(row["x_after"]) - int(row["x_before"])
    ody = int(row["y_after"]) - int(row["y_before"])
    tdx = int(row["target_x"]) - int(row["x_before"])
    tdy = int(row["target_y"]) - int(row["y_before"])
    observed_norm = hypot(odx, ody)
    target_norm = hypot(tdx, tdy)
    if observed_norm <= 1e-9:
        return "observed_stationary"
    if target_norm <= 1e-9:
        return "target_is_origin"
    cosine = (odx * tdx + ody * tdy) / (observed_norm * target_norm)
    if cosine >= 0.98:
        return "same_line_forward"
    if cosine >= 0.75:
        return "mostly_forward"
    if cosine <= -0.98:
        return "same_line_reverse"
    if cosine <= -0.75:
        return "mostly_reverse"
    if -0.25 <= cosine <= 0.25:
        return "roughly_perpendicular"
    return "oblique"


def _is_target_short_forward(row: Mapping[str, Any]) -> bool:
    warp = int(row["warp"])
    return (
        7 <= warp <= 9
        and _ratio_bucket(
            float(row["observed_distance"] or 0.0),
            float(row["nominal_max_distance"] or 0.0),
        ) == "<0.5x"
        and _target_relation(row) == "observed=other"
        and _direction_bucket(row) == "same_line_forward"
    )


def _load_rows(database: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(database), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "after_archive_turn",
            "ship_id",
            "hull_id",
            "warp",
            "is_gravitonic_hull",
            "x_before",
            "y_before",
            "x_after",
            "y_after",
            "target_x",
            "target_y",
            "observed_distance",
            "nominal_max_distance",
        ]
        raw_rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM {RESIDUAL_VIEW}
            WHERE warp BETWEEN 1 AND 9
              AND (hull_id IS NULL OR hull_id NOT BETWEEN 201 AND 213)
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in raw_rows]


def _ship_location_index(ship_groups: Mapping[tuple[int, int], tuple[Any, ...]]) -> dict[tuple[int, int, int], list[tuple[int, int, Mapping[str, Any]]]]:
    result: dict[tuple[int, int, int], list[tuple[int, int, Mapping[str, Any]]]] = defaultdict(list)
    for (turn, ship_id), group in ship_groups.items():
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id <= 0 or owner is None:
            continue
        raw = owner.raw
        x = _intish(raw.get("x"))
        y = _intish(raw.get("y"))
        if x is None or y is None:
            continue
        result[(int(turn), x, y)].append((int(ship_id), int(owner_id), raw))
    for rows in result.values():
        rows.sort(key=lambda item: item[0])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure whether post-v6 generic movement residuals were exposed to a co-located "
            "Privateer Mission-9 ship that could plausibly execute Rob Ship before movement. "
            "This is a population/exposure audit only; it does not reconstruct robbery order, "
            "diplomacy immunity or the 1% failure chance."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

    if not args.database.is_file():
        raise SystemExit(f"missing compiled corpus database: {args.database}")
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    rows = _load_rows(args.database)
    target_rows = [row for row in rows if _is_target_short_forward(row)]

    print("===== ROB SHIP PRE-MOVEMENT EXPOSURE AUDIT =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("generic_non_horwasp_warp1_9_rows=", len(rows))
    print("target_short_forward_rows=", len(target_rows))
    print("privateer_race_id=", PRIVATEER_RACE_ID)
    print("special_mission_id=", SPECIAL_MISSION_ID)

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals: Counter[str] = Counter()
    target: Counter[str] = Counter()
    exposure_by_game: Counter[int] = Counter()
    exposure_by_hull: Counter[int] = Counter()
    target_exposure_by_game: Counter[int] = Counter()
    target_exposure_by_hull: Counter[int] = Counter()
    examples: list[dict[str, Any]] = []

    def bump(key: str, *, is_target: bool, amount: int = 1) -> None:
        totals[key] += amount
        if is_target:
            target[key] += amount

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
        ship_groups = group_perspective_records(records, "ship")
        races = _race_map(records)
        specs = extract_static_specs(archive_data)
        ships_at = _ship_location_index(ship_groups)

        print(f"prepared game={game_id} cache_hit={hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            is_target = _is_target_short_forward(row)
            bump("rows", is_target=is_target)

            if row["is_gravitonic_hull"] is True:
                bump("gravitonic_excluded", is_target=is_target)
                continue

            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            hull_id = int(row["hull_id"]) if row["hull_id"] is not None else None

            owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or owner is None:
                bump("victim_owner_missing", is_target=is_target)
                continue
            before_raw = owner.raw
            if not _same_owner_identity_after(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
                owner_id=owner_id,
                before_raw=before_raw,
            ):
                bump("identity_break_after", is_target=is_target)
                continue
            bump("same_identity_after", is_target=is_target)

            victim_race = races.get(owner_id)
            if victim_race == PRIVATEER_RACE_ID:
                bump("victim_privateer_race", is_target=is_target)

            x = _intish(before_raw.get("x"))
            y = _intish(before_raw.get("y"))
            fuel_before = _intish(before_raw.get("neutronium"))
            victim_mission = _intish(before_raw.get("mission"))
            victim_iscloaked = before_raw.get("iscloaked") is True
            if x is None or y is None:
                bump("victim_position_missing", is_target=is_target)
                continue

            victim_spec = specs.hulls.get(hull_id) if hull_id is not None else None
            victim_static_noncloak = victim_spec is not None and not victim_spec.can_cloak
            if victim_static_noncloak:
                bump("victim_static_noncloak_hull", is_target=is_target)
            else:
                bump("victim_cloak_capability_not_excluded", is_target=is_target)
            if victim_iscloaked:
                bump("victim_submitted_iscloaked", is_target=is_target)

            colocated = ships_at.get((before_turn, x, y), ())
            mission9_privateers: list[dict[str, Any]] = []
            capable_robbers: list[dict[str, Any]] = []

            for other_ship_id, other_owner_id, other_raw in colocated:
                if other_ship_id == ship_id or other_owner_id == owner_id:
                    continue
                if races.get(other_owner_id) != PRIVATEER_RACE_ID:
                    continue
                if _intish(other_raw.get("mission")) != SPECIAL_MISSION_ID:
                    continue

                robber_hull_id = _intish(other_raw.get("hullid"))
                robber_fuel = _intish(other_raw.get("neutronium"))
                robber_spec = specs.hulls.get(robber_hull_id) if robber_hull_id is not None else None
                robber_beams = robber_spec.beam_count if robber_spec is not None else None
                robber_tank = robber_spec.fuel_tank if robber_spec is not None else None
                free_tank = None
                if robber_tank is not None and robber_fuel is not None:
                    free_tank = max(0, robber_tank - robber_fuel)

                detail = {
                    "ship": other_ship_id,
                    "owner": other_owner_id,
                    "hull": robber_hull_id,
                    "fuel": robber_fuel,
                    "fuel_tank": robber_tank,
                    "free_tank": free_tank,
                    "beams": robber_beams,
                }
                mission9_privateers.append(detail)

                if robber_spec is None or robber_beams is None or robber_beams <= 0:
                    continue
                if robber_fuel is None or robber_fuel <= 0:
                    continue
                if free_tank is None or free_tank <= 0:
                    continue
                capable_robbers.append(detail)

            if mission9_privateers:
                bump("privateer_mission9_at_origin", is_target=is_target)
            else:
                bump("no_privateer_mission9_at_origin", is_target=is_target)

            if capable_robbers:
                bump("rob_exposure_candidate", is_target=is_target)
                if victim_static_noncloak and victim_race != PRIVATEER_RACE_ID:
                    bump("rob_exposure_static_noncloak_victim", is_target=is_target)
                if fuel_before is not None and fuel_before > 0:
                    bump("rob_exposure_positive_victim_fuel", is_target=is_target)

                exposure_by_game[game_id] += 1
                if hull_id is not None:
                    exposure_by_hull[hull_id] += 1
                if is_target:
                    target_exposure_by_game[game_id] += 1
                    if hull_id is not None:
                        target_exposure_by_hull[hull_id] += 1

                if len(examples) < args.examples:
                    examples.append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "ship": ship_id,
                            "hull": hull_id,
                            "target_family": is_target,
                            "victim_owner": owner_id,
                            "victim_race": victim_race,
                            "victim_mission": victim_mission,
                            "victim_fuel": fuel_before,
                            "victim_static_noncloak": victim_static_noncloak,
                            "victim_submitted_iscloaked": victim_iscloaked,
                            "mission9_privateers": mission9_privateers,
                            "capable_robbers": capable_robbers,
                        }
                    )
            else:
                bump("no_capable_robber_at_origin", is_target=is_target)

    print("\n===== GLOBAL POST-V6 ROB EXPOSURE =====")
    for key in (
        "rows",
        "gravitonic_excluded",
        "same_identity_after",
        "identity_break_after",
        "victim_privateer_race",
        "victim_static_noncloak_hull",
        "victim_cloak_capability_not_excluded",
        "victim_submitted_iscloaked",
        "privateer_mission9_at_origin",
        "no_privateer_mission9_at_origin",
        "rob_exposure_candidate",
        "rob_exposure_static_noncloak_victim",
        "rob_exposure_positive_victim_fuel",
        "no_capable_robber_at_origin",
    ):
        print(f"{key}=", totals[key])

    print("\n===== TARGET 116 ROB EXPOSURE =====")
    for key in (
        "rows",
        "gravitonic_excluded",
        "same_identity_after",
        "identity_break_after",
        "victim_privateer_race",
        "victim_static_noncloak_hull",
        "victim_cloak_capability_not_excluded",
        "victim_submitted_iscloaked",
        "privateer_mission9_at_origin",
        "no_privateer_mission9_at_origin",
        "rob_exposure_candidate",
        "rob_exposure_static_noncloak_victim",
        "rob_exposure_positive_victim_fuel",
        "no_capable_robber_at_origin",
    ):
        print(f"target_short_{key}=", target[key])

    print("\n===== ROB EXPOSURE BY GAME =====")
    for key, value in exposure_by_game.most_common():
        print(key, value)

    print("\n===== ROB EXPOSURE BY HULL =====")
    for key, value in exposure_by_hull.most_common():
        print(key, value)

    print("\n===== TARGET 116 ROB EXPOSURE BY GAME =====")
    for key, value in target_exposure_by_game.most_common():
        print(key, value)

    print("\n===== TARGET 116 ROB EXPOSURE BY HULL =====")
    for key, value in target_exposure_by_hull.most_common():
        print(key, value)

    print("\n===== EXPOSURE EXAMPLES =====")
    for example in examples:
        print(example)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This is an exposure/population audit, not a Rob Ship simulator. A capable exposure requires a co-located owner-record Privateer ship on special mission 9, beams, positive fuel and free fuel-tank capacity. It does not yet apply ascending robber/target ID ordering, diplomacy Safe Passage immunity, victim Host-phase cloak state, Protofield destruction or the documented 1% Rob failure chance. If target_short_rob_exposure_candidate is zero, Rob Ship cannot explain the dominant 116-row family and should be rejected without a second pass."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
