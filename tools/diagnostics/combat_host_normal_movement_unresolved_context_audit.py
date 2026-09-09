from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import hypot
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_chunnel_context import (
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.movement_chunnel_match import route_equivalent_chunnel_category
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import (
    _segment_intersects_field,
    build_mine_evidence_context,
    nearest_damage_quantum,
    scaled_floor_normal_mine_endpoint,
)
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from combat_host_candidate_set_audit import _owner_rows_for_turn, _serialize
from combat_host_normal_movement_position_audit import _effective_requested_warp
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, SPECIAL_GAME_ID, _static_specs
from combat_host_residual_physical_stack_audit import _xy
from combat_host_residual_source_context_audit import _collect_factual_vcrs


RESIDUAL_SCHEMA = "planets-lab.combat-host-normal-movement-position-residual-audit.v1"
SCHEMA = "planets-lab.combat-host-normal-movement-unresolved-context-audit.v1"
DEFAULT_MAX_SLOWDOWN_HITS = 10


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _unresolved_rows(report: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    if report.get("schema") != RESIDUAL_SCHEMA:
        raise ValueError(f"residual report schema must be {RESIDUAL_SCHEMA}")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("residual report rows must be a list")
    return tuple(
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("context_status") == "unresolved"
    )


def _vcr_ship_starts(
    vcr_rows: Sequence[Mapping[str, Any]],
    *,
    ship_id: int,
    factual_site: tuple[int, int],
) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for row in vcr_rows:
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            continue
        x = _intish(payload.get("x"))
        y = _intish(payload.get("y"))
        if (x, y) != factual_site:
            continue
        for side in ("left", "right"):
            raw = payload.get(side)
            if not isinstance(raw, Mapping):
                continue
            if _intish(raw.get("objectid")) != ship_id:
                continue
            result.append(
                {
                    "vcr_id": _intish(row.get("vcr_id")),
                    "side": side,
                    "damage": _intish(raw.get("damage")),
                    "shield": _intish(raw.get("shield")),
                    "mass": _intish(raw.get("mass")),
                    "crew": _intish(raw.get("crew")),
                    "hullid": _intish(raw.get("hullid")),
                    "raceid": _intish(raw.get("raceid")),
                }
            )
    return tuple(sorted(result, key=lambda item: (item["vcr_id"] or -1, item["side"])))


def _mine_route_geometry(
    *,
    context: Any,
    origin: tuple[int, int],
    target: tuple[int, int],
    warp: int,
    hull_id: int,
) -> tuple[tuple[float, float], float, float] | None:
    if context.topology.sphere is not False:
        return None
    target_vector = _vector(origin, target, context.topology)
    target_distance = hypot(*target_vector)
    nominal_distance = float(warp * warp)
    if hull_id in GRAVITONIC_HULL_IDS:
        nominal_distance *= 2.0
    regular_distance = min(target_distance, nominal_distance)
    if target_distance <= 1e-9 or regular_distance <= 1e-9:
        return None
    scale = regular_distance / target_distance
    regular_vector = (target_vector[0] * scale, target_vector[1] * scale)
    return regular_vector, regular_distance, nominal_distance


def _normal_field_crossings(
    *,
    context: Any,
    turn: int,
    owner_id: int,
    origin: tuple[int, int],
    regular_vector: tuple[float, float],
) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for field_record in context.fields(turn):
        if field_record.is_web:
            continue
        if field_record.owner_id is None or field_record.owner_id <= 0:
            continue
        if field_record.owner_id == owner_id:
            continue
        if not _segment_intersects_field(
            origin=origin,
            vector=regular_vector,
            field_record=field_record,
            topology=context.topology,
        ):
            continue
        result.append(
            {
                "field_id": field_record.field_id,
                "owner_id": field_record.owner_id,
                "x": field_record.x,
                "y": field_record.y,
                "radius": field_record.radius,
            }
        )
    return tuple(result)


def _matching_scaled_floor_hits(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    factual_site: tuple[int, int],
    nominal_distance: float,
    regular_distance: float,
    max_hits: int,
) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for slowdown_hits in range(1, max_hits + 1):
        endpoint, penalty = scaled_floor_normal_mine_endpoint(
            origin=origin,
            target=target,
            nominal_distance=nominal_distance,
            regular_distance=regular_distance,
            slowdown_hits=slowdown_hits,
        )
        if endpoint != factual_site:
            continue
        result.append(
            {
                "slowdown_hits": slowdown_hits,
                "endpoint": list(endpoint),
                "major_axis_penalty": penalty,
            }
        )
    return tuple(result)


def _chunnel_matches(
    events: Sequence[Any],
    *,
    before_turn: int,
    predicted: tuple[int, int],
    factual_site: tuple[int, int],
    ship_id: int,
    owner_id: int,
) -> tuple[str | None, tuple[dict[str, Any], ...]]:
    matches = tuple(
        event
        for event in events
        if int(event.before_archive_turn) == before_turn
        and event.pre_chunnel_position == predicted
        and event.destination == factual_site
    )
    category = route_equivalent_chunnel_category(
        matches,
        ship_id=ship_id,
        owner_id=owner_id,
    )
    rows = tuple(
        {
            "initiator_ship_id": int(event.initiator_ship_id),
            "target_ship_id": int(event.target_ship_id),
            "owner_id": int(event.owner_id),
            "pre_chunnel_position": list(event.pre_chunnel_position)
            if event.pre_chunnel_position is not None
            else None,
            "destination": list(event.destination),
        }
        for event in matches
    )
    return category, rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    residual_report = json.loads(args.residual_report.read_text(encoding="utf-8"))
    unresolved = _unresolved_rows(residual_report)
    by_game: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in unresolved:
        game_id = _intish(row.get("game_id"))
        if game_id is None or game_id == SPECIAL_GAME_ID:
            raise ValueError(f"invalid ordinary game id: {row.get('game_id')!r}")
        by_game[int(game_id)].append(row)

    totals: Counter[str] = Counter()
    rows_out: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(by_game.items()):
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        specs = _static_specs(archive_data)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        abilities = extract_stable_chunnel_abilities(archive_data)
        chunnel_events, chunnel_event_counts = discover_observed_chunnel_events(
            prepared.snapshots,
            abilities,
        )

        vcr_cache: dict[int, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
        owner_rows_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}

        for source_row in sorted(
            game_rows,
            key=lambda item: (int(item["battle_turn"]), int(item["ship_id"])),
        ):
            totals["unresolved_rows"] += 1
            battle_turn = int(source_row["battle_turn"])
            before_turn = battle_turn - 1
            ship_id = int(source_row["ship_id"])
            owner_id = int(source_row["owner_id"])
            predicted_raw = source_row.get("predicted")
            factual_raw = source_row.get("factual_site")
            if (
                not isinstance(predicted_raw, list)
                or len(predicted_raw) != 2
                or not isinstance(factual_raw, list)
                or len(factual_raw) != 2
            ):
                totals["invalid_position_row"] += 1
                rows_out.append({**dict(source_row), "focused_status": "invalid_position_row"})
                continue
            predicted = (int(predicted_raw[0]), int(predicted_raw[1]))
            factual_site = (int(factual_raw[0]), int(factual_raw[1]))

            owner_rows = owner_rows_cache.setdefault(
                before_turn,
                _owner_rows_for_turn(ship_groups, before_turn),
            )
            owner_entry = owner_rows.get(ship_id)
            if owner_entry is None or owner_entry[0] != owner_id:
                totals["owner_current_missing"] += 1
                rows_out.append({**dict(source_row), "focused_status": "owner_current_missing"})
                continue
            _, raw = owner_entry

            origin_raw = _xy(raw)
            target_x = _intish(raw.get("targetx"))
            target_y = _intish(raw.get("targety"))
            hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
            if (
                origin_raw[0] is None
                or origin_raw[1] is None
                or target_x is None
                or target_y is None
                or hull_id is None
            ):
                totals["geometry_input_missing"] += 1
                rows_out.append({**dict(source_row), "focused_status": "geometry_input_missing"})
                continue
            origin = (int(origin_raw[0]), int(origin_raw[1]))
            target = (int(target_x), int(target_y))

            effective_warp, warp_issue = _effective_requested_warp(raw, race_id=None)
            if effective_warp is None or warp_issue is not None:
                # The source residual already contains the effective warp used by
                # the v2 predictor; preserve it when race resolution is required.
                effective_warp = _intish(source_row.get("effective_warp"))

            hull_spec = specs.hulls.get(hull_id)
            hull_mass = hull_spec.mass if hull_spec is not None else None
            hull_tech = hull_spec.tech_level if hull_spec is not None else None

            chunnel_category, chunnel_rows = _chunnel_matches(
                chunnel_events,
                before_turn=before_turn,
                predicted=predicted,
                factual_site=factual_site,
                ship_id=ship_id,
                owner_id=owner_id,
            )
            if chunnel_category is not None:
                totals["exact_chunnel_route"] += 1

            mine_geometry: dict[str, Any] | None = None
            if effective_warp is not None and effective_warp > 0:
                geometry = _mine_route_geometry(
                    context=mine_context,
                    origin=origin,
                    target=target,
                    warp=int(effective_warp),
                    hull_id=hull_id,
                )
                if geometry is not None:
                    regular_vector, regular_distance, nominal_distance = geometry
                    exact_hits = _matching_scaled_floor_hits(
                        origin=origin,
                        target=target,
                        factual_site=factual_site,
                        nominal_distance=nominal_distance,
                        regular_distance=regular_distance,
                        max_hits=args.max_slowdown_hits,
                    )
                    before_fields = _normal_field_crossings(
                        context=mine_context,
                        turn=before_turn,
                        owner_id=owner_id,
                        origin=origin,
                        regular_vector=regular_vector,
                    )
                    battle_fields = _normal_field_crossings(
                        context=mine_context,
                        turn=battle_turn,
                        owner_id=owner_id,
                        origin=origin,
                        regular_vector=regular_vector,
                    )
                    if exact_hits:
                        totals["exact_scaled_floor_geometry"] += 1
                    if exact_hits and (before_fields or battle_fields):
                        totals["exact_scaled_floor_with_field_crossing"] += 1
                    mine_geometry = {
                        "hull_tech": hull_tech,
                        "hull_mass": hull_mass,
                        "low_tech_slowdown_eligible": hull_tech is not None and hull_tech < 7,
                        "regular_distance": regular_distance,
                        "nominal_distance": nominal_distance,
                        "exact_scaled_floor_hits": list(exact_hits),
                        "normal_field_crossings_before_turn": list(before_fields),
                        "normal_field_crossings_battle_turn": list(battle_fields),
                        "normal_mine_damage_quantum": nearest_damage_quantum(hull_mass, web=False)
                        if hull_mass is not None
                        else None,
                    }

            if battle_turn not in vcr_cache:
                vcr_cache[battle_turn] = _collect_factual_vcrs(
                    archive_data,
                    game_id=game_id,
                    battle_turn=battle_turn,
                )
            vcr_rows, vcr_conflicts = vcr_cache[battle_turn]
            starts = _vcr_ship_starts(
                vcr_rows,
                ship_id=ship_id,
                factual_site=factual_site,
            )
            if vcr_conflicts:
                totals["vcr_payload_conflicts"] += len(vcr_conflicts)
            if starts:
                totals["vcr_start_found"] += 1

            t1_damage = _intish(raw.get("damage"))
            t1_supplies = _intish(raw.get("supplies"))
            quantum = (
                mine_geometry.get("normal_mine_damage_quantum")
                if mine_geometry is not None
                else None
            )
            starts_with_deltas: list[dict[str, Any]] = []
            direct_damage_multiple = False
            for start in starts:
                start_damage = _intish(start.get("damage"))
                delta = (
                    start_damage - t1_damage
                    if start_damage is not None and t1_damage is not None
                    else None
                )
                multiple = (
                    delta is not None
                    and delta > 0
                    and isinstance(quantum, int)
                    and quantum > 0
                    and delta % quantum == 0
                )
                if multiple:
                    direct_damage_multiple = True
                starts_with_deltas.append(
                    {
                        **start,
                        "damage_delta_from_t1": delta,
                        "positive_normal_mine_quantum_multiple": multiple,
                    }
                )
            if direct_damage_multiple:
                totals["vcr_damage_normal_mine_multiple"] += 1

            candidate_families: list[str] = []
            if chunnel_category is not None:
                candidate_families.append("chunnel")
            if (
                mine_geometry is not None
                and mine_geometry["low_tech_slowdown_eligible"]
                and mine_geometry["exact_scaled_floor_hits"]
                and (
                    mine_geometry["normal_field_crossings_before_turn"]
                    or mine_geometry["normal_field_crossings_battle_turn"]
                )
            ):
                candidate_families.append("normal_mine_scaled_floor")

            if len(candidate_families) == 1:
                focused_status = "single_focused_candidate_family"
                totals[focused_status] += 1
            elif len(candidate_families) > 1:
                focused_status = "multiple_focused_candidate_families"
                totals[focused_status] += 1
            else:
                focused_status = "still_unresolved"
                totals[focused_status] += 1

            rows_out.append(
                {
                    **dict(source_row),
                    "before_turn": before_turn,
                    "origin": list(origin),
                    "target": list(target),
                    "effective_warp": effective_warp,
                    "hull_id": hull_id,
                    "t1_damage": t1_damage,
                    "t1_supplies": t1_supplies,
                    "chunnel_category": chunnel_category,
                    "chunnel_matches": list(chunnel_rows),
                    "chunnel_event_population": len(chunnel_events),
                    "chunnel_event_counts": dict(chunnel_event_counts),
                    "mine_geometry": mine_geometry,
                    "vcr_starts": starts_with_deltas,
                    "candidate_families": candidate_families,
                    "focused_status": focused_status,
                }
            )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "source_residual_report": str(args.residual_report),
        "summary": _serialize(totals),
        "rows": rows_out,
        "evidence_boundary": (
            "Attribution-only follow-up for the rows left unresolved by the bounded v2 residual audit. "
            "Observed Chunnel events and factual VCR combat-start damage may use post-movement/factual data and must "
            "not be fed into candidate generation. Scaled-floor mine geometry is only promoted as a candidate family "
            "when the hull is tech <7, the factual endpoint exactly matches the existing empirical scaled-floor helper, "
            "and at least one hostile normal field crossing is visible in the before/battle-turn evidence. Even then, "
            "random mine-hit outcome is not a deterministic T-1 predictor until the relevant minefield phase/RNG context "
            "is independently reconstructed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe Chunnel and field-backed scaled-floor mine context for unresolved combat movement rows."
    )
    parser.add_argument("--residual-report", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--max-slowdown-hits", type=int, default=DEFAULT_MAX_SLOWDOWN_HITS)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT UNRESOLVED MOVEMENT CONTEXT AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("UNRESOLVED CONTEXT ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: attribution-only; observed Chunnel/VCR facts are never predictor inputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
