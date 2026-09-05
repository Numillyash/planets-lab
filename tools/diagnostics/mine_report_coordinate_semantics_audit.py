from __future__ import annotations

import re
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
TARGET_GAME = 511506
TARGET_TURN = 23
TARGET_SHIP = 160

SHIP_ID_RE = re.compile(r"#\s*(?P<ship>\d+)", re.IGNORECASE)
DAMAGE_RE = re.compile(r"Damage is at:\s*(?P<damage>\d+)", re.IGNORECASE)


def _load_rows() -> list[dict[str, Any]]:
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
            "mine_category",
            "mine_damage_hits",
            "mine_slowdown_hits",
        ]
        rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM movement_labeled_residual
            WHERE mine_strong_explained = true
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in rows]


def _critical_mine_excerpt(message: Mapping[str, Any], *, ship_id: int) -> dict[str, Any] | None:
    messagetype = message.get("messagetype")
    target = message.get("target")
    try:
        messagetype_int = int(messagetype) if messagetype is not None else None
    except (TypeError, ValueError):
        messagetype_int = None
    try:
        target_int = int(target) if target is not None else None
    except (TypeError, ValueError):
        target_int = None

    body = message.get("body") if isinstance(message.get("body"), str) else ""
    body_lower = body.lower()
    is_mine_phrase = "mine" in body_lower and (
        "struck" in body_lower or "hit" in body_lower
    )
    ship_match = SHIP_ID_RE.search(body)
    body_ship = int(ship_match.group("ship")) if ship_match else None
    damage_match = DAMAGE_RE.search(body)
    reported_damage = int(damage_match.group("damage")) if damage_match else None

    if messagetype_int != 16:
        return None
    if target_int != ship_id and body_ship != ship_id:
        return None
    if not is_mine_phrase:
        return None

    def intish(value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "message_id": intish(message.get("id")),
        "messagetype": messagetype_int,
        "target": target_int,
        "event_x": intish(message.get("x")),
        "event_y": intish(message.get("y")),
        "reported_ship_id": body_ship,
        "reported_damage": reported_damage,
        "body_has_web_token": "web" in body_lower,
        "body_length": len(body),
    }


def _route_metrics(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    point: tuple[int, int],
    topology: Any,
) -> dict[str, float] | None:
    tx, ty = _vector(origin, target, topology)
    px, py = _vector(origin, point, topology)
    route_length = hypot(tx, ty)
    if route_length <= 1e-9:
        return None
    ux, uy = tx / route_length, ty / route_length
    progress = px * ux + py * uy
    cross_track = abs(px * uy - py * ux)
    return {
        "distance_from_origin": hypot(px, py),
        "route_progress": progress,
        "cross_track": cross_track,
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    rows = _load_rows()
    print("===== MINE REPORT COORDINATE SEMANTICS AUDIT =====")
    print("production_mine_strong_rows=", len(rows))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals = Counter()
    category_counts = Counter()
    normal_report_leg_buckets = Counter()
    target_example: dict[str, Any] | None = None
    normal_examples: list[dict[str, Any]] = []

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
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        raw_payload_cache: dict[tuple[int, int], Mapping[str, Any]] = {}

        for row in by_game[game_id]:
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            category = str(row["mine_category"] or "unknown")
            category_counts[category] += 1

            owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            if owner_id is None or owner is None:
                totals["owner_missing"] += 1
                continue
            totals["owner_ready"] += 1

            key = (after_turn, owner_id)
            if key not in raw_payload_cache:
                raw_payload_cache[key] = _raw_turn_payload(
                    archive_data,
                    turn=after_turn,
                    player_id=owner_id,
                )
            payload = raw_payload_cache[key]
            reports = [
                excerpt
                for message in _messages(payload)
                if (excerpt := _critical_mine_excerpt(message, ship_id=ship_id)) is not None
            ]

            if not reports:
                totals["no_matching_mine_report"] += 1
                continue
            totals["rows_with_mine_report"] += 1
            if len(reports) > 1:
                totals["rows_with_multiple_reports"] += 1
            totals["matching_report_rows"] += len(reports)

            origin = (int(row["x_before"]), int(row["y_before"]))
            observed = (int(row["x_after"]), int(row["y_after"]))
            target = (int(row["target_x"]), int(row["target_y"]))
            observed_vector = _vector(origin, observed, topology)
            observed_distance = hypot(*observed_vector)
            target_vector = _vector(origin, target, topology)
            target_distance = hypot(*target_vector)
            nominal = float(row["nominal_max_distance"] or 0.0)
            regular_distance = min(target_distance, nominal)

            per_row_reports: list[dict[str, Any]] = []
            for report in reports:
                event_x = report.get("event_x")
                event_y = report.get("event_y")
                event_metrics = None
                event_to_observed = None
                on_submitted_route = False
                before_or_at_observed = False
                if isinstance(event_x, int) and isinstance(event_y, int):
                    event = (event_x, event_y)
                    event_metrics = _route_metrics(
                        origin=origin,
                        target=target,
                        point=event,
                        topology=topology,
                    )
                    ex, ey = _vector(event, observed, topology)
                    event_to_observed = hypot(ex, ey)
                    if event_metrics is not None:
                        on_submitted_route = (
                            event_metrics["cross_track"] <= 1.5
                            and -1.5 <= event_metrics["route_progress"] <= regular_distance + 1.5
                        )
                        before_or_at_observed = (
                            on_submitted_route
                            and event_metrics["route_progress"] <= observed_distance + 1.5
                        )

                if event_metrics is None:
                    totals["report_without_coordinates"] += 1
                else:
                    totals["report_with_coordinates"] += 1
                    if on_submitted_route:
                        totals["report_on_submitted_route"] += 1
                    else:
                        totals["report_off_submitted_route"] += 1
                    if before_or_at_observed:
                        totals["report_before_or_at_observed"] += 1
                    else:
                        totals["report_after_observed_or_offroute"] += 1

                is_normal = category.startswith("normal_mine")
                is_web = category.startswith("web_mine")
                if is_normal:
                    totals["normal_report_rows"] += 1
                    if event_metrics is not None and on_submitted_route:
                        totals["normal_report_on_route"] += 1
                    if event_metrics is not None and before_or_at_observed:
                        totals["normal_report_before_or_at_observed"] += 1
                    if event_to_observed is not None:
                        if event_to_observed <= 1.5:
                            normal_report_leg_buckets["<=1.5"] += 1
                        elif event_to_observed <= 10.5:
                            normal_report_leg_buckets["1.5-10.5"] += 1
                        elif event_to_observed <= 20.5:
                            normal_report_leg_buckets["10.5-20.5"] += 1
                        else:
                            normal_report_leg_buckets[">20.5"] += 1
                elif is_web:
                    totals["web_report_rows"] += 1
                    if event_to_observed is not None and event_to_observed <= 1.5:
                        totals["web_report_at_observed"] += 1

                safe = {
                    "game_id": game_id,
                    "before_turn": before_turn,
                    "ship_id": ship_id,
                    "mine_category": category,
                    "mine_damage_hits": row["mine_damage_hits"],
                    "mine_slowdown_hits": row["mine_slowdown_hits"],
                    "observed_distance": round(observed_distance, 3),
                    "regular_distance": round(regular_distance, 3),
                    "lost_distance": round(regular_distance - observed_distance, 3),
                    "event_x": event_x,
                    "event_y": event_y,
                    "reported_damage": report.get("reported_damage"),
                    "body_has_web_token": report.get("body_has_web_token"),
                    "event_route_progress": round(event_metrics["route_progress"], 3) if event_metrics else None,
                    "event_cross_track": round(event_metrics["cross_track"], 3) if event_metrics else None,
                    "event_to_observed_distance": round(event_to_observed, 3) if event_to_observed is not None else None,
                    "event_on_submitted_route": on_submitted_route,
                    "event_before_or_at_observed": before_or_at_observed,
                }
                per_row_reports.append(safe)

                if is_normal and len(normal_examples) < 20:
                    normal_examples.append(safe)
                if (
                    game_id == TARGET_GAME
                    and before_turn == TARGET_TURN
                    and ship_id == TARGET_SHIP
                ):
                    target_example = safe

    print("\n===== CATEGORY COUNTS =====")
    print(dict(sorted(category_counts.items())))

    print("\n===== COORDINATE SEMANTICS SUMMARY =====")
    for key in (
        "owner_ready",
        "rows_with_mine_report",
        "no_matching_mine_report",
        "rows_with_multiple_reports",
        "matching_report_rows",
        "report_with_coordinates",
        "report_without_coordinates",
        "report_on_submitted_route",
        "report_off_submitted_route",
        "report_before_or_at_observed",
        "report_after_observed_or_offroute",
        "normal_report_rows",
        "normal_report_on_route",
        "normal_report_before_or_at_observed",
        "web_report_rows",
        "web_report_at_observed",
    ):
        print(f"{key}=", totals[key])
    print("normal_event_to_observed_buckets=", dict(sorted(normal_report_leg_buckets.items())))

    print("\n===== NORMAL REPORT EXAMPLES =====")
    for example in normal_examples:
        print(example)

    print("\n===== TARGET CASE =====")
    print(target_example)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic validates the semantics of critical mine-report x/y using only transitions already "
        "production-labeled mine_strong_explained. Raw message body text is never printed. A coordinate is treated "
        "as impact-position evidence only if independent known mine cases place it consistently on the submitted "
        "route at or before the observed endpoint. The target 511506/T23/ship160 remains outside the production "
        "mine label population and is shown only if it is encountered indirectly; no label/accounting change is made."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
