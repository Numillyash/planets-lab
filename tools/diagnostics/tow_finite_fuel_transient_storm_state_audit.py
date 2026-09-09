from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from planets_lab.corpus.movement_context import (
    MOVE_MOST_CANDIDATE,
    MovementMissionConvention,
    _classify_owner_record,
)
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _resolved_value,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _navigation_endpoint,
    _owner_record,
    _storm_clusters,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.readiness import READY
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.ion_storm import (
    CLASS_4_MIN_VOLTAGE,
    IonStormCircle,
    integer_drag_delta,
    local_voltage,
    translated_circle,
)
from planets_lab.validation.movement_geometry import MovementSample

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from tow_finite_fuel_residual_shape_audit import _parse_clean_cases, _xy


EXAMPLE_LIMIT = 100
CONTROL_EXAMPLE_LIMIT = 40


def _circle(record: Any) -> IonStormCircle:
    return IonStormCircle(
        id=int(record.id),
        x=float(record.x),
        y=float(record.y),
        radius=float(record.radius),
        voltage=float(record.voltage),
        warp=int(record.warp),
        heading=float(record.heading),
        parent_id=int(record.parent_id),
    )


def _cluster_map(storms: Sequence[Any]) -> dict[int, tuple[Any, tuple[Any, ...]]]:
    return {int(root.id): (root, tuple(circles)) for root, circles in _storm_clusters(storms)}


def _hybrid_circle(
    *,
    position: IonStormCircle,
    strength: Any,
) -> IonStormCircle:
    return IonStormCircle(
        id=int(strength.id),
        x=float(position.x),
        y=float(position.y),
        radius=float(strength.radius),
        voltage=float(strength.voltage),
        warp=int(strength.warp),
        heading=float(strength.heading),
        parent_id=int(strength.parent_id),
    )


def _membership_variants(
    *,
    before_cluster: tuple[Any, tuple[Any, ...]] | None,
    after_cluster: tuple[Any, tuple[Any, ...]],
) -> tuple[dict[str, tuple[IonStormCircle, ...]], dict[str, Any]]:
    after_root, after_records = after_cluster
    variants: dict[str, tuple[IonStormCircle, ...]] = {
        "after_raw": tuple(_circle(item) for item in after_records),
    }
    meta: dict[str, Any] = {
        "root_id": int(after_root.id),
        "stable_root_pair": before_cluster is not None,
        "stable_cluster_id_set": False,
    }
    if before_cluster is None:
        return variants, meta

    _, before_records = before_cluster
    before_circles = tuple(_circle(item) for item in before_records)
    translated_before = tuple(translated_circle(item) for item in before_circles)
    variants["before_raw"] = before_circles
    variants["before_translated_before_strength"] = translated_before

    before_by_id = {int(item.id): item for item in before_records}
    after_by_id = {int(item.id): item for item in after_records}
    if set(before_by_id) != set(after_by_id):
        return variants, meta

    meta["stable_cluster_id_set"] = True
    translated_by_id = {int(item.id): item for item in translated_before}
    variants["before_translated_after_strength"] = tuple(
        _hybrid_circle(position=translated_by_id[item_id], strength=after_by_id[item_id])
        for item_id in sorted(after_by_id)
    )
    variants["after_coords_before_strength"] = tuple(
        _hybrid_circle(position=_circle(after_by_id[item_id]), strength=before_by_id[item_id])
        for item_id in sorted(after_by_id)
    )
    return variants, meta


def _after_root_vector_matches(
    storms: Sequence[Any],
    residual: tuple[int, int],
) -> tuple[int, ...]:
    return tuple(
        int(root.id)
        for root, _ in _storm_clusters(storms)
        if integer_drag_delta(int(root.warp), float(root.heading)) == residual
    )


def _variant_membership(
    *,
    root_ids: Sequence[int],
    before_storms: Sequence[Any],
    after_storms: Sequence[Any],
    origin: tuple[int, int],
    geometry: tuple[int, int],
) -> tuple[dict[str, bool], tuple[dict[str, Any], ...], dict[str, int]]:
    before_map = _cluster_map(before_storms)
    after_map = _cluster_map(after_storms)
    row_hits: dict[str, bool] = {}
    witnesses: list[dict[str, Any]] = []
    meta_counts = Counter()

    for root_id in root_ids:
        after_cluster = after_map.get(int(root_id))
        if after_cluster is None:
            continue
        variants, meta = _membership_variants(
            before_cluster=before_map.get(int(root_id)),
            after_cluster=after_cluster,
        )
        if meta["stable_root_pair"]:
            meta_counts["stable_root_pair"] += 1
        if meta["stable_cluster_id_set"]:
            meta_counts["stable_cluster_id_set"] += 1

        for variant, circles in variants.items():
            for point_name, point in (("origin", origin), ("geometry", geometry)):
                voltage = float(local_voltage(circles, *point))
                key = f"{variant}_{point_name}"
                if voltage >= CLASS_4_MIN_VOLTAGE:
                    row_hits[key] = True
                    witnesses.append(
                        {
                            "root_id": int(root_id),
                            "variant": variant,
                            "point": point_name,
                            "voltage": round(voltage, 3),
                        }
                    )
                else:
                    row_hits.setdefault(key, False)

    return row_hits, tuple(witnesses), dict(meta_counts)


def _sample_from_transition(
    transition: Any,
    entities: Mapping[tuple[str, int, int], Any],
) -> MovementSample | None:
    before = entities.get(("ship", transition.before_archive_turn, transition.entity_id))
    after = entities.get(("ship", transition.after_archive_turn, transition.entity_id))
    if before is None or after is None:
        return None

    values = {
        "x": _intish(_resolved_value(before, "x")),
        "y": _intish(_resolved_value(before, "y")),
        "target_x": _intish(_resolved_value(before, "targetx")),
        "target_y": _intish(_resolved_value(before, "targety")),
        "warp": _intish(_resolved_value(before, "warp")),
        "next_x": _intish(_resolved_value(after, "x")),
        "next_y": _intish(_resolved_value(after, "y")),
        "hull_id": _intish(_resolved_value(before, "hullid")),
    }
    if any(values[key] is None for key in ("x", "y", "target_x", "target_y", "warp", "next_x", "next_y")):
        return None
    hull_id = values["hull_id"]
    return MovementSample(
        turn=int(transition.before_embedded_turn),
        ship_id=int(transition.entity_id),
        x=int(values["x"]),
        y=int(values["y"]),
        target_x=int(values["target_x"]),
        target_y=int(values["target_y"]),
        warp=int(values["warp"]),
        next_x=int(values["next_x"]),
        next_y=int(values["next_y"]),
        hull_id=int(hull_id) if hull_id is not None else None,
        gravitonic=(int(hull_id) in GRAVITONIC_HULL_IDS) if hull_id is not None else False,
    )


def _single_current_active_root(
    storms: Sequence[Any],
    *,
    origin: tuple[int, int],
) -> int | None:
    effective_x, effective_y = origin
    active: list[int] = []
    for root, circles in _storm_clusters(storms):
        voltage = float(local_voltage(tuple(_circle(item) for item in circles), effective_x, effective_y))
        if voltage < CLASS_4_MIN_VOLTAGE:
            continue
        if voltage >= 400.0:
            return None
        dx, dy = integer_drag_delta(int(root.warp), float(root.heading))
        effective_x += dx
        effective_y += dy
        active.append(int(root.id))
    return active[0] if len(active) == 1 else None


def _ordinary_direct_controls(
    *,
    game_id: int,
    prepared: Any,
    storms_by_turn: Mapping[int, Sequence[Any]],
    storm_conflicts: frozenset[int],
    storm_invalid: frozenset[int],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    entities = _entity_map(prepared.snapshots)
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    convention = MovementMissionConvention()
    controls: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for transition in prepared.movement_geometry_readiness.results:
        if transition.status != READY:
            continue
        owner_id, owner = _owner_record(ship_groups.get((transition.before_archive_turn, transition.entity_id), ()))
        if owner_id is None or owner is None:
            continue
        if _classify_owner_record(owner, convention=convention) != MOVE_MOST_CANDIDATE:
            continue
        after_turn = int(transition.after_archive_turn)
        before_turn = int(transition.before_archive_turn)
        if after_turn in storm_conflicts or after_turn in storm_invalid:
            continue
        sample = _sample_from_transition(transition, entities)
        if sample is None:
            continue
        after_storms = storms_by_turn.get(after_turn, ())
        if not after_storms:
            continue
        category, _ = _storm_expected_category(
            sample,
            storms=after_storms,
            planets=planets_by_turn.get(before_turn, ()),
        )
        if category != "ion_storm_drag":
            continue

        counts["ordinary_direct_classifier_rows"] += 1
        origin = (sample.x, sample.y)
        geometry = _navigation_endpoint(sample)
        observed = sample.observed_destination
        residual = (observed[0] - geometry[0], observed[1] - geometry[1])
        active_root = _single_current_active_root(after_storms, origin=origin)
        if active_root is None:
            counts["ordinary_control_not_single_active_root"] += 1
            continue
        after_map = _cluster_map(after_storms)
        root = after_map[active_root][0]
        if integer_drag_delta(int(root.warp), float(root.heading)) != residual:
            counts["ordinary_control_single_root_vector_mismatch"] += 1
            continue

        counts["ordinary_single_root_direct_controls"] += 1
        before_storms = storms_by_turn.get(before_turn, ())
        hits, witnesses, meta = _variant_membership(
            root_ids=(active_root,),
            before_storms=before_storms,
            after_storms=after_storms,
            origin=origin,
            geometry=geometry,
        )
        controls.append(
            {
                "game": game_id,
                "turn": before_turn,
                "after_turn": after_turn,
                "ship": int(sample.ship_id),
                "root_id": active_root,
                "origin": origin,
                "geometry": geometry,
                "observed": observed,
                "residual": residual,
                "hits": hits,
                "witnesses": witnesses,
                "meta": meta,
            }
        )
    return controls, counts


def _record_hit_counters(prefix: str, hits: Mapping[str, bool], totals: Counter[str]) -> None:
    any_origin = False
    any_geometry = False
    any_transient_origin = False
    any_transient_geometry = False
    for key, hit in hits.items():
        if not hit:
            continue
        totals[f"{prefix}_{key}_qualifies"] += 1
        if key.endswith("_origin"):
            any_origin = True
            if not key.startswith("after_raw_") and not key.startswith("before_raw_"):
                any_transient_origin = True
        if key.endswith("_geometry"):
            any_geometry = True
            if not key.startswith("after_raw_") and not key.startswith("before_raw_"):
                any_transient_geometry = True
    if any_origin:
        totals[f"{prefix}_any_origin_qualifies"] += 1
    if any_geometry:
        totals[f"{prefix}_any_geometry_qualifies"] += 1
    if any_transient_origin:
        totals[f"{prefix}_any_transient_origin_qualifies"] += 1
    if any_transient_geometry:
        totals[f"{prefix}_any_transient_geometry_qualifies"] += 1
    if any_transient_origin or any_transient_geometry:
        totals[f"{prefix}_any_transient_causal_point_qualifies"] += 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Test bounded transient ion-storm membership states for the clean finite-fuel Tow rows "
            "whose residual exactly equals an after-turn root-storm drag vector. The same candidate "
            "states are evaluated on ordinary non-Tow direct storm controls. Evidence mining only."
        )
    )
    parser.add_argument("--external-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    parser.add_argument("--control-examples", type=int, default=CONTROL_EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0 or args.control_examples < 0:
        raise SystemExit("example limits must be non-negative")

    expected, clean_cases = _parse_clean_cases(args.external_log)
    tow_by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in clean_cases:
        tow_by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter()
    totals["clean_residual_input"] = expected
    tow_examples: list[dict[str, Any]] = []
    control_examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW TRANSIENT STORM-STATE AUDIT =====")
    print("external_log=", args.external_log)
    print("clean_residual_input=", expected)

    archive_paths = sorted(RAW_DIR.glob("game-*.zip"), key=lambda path: int(path.stem.split("-")[-1]))
    if not archive_paths:
        raise FileNotFoundError(f"No historical archives under {RAW_DIR}")

    for archive_path in archive_paths:
        game_id = int(archive_path.stem.split("-")[-1])
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        game_counts: Counter[str] = Counter()

        for case in tow_by_game.get(game_id, ()):
            before_turn = int(case["turn"])
            after_turn = int(case["after_turn"])
            origin = _xy(case["origin"], "origin")
            geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")
            observed = _xy(case["observed"], "observed")
            residual = (observed[0] - geometry[0], observed[1] - geometry[1])
            totals["tow_clean_cases"] += 1
            game_counts["tow_clean_cases"] += 1

            if before_turn in storm_conflicts or before_turn in storm_invalid:
                totals["tow_before_storm_context_unusable"] += 1
                continue
            if after_turn in storm_conflicts or after_turn in storm_invalid:
                totals["tow_after_storm_context_unusable"] += 1
                continue
            before_storms = storms_by_turn.get(before_turn, ())
            after_storms = storms_by_turn.get(after_turn, ())
            root_ids = _after_root_vector_matches(after_storms, residual)
            if not root_ids:
                totals["tow_no_after_root_vector_match"] += 1
                game_counts["tow_no_after_root_vector_match"] += 1
                continue

            totals["tow_after_root_vector_rows"] += 1
            game_counts["tow_after_root_vector_rows"] += 1
            totals["tow_after_root_vector_matches"] += len(root_ids)
            if len(root_ids) > 1:
                totals["tow_after_root_vector_ambiguous_rows"] += 1

            hits, witnesses, meta = _variant_membership(
                root_ids=root_ids,
                before_storms=before_storms,
                after_storms=after_storms,
                origin=origin,
                geometry=geometry,
            )
            if meta.get("stable_root_pair", 0):
                totals["tow_rows_with_stable_root_pair"] += 1
            if meta.get("stable_cluster_id_set", 0):
                totals["tow_rows_with_stable_cluster_id_set"] += 1
            _record_hit_counters("tow", hits, totals)

            if len(tow_examples) < args.examples:
                tow_examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "tower_ship": int(case["tower_ship"]),
                        "target_ship": int(case["target_ship"]),
                        "root_ids": root_ids,
                        "origin": origin,
                        "geometry": geometry,
                        "observed": observed,
                        "residual": residual,
                        "hits": {key: value for key, value in sorted(hits.items()) if value},
                        "witnesses": witnesses,
                        "meta": meta,
                    }
                )

        controls, control_counts = _ordinary_direct_controls(
            game_id=game_id,
            prepared=prepared,
            storms_by_turn=storms_by_turn,
            storm_conflicts=storm_conflicts,
            storm_invalid=storm_invalid,
        )
        totals.update(control_counts)
        game_counts.update(control_counts)
        for control in controls:
            hits = control["hits"]
            _record_hit_counters("control", hits, totals)
            if len(control_examples) < args.control_examples:
                control_examples.append(control)

        if game_counts:
            print({"game": game_id, "cache_hit": cache_hit, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["tow_clean_cases"] != totals["clean_residual_input"]:
        raise AssertionError(
            f"Tow case accounting mismatch: input={totals['clean_residual_input']} cases={totals['tow_clean_cases']}"
        )
    if totals["tow_after_root_vector_rows"] + totals["tow_no_after_root_vector_match"] != totals["tow_clean_cases"]:
        raise AssertionError("Tow after-root vector accounting mismatch")
    if totals["ordinary_single_root_direct_controls"] != len(
        [item for item in control_examples]
    ) and totals["ordinary_single_root_direct_controls"] < len(control_examples):
        raise AssertionError("ordinary control example accounting impossible")

    print("\n===== SUMMARY =====")
    primary_keys = (
        "clean_residual_input",
        "tow_clean_cases",
        "tow_after_root_vector_rows",
        "tow_no_after_root_vector_match",
        "tow_after_root_vector_matches",
        "tow_after_root_vector_ambiguous_rows",
        "tow_rows_with_stable_root_pair",
        "tow_rows_with_stable_cluster_id_set",
        "tow_any_transient_origin_qualifies",
        "tow_any_transient_geometry_qualifies",
        "tow_any_transient_causal_point_qualifies",
        "ordinary_direct_classifier_rows",
        "ordinary_control_not_single_active_root",
        "ordinary_control_single_root_vector_mismatch",
        "ordinary_single_root_direct_controls",
        "control_after_raw_origin_qualifies",
        "control_any_transient_origin_qualifies",
        "control_any_transient_geometry_qualifies",
        "control_any_transient_causal_point_qualifies",
    )
    for key in primary_keys:
        print(f"{key}= {totals[key]}")

    print("\n===== TOW VARIANT COUNTERS =====")
    for key, value in sorted(totals.items()):
        if key.startswith("tow_") and key.endswith("_qualifies") and key not in primary_keys:
            print(f"{key}= {value}")

    print("\n===== ORDINARY CONTROL VARIANT COUNTERS =====")
    for key, value in sorted(totals.items()):
        if key.startswith("control_") and key.endswith("_qualifies") and key not in primary_keys:
            print(f"{key}= {value}")

    print("\n===== TOW EXAMPLES =====")
    for item in tow_examples:
        print(item)

    print("\n===== ORDINARY CONTROL EXAMPLES =====")
    for item in control_examples:
        print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "The Tow input is restricted to clean residuals and only rows whose displacement exactly equals an after-turn root-storm drag vector. "
        "A class-4 hit under a transient membership variant is a Host-order lead, not promotion."
    )
    print(
        "Ordinary controls are non-Tow Move Most transitions already reproduced as direct ion_storm_drag by the current classifier and narrowed "
        "to one active after-turn root whose vector exactly equals the factual displacement. A candidate transient state that harms these controls "
        "must not replace the generic storm classifier."
    )
    print(
        "The factual observed endpoint is not used to establish transient storm membership; causal membership counters use only origin and direct navigation geometry."
    )
    print("finite-fuel Tow remains OPEN; no simulator or planets-intel rule changes are made here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
