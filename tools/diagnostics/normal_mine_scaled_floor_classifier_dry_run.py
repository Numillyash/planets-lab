from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from normal_mine_reported_excess_shortening_residual_audit import DATABASE, _load_rows
from normal_mine_short_waypoint_scaled_penalty_audit import _residual_items


BASELINE_POST_FUEL_RESIDUAL = 2220


def _key_from_row(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(row["game_id"]),
        int(row["before_archive_turn"]),
        int(row["ship_id"]),
    )


def _key_from_item(item: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(item["game_id"]),
        int(item["before_turn"]),
        int(item["ship_id"]),
    )


def _active_explained_flags(row: dict[str, Any]) -> tuple[str, ...]:
    active: list[str] = []
    for key, value in row.items():
        if not str(key).endswith("_explained"):
            continue
        if value is True or value == 1:
            active.append(str(key))
    return tuple(sorted(active))


def _nonempty_labelish_values(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        name = str(key)
        lower = name.lower()
        if not (
            lower.endswith("_category")
            or "label" in lower
            or lower.endswith("_reason")
        ):
            continue
        if value is None or value is False or value == "":
            continue
        result[name] = value
    return dict(sorted(result.items()))


def _candidate_record(item: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    model = item["models"].get("scaled_floor", {})
    delta = model.get("delta_observed_minus_expected_loss")
    return {
        "game_id": int(item["game_id"]),
        "before_turn": int(item["before_turn"]),
        "ship_id": int(item["ship_id"]),
        "hull_id": item.get("hull_id"),
        "warp": int(item["warp"]),
        "short_waypoint": bool(item["short_waypoint"]),
        "nominal_distance": item["nominal_distance"],
        "regular_distance": item["regular_distance"],
        "scale_nominal_over_regular": item["scale_nominal_over_regular"],
        "observed_click_loss": item.get("observed_click_loss"),
        "scaled_floor_penalty": model.get("penalty_clicks"),
        "scaled_floor_delta": delta,
        "scaled_floor_endpoint_exact": model.get("endpoint_exact"),
        "scaled_floor_loss_within_1": model.get("loss_within_1"),
        "existing_explained_flags": _active_explained_flags(row) if row is not None else (),
        "existing_labelish_values": _nonempty_labelish_values(row) if row is not None else {},
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    source_rows = _load_rows()
    source_by_key = {_key_from_row(row): row for row in source_rows}

    print("===== NORMAL-MINE SCALED-FLOOR CLASSIFIER DRY RUN =====")
    print("source_post_fuel_residual_rows=", len(source_rows))
    print("baseline_expected_post_fuel_residual=", BASELINE_POST_FUEL_RESIDUAL)
    print("baseline_matches_source=", len(source_rows) == BASELINE_POST_FUEL_RESIDUAL)

    strict_items = _residual_items()
    print("strict_single_normal_report_rows=", len(strict_items))

    totals: Counter[str] = Counter()
    exact_items: list[dict[str, Any]] = []
    tolerance_only_items: list[dict[str, Any]] = []
    rejected_items: list[dict[str, Any]] = []
    missing_source_keys: list[tuple[int, int, int]] = []
    by_game_exact: Counter[int] = Counter()
    by_game_tolerance: Counter[int] = Counter()
    by_hull_tolerance: Counter[int] = Counter()
    tolerance_deltas: Counter[int] = Counter()

    for item in strict_items:
        totals["strict_rows"] += 1
        status = item.get("click_status")
        if status == "sphere_skipped":
            totals["sphere_skipped"] += 1
            rejected_items.append(item)
            continue
        if status != "resolved":
            totals["click_unresolved"] += 1
            rejected_items.append(item)
            continue

        totals["click_resolved"] += 1
        model = item.get("models", {}).get("scaled_floor")
        if not isinstance(model, dict):
            totals["scaled_floor_model_missing"] += 1
            rejected_items.append(item)
            continue

        delta = model.get("delta_observed_minus_expected_loss")
        if not isinstance(delta, int):
            totals["scaled_floor_delta_unavailable"] += 1
            rejected_items.append(item)
            continue
        tolerance_deltas[delta] += 1

        key = _key_from_item(item)
        row = source_by_key.get(key)
        if row is None:
            missing_source_keys.append(key)

        if model.get("endpoint_exact") is True and delta == 0:
            totals["exact_accept"] += 1
            exact_items.append(item)
            by_game_exact[int(item["game_id"])] += 1

        if abs(delta) <= 1:
            totals["tolerance_accept"] += 1
            by_game_tolerance[int(item["game_id"])] += 1
            hull_id = item.get("hull_id")
            if isinstance(hull_id, int):
                by_hull_tolerance[hull_id] += 1
            if not (model.get("endpoint_exact") is True and delta == 0):
                totals["tolerance_only_accept"] += 1
                tolerance_only_items.append(item)
        else:
            totals["scaled_floor_outside_band"] += 1
            rejected_items.append(item)

    exact_keys = {_key_from_item(item) for item in exact_items}
    tolerance_keys = {
        _key_from_item(item)
        for item in strict_items
        if item.get("click_status") == "resolved"
        and isinstance(item.get("models", {}).get("scaled_floor"), dict)
        and isinstance(item["models"]["scaled_floor"].get("delta_observed_minus_expected_loss"), int)
        and abs(int(item["models"]["scaled_floor"]["delta_observed_minus_expected_loss"])) <= 1
    }

    exact_overlap_flags = Counter()
    tolerance_overlap_flags = Counter()
    exact_nonempty_labelish = 0
    tolerance_nonempty_labelish = 0
    for key in exact_keys:
        row = source_by_key.get(key)
        if row is None:
            continue
        flags = _active_explained_flags(row)
        exact_overlap_flags.update(flags)
        if _nonempty_labelish_values(row):
            exact_nonempty_labelish += 1
    for key in tolerance_keys:
        row = source_by_key.get(key)
        if row is None:
            continue
        flags = _active_explained_flags(row)
        tolerance_overlap_flags.update(flags)
        if _nonempty_labelish_values(row):
            tolerance_nonempty_labelish += 1

    print("\n===== DRY-RUN SUMMARY =====")
    for key in (
        "strict_rows",
        "sphere_skipped",
        "click_unresolved",
        "click_resolved",
        "scaled_floor_model_missing",
        "scaled_floor_delta_unavailable",
        "exact_accept",
        "tolerance_only_accept",
        "tolerance_accept",
        "scaled_floor_outside_band",
    ):
        print(f"{key}=", totals[key])
    print("scaled_floor_delta_distribution=", dict(sorted(tolerance_deltas.items())))
    print("missing_source_key_count=", len(missing_source_keys))
    print("missing_source_keys=", missing_source_keys)

    print("\n===== PREDICTED ACCOUNTING (NO WRITE) =====")
    print("baseline_post_fuel_residual=", len(source_rows))
    print("exact_only_new_mine_rows=", len(exact_keys))
    print("exact_only_predicted_residual=", len(source_rows) - len(exact_keys))
    print("tolerance_new_mine_rows=", len(tolerance_keys))
    print("tolerance_predicted_residual=", len(source_rows) - len(tolerance_keys))
    print("note=These are dry-run counts only; no production rows are relabeled.")

    print("\n===== DISTRIBUTION =====")
    print("exact_by_game=", dict(sorted(by_game_exact.items())))
    print("tolerance_by_game=", dict(sorted(by_game_tolerance.items())))
    print("tolerance_by_hull=", dict(sorted(by_hull_tolerance.items())))

    print("\n===== EXISTING LABEL / OVERLAP CHECK =====")
    print("exact_active_explained_flags=", dict(sorted(exact_overlap_flags.items())))
    print("tolerance_active_explained_flags=", dict(sorted(tolerance_overlap_flags.items())))
    print("exact_rows_with_nonempty_labelish_values=", exact_nonempty_labelish)
    print("tolerance_rows_with_nonempty_labelish_values=", tolerance_nonempty_labelish)

    print("\n===== EXACT ACCEPT (DELTA 0 + ENDPOINT EXACT) =====")
    for item in exact_items:
        key = _key_from_item(item)
        print(_candidate_record(item, source_by_key.get(key)))

    print("\n===== TOLERANCE-ONLY ACCEPT (ABS DELTA <= 1, NOT EXACT) =====")
    for item in tolerance_only_items:
        key = _key_from_item(item)
        print(_candidate_record(item, source_by_key.get(key)))

    print("\n===== REJECTED STRICT ROWS =====")
    for item in rejected_items:
        model = item.get("models", {}).get("scaled_floor", {})
        print(
            {
                "game_id": item.get("game_id"),
                "before_turn": item.get("before_turn"),
                "ship_id": item.get("ship_id"),
                "hull_id": item.get("hull_id"),
                "click_status": item.get("click_status"),
                "sphere_topology": item.get("sphere_topology"),
                "scaled_floor_delta": model.get("delta_observed_minus_expected_loss") if isinstance(model, dict) else None,
                "scaled_floor_endpoint_exact": model.get("endpoint_exact") if isinstance(model, dict) else None,
            }
        )

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This is a dry-run classifier audit only. It applies the corpus-observed planar scaled-floor short-waypoint "
        "signature to the separately selected strict single-normal-report residual population. Exact acceptance "
        "requires both zero click-loss delta and exact endpoint; tolerance acceptance allows only the production-"
        "control band of +/-1 click. Sphere and unresolved rows fail closed. Existing *_explained flags and label-like "
        "fields are reported for overlap inspection. No production classifier, schemas, labels, database rows, or "
        "compiled-corpus accounting are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
