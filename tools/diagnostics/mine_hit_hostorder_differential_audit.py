from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
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


def _damage_quantum(hull_mass: int | None, *, web: bool) -> int | None:
    if hull_mass is None or hull_mass < 0:
        return None
    numerator = 1_000 if web else 10_000
    denominator = hull_mass + 1
    return (numerator + denominator - 1) // denominator


def _owner_states(
    *,
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    before_turn: int,
    after_turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None, Mapping[str, Any] | None, bool]:
    owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
    if owner_id is None or before_owner is None:
        return owner_id, None, None, False

    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
    if after_owner_id != owner_id or after_owner is None:
        return owner_id, before_owner.raw, None, False

    before_raw = before_owner.raw
    after_raw = after_owner.raw
    before_hull = _intish(before_raw.get("hullid", before_raw.get("hull_id")))
    after_hull = _intish(after_raw.get("hullid", after_raw.get("hull_id")))
    if before_hull is None or after_hull is None or before_hull != after_hull:
        return owner_id, before_raw, after_raw, False

    # Raw ship `turn` is already used elsewhere in the corpus as a stable
    # identity discriminator. If both sides expose it, require it to remain
    # unchanged so a destroyed/rebuilt ship slot cannot masquerade as movement.
    before_identity_turn = _intish(before_raw.get("turn"))
    after_identity_turn = _intish(after_raw.get("turn"))
    if (
        before_identity_turn is not None
        and after_identity_turn is not None
        and before_identity_turn != after_identity_turn
    ):
        return owner_id, before_raw, after_raw, False

    return owner_id, before_raw, after_raw, True


def _post_reset(after_raw: Mapping[str, Any] | None, observed: tuple[int, int]) -> bool:
    if after_raw is None:
        return False
    warp = _intish(after_raw.get("warp"))
    target_x = _intish(after_raw.get("targetx", after_raw.get("waypointx")))
    target_y = _intish(after_raw.get("targety", after_raw.get("waypointy")))
    return warp == 0 and (target_x, target_y) == observed


def _field_identity(field: Mapping[str, Any]) -> tuple[int, int, bool] | None:
    field_id = field.get("id")
    owner_id = field.get("owner_id")
    is_web = field.get("is_web")
    if (
        not isinstance(field_id, int)
        or not isinstance(owner_id, int)
        or not isinstance(is_web, bool)
    ):
        return None
    return field_id, owner_id, is_web


def _persistent_identities(
    before_fields: Sequence[Mapping[str, Any]],
    after_fields: Sequence[Mapping[str, Any]],
) -> frozenset[tuple[int, int, bool]]:
    before = {
        identity
        for field in before_fields
        if (identity := _field_identity(field)) is not None
    }
    after = {
        identity
        for field in after_fields
        if (identity := _field_identity(field)) is not None
    }
    return frozenset(before.intersection(after))


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


def _positive_multiple(value: int | None, quantum: int | None) -> tuple[bool, int | None]:
    if value is None or quantum is None or value <= 0 or quantum <= 0:
        return False, None
    if value % quantum != 0:
        return False, None
    return True, value // quantum


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Second-pass mine/web residual differential. It combines documented "
            "mine damage quanta with movement loss, post-movement navigation state, "
            "after-turn minefield geometry and same-identity owner state. Private "
            "prepared data stays local; output is derived mechanical evidence only."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
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

    print("===== MINE-HIT HOST-ORDER DIFFERENTIAL =====")
    print("generic_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    web_hulls = Counter()
    web_games = Counter()
    normal_hulls = Counter()
    normal_games = Counter()
    normal_exact_hits = Counter()
    web_exact_hits = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
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
            raw_regular_distance = min(target_distance, raw_nominal)
            effective_regular_distance = min(target_distance, effective_nominal)

            raw_short = _short_same_line(
                target_vector=target_vector,
                observed_vector=observed_vector,
                regular_distance=raw_regular_distance,
            )
            effective_short = _short_same_line(
                target_vector=target_vector,
                observed_vector=observed_vector,
                regular_distance=effective_regular_distance,
            )
            if raw_short:
                totals["raw_short_same_line"] += 1
                totals["raw_short_gravitonic" if gravitonic else "raw_short_non_gravitonic"] += 1
            if effective_short:
                totals["effective_short_same_line"] += 1
                totals[
                    "effective_short_gravitonic" if gravitonic else "effective_short_non_gravitonic"
                ] += 1
            if not effective_short:
                continue

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None:
                totals["owner_state_missing"] += 1
                continue
            if after_raw is None:
                totals["after_owner_state_missing"] += 1
                continue
            if not same_identity:
                totals["after_identity_break"] += 1
                continue
            totals["same_identity_after"] += 1

            hull_spec = specs.hulls.get(hull_id)
            hull_mass = hull_spec.mass if hull_spec is not None else None
            hull_tech = hull_spec.tech_level if hull_spec is not None else None
            normal_quantum = _damage_quantum(hull_mass, web=False)
            web_quantum = _damage_quantum(hull_mass, web=True)

            before_damage = _intish(before_raw.get("damage"))
            after_damage = _intish(after_raw.get("damage"))
            damage_delta = (
                after_damage - before_damage
                if before_damage is not None and after_damage is not None
                else None
            )
            damage_increase = damage_delta is not None and damage_delta > 0
            if damage_increase:
                totals["damage_increase"] += 1

            before_supplies = _intish(before_raw.get("supplies"))
            after_supplies = _intish(after_raw.get("supplies"))
            supply_bracket_low = (
                before_supplies is not None
                and after_supplies is not None
                and before_supplies < 5
                and after_supplies < 5
            )

            reset = _post_reset(after_raw, observed)
            if reset:
                totals["post_warp0_waypoint_reset"] += 1
            web_state = damage_increase and reset
            if web_state:
                totals["web_state_signature"] += 1

            before_any = [
                field
                for field in fields(before_turn, None)
                if _field_parseable(field) and _enemyish(field, owner_id)
            ]
            after_any = [
                field
                for field in fields(after_turn, None)
                if _field_parseable(field) and _enemyish(field, owner_id)
            ]
            after_owner = [
                field
                for field in fields(after_turn, owner_id)
                if _field_parseable(field) and _enemyish(field, owner_id)
            ]

            before_web_at_observed = [
                field
                for field in before_any
                if field.get("is_web") is True and _point_in_field(observed, field, topology)
            ]
            after_web_at_observed = [
                field
                for field in after_any
                if field.get("is_web") is True and _point_in_field(observed, field, topology)
            ]
            owner_after_web_at_observed = [
                field
                for field in after_owner
                if field.get("is_web") is True and _point_in_field(observed, field, topology)
            ]
            persistent_web_ids = _persistent_identities(
                before_web_at_observed,
                after_web_at_observed,
            )

            if after_web_at_observed:
                totals["after_visible_web_at_observed"] += 1
            if owner_after_web_at_observed:
                totals["owner_after_visible_web_at_observed"] += 1
            if persistent_web_ids:
                totals["persistent_web_at_observed"] += 1

            web_after_field = web_state and bool(after_web_at_observed)
            if web_after_field:
                totals["web_after_field_strong"] += 1

            web_damage_from_zero, web_hits_from_zero = _positive_multiple(
                after_damage if before_damage == 0 else None,
                web_quantum,
            )
            web_damage_delta_match, web_hits_from_delta = _positive_multiple(
                damage_delta,
                web_quantum,
            )

            if web_after_field and web_damage_from_zero:
                totals["web_exact_damage_after_field"] += 1
                web_hulls[hull_id] += 1
                web_games[game_id] += 1
                if web_hits_from_zero is not None:
                    web_exact_hits[web_hits_from_zero] += 1
            if web_after_field and web_damage_delta_match:
                totals["web_delta_quantum_after_field"] += 1
            if web_after_field and web_damage_from_zero and persistent_web_ids:
                totals["web_exact_damage_persistent_field"] += 1
            if web_after_field and web_damage_from_zero and supply_bracket_low:
                totals["web_exact_damage_low_supply_bracket"] += 1

            lost_distance = effective_regular_distance - observed_distance
            inferred_slow_hits = int(round(lost_distance / 10.0)) if lost_distance > 0.0 else 0
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
                regular_distance=effective_regular_distance,
            )
            before_normal_crossing = [
                field
                for field in before_any
                if field.get("is_web") is False
                and _segment_intersects_field(
                    origin=origin,
                    target_vector=regular_vector,
                    field=field,
                    topology=topology,
                )
            ]
            after_normal_crossing = [
                field
                for field in after_any
                if field.get("is_web") is False
                and _segment_intersects_field(
                    origin=origin,
                    target_vector=regular_vector,
                    field=field,
                    topology=topology,
                )
            ]
            owner_after_normal_crossing = [
                field
                for field in after_owner
                if field.get("is_web") is False
                and _segment_intersects_field(
                    origin=origin,
                    target_vector=regular_vector,
                    field=field,
                    topology=topology,
                )
            ]
            persistent_normal_ids = _persistent_identities(
                before_normal_crossing,
                after_normal_crossing,
            )

            if after_normal_crossing:
                totals["after_visible_normal_field_crossing"] += 1
            if owner_after_normal_crossing:
                totals["owner_after_visible_normal_field_crossing"] += 1
            if persistent_normal_ids:
                totals["persistent_normal_field_crossing"] += 1

            normal_after_field = damage_increase and ten_ly_match and bool(after_normal_crossing)
            if normal_after_field:
                totals["normal_after_field_strong"] += 1

            expected_normal_damage = (
                inferred_slow_hits * normal_quantum
                if ten_ly_match and normal_quantum is not None
                else None
            )
            normal_exact_from_zero = (
                before_damage == 0
                and after_damage is not None
                and expected_normal_damage is not None
                and after_damage == expected_normal_damage
            )
            normal_exact_delta = (
                damage_delta is not None
                and expected_normal_damage is not None
                and damage_delta == expected_normal_damage
            )

            if ten_ly_match and normal_exact_from_zero:
                totals["normal_exact_distance_damage"] += 1
            if normal_after_field and normal_exact_from_zero:
                totals["normal_exact_damage_after_field"] += 1
                normal_hulls[hull_id] += 1
                normal_games[game_id] += 1
                normal_exact_hits[inferred_slow_hits] += 1
            if normal_after_field and normal_exact_delta:
                totals["normal_delta_damage_after_field"] += 1
            if normal_after_field and normal_exact_from_zero and persistent_normal_ids:
                totals["normal_exact_damage_persistent_field"] += 1
            if normal_after_field and normal_exact_from_zero and supply_bracket_low:
                totals["normal_exact_damage_low_supply_bracket"] += 1
            if ten_ly_match and normal_exact_from_zero and not after_normal_crossing:
                totals["normal_exact_damage_no_after_field"] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "baseline": str(baseline_category),
                "warp": warp,
                "gravitonic": gravitonic,
                "hull_mass": hull_mass,
                "hull_tech": hull_tech,
                "regular_distance": round(effective_regular_distance, 3),
                "observed_distance": round(observed_distance, 3),
                "lost_distance": round(lost_distance, 3),
                "damage_before": before_damage,
                "damage_after": after_damage,
                "damage_delta": damage_delta,
                "normal_damage_quantum": normal_quantum,
                "web_damage_quantum": web_quantum,
                "inferred_slow_hits": inferred_slow_hits,
                "expected_normal_damage": expected_normal_damage,
                "supplies_before": before_supplies,
                "supplies_after": after_supplies,
                "post_reset": reset,
                "after_web": bool(after_web_at_observed),
                "persistent_web": bool(persistent_web_ids),
                "after_normal_crossing": bool(after_normal_crossing),
                "persistent_normal_crossing": bool(persistent_normal_ids),
            }

            if web_after_field and web_damage_from_zero and len(examples["web_exact"]) < args.examples:
                web_detail = dict(detail)
                web_detail["web_hits_from_damage"] = web_hits_from_zero
                examples["web_exact"].append(web_detail)
            elif web_after_field and len(examples["web_nonexact"]) < args.examples:
                web_detail = dict(detail)
                web_detail["web_hits_from_delta"] = web_hits_from_delta
                examples["web_nonexact"].append(web_detail)

            if normal_after_field and normal_exact_from_zero and len(examples["normal_exact"]) < args.examples:
                examples["normal_exact"].append(dict(detail))
            elif normal_after_field and len(examples["normal_nonexact"]) < args.examples:
                examples["normal_nonexact"].append(dict(detail))

    print("\n===== POPULATION / CONSISTENCY =====")
    for key in (
        "raw_short_same_line",
        "raw_short_non_gravitonic",
        "raw_short_gravitonic",
        "effective_short_same_line",
        "effective_short_non_gravitonic",
        "effective_short_gravitonic",
        "owner_state_missing",
        "after_owner_state_missing",
        "after_identity_break",
        "same_identity_after",
        "damage_increase",
        "post_warp0_waypoint_reset",
    ):
        print(f"{key}=", totals[key])

    print("\n===== WEB HOST-ORDER EVIDENCE =====")
    for key in (
        "web_state_signature",
        "after_visible_web_at_observed",
        "owner_after_visible_web_at_observed",
        "persistent_web_at_observed",
        "web_after_field_strong",
        "web_exact_damage_after_field",
        "web_delta_quantum_after_field",
        "web_exact_damage_persistent_field",
        "web_exact_damage_low_supply_bracket",
    ):
        print(f"{key}=", totals[key])
    print("web_exact_games=", sorted(web_games))
    print("web_exact_hulls=", dict(web_hulls.most_common()))
    print("web_exact_hit_multiples=", dict(sorted(web_exact_hits.items())))

    print("\n===== NORMAL MINE HOST-ORDER EVIDENCE =====")
    for key in (
        "normal_mine_10ly_geometry",
        "after_visible_normal_field_crossing",
        "owner_after_visible_normal_field_crossing",
        "persistent_normal_field_crossing",
        "normal_after_field_strong",
        "normal_exact_distance_damage",
        "normal_exact_damage_after_field",
        "normal_delta_damage_after_field",
        "normal_exact_damage_persistent_field",
        "normal_exact_damage_low_supply_bracket",
        "normal_exact_damage_no_after_field",
    ):
        print(f"{key}=", totals[key])
    print("normal_exact_games=", sorted(normal_games))
    print("normal_exact_hulls=", dict(normal_hulls.most_common()))
    print("normal_exact_slow_hits=", dict(sorted(normal_exact_hits.items())))

    for bucket, title in (
        ("web_exact", "WEB EXACT DAMAGE EXAMPLES"),
        ("web_nonexact", "WEB STATE/FIELD BUT NON-EXACT DAMAGE EXAMPLES"),
        ("normal_exact", "NORMAL EXACT DISTANCE+DAMAGE EXAMPLES"),
        ("normal_nonexact", "NORMAL FIELD/10LY BUT NON-EXACT DAMAGE EXAMPLES"),
    ):
        print(f"\n===== {title} =====")
        for item in examples[bucket]:
            print(item)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "After-turn minefield geometry is used as the stronger Host-order proxy because "
        "documented lay/web-lay, sweep, decay and minefield-destruction phases occur "
        "before ordinary movement. Persistent before+after field identity is reported "
        "separately and is stronger still, but neither substitutes for an event log."
    )
    print(
        "Exact normal-mine evidence requires the documented low-tech 10-ly slowdown "
        "count and the matching integer damage quantum ceil(10000/(hull_mass+1)) "
        "on a surviving same-identity owner ship. Exact web evidence requires the "
        "Warp-0/waypoint reset state, an after-turn web field at the endpoint, and "
        "damage in integer multiples of ceil(1000/(hull_mass+1))."
    )
    print(
        "No production label should be promoted until this differential is run across "
        "the corpus and identity/repair/visibility edge cases are reviewed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
