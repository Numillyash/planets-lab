from __future__ import annotations

import re
from collections import Counter
from math import hypot
from typing import Any, Mapping

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from normal_mine_single_candidate_immunity_repair_audit import (
    BEFORE_TURN,
    EXPECTED_OWNER,
    GAME_ID,
    PREPARED_DIR,
    RAW_DIR,
    SHIP_ID,
    _load_row,
    _sample,
)
from normal_mine_single_candidate_post_hit_motion_audit import (
    _messages,
    _raw_turn_payload,
)


MESSAGE_SHIP_RE = re.compile(r"(?:#\s*160\b|\bship\s*#?\s*160\b)", re.IGNORECASE)
SELECTED_STATE_FIELDS = (
    "x",
    "y",
    "warp",
    "targetx",
    "targety",
    "mission",
    "mission1target",
    "mission2target",
    "friendlycode",
    "damage",
    "crew",
    "neutronium",
    "supplies",
    "clans",
    "duranium",
    "tritanium",
    "molybdenum",
    "megacredits",
    "mass",
)


def _point(raw: Mapping[str, Any]) -> tuple[int, int] | None:
    x = _intish(raw.get("x"))
    y = _intish(raw.get("y"))
    if x is None or y is None:
        return None
    return x, y


def _target_point(raw: Mapping[str, Any]) -> tuple[int | None, int | None]:
    return (
        _intish(raw.get("targetx", raw.get("waypointx"))),
        _intish(raw.get("targety", raw.get("waypointy"))),
    )


def _selected_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in SELECTED_STATE_FIELDS:
        if key not in raw:
            continue
        value = raw.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
    result["target_xy"] = _target_point(raw)
    return result


def _state_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, tuple[Any, Any]]:
    left = _selected_state(before)
    right = _selected_state(after)
    keys = sorted(set(left) | set(right))
    return {
        key: (left.get(key), right.get(key))
        for key in keys
        if left.get(key) != right.get(key)
    }


def _mission_repo_convention(raw: Mapping[str, Any]) -> str | None:
    mission = _intish(raw.get("mission"))
    if mission == 6:
        return "tow_attempt"
    if mission == 7:
        return "intercept"
    return None


def _target_reference_fields(raw: Mapping[str, Any], *, ship_id: int) -> list[str]:
    matches: list[str] = []
    for key, value in raw.items():
        normalized = str(key).lower().replace("_", "")
        if "target" not in normalized:
            continue
        if _intish(value) == ship_id:
            matches.append(str(key))
    return sorted(matches)


def _ship_excerpt(
    *,
    ship_id: int,
    owner_id: int,
    before_raw: Mapping[str, Any],
    after_raw: Mapping[str, Any],
    target_origin: tuple[int, int],
    target_observed: tuple[int, int],
    target_move: tuple[int, int],
    impact: tuple[int, int],
) -> dict[str, Any]:
    before_xy = _point(before_raw)
    after_xy = _point(after_raw)
    move = None
    if before_xy is not None and after_xy is not None:
        move = (after_xy[0] - before_xy[0], after_xy[1] - before_xy[1])

    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "hull_id": _intish(before_raw.get("hullid", before_raw.get("hull_id"))),
        "before_xy": before_xy,
        "after_xy": after_xy,
        "move": move,
        "before_distance_to_target_origin": (
            round(hypot(before_xy[0] - target_origin[0], before_xy[1] - target_origin[1]), 3)
            if before_xy is not None else None
        ),
        "after_distance_to_target_observed": (
            round(hypot(after_xy[0] - target_observed[0], after_xy[1] - target_observed[1]), 3)
            if after_xy is not None else None
        ),
        "after_distance_to_impact": (
            round(hypot(after_xy[0] - impact[0], after_xy[1] - impact[1]), 3)
            if after_xy is not None else None
        ),
        "same_move_vector_as_target": move == target_move,
        "warp_before": _intish(before_raw.get("warp")),
        "warp_after": _intish(after_raw.get("warp")),
        "mission_numeric_before": _intish(before_raw.get("mission")),
        "mission_repo_convention_before": _mission_repo_convention(before_raw),
        "mission1target_before": _intish(before_raw.get("mission1target", before_raw.get("mission1_target_id"))),
        "target_xy_before": _target_point(before_raw),
        "damage_before": _intish(before_raw.get("damage")),
        "damage_after": _intish(after_raw.get("damage")),
        "target_reference_fields": _target_reference_fields(before_raw, ship_id=SHIP_ID),
    }


def _message_excerpt(message: Mapping[str, Any], *, archive_turn: int) -> dict[str, Any]:
    body = message.get("body") if isinstance(message.get("body"), str) else ""
    normalized_body = " ".join(body.split())
    if len(normalized_body) > 260:
        normalized_body = normalized_body[:257] + "..."
    return {
        "archive_turn": archive_turn,
        "message_id": _intish(message.get("id")),
        "messagetype": _intish(message.get("messagetype")),
        "target": _intish(message.get("target")),
        "x": _intish(message.get("x")),
        "y": _intish(message.get("y")),
        "body_excerpt": normalized_body,
    }


def _message_relevant(
    message: Mapping[str, Any],
    *,
    impact: tuple[int, int],
    observed: tuple[int, int],
) -> bool:
    if _intish(message.get("target")) == SHIP_ID:
        return True
    x = _intish(message.get("x"))
    y = _intish(message.get("y"))
    if x is not None and y is not None and (x, y) in {impact, observed}:
        return True
    body = message.get("body") if isinstance(message.get("body"), str) else ""
    return MESSAGE_SHIP_RE.search(body) is not None


def main() -> int:
    row = _load_row()
    archive_path = RAW_DIR / f"game-{GAME_ID}.zip"
    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=GAME_ID,
        cache_path=PREPARED_DIR / f"game-{GAME_ID}.pickle",
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")

    after_turn = int(row["after_archive_turn"])
    owner_id, before_owner = _owner_record(ship_groups.get((BEFORE_TURN, SHIP_ID), ()))
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, SHIP_ID), ()))
    if owner_id != EXPECTED_OWNER or before_owner is None:
        raise SystemExit(f"target before-owner guard failed: expected {EXPECTED_OWNER}, got {owner_id}")
    if after_owner_id != owner_id or after_owner is None:
        raise SystemExit("target after-owner identity unavailable")

    sample = _sample(row)
    origin = (sample.x, sample.y)
    observed = sample.observed_destination
    target_move = (observed[0] - origin[0], observed[1] - origin[1])
    impact = (2546, 1792)

    before_raw = before_owner.raw
    after_raw = after_owner.raw

    print("===== NORMAL-MINE TARGET EVENT / CO-MOVEMENT AUDIT =====")
    print("game=", GAME_ID)
    print("before_turn=", BEFORE_TURN)
    print("after_turn=", after_turn)
    print("ship=", SHIP_ID)
    print("prepared_cache_hit=", cache_hit)
    print("owner_id=", owner_id)
    print("origin=", origin)
    print("observed=", observed)
    print("submitted_target=", (sample.target_x, sample.target_y))
    print("observed_move_vector=", target_move)
    print("known_mine_impact=", impact)

    print("\n===== TARGET STATE =====")
    print("before=", _selected_state(before_raw))
    print("after=", _selected_state(after_raw))
    print("changes=", _state_changes(before_raw, after_raw))
    print("before_mission_numeric=", _intish(before_raw.get("mission")))
    print("before_mission_repo_convention=", _mission_repo_convention(before_raw))

    print("\n===== TARGET-RELEVANT MESSAGES =====")
    relevant_messages: list[dict[str, Any]] = []
    message_counts: dict[int, int] = {}
    for archive_turn in (BEFORE_TURN, after_turn):
        payload = _raw_turn_payload(archive_data, turn=archive_turn, player_id=owner_id)
        messages = _messages(payload)
        message_counts[archive_turn] = len(messages)
        for message in messages:
            if _message_relevant(message, impact=impact, observed=observed):
                relevant_messages.append(_message_excerpt(message, archive_turn=archive_turn))
    print("all_owner_message_counts_by_turn=", message_counts)
    print("relevant_message_count=", len(relevant_messages))
    for item in relevant_messages:
        print(item)

    print("\n===== SAME-ORIGIN / SAME-ENDPOINT CONTEXT =====")
    counts = Counter()
    same_origin: list[dict[str, Any]] = []
    near_origin: list[dict[str, Any]] = []
    same_endpoint: list[dict[str, Any]] = []
    near_endpoint: list[dict[str, Any]] = []
    same_vector: list[dict[str, Any]] = []
    near_impact_after: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    ship_ids = sorted({
        ship_id
        for turn, ship_id in ship_groups
        if turn in {BEFORE_TURN, after_turn}
    })
    for candidate_id in ship_ids:
        if candidate_id == SHIP_ID:
            continue
        candidate_owner_id, candidate_before = _owner_record(
            ship_groups.get((BEFORE_TURN, candidate_id), ())
        )
        candidate_after_owner_id, candidate_after = _owner_record(
            ship_groups.get((after_turn, candidate_id), ())
        )
        if (
            candidate_owner_id is None
            or candidate_owner_id <= 0
            or candidate_before is None
            or candidate_after_owner_id != candidate_owner_id
            or candidate_after is None
        ):
            counts["candidate_owner_pair_unavailable"] += 1
            continue
        counts["candidate_owner_pair_ready"] += 1

        excerpt = _ship_excerpt(
            ship_id=candidate_id,
            owner_id=candidate_owner_id,
            before_raw=candidate_before.raw,
            after_raw=candidate_after.raw,
            target_origin=origin,
            target_observed=observed,
            target_move=target_move,
            impact=impact,
        )
        before_distance = excerpt["before_distance_to_target_origin"]
        after_distance = excerpt["after_distance_to_target_observed"]
        impact_distance = excerpt["after_distance_to_impact"]

        if before_distance == 0.0:
            same_origin.append(excerpt)
        if isinstance(before_distance, float) and before_distance <= 5.0:
            near_origin.append(excerpt)
        if after_distance == 0.0:
            same_endpoint.append(excerpt)
        if isinstance(after_distance, float) and after_distance <= 5.0:
            near_endpoint.append(excerpt)
        if excerpt["same_move_vector_as_target"] is True:
            same_vector.append(excerpt)
        if isinstance(impact_distance, float) and impact_distance <= 5.0:
            near_impact_after.append(excerpt)
        if excerpt["target_reference_fields"]:
            references.append(excerpt)

    print("owner_pair_counts=", dict(sorted(counts.items())))
    print("same_origin_count=", len(same_origin))
    for item in same_origin:
        print("same_origin", item)
    print("near_origin_within_5ly_count=", len(near_origin))
    for item in near_origin:
        print("near_origin", item)
    print("same_endpoint_count=", len(same_endpoint))
    for item in same_endpoint:
        print("same_endpoint", item)
    print("near_endpoint_within_5ly_count=", len(near_endpoint))
    for item in near_endpoint:
        print("near_endpoint", item)
    print("same_vector_count=", len(same_vector))
    for item in same_vector:
        print("same_vector", item)
    print("near_impact_after_within_5ly_count=", len(near_impact_after))
    for item in near_impact_after:
        print("near_impact_after", item)

    print("\n===== REFERENCES TO TARGET SHIP =====")
    print("reference_candidate_count=", len(references))
    for item in references:
        print(item)

    print("\n===== SUMMARY =====")
    print("relevant_message_count=", len(relevant_messages))
    print("same_origin_count=", len(same_origin))
    print("same_endpoint_count=", len(same_endpoint))
    print("same_vector_count=", len(same_vector))
    print("reference_candidate_count=", len(references))
    print("target_crew_before=", _intish(before_raw.get("crew")))
    print("target_crew_after=", _intish(after_raw.get("crew")))
    print("target_mission_before=", _intish(before_raw.get("mission")))
    print("target_mission_after=", _intish(after_raw.get("mission")))
    print("target_mission1target_before=", _intish(before_raw.get("mission1target", before_raw.get("mission1_target_id"))))
    print("target_mission1target_after=", _intish(after_raw.get("mission1target", after_raw.get("mission1_target_id"))))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This is a narrow evidence-only target diagnostic. It does not infer causality from co-location, co-movement, "
        "message type numbers, or arbitrary target-like fields. Mission 6/7 names are shown only through the existing "
        "repository convention (Tow / Intercept); all other mission values remain numeric. Message bodies are limited "
        "to target-relevant records and truncated. No production labels, schemas, or accounting are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
