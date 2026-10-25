"""Strict count-only VCR archive temporal and participant-source readiness.

VCR id is meaningful only within its battle turn and qualified source,
NOT a cross-archive physical/combat continuity key. No Host phase or
combat results follow from these descriptive source counts.
"""
from __future__ import annotations
from collections import Counter
from collections.abc import Mapping
from typing import Any

KEYS = (
    "qualified_archive_pairs",
    "before_vcr_rows",
    "after_vcr_rows",
    "before_turn_exact",
    "before_turn_earlier",
    "before_turn_future",
    "before_turn_missing_or_invalid",
    "after_turn_exact",
    "after_turn_earlier",
    "after_turn_future",
    "after_turn_missing_or_invalid",
    "before_two_participant_objectids_typed",
    "after_two_participant_objectids_typed",
    "before_two_ownerids_typed",
    "after_two_ownerids_typed",
    "before_exact_turn_and_typed_participants",
    "after_exact_turn_and_typed_participants",
    "before_exact_turn_and_full_typed_participants_owners",
    "after_exact_turn_and_full_typed_participants_owners",
    "same_id_across_adjacent_archives_not_battle_link",
)


def _valid_id(value: Any) -> bool:
    return type(value) is int and value > 0


def _vcrs(payload: Mapping[str, Any]) -> dict[int, Mapping[str, Any]] | None:
    rows = payload.get("vcrs")
    if type(rows) is not list:
        return None
    found = {}
    for raw in rows:
        if not isinstance(raw, Mapping) or not _valid_id(raw.get("id")):
            return None
        identity = raw["id"]
        if identity in found:
            return None
        found[identity] = raw
    return found


def profile_vcr_archive_pair(
    before: Mapping[str, Any], after: Mapping[str, Any], *,
    before_turn: int, after_turn: int,
) -> dict[str, int]:
    """Count exact turn anchor and typed participant qualification independently.

    No battle identity, ship identity, game ID or raw VCR row is returned.
    """
    if (type(before_turn) is not int or before_turn <= 0
            or type(after_turn) is not int or after_turn != before_turn + 1):
        raise ValueError("INVALID_SOURCE_EMBEDDED_TURNS")
    if type(before.get("vcrs")) is not list or type(after.get("vcrs")) is not list:
        return {"ABSTAIN_MISSING_VCR_ARRAY": 1}
    b, a = _vcrs(before), _vcrs(after)
    if b is None or a is None:
        return {"ABSTAIN_INVALID_OR_DUPLICATE_VCR_IDS": 1}
    result: Counter[str] = Counter({key: 0 for key in KEYS})
    result["qualified_archive_pairs"] = 1
    result["before_vcr_rows"] = len(b)
    result["after_vcr_rows"] = len(a)
    result["same_id_across_adjacent_archives_not_battle_link"] = len(b.keys() & a.keys())
    for key, rows, turn in (("before", b, before_turn), ("after", a, after_turn)):
        for row in rows.values():
            observed = row.get("turn")
            if not _valid_id(observed):
                category = "missing_or_invalid"
            elif observed < turn:
                category = "earlier"
            elif observed > turn:
                category = "future"
            else:
                category = "exact"
            result[f"{key}_turn_{category}"] += 1
            left, right = row.get("left"), row.get("right")
            typed_participants = (
                isinstance(left, Mapping) and isinstance(right, Mapping)
                and _valid_id(left.get("objectid"))
                and _valid_id(right.get("objectid"))
            )
            typed_owners = (
                _valid_id(row.get("leftownerid"))
                and _valid_id(row.get("rightownerid"))
            )
            if typed_participants:
                result[f"{key}_two_participant_objectids_typed"] += 1
            if typed_owners:
                result[f"{key}_two_ownerids_typed"] += 1
            if category == "exact" and typed_participants:
                result[f"{key}_exact_turn_and_typed_participants"] += 1
                if typed_owners:
                    result[f"{key}_exact_turn_and_full_typed_participants_owners"] += 1
    for side in ("before", "after"):
        rows = result[f"{side}_vcr_rows"]
        partitions = sum(result[f"{side}_turn_{tag}"] for tag in (
            "exact", "earlier", "future", "missing_or_invalid"
        ))
        if not (partitions == rows
                and result[f"{side}_exact_turn_and_full_typed_participants_owners"]
                    <= result[f"{side}_exact_turn_and_typed_participants"]
                    <= min(result[f"{side}_turn_exact"],
                           result[f"{side}_two_participant_objectids_typed"])
                and result[f"{side}_exact_turn_and_full_typed_participants_owners"]
                    <= result[f"{side}_two_ownerids_typed"]):
            raise ValueError("VCR_TEMPORAL_SOURCE_CONSERVATION")
    if result["same_id_across_adjacent_archives_not_battle_link"] > min(len(b),len(a)):
        raise ValueError("VCR_ID_PAIR_CONSERVATION")
    return dict(sorted(result.items()))
