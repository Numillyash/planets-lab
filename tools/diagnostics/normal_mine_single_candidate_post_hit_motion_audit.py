from __future__ import annotations

import re
from math import hypot
from typing import Any, Mapping

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import _segment_intersects_field, build_mine_evidence_context, nearest_damage_quantum
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from damage_limited_warp_residual_audit import _max_warp_from_damage
from normal_mine_single_candidate_immunity_repair_audit import (
    BEFORE_TURN,
    DATABASE,
    EXPECTED_HULL,
    EXPECTED_OWNER,
    GAME_ID,
    PREPARED_DIR,
    RAW_DIR,
    SHIP_ID,
    _load_row,
    _planned_vector,
    _player_excerpt,
    _route_interval,
    _sample,
)


MINE_REPORT_RE = re.compile(
    r"#\s*(?P<ship>\d+)\s+has struck a mine!.*?Damage is at:\s*(?P<damage>\d+)",
    re.IGNORECASE | re.DOTALL,
)


def _raw_turn_payload(archive_data: bytes, *, turn: int, player_id: int) -> Mapping[str, Any]:
    members = [
        member for member in turn_members(archive_data)
        if member.turn == turn and member.player == player_id
    ]
    if len(members) != 1:
        raise SystemExit(
            f"expected exactly one raw member for turn={turn} player={player_id}; "
            f"found {[member.name for member in members]}"
        )
    member = members[0]
    raw_bytes = read_archive_members(archive_data, [member.name])[member.name]
    parsed, _ = _decode_member_json(raw_bytes, member)
    if not isinstance(parsed, Mapping):
        raise SystemExit(f"decoded raw member is not a mapping: {member.name}")
    return parsed


def _messages(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    direct = payload.get("messages")
    if isinstance(direct, list):
        return [item for item in direct if isinstance(item, Mapping)]
    rst = payload.get("rst")
    if isinstance(rst, Mapping):
        nested = rst.get("messages")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, Mapping)]
    return []


def _mine_report_excerpt(message: Mapping[str, Any], *, archive_turn: int) -> dict[str, Any] | None:
    messagetype = _intish(message.get("messagetype"))
    target = _intish(message.get("target"))
    body = message.get("body") if isinstance(message.get("body"), str) else ""
    match = MINE_REPORT_RE.search(body)
    reported_ship = int(match.group("ship")) if match else None
    reported_damage = int(match.group("damage")) if match else None
    mentions_mine_hit = "struck a mine" in body.lower()

    if messagetype != 16:
        return None
    if target != SHIP_ID and reported_ship != SHIP_ID:
        return None

    return {
        "archive_turn": archive_turn,
        "message_id": _intish(message.get("id")),
        "messagetype": messagetype,
        "target": target,
        "event_x": _intish(message.get("x")),
        "event_y": _intish(message.get("y")),
        "reported_ship_id": reported_ship,
        "reported_damage": reported_damage,
        "body_has_mine_hit_phrase": mentions_mine_hit,
        "body_length": len(body),
    }


def _route_metrics(
    *,
    origin: tuple[int, int],
    route_vector: tuple[float, float],
    point: tuple[int, int],
    topology: Any,
) -> dict[str, float] | None:
    route_length = hypot(*route_vector)
    if route_length <= 1e-9:
        return None
    px, py = _vector(origin, point, topology)
    ux = route_vector[0] / route_length
    uy = route_vector[1] / route_length
    progress = px * ux + py * uy
    cross = abs(px * uy - py * ux)
    return {
        "distance_from_origin": hypot(px, py),
        "route_progress": progress,
        "cross_track": cross,
    }


def _post_hit_warp_prediction(
    *,
    hit_point: tuple[int, int],
    target_point: tuple[int, int],
    warp: int,
    topology: Any,
) -> tuple[tuple[int, int], float]:
    tx, ty = _vector(hit_point, target_point, topology)
    synthetic_target = (hit_point[0] + int(tx), hit_point[1] + int(ty))
    sample = MovementSample(
        turn=BEFORE_TURN,
        ship_id=SHIP_ID,
        x=hit_point[0],
        y=hit_point[1],
        target_x=synthetic_target[0],
        target_y=synthetic_target[1],
        warp=warp,
        next_x=hit_point[0],
        next_y=hit_point[1],
        gravitonic=False,
        game_id=GAME_ID,
        hull_id=EXPECTED_HULL,
    )
    destination = host_major_minor_destination(sample)
    return destination, hypot(destination[0] - hit_point[0], destination[1] - hit_point[1])


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    row = _load_row()
    archive_path = RAW_DIR / f"game-{GAME_ID}.zip"
    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=GAME_ID,
        cache_path=PREPARED_DIR / f"game-{GAME_ID}.pickle",
    )
    context = build_mine_evidence_context(
        game_id=GAME_ID,
        archive_data=archive_data,
        snapshots=prepared.snapshots,
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")

    before_turn = int(row["before_archive_turn"])
    after_turn = int(row["after_archive_turn"])
    owner_id, owner = _owner_record(ship_groups.get((before_turn, SHIP_ID), ()))
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, SHIP_ID), ()))
    if owner_id != EXPECTED_OWNER or owner is None:
        raise SystemExit(f"owner guard failed: expected {EXPECTED_OWNER}, got {owner_id}")
    if after_owner_id != owner_id or after_owner is None:
        raise SystemExit("after-owner identity unavailable")

    hull_id = int(row["hull_id"]) if row["hull_id"] is not None else None
    if hull_id != EXPECTED_HULL:
        raise SystemExit(f"hull guard failed: expected {EXPECTED_HULL}, got {hull_id}")
    hull = context.specs.hulls.get(hull_id)
    if hull is None:
        raise SystemExit("missing hull spec")

    sample = _sample(row)
    raw_topology = extract_map_topology(archive_data)
    topology = effective_sphere_topology(game_id=GAME_ID, topology=raw_topology)
    effective_sample = sample
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        effective_sample = sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )

    planned_vector, planned_distance, target_distance = _planned_vector(
        effective_sample,
        float(row["nominal_max_distance"] or 0.0),
    )
    observed_vector = (
        float(effective_sample.next_x - effective_sample.x),
        float(effective_sample.next_y - effective_sample.y),
    )
    observed_distance = hypot(*observed_vector)
    origin = (effective_sample.x, effective_sample.y)
    observed_point = (effective_sample.next_x, effective_sample.next_y)
    target_point = (effective_sample.target_x, effective_sample.target_y)

    enemy_normal_fields = [
        field for field in context.fields(after_turn)
        if not field.is_web
        and field.owner_id is not None
        and field.owner_id > 0
        and field.owner_id != owner_id
    ]
    planned_fields = [
        field for field in enemy_normal_fields
        if _segment_intersects_field(
            origin=origin,
            vector=planned_vector,
            field_record=field,
            topology=topology,
        )
    ]

    before_payload = _raw_turn_payload(archive_data, turn=before_turn, player_id=owner_id)
    after_payload = _raw_turn_payload(archive_data, turn=after_turn, player_id=owner_id)
    before_player = _player_excerpt(before_payload.get("players"), owner_id)
    if before_player is None:
        before_player = _player_excerpt(
            before_payload.get("rst", {}).get("players") if isinstance(before_payload.get("rst"), Mapping) else None,
            owner_id,
        )
    race_id = before_player.get("raceid") if before_player is not None else None

    reports: list[dict[str, Any]] = []
    for turn, payload in ((before_turn, before_payload), (after_turn, after_payload)):
        for message in _messages(payload):
            excerpt = _mine_report_excerpt(message, archive_turn=turn)
            if excerpt is not None:
                reports.append(excerpt)

    before_raw = owner.raw
    after_raw = after_owner.raw
    before_damage = _intish(before_raw.get("damage"))
    before_supplies = _intish(before_raw.get("supplies"))
    after_damage = _intish(after_raw.get("damage"))
    after_supplies = _intish(after_raw.get("supplies"))
    quantum = nearest_damage_quantum(hull.mass, web=False)

    raw_one_hit_damage = (
        before_damage + quantum
        if before_damage is not None and quantum is not None
        else None
    )
    one_hit_damage_warp_limit = _max_warp_from_damage(raw_one_hit_damage, race_id)
    post_repair_warp_limit = _max_warp_from_damage(after_damage, race_id)

    print("===== NORMAL-MINE SINGLE CANDIDATE POST-HIT MOTION AUDIT =====")
    print("game=", GAME_ID)
    print("turn=", before_turn)
    print("ship=", SHIP_ID)
    print("prepared_cache_hit=", cache_hit)
    print("owner_id=", owner_id)
    print("owner_race_id=", race_id)
    print("hull_id=", hull_id)
    print("hull_tech=", hull.tech_level)
    print("hull_mass=", hull.mass)
    print("requested_warp=", sample.warp)
    print("origin=", origin)
    print("observed_endpoint=", observed_point)
    print("target=", target_point)
    print("planned_distance=", round(planned_distance, 3))
    print("observed_distance=", round(observed_distance, 3))
    print("distance_deficit=", round(planned_distance - observed_distance, 3))

    print("\n===== ACTUAL-SEGMENT FIELD REACHABILITY =====")
    actually_reached_field_ids: list[int] = []
    for field in planned_fields:
        planned_interval = _route_interval(
            origin=origin,
            vector=planned_vector,
            field=field,
            topology=topology,
        )
        observed_interval = _route_interval(
            origin=origin,
            vector=observed_vector,
            field=field,
            topology=topology,
        )
        actually_reached = observed_interval is not None and observed_interval[2] > 1e-9
        if actually_reached and field.field_id is not None:
            actually_reached_field_ids.append(int(field.field_id))
        print({
            "field_id": field.field_id,
            "field_owner": field.owner_id,
            "planned_interval_ly": tuple(round(v, 3) for v in planned_interval) if planned_interval else None,
            "observed_interval_ly": tuple(round(v, 3) for v in observed_interval) if observed_interval else None,
            "reachable_on_actual_observed_segment": actually_reached,
        })
    print("actually_reached_field_ids=", actually_reached_field_ids)

    print("\n===== PRIVACY-SAFE RAW MINE REPORT EVIDENCE =====")
    print("matching_critical_message_count=", len(reports))
    for report in reports:
        event_x = report.get("event_x")
        event_y = report.get("event_y")
        event_metrics = None
        event_equals_observed = None
        post_hit_prediction = None
        if isinstance(event_x, int) and isinstance(event_y, int):
            event_point = (event_x, event_y)
            event_metrics = _route_metrics(
                origin=origin,
                route_vector=planned_vector,
                point=event_point,
                topology=topology,
            )
            event_equals_observed = event_point == observed_point
            if one_hit_damage_warp_limit is not None:
                predicted_endpoint, leg_distance = _post_hit_warp_prediction(
                    hit_point=event_point,
                    target_point=target_point,
                    warp=one_hit_damage_warp_limit,
                    topology=topology,
                )
                post_hit_prediction = {
                    "warp": one_hit_damage_warp_limit,
                    "predicted_endpoint_if_fresh_leg": predicted_endpoint,
                    "fresh_leg_distance": round(leg_distance, 3),
                    "matches_observed_endpoint": predicted_endpoint == observed_point,
                }
        safe_report = dict(report)
        safe_report["event_route_metrics"] = (
            {key: round(value, 3) for key, value in event_metrics.items()}
            if event_metrics is not None
            else None
        )
        safe_report["event_equals_observed_endpoint"] = event_equals_observed
        safe_report["post_hit_damage_limited_fresh_leg"] = post_hit_prediction
        print(safe_report)

    print("\n===== ONE-HIT MOTION CONSEQUENCE CHECKS =====")
    pure_slowdown_distance = max(0.0, planned_distance - 10.0)
    print("documented_one_hit_10ly_slowdown_distance=", round(pure_slowdown_distance, 3))
    print("pure_10ly_slowdown_matches_observed_distance=", abs(pure_slowdown_distance - observed_distance) <= 1.5)
    print("residual_beyond_one_10ly_slowdown=", round(pure_slowdown_distance - observed_distance, 3))
    print("before_damage=", before_damage)
    print("normal_mine_damage_quantum=", quantum)
    print("raw_damage_after_one_hit_before_repair=", raw_one_hit_damage)
    print("max_warp_at_raw_one_hit_damage=", one_hit_damage_warp_limit)
    if one_hit_damage_warp_limit is not None:
        probe = MovementSample(
            turn=before_turn,
            ship_id=SHIP_ID,
            x=origin[0],
            y=origin[1],
            target_x=target_point[0],
            target_y=target_point[1],
            warp=one_hit_damage_warp_limit,
            next_x=observed_point[0],
            next_y=observed_point[1],
            gravitonic=False,
            game_id=GAME_ID,
            hull_id=hull_id,
        )
        whole_turn_damage_cap_endpoint = host_major_minor_destination(probe)
        print("damage_cap_whole_turn_endpoint=", whole_turn_damage_cap_endpoint)
        print("damage_cap_whole_turn_distance=", round(hypot(whole_turn_damage_cap_endpoint[0] - origin[0], whole_turn_damage_cap_endpoint[1] - origin[1]), 3))
        print("damage_cap_whole_turn_matches_observed=", whole_turn_damage_cap_endpoint == observed_point)
        print("fresh_warp_cap_nominal_distance=", probe.nominal_max_distance)
        print("continuous_hit_progress_needed_for_fresh_warp_cap_to_end_at_observed=", round(max(0.0, observed_distance - probe.nominal_max_distance), 3))
    print("after_damage_observed_post_repair=", after_damage)
    print("after_supplies_observational=", after_supplies)
    print("max_warp_at_observed_post_repair_damage=", post_repair_warp_limit)
    print("before_supplies=", before_supplies)

    print("\n===== SUMMARY =====")
    print("planned_intersected_normal_fields=", len(planned_fields))
    print("actually_reached_normal_fields=", len(actually_reached_field_ids))
    print("actually_reached_field_ids=", actually_reached_field_ids)
    print("mine_report_evidence_rows=", len(reports))
    print("one_hit_repair_quantum_ready=", raw_one_hit_damage is not None)
    print("pure_10ly_slowdown_remaining_discrepancy=", round(pure_slowdown_distance - observed_distance, 3))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic does not infer mine RNG or promote a production label. It narrows the sole candidate by "
        "distinguishing fields intersecting the submitted/planned segment from fields actually reachable before the "
        "observed endpoint. Raw turn messages are inspected only for critical/system records that target ship 160; "
        "message body text is never printed, only mechanical metadata and regex-derived mine-hit fields. Event x/y "
        "are treated as report coordinates until independently validated as exact impact coordinates. Damage-limited "
        "warp checks are competing post-hit hypotheses, not assumed Host semantics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
