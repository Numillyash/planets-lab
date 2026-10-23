"""Strict noncausal T−1→T observation signatures for public PQ/PPQ windows.

We may compare visible *owner-current* typed identities within the same
perspective across consecutive embedded turns. This never proves a built
ship, destroyed ship, priority points, warehouses, or Host accepted orders.
No individual IDs, resources, commands, names, or private fields are output.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

SCHEMA = "planets-lab.pq-owned-observed-transition.v1"


def _typed_owner(row: Mapping[str, Any]) -> int | None:
    first = row.get("ownerid")
    second = row.get("owner_id")
    if first is not None and second is not None and first != second:
        return None
    value = first if first is not None else second
    if type(value) is int and value > 0:
        return value
    return None


def _id(row: Mapping[str, Any], name: str) -> int | None:
    value = row.get(name)
    return value if type(value) is int and value > 0 else None


def _fresh_owned_entity_ids(
    snapshot: Mapping[str, Any], kind: str, owner: int, turn: int,
) -> tuple[set[int], dict[str, int | bool]]:
    raw = snapshot.get(kind)
    if type(raw) is not list:
        return set(), {
            "array_present": False, "visible_rows": 0,
            "fresh_owned_typed_rows": 0, "unqualified_rows": 0,
            "ambiguous_duplicate_ids": 0,
        }
    seen = Counter(
        value for row in raw if type(row) is dict
        if (value := _id(row, "id")) is not None
    )
    ids: set[int] = set()
    ambiguity = 0
    for row in raw:
        if type(row) is not dict:
            continue
        ident = _id(row, "id")
        if ident is not None and seen[ident] > 1:
            ambiguity += 1
            continue
        if (
            ident is not None and _typed_owner(row) == owner
            and type(row.get("infoturn")) is int
            and row["infoturn"] == turn
        ):
            ids.add(ident)
    return ids, {
        "array_present": True,
        "visible_rows": len(raw),
        "fresh_owned_typed_rows": len(ids),
        "unqualified_rows": len(raw) - len(ids),
        "ambiguous_duplicate_ids": ambiguity,
    }


def _fresh_owned_base_ids(
    snapshot: Mapping[str, Any], owner: int, turn: int,
) -> tuple[set[int], dict[str, int | bool]]:
    bases = snapshot.get("starbases")
    planets = snapshot.get("planets")
    if type(bases) is not list or type(planets) is not list:
        return set(), {
            "array_present": False, "visible_rows": 0,
            "fresh_owned_typed_rows": 0, "unqualified_rows": 0,
            "ambiguous_duplicate_ids": 0,
        }
    planet_owners = Counter(
        _id(row, "id") for row in planets if type(row) is dict
        if _id(row, "id") is not None
    )
    fresh_planets = {
        _id(row, "id") for row in planets
        if type(row) is dict and _id(row, "id") is not None
        and planet_owners[_id(row, "id")] == 1
        and _typed_owner(row) == owner
        and type(row.get("infoturn")) is int
        and row["infoturn"] == turn
    }
    counts = Counter(
        ident for row in bases if type(row) is dict
        if (ident := _id(row, "planetid")) is not None
    )
    result: set[int] = set()
    ambiguity = 0
    for raw in bases:
        if type(raw) is not dict:
            continue
        # Historical base records are keyed by planetid. No invented
        # fallback to a ship/base ID or missing/zero planet ID.
        pid = _id(raw, "planetid")
        if pid is not None and counts[pid] > 1:
            ambiguity += 1
            continue
        explicit = _typed_owner(raw)
        if (
            pid in fresh_planets and (
                explicit is None and raw.get("ownerid") is None
                and raw.get("owner_id") is None
                or explicit == owner
            )
            and type(raw.get("infoturn")) is int
            and raw["infoturn"] == turn
        ):
            result.add(pid)
    return result, {
        "array_present": True,
        "visible_rows": len(bases),
        "fresh_owned_typed_rows": len(result),
        "unqualified_rows": len(bases) - len(result),
        "ambiguous_duplicate_ids": ambiguity,
    }


def observed_owned_transition_signature(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *, perspective: int, before_turn: int, after_turn: int,
) -> dict[str, Any]:
    if (
        type(perspective) is not int or not 1 <= perspective <= 50
        or type(before_turn) is not int or before_turn < 0
        or type(after_turn) is not int or after_turn != before_turn + 1
    ):
        raise ValueError("unsupported nonconsecutive or malformed transition")
    signatures: dict[str, Any] = {}
    any_invalid = False
    for label, kind in (
        ("planets", "planets"), ("ships", "ships"), ("starbases", "starbases"),
    ):
        getter = _fresh_owned_base_ids if label == "starbases" else _fresh_owned_entity_ids
        if label == "starbases":
            left, b = getter(before, perspective, before_turn)
            right, a = getter(after, perspective, after_turn)
        else:
            left, b = getter(before, kind, perspective, before_turn)
            right, a = getter(after, kind, perspective, after_turn)
        if (not b["array_present"] or not a["array_present"]
                or b["ambiguous_duplicate_ids"] or a["ambiguous_duplicate_ids"]):
            any_invalid = True
        signatures[label] = {
            "before": b, "after": a,
            "observed_in_both": len(left & right),
            "newly_visible_owned_fresh_ids": len(right - left),
            "no_longer_visible_owned_fresh_ids": len(left - right),
        }
    return {
        "schema": SCHEMA,
        "status": (
            "ABSTAIN_AMBIGUOUS_OR_MISSING_SOURCE_ARRAYS"
            if any_invalid else "OBSERVED_OWNER_CURRENT_IDENTITY_INTERSECTION_ONLY"
        ),
        "owner_perspective_slot": perspective,
        "embedded_before_turn": before_turn,
        "embedded_after_turn": after_turn,
        "entity_signatures": signatures,
        "owner_current_views_are_globally_complete": False,
        "appearance_is_ship_construction_verified": False,
        "disappearance_is_ship_loss_verified": False,
        "queue_and_warehouse_after_before_verified": False,
        "owner_pp_verified": False,
        "accepted_host_orders_verified": False,
        "nuhost_phase_order_verified": False,
        "host_causal_verified": False,
        "private_entity_fields_emitted": False,
        "evidence": "PUBLIC_ARCHIVE_OWNER_CURRENT_IDENTITY_OBSERVATION_NOT_HOST_CAUSAL",
    }
