"""Read-only field-availability triage for *observed* new owned-ship identities.

This module deliberately reports presence and typedness, NEVER field values,
entity IDs, plans, full warehouses, server-accepted orders or Host causality.
The selected archive windows stay within the previously frozen control12
public cohort. Observed new identity != ship built.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from planets_lab.corpus.pq_observed_transition import (
    _fresh_owned_entity_ids, _fresh_owned_base_ids,
)

SCHEMA = "planets-lab.pq-ship-appearance-source-fields.v1"

# Keys are a limited source discovery vocabulary, NOT a host-order schema.
# Presence may refer to client display/snapshot, not accepted command.
FIELDS = {
    "planet": (
        "megacredits", "duranium", "tritanium", "molybdenum",
        "infoturn", "ownerid",
    ),
    "starbase": (
        "buildhullid", "buildengineid", "buildbeamid", "buildtorpedoid",
        "buildbeamcount", "buildtorpcount",
        "hulls", "engines", "beams", "torpedoes",
        "hulltechlevel", "enginetechlevel",
        "beamtechlevel", "torptechlevel", "infoturn",
    ),
    "ship": (
        "hullid", "engineid", "beamid", "torpedoid",
        "beamcount", "torpcount", "mass", "fuel",
        "infoturn", "ownerid",
    ),
    "player": (
        "prioritypoints", "prioritybuildpoints", "pbps",
        "pp", "priority", "shipcount",
    ),
}


def _typed_positive_id(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    return value if type(value) is int and value > 0 else None


def _presence(rows: list[Mapping[str, Any]], kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in FIELDS[kind]:
        present = 0
        typed_nonnegative = 0
        null = 0
        invalid_or_negative = 0
        for item in rows:
            if key not in item:
                continue
            present += 1
            value = item[key]
            if value is None:
                null += 1
            elif type(value) is int and value >= 0:
                typed_nonnegative += 1
            else:
                invalid_or_negative += 1
        result[key] = {
            "key_present_rows": present,
            "typed_nonnegative_integer_rows": typed_nonnegative,
            "null_rows": null,
            "other_or_negative_rows": invalid_or_negative,
        }
    return {"selected_source_rows": len(rows), "source_key_status": result}


def _typed_owned_qualified(
    snapshot: Mapping[str, Any], kind: str, qualified_ids: set[int],
    *, key: str,
) -> list[Mapping[str, Any]]:
    value = snapshot.get(kind)
    if type(value) is not list:
        return []
    return [
        row for row in value if type(row) is dict
        and _typed_positive_id(row, key) in qualified_ids
    ]


def _owned_current_source(
    snapshot: Mapping[str, Any], owner: int, turn: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    planet_ids, _ = _fresh_owned_entity_ids(snapshot, "planets", owner, turn)
    base_planet_ids, _ = _fresh_owned_base_ids(snapshot, owner, turn)
    planets = _typed_owned_qualified(snapshot, "planets", planet_ids, key="id")
    bases = _typed_owned_qualified(
        snapshot, "starbases", base_planet_ids, key="planetid",
    )
    return planets, bases


def source_fields_for_ship_appearance(
    before: Mapping[str, Any], after: Mapping[str, Any], *,
    perspective: int, embedded_before: int, embedded_after: int,
) -> dict[str, Any]:
    if (
        type(perspective) is not int or perspective <= 0 or perspective > 50
        or type(embedded_before) is not int or embedded_before < 0
        or type(embedded_after) is not int
        or embedded_after != embedded_before + 1
    ):
        raise ValueError("unsupported source-field audit context")

    earlier, before_info = _fresh_owned_entity_ids(
        before, "ships", perspective, embedded_before,
    )
    later, after_info = _fresh_owned_entity_ids(
        after, "ships", perspective, embedded_after,
    )
    before_planets, before_bases = _owned_current_source(
        before, perspective, embedded_before,
    )
    after_planets, after_bases = _owned_current_source(
        after, perspective, embedded_after,
    )
    additions = later - earlier
    # Only count source keys on rows for genuinely fresh typed *newly
    # observed* ship IDs. Never export any IDs even as hashes.
    new_ships = _typed_owned_qualified(after, "ships", additions, key="id")

    player_before = before.get("player")
    player_after = after.get("player")
    players_b = [player_before] if type(player_before) is dict else []
    players_a = [player_after] if type(player_after) is dict else []
    missing = []
    for side, snap, info in (
        ("before", before, before_info),
        ("after", after, after_info),
    ):
        for kind in ("ships", "planets", "starbases"):
            if type(snap.get(kind)) is not list:
                missing.append(f"{side.upper()}_{kind.upper()}_ARRAY_MISSING")
        if not info["array_present"] or info["ambiguous_duplicate_ids"]:
            missing.append(f"{side.upper()}_SHIPS_IDENTITY_UNQUALIFIED")
        if type(snap.get("player")) is not dict:
            missing.append(f"{side.upper()}_PLAYER_RECORD_MISSING")

    status = (
        "ABSTAIN_SOURCE_SHAPE_OR_IDENTITY"
        if missing else
        "OBSERVED_NEW_OWNED_SHIP_SOURCE_FIELDS" if additions else
        "NO_NEWLY_VISIBLE_OWNED_SHIP_IN_THIS_WINDOW"
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "newly_visible_owned_current_ship_ids_count": len(additions),
        "source_field_presence_only": {
            "before_owned_current_planets": _presence(before_planets, "planet"),
            "after_owned_current_planets": _presence(after_planets, "planet"),
            "before_owned_current_bases": _presence(before_bases, "starbase"),
            "after_owned_current_bases": _presence(after_bases, "starbase"),
            "newly_visible_owned_current_ships": _presence(new_ships, "ship"),
            "before_perspective_player": _presence(players_b, "player"),
            "after_perspective_player": _presence(players_a, "player"),
        },
        "missing_or_ambiguous_source": sorted(set(missing)),
        "all_own_ships_independently_complete": False,
        "queued_build_command_authenticated": False,
        "starbase_components_complete": False,
        "owner_priority_points_independently_complete": False,
        "host_orders_accepted_verified": False,
        "source_fields_match_causal_build_event": False,
        "nuhost_build_execution_verified": False,
        "private_values_or_ids_emitted": False,
        "evidence": "PUBLIC_ARCHIVAL_FIELD_PRESENCE_AFTER_OWN_SHIP_APPEARANCE_NOT_HOST_PARITY",
    }
