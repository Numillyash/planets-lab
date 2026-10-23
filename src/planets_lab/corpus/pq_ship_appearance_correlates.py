"""Noncausal PPQ appearance correlates in strictly approved two-turn archives.

Compute only categorical before-base template compatibility and player
priority-points direction for newly observed own-current ship IDs. Any
unexpected source leaves the result ABSTAIN/UNKNOWN. No entity IDs, actual
orders, PP values, component stock or ship specifications are emitted.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from planets_lab.corpus.pq_observed_transition import _fresh_owned_entity_ids
from planets_lab.corpus.pq_ship_appearance_fields import (
    _owned_current_source, _typed_owned_qualified,
)

SCHEMA = "planets-lab.pq-noncausal-appearance-correlates.v1"

def _pos_int(row: Mapping[str, Any], field: str) -> int | None:
    v = row.get(field)
    return v if type(v) is int and v > 0 else None


def _pp_trend(before: Mapping[str, Any], after: Mapping[str, Any],
              perspective: int) -> str:
    p1, p2 = before.get("player"), after.get("player")
    if type(p1) is not dict or type(p2) is not dict:
        return "ABSTAIN_PLAYER_RECORD_MISSING"
    if type(p1.get("id")) is not int or p1["id"] != perspective:
        return "ABSTAIN_PLAYER_IDENTITY"
    if type(p2.get("id")) is not int or p2["id"] != perspective:
        return "ABSTAIN_PLAYER_IDENTITY"
    b, a = p1.get("prioritypoints"), p2.get("prioritypoints")
    if type(b) is not int or b < 0 or type(a) is not int or a < 0:
        return "UNKNOWN_PRIORITYPOINTS_SOURCE"
    return "PP_INCREASED" if a > b else "PP_DECREASED" if a < b else "PP_UNCHANGED"


def appearance_correlates(
    before: Mapping[str, Any], after: Mapping[str, Any],
    *, perspective: int, embedded_before: int, embedded_after: int,
) -> dict[str, Any]:
    if (
        type(perspective) is not int or not 1 <= perspective <= 50
        or type(embedded_before) is not int or embedded_before < 0
        or type(embedded_after) is not int
        or embedded_after != embedded_before + 1
    ):
        raise ValueError("invalid noncausal appearance boundary")

    seen, left_info = _fresh_owned_entity_ids(
        before, "ships", perspective, embedded_before,
    )
    current, right_info = _fresh_owned_entity_ids(
        after, "ships", perspective, embedded_after,
    )
    appearing = current - seen
    found = _typed_owned_qualified(after, "ships", appearing, key="id")
    _, sites = _owned_current_source(before, perspective, embedded_before)
    source_missing = any(
        type(turn.get(key)) is not list
        for turn in (before, after) for key in ("ships", "planets", "starbases")
    )
    duplicate_ship_ids = (
        left_info["ambiguous_duplicate_ids"] > 0
        or right_info["ambiguous_duplicate_ids"] > 0
    )
    pp = _pp_trend(before, after, perspective)
    if source_missing or duplicate_ship_ids:
        compatibility = "ABSTAIN_UNQUALIFIED_ARCHIVE_SOURCE"
    elif not appearing:
        compatibility = "NO_NEW_OWN_CURRENT_IDENTITY"
    elif len(appearing) != 1 or len(found) != 1:
        compatibility = "ABSTAIN_MULTIPLE_APPEARANCES"
    elif len(sites) != 1 or len(before["starbases"]) != 1:
        # More than one visible site, or no independently fresh unique
        # site: no basis for assigning a single ship to a particular base.
        compatibility = "ABSTAIN_NO_UNIQUE_CURRENT_BASE"
    else:
        base, ship = sites[0], found[0]
        bh, be = _pos_int(base, "buildhullid"), _pos_int(base, "buildengineid")
        sh, se = _pos_int(ship, "hullid"), _pos_int(ship, "engineid")
        if None in (bh, be, sh, se):
            compatibility = "ABSTAIN_BUILD_TEMPLATE_FIELD_NOT_TYPED_POSITIVE"
        elif bh == sh and be == se:
            compatibility = "OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH"
        elif bh == sh:
            compatibility = "OBSERVED_HULL_ONLY_ENGINE_MISMATCH"
        elif be == se:
            compatibility = "OBSERVED_ENGINE_ONLY_HULL_MISMATCH"
        else:
            compatibility = "OBSERVED_HULL_AND_ENGINE_MISMATCH"
    return {
        "schema": SCHEMA,
        "newly_visible_owned_current_ship_count": len(appearing),
        "before_current_base_vs_new_ship": compatibility,
        "observed_prioritypoints_trend": pp,
        "same_source_window_posthoc_exploratory": True,
        "before_base_build_fields_are_accepted_orders": False,
        "hull_engine_match_proves_construction": False,
        "pp_delta_proves_build_spend": False,
        "all_own_ship_identities_independently_complete": False,
        "warehouse_and_build_resources_independently_complete": False,
        "host_accepted_orders_verified": False,
        "host_causal_verified": False,
        "raw_ids_values_or_orders_emitted": False,
        "evidence": "ARCHIVAL_BEFORE_TEMPLATE_AND_PP_DIRECTION_ASSOCIATIONS_NOT_HOST_CAUSAL",
    }
