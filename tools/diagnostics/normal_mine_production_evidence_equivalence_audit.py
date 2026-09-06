from __future__ import annotations

from collections import Counter, defaultdict
from math import floor, hypot
from typing import Any, Mapping

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import (
    _positive_multiple,
    _segment_intersects_field,
    build_mine_evidence_context,
    nearest_damage_quantum,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.ship_repair import repair_damage_with_supplies

from normal_mine_direct_major_click_penalty_audit import _regular_major_click
from normal_mine_reported_excess_shortening_residual_audit import (
    DATABASE,
    PREPARED_DIR,
    RAW_DIR,
    _effective_sample,
    _load_rows,
    _same_line_metrics,
    _sample,
)
from normal_mine_short_waypoint_scaled_penalty_audit import _residual_items
from normal_mine_single_candidate_step_state_warpwell_audit import (
    _click_for_point,
    _major_axis_clicks,
)


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _key(row: Mapping[str, Any]) -> tuple[int, int, int]:
    before_turn = row.get("before_turn", row.get("before_archive_turn"))
    return int(row["game_id"]), int(before_turn), int(row["ship_id"])


def _exact_repair_hit_counts(
    *,
    before_damage: int | None,
    after_damage: int | None,
    before_supplies: int | None,
    after_supplies: int | None,
    quantum: int | None,
) -> tuple[int, ...]:
    if (
        before_damage is None
        or after_damage is None
        or before_supplies is None
        or after_supplies is None
        or quantum is None
        or quantum <= 0
        or before_damage < 0
        or after_damage < 0
        or before_supplies < 0
        or after_supplies < 0
    ):
        return ()

    matches: list[int] = []
    # A surviving observed transition cannot need an unbounded search. Nine hits
    # is already far beyond every corpus-observed normal-mine multiplicity here;
    # keep the diagnostic finite and explicit rather than deriving from messages.
    for hits in range(1, 10):
        raw_damage = before_damage + hits * quantum
        expected_damage, expected_supplies, _ = repair_damage_with_supplies(
            damage=raw_damage,
            supplies=before_supplies,
        )
        if expected_damage == after_damage and expected_supplies == after_supplies:
            matches.append(hits)
    return tuple(matches)


def _damage_hit_candidates(
    *,
    before_raw: Mapping[str, Any],
    after_raw: Mapping[str, Any],
    quantum: int | None,
) -> dict[int, set[str]]:
    result: dict[int, set[str]] = defaultdict(set)
    before_damage = _intish(before_raw.get("damage"))
    after_damage = _intish(after_raw.get("damage"))
    if before_damage is not None and after_damage is not None:
        direct_hits = _positive_multiple(after_damage - before_damage, quantum)
        if direct_hits is not None:
            result[direct_hits].add("direct_damage_delta")

    before_supplies = _intish(before_raw.get("supplies"))
    after_supplies = _intish(after_raw.get("supplies"))
    for hits in _exact_repair_hit_counts(
        before_damage=before_damage,
        after_damage=after_damage,
        before_supplies=before_supplies,
        after_supplies=after_supplies,
        quantum=quantum,
    ):
        result[hits].add("exact_supply_repair_trace")
    return result


def _report_reference_keys() -> set[tuple[int, int, int]]:
    keys: set[tuple[int, int, int]] = set()
    for item in _residual_items():
        if item.get("short_waypoint") is not True or item.get("click_status") != "resolved":
            continue
        model = item.get("models", {}).get("scaled_floor")
        if not isinstance(model, Mapping):
            continue
        if model.get("endpoint_exact") is True and model.get("delta_observed_minus_expected_loss") == 0:
            keys.add(_key(item))
    return keys


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    source_rows = _load_rows()
    report_reference = _report_reference_keys()
    print("===== NORMAL-MINE PRODUCTION-EVIDENCE EQUIVALENCE AUDIT =====")
    print("source_post_fuel_residual_rows=", len(source_rows))
    print("report_backed_short_waypoint_exact_keys=", len(report_reference))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        by_game[int(row["game_id"])].append(row)

    totals: Counter[str] = Counter()
    production_candidates: dict[tuple[int, int, int], dict[str, Any]] = {}

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        print(f"production-visible prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])

            owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or before_owner is None:
                continue
            if after_owner_id != owner_id or after_owner is None:
                continue

            sample = _effective_sample(_sample(row), topology)
            hull_id = sample.hull_id
            hull = mine_context.specs.hulls.get(int(hull_id)) if hull_id is not None else None
            if hull is None or hull.tech_level >= 7 or not 1 <= sample.warp <= 9:
                continue
            if topology.sphere is True:
                totals["sphere_fail_closed"] += 1
                continue

            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = sample.observed_destination
            target_vector = _vector(origin, target, topology)
            observed_vector = _vector(origin, observed, topology)
            target_distance = hypot(*target_vector)
            observed_distance = hypot(*observed_vector)
            nominal_distance = float(row["nominal_max_distance"] or 0.0)
            regular_distance = min(target_distance, nominal_distance)
            if not (regular_distance < nominal_distance - 1e-9):
                continue
            totals["short_waypoint_lowtech_planar"] += 1

            observed_cross, observed_progress = _same_line_metrics(
                origin=origin,
                target=target,
                observed=observed,
                topology=topology,
            )
            if (
                observed_cross is None
                or observed_progress is None
                or observed_cross > 1.5
                or observed_progress <= 0.0
                or observed_distance <= 0.0
                or observed_distance + 1.5 >= regular_distance
            ):
                continue
            totals["short_same_line"] += 1

            normal_field_crossing = any(
                not field.is_web
                and field.owner_id is not None
                and field.owner_id > 0
                and field.owner_id != owner_id
                and _segment_intersects_field(
                    origin=origin,
                    vector=target_vector,
                    field_record=field,
                    topology=topology,
                )
                for field in mine_context.fields(after_turn)
            )
            if not normal_field_crossing:
                continue
            totals["normal_field_crossing"] += 1

            quantum = nearest_damage_quantum(hull.mass, web=False)
            hit_candidates = _damage_hit_candidates(
                before_raw=before_owner.raw,
                after_raw=after_owner.raw,
                quantum=quantum,
            )
            if not hit_candidates:
                continue
            totals["damage_or_repair_evidence"] += 1

            clicks = _major_axis_clicks(origin=origin, target=target)
            regular_click = _regular_major_click(
                origin=origin,
                target=target,
                regular_distance=regular_distance,
            )
            observed_click = _click_for_point(clicks, observed)
            if regular_click is None or observed_click is None:
                totals["click_unresolved"] += 1
                continue
            observed_loss = regular_click - observed_click

            exact_models: list[dict[str, Any]] = []
            for damage_hits, evidence_modes in sorted(hit_candidates.items()):
                for slowdown_hits in range(1, damage_hits + 1):
                    scaled_raw = 10.0 * slowdown_hits * nominal_distance / regular_distance
                    penalty = floor(scaled_raw + 1e-12)
                    expected_click = max(0, regular_click - penalty)
                    expected_endpoint = clicks[expected_click][1]
                    if observed_loss != penalty or expected_endpoint != observed:
                        continue
                    exact_models.append(
                        {
                            "damage_hits": damage_hits,
                            "slowdown_hits": slowdown_hits,
                            "evidence_modes": tuple(sorted(evidence_modes)),
                            "scaled_raw": round(scaled_raw, 6),
                            "penalty_clicks": penalty,
                        }
                    )

            if not exact_models:
                continue
            totals["scaled_floor_exact"] += 1
            key = (game_id, before_turn, ship_id)
            production_candidates[key] = {
                "game_id": game_id,
                "before_turn": before_turn,
                "ship_id": ship_id,
                "hull_id": int(hull_id) if hull_id is not None else None,
                "warp": sample.warp,
                "origin": origin,
                "target": target,
                "observed": observed,
                "nominal_distance": round(nominal_distance, 6),
                "regular_distance": round(regular_distance, 6),
                "regular_click": regular_click,
                "observed_click": observed_click,
                "observed_click_loss": observed_loss,
                "quantum": quantum,
                "before_damage": _intish(before_owner.raw.get("damage")),
                "after_damage": _intish(after_owner.raw.get("damage")),
                "before_supplies": _intish(before_owner.raw.get("supplies")),
                "after_supplies": _intish(after_owner.raw.get("supplies")),
                "models": exact_models,
            }

    production_keys = set(production_candidates)
    matched = production_keys & report_reference
    missed = report_reference - production_keys
    extra = production_keys - report_reference

    evidence_mode_counts: Counter[str] = Counter()
    for item in production_candidates.values():
        modes = {
            mode
            for model in item["models"]
            for mode in model["evidence_modes"]
        }
        evidence_mode_counts.update(modes)

    print("\n===== SUMMARY =====")
    for name in (
        "sphere_fail_closed",
        "short_waypoint_lowtech_planar",
        "short_same_line",
        "normal_field_crossing",
        "damage_or_repair_evidence",
        "click_unresolved",
        "scaled_floor_exact",
    ):
        print(f"{name}=", totals[name])
    print("production_visible_candidate_count=", len(production_keys))
    print("report_reference_count=", len(report_reference))
    print("intersection_count=", len(matched))
    print("missed_report_backed_count=", len(missed))
    print("extra_production_only_count=", len(extra))
    print("evidence_mode_counts=", dict(sorted(evidence_mode_counts.items())))

    print("\n===== MATCHED REPORT-BACKED =====")
    for key in sorted(matched):
        print(production_candidates[key])

    print("\n===== MISSED REPORT-BACKED =====")
    for key in sorted(missed):
        print(key)

    print("\n===== EXTRA PRODUCTION-ONLY =====")
    for key in sorted(extra):
        print(production_candidates[key])

    print("\n===== TARGET =====")
    print(production_candidates.get((511506, 23, 160)))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic compares the report-backed exact short-waypoint reference set against a candidate using only "
        "privacy-safe production-visible state: hostile normal-field crossing, low-tech planar short-waypoint geometry, "
        "normal-mine damage quantum, direct damage delta or an exact canonical supply-repair trace, and an exact scaled-"
        "floor Host-click endpoint. It does not read messages for the production-visible candidate side. Any extra keys "
        "must be inspected before production integration; misses mean message-derived evidence cannot yet be reproduced "
        "from the normalized corpus. No production classifier, schemas, labels, or accounting are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
