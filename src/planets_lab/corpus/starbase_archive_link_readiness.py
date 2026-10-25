"""Privacy-safe same-ID starbase→planet source provenance across frozen T-1/T.

A planet link is only a conditional *observer-archive* ownership witness.
It does not prove the starbase record's freshness unless separately typed,
and neither case proves real NuHost construction, accepted orders or phases.
Never export IDs, names, positions, foreign relations or raw row values.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any


def _id_map(rows: list[Any]) -> dict[int, Mapping[str, Any]] | None:
    found: dict[int, Mapping[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            return None
        key = raw.get("id")
        if type(key) is not int or key <= 0 or key in found:
            return None
        found[key] = raw
    return found


def _positive_alias(row: Mapping[str, Any], left: str, right: str) -> int | None:
    """Fail closed on both-present conflicting/untyped aliases."""
    has_a, has_b = left in row, right in row
    if not (has_a or has_b):
        return None
    a = row.get(left)
    b = row.get(right)
    if has_a and has_b and a != b:
        return None
    value = a if has_a else b
    return value if type(value) is int and value > 0 else None


def _planet_owners(snapshot: Mapping[str, Any], turn: int) -> dict[int, int]:
    planets = snapshot["planets"]
    assert type(planets) is list
    multiplicity: Counter[int] = Counter(
        row["id"] for row in planets
        if isinstance(row, Mapping) and type(row.get("id")) is int
        and row["id"] > 0
    )
    valid: dict[int, int] = {}
    for row in planets:
        if not isinstance(row, Mapping):
            continue
        pid = row.get("id")
        if type(pid) is not int or pid <= 0 or multiplicity[pid] != 1:
            continue
        owner = _positive_alias(row, "ownerid", "owner_id")
        if owner is None or type(row.get("infoturn")) is not int or row["infoturn"] != turn:
            continue
        valid[pid] = owner
    return valid


def _anchor_frequency(rows: list[Any]) -> Counter[int]:
    frequencies: Counter[int] = Counter()
    for base in rows:
        if isinstance(base, Mapping):
            anchor = _positive_alias(base, "planetid", "planet_id")
            if anchor is not None:
                frequencies[anchor] += 1
    return frequencies


def profile_starbase_archive_link_pair(
    before: Mapping[str, Any], after: Mapping[str, Any],
    *, observer: int, before_turn: int, after_turn: int,
) -> dict[str, int]:
    """Count only fixed integer buckets, never actual base or planet IDs."""
    if (type(observer) is not int or observer <= 0
            or type(before_turn) is not int or before_turn <= 0
            or type(after_turn) is not int or after_turn != before_turn + 1):
        raise ValueError("INVALID_FROZEN_ARCHIVE_OBSERVER_TURN")
    bb, aa = before.get("starbases"), after.get("starbases")
    bp, ap = before.get("planets"), after.get("planets")
    if any(type(x) is not list for x in (bb, aa, bp, ap)):
        return {"ABSTAIN_REQUIRED_ARCHIVE_SECTION_NOT_LIST": 1}
    b = _id_map(bb)
    a = _id_map(aa)
    if b is None or a is None:
        return {"ABSTAIN_STARBASE_SECTION_DUPLICATE_OR_INVALID_ID": 1}

    shared = b.keys() & a.keys()
    result: Counter[str] = Counter({
        "qualified_source_list_pairs": 1,
        "same_id_starbase_observer_occurrences": len(shared),
        "same_id_planet_linked_current_own_both_archives": 0,
        "same_id_planet_linked_base_current_both_archives": 0,
        "same_id_planet_linked_base_infoturn_missing_any": 0,
        "same_id_planet_linked_base_infoturn_stale_or_invalid_any": 0,
        "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED": 0,
        "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED": 0,
        "ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS": 0,
        "ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT": 0,
    })
    owners_b = _planet_owners(before, before_turn)
    owners_a = _planet_owners(after, after_turn)
    freq_b, freq_a = _anchor_frequency(bb), _anchor_frequency(aa)
    for key in shared:
        left, right = b[key], a[key]
        pl = _positive_alias(left, "planetid", "planet_id")
        pr = _positive_alias(right, "planetid", "planet_id")
        if pl is None or pr is None or pl != pr:
            result["ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED"] += 1
            continue
        if freq_b[pl] != 1 or freq_a[pr] != 1:
            result["ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS"] += 1
            continue
        if owners_b.get(pl) != observer or owners_a.get(pl) != observer:
            result["ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED"] += 1
            continue
        own_b = _positive_alias(left, "ownerid", "owner_id") if (
            "ownerid" in left or "owner_id" in left
        ) else observer
        own_a = _positive_alias(right, "ownerid", "owner_id") if (
            "ownerid" in right or "owner_id" in right
        ) else observer
        if own_b != observer or own_a != observer:
            result["ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT"] += 1
            continue
        result["same_id_planet_linked_current_own_both_archives"] += 1
        info_b, info_a = left.get("infoturn"), right.get("infoturn")
        if (type(info_b) is int and info_b == before_turn
                and type(info_a) is int and info_a == after_turn):
            result["same_id_planet_linked_base_current_both_archives"] += 1
        elif ((info_b is not None and (type(info_b) is not int or info_b != before_turn))
              or (info_a is not None and (type(info_a) is not int or info_a != after_turn))):
            result["same_id_planet_linked_base_infoturn_stale_or_invalid_any"] += 1
        else:
            result["same_id_planet_linked_base_infoturn_missing_any"] += 1
    owned = result["same_id_planet_linked_current_own_both_archives"]
    if (
        owned + sum(result[k] for k in (
            "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED",
            "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED",
            "ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS",
            "ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT",
        )) != len(shared)
        or sum(result[k] for k in (
            "same_id_planet_linked_base_current_both_archives",
            "same_id_planet_linked_base_infoturn_missing_any",
            "same_id_planet_linked_base_infoturn_stale_or_invalid_any",
        )) != owned
    ):
        raise ValueError("STARBASE_SOURCE_LINK_CONSERVATION_FAILURE")
    return dict(sorted(result.items()))
