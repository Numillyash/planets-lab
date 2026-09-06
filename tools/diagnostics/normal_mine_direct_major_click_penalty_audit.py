from __future__ import annotations

from collections import Counter, defaultdict
from math import floor, hypot
from typing import Any, Mapping

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache

from normal_mine_click_accounting_cross_case_audit import (
    PREPARED_DIR,
    RAW_DIR,
    TARGET_AFTER_TURN,
    TARGET_BEFORE_TURN,
    TARGET_GAME,
    TARGET_SHIP,
    _effective_sample,
    _load_production_rows,
    _load_target_row,
    _sample_from_row,
)
from normal_mine_single_candidate_step_state_warpwell_audit import (
    _click_for_point,
    _major_axis_clicks,
)


def _regular_major_click(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    regular_distance: float,
) -> int | None:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    major = max(abs(dx), abs(dy))
    route_distance = hypot(dx, dy)
    if major <= 0 or route_distance <= 1e-9:
        return None
    if regular_distance >= route_distance - 1e-9:
        return major
    click = floor(regular_distance * major / route_distance + 0.5)
    return max(0, min(major, click))


def _point_for_click(
    clicks: list[tuple[int, tuple[int, int]]],
    click: int,
) -> tuple[int, int] | None:
    matches = [point for index, point in clicks if index == click]
    if len(matches) != 1:
        return None
    return matches[0]


def _analyze(row: Mapping[str, Any], *, topology: Any, label: str) -> dict[str, Any]:
    sample = _effective_sample(_sample_from_row(dict(row)), topology=topology)
    origin = (sample.x, sample.y)
    target = (sample.target_x, sample.target_y)
    observed = sample.observed_destination
    slowdown_hits = int(row.get("mine_slowdown_hits") or 0)

    target_vector = _vector(origin, target, topology)
    observed_vector = _vector(origin, observed, topology)
    target_distance = hypot(*target_vector)
    observed_distance = hypot(*observed_vector)
    nominal_distance = float(row.get("nominal_max_distance") or 0.0)
    regular_distance = min(target_distance, nominal_distance)
    scalar_expected_loss = 10.0 * slowdown_hits
    scalar_loss = regular_distance - observed_distance

    item: dict[str, Any] = {
        "label": label,
        "game_id": int(row["game_id"]),
        "before_turn": int(row["before_archive_turn"]),
        "ship_id": int(row["ship_id"]),
        "hull_id": row.get("hull_id"),
        "warp": int(row["warp"]),
        "mine_damage_hits": int(row.get("mine_damage_hits") or 0),
        "mine_slowdown_hits": slowdown_hits,
        "origin": origin,
        "target": target,
        "observed": observed,
        "regular_distance": round(regular_distance, 6),
        "observed_distance": round(observed_distance, 6),
        "scalar_loss": round(scalar_loss, 6),
        "scalar_minus10_error": round(scalar_loss - scalar_expected_loss, 6),
        "scalar_minus10_within_1_5": abs(scalar_loss - scalar_expected_loss) <= 1.5,
        "sphere_topology": topology.sphere is True,
    }

    # The direct major-axis hypothesis is meaningful only on the ordinary planar
    # route representation used by the validated classic Host stepping helper.
    if topology.sphere is True:
        item.update(
            {
                "click_status": "sphere_skipped",
                "regular_click": None,
                "observed_click": None,
                "observed_click_loss": None,
                "direct_expected_click_loss": None,
                "direct_expected_click": None,
                "direct_expected_endpoint": None,
                "direct_click_loss_delta": None,
                "direct_major_click_loss_exact": False,
                "direct_major_click_loss_within_1": False,
                "direct_major_click_endpoint_exact": False,
            }
        )
        return item

    clicks = _major_axis_clicks(origin=origin, target=target)
    regular_click = _regular_major_click(
        origin=origin,
        target=target,
        regular_distance=regular_distance,
    )
    observed_click = _click_for_point(clicks, observed)
    expected_click_loss = 10 * slowdown_hits
    direct_expected_click = (
        max(0, regular_click - expected_click_loss)
        if regular_click is not None
        else None
    )
    direct_expected_endpoint = (
        _point_for_click(clicks, direct_expected_click)
        if direct_expected_click is not None
        else None
    )
    observed_click_loss = (
        regular_click - observed_click
        if regular_click is not None and observed_click is not None
        else None
    )
    delta = (
        observed_click_loss - expected_click_loss
        if observed_click_loss is not None
        else None
    )

    item.update(
        {
            "click_status": "resolved" if delta is not None else "unresolved",
            "regular_click": regular_click,
            "observed_click": observed_click,
            "observed_click_loss": observed_click_loss,
            "direct_expected_click_loss": expected_click_loss,
            "direct_expected_click": direct_expected_click,
            "direct_expected_endpoint": direct_expected_endpoint,
            "direct_click_loss_delta": delta,
            "direct_major_click_loss_exact": delta == 0,
            "direct_major_click_loss_within_1": delta is not None and abs(delta) <= 1,
            "direct_major_click_endpoint_exact": direct_expected_endpoint == observed,
        }
    )
    return item


def main() -> int:
    production = _load_production_rows()
    print("===== NORMAL-MINE DIRECT MAJOR-CLICK PENALTY AUDIT =====")
    print("production_normal_rows=", len(production))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in production:
        by_game[int(row["game_id"])].append(row)

    analyzed: list[dict[str, Any]] = []
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
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")
        for row in by_game[game_id]:
            analyzed.append(_analyze(row, topology=topology, label="PRODUCTION"))

    target_row = dict(_load_target_row())
    target_row.setdefault("game_id", TARGET_GAME)
    target_row.setdefault("before_archive_turn", TARGET_BEFORE_TURN)
    target_row.setdefault("after_archive_turn", TARGET_AFTER_TURN)
    target_row.setdefault("before_embedded_turn", TARGET_BEFORE_TURN)
    target_row.setdefault("ship_id", TARGET_SHIP)
    target_row.setdefault("mine_damage_hits", 1)
    target_row.setdefault("mine_slowdown_hits", 1)
    target_archive = (RAW_DIR / f"game-{TARGET_GAME}.zip").read_bytes()
    target_prepared, target_cache_hit = load_or_build_prepared_game_cache(
        target_archive,
        game_id=TARGET_GAME,
        cache_path=PREPARED_DIR / f"game-{TARGET_GAME}.pickle",
    )
    target_topology = effective_sphere_topology(
        game_id=TARGET_GAME,
        topology=extract_map_topology(target_archive),
    )
    target = _analyze(target_row, topology=target_topology, label="TARGET")

    totals: Counter[str] = Counter()
    deltas: list[int] = []
    for item in analyzed:
        if item["scalar_minus10_within_1_5"]:
            totals["scalar_minus10_within_1_5"] += 1
        if item["click_status"] == "sphere_skipped":
            totals["sphere_skipped"] += 1
            continue
        if item["click_status"] != "resolved":
            totals["click_unresolved"] += 1
            continue
        totals["click_resolved"] += 1
        delta = int(item["direct_click_loss_delta"])
        deltas.append(delta)
        if item["direct_major_click_loss_exact"]:
            totals["direct_major_click_loss_exact"] += 1
        if item["direct_major_click_loss_within_1"]:
            totals["direct_major_click_loss_within_1"] += 1
        if item["direct_major_click_endpoint_exact"]:
            totals["direct_major_click_endpoint_exact"] += 1

    print("\n===== PRODUCTION SUMMARY =====")
    print("scalar_minus10_within_1_5=", totals["scalar_minus10_within_1_5"])
    print("sphere_skipped=", totals["sphere_skipped"])
    print("click_unresolved=", totals["click_unresolved"])
    print("click_resolved=", totals["click_resolved"])
    print("direct_major_click_loss_exact=", totals["direct_major_click_loss_exact"])
    print("direct_major_click_loss_within_1=", totals["direct_major_click_loss_within_1"])
    print("direct_major_click_endpoint_exact=", totals["direct_major_click_endpoint_exact"])
    print("direct_click_loss_delta_values=", sorted(deltas))

    print("\n===== PRODUCTION ROWS =====")
    for item in analyzed:
        print(item)

    print("\n===== TARGET OUT-OF-SAMPLE =====")
    print("prepared_cache_hit=", target_cache_hit)
    print(target)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic tests a direct discrete hypothesis: each already-labeled normal-mine slowdown hit removes "
        "exactly 10 major-axis Host clicks from the regular movement budget. It uses the 19 production-closed normal-"
        "mine rows as controls and appends ship 160 only out-of-sample. Sphere-topology rows are skipped rather than "
        "forced through planar click geometry. A match would support a classifier refinement; it would not by itself "
        "prove internal NuHost implementation or relabel any residual row. No schemas, labels, or accounting change."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
