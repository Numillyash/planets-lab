from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from mine_hit_residual_audit import (
    DEFAULT_DATABASE,
    PREPARED_DIR,
    RAW_DIR,
    _cross_track_and_progress,
    _enemyish,
    _field_parseable,
    _minefields_for_snapshots,
    _point_in_field,
    _segment_intersects_field,
    _static_specs,
)
from mine_hit_hostorder_differential_audit import _owner_states, _post_reset


def _damage_quantums(hull_mass: int | None, *, web: bool) -> dict[str, int] | None:
    if hull_mass is None or hull_mass < 0:
        return None
    numerator = 1_000 if web else 10_000
    denominator = hull_mass + 1
    # Nu documentation says damage is rounded up. Historical NuHost examples
    # motivating this audit frequently look like positive Math.round semantics
    # instead, so keep all candidates explicit and compare them on the corpus.
    return {
        "ceil": (numerator + denominator - 1) // denominator,
        "floor": numerator // denominator,
        "nearest": (2 * numerator + denominator) // (2 * denominator),
    }


def _positive_multiple(value: int | None, quantum: int | None) -> tuple[bool, int | None]:
    if value is None or quantum is None or value <= 0 or quantum <= 0:
        return False, None
    if value % quantum != 0:
        return False, None
    return True, value // quantum


def _short_same_line(
    *,
    target_vector: tuple[int, int],
    observed_vector: tuple[int, int],
    regular_distance: float,
) -> bool:
    observed_distance = hypot(*observed_vector)
    cross_track, progress = _cross_track_and_progress(target_vector, observed_vector)
    return (
        cross_track is not None
        and progress is not None
        and cross_track <= 1.5
        and progress > 0.0
        and observed_distance > 0.0
        and observed_distance + 1.5 < regular_distance
    )


def _regular_vector(
    target_vector: tuple[int, int],
    *,
    target_distance: float,
    regular_distance: float,
) -> tuple[float, float]:
    if target_distance <= 0.0 or regular_distance <= 0.0:
        return 0.0, 0.0
    scale = regular_distance / target_distance
    return target_vector[0] * scale, target_vector[1] * scale


def _nearest_positive_tenth_hits(lost_distance: float) -> int:
    if lost_distance <= 0.0:
        return 0
    # Positive round-half-up rather than Python banker's round.
    return int(lost_distance / 10.0 + 0.5)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare ceil/floor/nearest mine-damage rounding against the current "
            "post-v4 short-forward residual, while preserving Host-order field and "
            "repair controls. Private prepared data stays local."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=30)
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
                baseline_category,
                warp,
                is_gravitonic_hull,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                nominal_max_distance
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp BETWEEN 1 AND 9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== MINE DAMAGE ROUNDING DIFFERENTIAL =====")
    print("generic_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    web_mode_hulls: dict[str, Counter[int]] = defaultdict(Counter)
    web_mode_games: dict[str, Counter[int]] = defaultdict(Counter)
    normal_mode_hulls: dict[str, Counter[int]] = defaultdict(Counter)
    normal_mode_games: dict[str, Counter[int]] = defaultdict(Counter)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, prepared_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        specs = _static_specs(archive_data)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        print(
            f"prepared game={game_id} cache_hit={prepared_hit} rows={len(by_game[game_id])} "
            f"raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )

        field_cache: dict[tuple[int, int | None], list[dict[str, Any]]] = {}

        def fields(turn: int, player_id: int | None) -> list[dict[str, Any]]:
            key = (turn, player_id)
            if key not in field_cache:
                parsed, _ = _minefields_for_snapshots(
                    prepared.snapshots,
                    archive_turn=turn,
                    player_id=player_id,
                )
                field_cache[key] = parsed
            return field_cache[key]

        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                baseline_category,
                warp,
                is_gravitonic,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                nominal_max_distance,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            gravitonic = is_gravitonic is True

            origin = (int(x_before), int(y_before))
            observed = (int(x_after), int(y_after))
            target = (int(target_x), int(target_y))
            observed_vector = _vector(origin, observed, topology)
            target_vector = _vector(origin, target, topology)
            observed_distance = hypot(*observed_vector)
            target_distance = hypot(*target_vector)
            raw_nominal = float(nominal_max_distance or 0.0)
            effective_nominal = raw_nominal * (2.0 if gravitonic else 1.0)
            regular_distance = min(target_distance, effective_nominal)
            if not _short_same_line(
                target_vector=target_vector,
                observed_vector=observed_vector,
                regular_distance=regular_distance,
            ):
                continue
            totals["effective_short_same_line"] += 1

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None or after_raw is None or not same_identity:
                totals["state_or_identity_unusable"] += 1
                continue
            totals["same_identity_after"] += 1

            hull_spec = specs.hulls.get(hull_id)
            hull_mass = hull_spec.mass if hull_spec is not None else None
            hull_tech = hull_spec.tech_level if hull_spec is not None else None
            web_q = _damage_quantums(hull_mass, web=True)
            normal_q = _damage_quantums(hull_mass, web=False)
            if web_q is None or normal_q is None:
                totals["missing_hull_mass"] += 1
                continue

            before_damage_raw = before_raw.get("damage")
            after_damage_raw = after_raw.get("damage")
            before_damage = (
                int(before_damage_raw)
                if isinstance(before_damage_raw, int) and not isinstance(before_damage_raw, bool)
                else None
            )
            after_damage = (
                int(after_damage_raw)
                if isinstance(after_damage_raw, int) and not isinstance(after_damage_raw, bool)
                else None
            )
            damage_delta = (
                after_damage - before_damage
                if before_damage is not None and after_damage is not None
                else None
            )
            damage_increase = damage_delta is not None and damage_delta > 0

            before_supplies_raw = before_raw.get("supplies")
            after_supplies_raw = after_raw.get("supplies")
            before_supplies = (
                int(before_supplies_raw)
                if isinstance(before_supplies_raw, int) and not isinstance(before_supplies_raw, bool)
                else None
            )
            after_supplies = (
                int(after_supplies_raw)
                if isinstance(after_supplies_raw, int) and not isinstance(after_supplies_raw, bool)
                else None
            )
            no_repair_supply = before_supplies is not None and before_supplies < 5
            max_repair_points = (
                before_supplies // 5
                if before_supplies is not None and before_supplies >= 0
                else None
            )

            after_enemy = [
                field
                for field in fields(after_turn, None)
                if _field_parseable(field) and _enemyish(field, owner_id)
            ]
            after_web = [
                field
                for field in after_enemy
                if field.get("is_web") is True and _point_in_field(observed, field, topology)
            ]

            reset = _post_reset(after_raw, observed)
            web_state = damage_increase and reset
            web_strong = web_state and bool(after_web)
            if web_state:
                totals["web_state_signature"] += 1
            if web_strong:
                totals["web_after_field_strong"] += 1

            web_delta_matches: dict[str, bool] = {}
            for mode, quantum in web_q.items():
                delta_match, _ = _positive_multiple(damage_delta, quantum)
                zero_match, _ = _positive_multiple(
                    after_damage if before_damage == 0 else None,
                    quantum,
                )
                web_delta_matches[mode] = delta_match
                if web_strong and delta_match:
                    totals[f"web_{mode}_delta_match_after_field"] += 1
                    web_mode_hulls[mode][hull_id] += 1
                    web_mode_games[mode][game_id] += 1
                if web_strong and zero_match:
                    totals[f"web_{mode}_from_zero_after_field"] += 1
                if web_strong and no_repair_supply and zero_match:
                    totals[f"web_{mode}_from_zero_no_repair_supply"] += 1

            if web_strong and web_delta_matches["nearest"] and not web_delta_matches["ceil"]:
                totals["web_nearest_not_ceil_delta"] += 1
                if len(examples["web_nearest_not_ceil"]) < args.examples:
                    examples["web_nearest_not_ceil"].append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "ship": ship_id,
                            "hull": hull_id,
                            "mass": hull_mass,
                            "damage_before": before_damage,
                            "damage_after": after_damage,
                            "damage_delta": damage_delta,
                            "quantums": web_q,
                            "supplies_before": before_supplies,
                            "supplies_after": after_supplies,
                            "lost_distance": round(regular_distance - observed_distance, 3),
                        }
                    )
            if web_state and not after_web and web_delta_matches["nearest"]:
                totals["web_nearest_control_no_after_field"] += 1

            lost_distance = regular_distance - observed_distance
            inferred_slow_hits = _nearest_positive_tenth_hits(lost_distance)
            ten_ly_match = (
                hull_tech is not None
                and hull_tech < 7
                and inferred_slow_hits >= 1
                and abs(lost_distance - inferred_slow_hits * 10.0) <= 1.5
            )
            if ten_ly_match:
                totals["normal_mine_10ly_geometry"] += 1

            regular_vector = _regular_vector(
                target_vector,
                target_distance=target_distance,
                regular_distance=regular_distance,
            )
            after_normal = [
                field
                for field in after_enemy
                if field.get("is_web") is False
                and _segment_intersects_field(
                    origin=origin,
                    target_vector=regular_vector,
                    field=field,
                    topology=topology,
                )
            ]
            normal_strong = damage_increase and ten_ly_match and bool(after_normal)
            if normal_strong:
                totals["normal_after_field_strong"] += 1

            normal_exact: dict[str, bool] = {}
            normal_multiple: dict[str, bool] = {}
            normal_damage_hits: dict[str, int | None] = {}
            for mode, quantum in normal_q.items():
                expected = inferred_slow_hits * quantum if ten_ly_match else None
                delta_exact = damage_delta is not None and expected is not None and damage_delta == expected
                zero_exact = (
                    before_damage == 0
                    and after_damage is not None
                    and expected is not None
                    and after_damage == expected
                )
                delta_multiple, delta_hits = _positive_multiple(damage_delta, quantum)
                zero_multiple, zero_hits = _positive_multiple(
                    after_damage if before_damage == 0 else None,
                    quantum,
                )
                normal_exact[mode] = zero_exact
                normal_multiple[mode] = delta_multiple
                normal_damage_hits[mode] = delta_hits

                if normal_strong and delta_multiple:
                    totals[f"normal_{mode}_delta_multiple_after_field"] += 1
                if normal_strong and zero_multiple:
                    totals[f"normal_{mode}_from_zero_multiple_after_field"] += 1
                if normal_strong and no_repair_supply and zero_multiple:
                    totals[f"normal_{mode}_from_zero_multiple_no_repair_supply"] += 1

                if normal_strong and delta_exact:
                    totals[f"normal_{mode}_delta_exact_after_field"] += 1
                if normal_strong and zero_exact:
                    totals[f"normal_{mode}_from_zero_exact_after_field"] += 1
                    normal_mode_hulls[mode][hull_id] += 1
                    normal_mode_games[mode][game_id] += 1
                if normal_strong and no_repair_supply and zero_exact:
                    totals[f"normal_{mode}_from_zero_no_repair_supply"] += 1

                if (
                    normal_strong
                    and mode == "nearest"
                    and before_damage == 0
                    and after_damage is not None
                    and expected is not None
                    and max_repair_points is not None
                    and 0 <= expected - after_damage <= max_repair_points
                ):
                    totals["normal_nearest_repair_bracket_from_zero"] += 1

            nearest_damage_hits = normal_damage_hits["nearest"]
            if (
                normal_strong
                and normal_multiple["nearest"]
                and nearest_damage_hits is not None
                and nearest_damage_hits != inferred_slow_hits
            ):
                totals["normal_nearest_damage_hits_differ_from_slow_hits"] += 1
                if len(examples["normal_damage_vs_slow_hits"]) < args.examples:
                    examples["normal_damage_vs_slow_hits"].append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "ship": ship_id,
                            "hull": hull_id,
                            "mass": hull_mass,
                            "hull_tech": hull_tech,
                            "damage_before": before_damage,
                            "damage_after": after_damage,
                            "damage_delta": damage_delta,
                            "nearest_quantum": normal_q["nearest"],
                            "damage_hits": nearest_damage_hits,
                            "slow_hits": inferred_slow_hits,
                            "lost_distance": round(lost_distance, 3),
                            "supplies_before": before_supplies,
                            "supplies_after": after_supplies,
                        }
                    )

            if normal_strong and normal_exact["nearest"] and not normal_exact["ceil"]:
                totals["normal_nearest_not_ceil_from_zero"] += 1
                if len(examples["normal_nearest_not_ceil"]) < args.examples:
                    examples["normal_nearest_not_ceil"].append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "ship": ship_id,
                            "hull": hull_id,
                            "mass": hull_mass,
                            "hull_tech": hull_tech,
                            "damage_before": before_damage,
                            "damage_after": after_damage,
                            "damage_delta": damage_delta,
                            "quantums": normal_q,
                            "inferred_slow_hits": inferred_slow_hits,
                            "lost_distance": round(lost_distance, 3),
                            "supplies_before": before_supplies,
                            "supplies_after": after_supplies,
                        }
                    )
            if ten_ly_match and not after_normal and normal_exact["nearest"]:
                totals["normal_nearest_control_no_after_field"] += 1

    print("\n===== POPULATION =====")
    for key in (
        "effective_short_same_line",
        "state_or_identity_unusable",
        "same_identity_after",
        "missing_hull_mass",
        "web_state_signature",
        "web_after_field_strong",
        "normal_mine_10ly_geometry",
        "normal_after_field_strong",
    ):
        print(f"{key}=", totals[key])

    print("\n===== WEB ROUNDING DIFFERENTIAL =====")
    for mode in ("ceil", "floor", "nearest"):
        print(f"web_{mode}_delta_match_after_field=", totals[f"web_{mode}_delta_match_after_field"])
        print(f"web_{mode}_from_zero_after_field=", totals[f"web_{mode}_from_zero_after_field"])
        print(f"web_{mode}_from_zero_no_repair_supply=", totals[f"web_{mode}_from_zero_no_repair_supply"])
        print(f"web_{mode}_hulls=", dict(web_mode_hulls[mode].most_common()))
        print(f"web_{mode}_games=", sorted(web_mode_games[mode]))
    print("web_nearest_not_ceil_delta=", totals["web_nearest_not_ceil_delta"])
    print("web_nearest_control_no_after_field=", totals["web_nearest_control_no_after_field"])

    print("\n===== NORMAL MINE ROUNDING DIFFERENTIAL =====")
    for mode in ("ceil", "floor", "nearest"):
        print(f"normal_{mode}_delta_multiple_after_field=", totals[f"normal_{mode}_delta_multiple_after_field"])
        print(f"normal_{mode}_from_zero_multiple_after_field=", totals[f"normal_{mode}_from_zero_multiple_after_field"])
        print(f"normal_{mode}_from_zero_multiple_no_repair_supply=", totals[f"normal_{mode}_from_zero_multiple_no_repair_supply"])
        print(f"normal_{mode}_delta_exact_after_field=", totals[f"normal_{mode}_delta_exact_after_field"])
        print(f"normal_{mode}_from_zero_exact_after_field=", totals[f"normal_{mode}_from_zero_exact_after_field"])
        print(f"normal_{mode}_from_zero_no_repair_supply=", totals[f"normal_{mode}_from_zero_no_repair_supply"])
        print(f"normal_{mode}_hulls=", dict(normal_mode_hulls[mode].most_common()))
        print(f"normal_{mode}_games=", sorted(normal_mode_games[mode]))
    print("normal_nearest_repair_bracket_from_zero=", totals["normal_nearest_repair_bracket_from_zero"])
    print("normal_nearest_not_ceil_from_zero=", totals["normal_nearest_not_ceil_from_zero"])
    print("normal_nearest_damage_hits_differ_from_slow_hits=", totals["normal_nearest_damage_hits_differ_from_slow_hits"])
    print("normal_nearest_control_no_after_field=", totals["normal_nearest_control_no_after_field"])

    for bucket, title in (
        ("web_nearest_not_ceil", "WEB NEAREST-BUT-NOT-CEIL EXAMPLES"),
        ("normal_nearest_not_ceil", "NORMAL NEAREST-BUT-NOT-CEIL EXAMPLES"),
        ("normal_damage_vs_slow_hits", "NORMAL DAMAGE-HITS VS SLOW-HITS EXAMPLES"),
    ):
        print(f"\n===== {title} =====")
        for item in examples[bucket]:
            print(item)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "The Planets.nu minefield documentation states that damage is rounded up. "
        "This audit does not assume that statement matches NuHost implementation: "
        "ceil, floor and positive round-half-up are compared directly on surviving "
        "same-identity mine/web candidates."
    )
    print(
        "Five supplies repair one percentage point and repair phases occur after normal "
        "movement, so exact damage is strongest when the ship started undamaged and had "
        "fewer than five supplies. Repair-bracket counts are supportive, not exact proof."
    )
    print(
        "Normal-mine damage-hit multiplicity is measured separately from 10-ly slowdown "
        "count. Documentation allows multiple impacts and only applies a slowdown when "
        "more than 10 ly remain at the relevant hit; therefore equal counts are a strong "
        "subset, not a universal requirement."
    )
    print(
        "Field overlap alone remains insufficient. Promote a damage rounding rule only "
        "if it wins on field-backed rows across multiple hulls/games and does not show "
        "comparable support in the no-after-field controls."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
