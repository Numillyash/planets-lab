"""Strict, privacy-minimal owner provenance for visible historical starbases.

A starbase is anchored by planetid, and Nu import can recover its owner
from a planet. This does NOT prove the starbase row's current-turn freshness,
queue state, available components, PP ledger or accepted orders.
No entity IDs, raw values or private payload fields leave this module.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

# Fixed mechanical keys only; counts reflect mere presence, NOT complete
# warehouse inventories, queue orders, or a verified build.
STARBASE_SOURCE_KEYS = (
    "planetid",
    "ownerid",
    "owner_id",
    "infoturn",
    "buildhullid",
    "hulltechlevel",
    "enginetechlevel",
    "beamtechlevel",
    "torptechlevel",
    "hulls",
    "engines",
    "beams",
    "torpedoes",
)


def _owner(raw: Mapping[str, Any]) -> int | None:
    first = raw.get("ownerid")
    if first is None:
        first = raw.get("owner_id")
    return first if type(first) is int and first > 0 else None


def starbase_owner_provenance(
    snapshot: Mapping[str, Any],
    *,
    perspective: int,
    embedded_turn: int,
) -> dict[str, Any]:
    if (
        type(perspective) is not int or perspective <= 0
        or type(embedded_turn) is not int or embedded_turn < 0
    ):
        raise ValueError("malformed starbase diagnostic perspective/turn")
    bases = snapshot.get("starbases")
    planets = snapshot.get("planets")
    if type(bases) is not list or type(planets) is not list:
        return {
            "status": "ABSTAIN_PLANET_OR_STARBASE_ARRAY_MISSING",
            "visible_starbase_rows": len(bases) if type(bases) is list else None,
            "fresh_owned_planet_linked_bases": 0,
            "linked_owned_planet_bases_without_base_infoturn": 0,
            "linked_owned_planet_bases_with_stale_base_infoturn": 0,
            "unresolved_or_ambiguous_base_rows": None,
            "owner_conflicts_with_planet": 0,
            "source_key_presence_counts": {},
            "warehouse_and_queue_complete": False,
            "independent_host_owner_freshness_verified": False,
        }

    # Never promote an ambiguous duplicate planet ID to an owner identity.
    planet_id_counts = Counter(
        row["id"] for row in planets
        if type(row) is dict and type(row.get("id")) is int
    )
    fresh_owners: dict[int, int] = {}
    for raw in planets:
        if type(raw) is not dict:
            continue
        pid = raw.get("id")
        if type(pid) is not int or planet_id_counts[pid] != 1:
            continue
        if raw.get("infoturn") != embedded_turn or type(raw.get("infoturn")) is not int:
            continue
        o = _owner(raw)
        if o is not None:
            fresh_owners[pid] = o

    # A planet can have only one starbase in the documented model.
    # Two visible base records for one planet are ambiguous, not two
    # independently verified production sites.
    base_id_counts = Counter(
        raw.get("planetid", raw.get("planet_id"))
        for raw in bases
        if type(raw) is dict and
        type(raw.get("planetid", raw.get("planet_id"))) is int
    )
    source_counts: Counter[str] = Counter()
    current = without_freshness = stale = unresolved = conflicts = 0
    link_ownership = 0
    for base in bases:
        if type(base) is not dict:
            unresolved += 1
            continue
        for key in STARBASE_SOURCE_KEYS:
            if key in base:
                source_counts[key] += 1
        pid = base.get("planetid", base.get("planet_id"))
        if type(pid) is not int or base_id_counts[pid] != 1 or pid not in fresh_owners:
            unresolved += 1
            continue
        planet_owner = fresh_owners[pid]
        explicit_owner = _owner(base)
        if explicit_owner is not None and explicit_owner != planet_owner:
            conflicts += 1
            unresolved += 1
            continue
        if planet_owner != perspective:
            # A foreign base on a known fresh foreign planet is not an
            # unknown own starbase: no counts in the owned candidate buckets.
            continue
        link_ownership += 1
        info = base.get("infoturn")
        if info is None:
            without_freshness += 1
        elif type(info) is int and info == embedded_turn:
            current += 1
        else:
            stale += 1

    return {
        "status": "BOUNDED_PLANET_LINK_ONLY_NOT_HOST_VERIFIED",
        "visible_starbase_rows": len(bases),
        "owned_planet_linked_base_rows": link_ownership,
        "fresh_owned_planet_linked_bases": current,
        "linked_owned_planet_bases_without_base_infoturn": without_freshness,
        "linked_owned_planet_bases_with_stale_base_infoturn": stale,
        "unresolved_or_ambiguous_base_rows": unresolved,
        "owner_conflicts_with_planet": conflicts,
        "source_key_presence_counts": {
            key: source_counts[key] for key in STARBASE_SOURCE_KEYS
        },
        "warehouse_and_queue_complete": False,
        "independent_host_owner_freshness_verified": False,
    }
