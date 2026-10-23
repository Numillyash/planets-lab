"""Exploratory within-window baseline: already observed owned ships vs base template.

For a consecutively observed own ship (same typed ID owned and fresh on
both adjacent embedded turns), compare its BEFORE hull+engine to a single
BEFORE owner-current starbase's configured buildhullid/buildengineid.

This is a descriptive *negative-control-like reference*, NOT an independent
negative sample: a persistent ship might itself have been built previously.
Outputs contain only aggregate counts/categories, never raw IDs or values.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from planets_lab.corpus.pq_observed_transition import _fresh_owned_entity_ids
from planets_lab.corpus.pq_ship_appearance_fields import (
    _owned_current_source, _typed_owned_qualified,
)
from planets_lab.corpus.pq_ship_appearance_correlates import _pos_int

SCHEMA = "planets-lab.pq-existing-ship-template-reference.v1"


def existing_ship_template_reference(
    before: Mapping[str, Any], after: Mapping[str, Any], *,
    perspective: int, embedded_before: int, embedded_after: int,
) -> dict[str, Any]:
    if (
        type(perspective) is not int or not 1 <= perspective <= 50
        or type(embedded_before) is not int or embedded_before < 0
        or type(embedded_after) is not int
        or embedded_after != embedded_before + 1
    ):
        raise ValueError("invalid baseline source boundary")

    prior, prior_source = _fresh_owned_entity_ids(
        before, "ships", perspective, embedded_before,
    )
    next_ids, next_source = _fresh_owned_entity_ids(
        after, "ships", perspective, embedded_after,
    )
    stable_ids = prior & next_ids
    new_ids = next_ids - prior
    qualified_bases = _owned_current_source(
        before, perspective, embedded_before,
    )[1]

    missing = any(
        type(snap.get(group)) is not list
        for snap in (before, after)
        for group in ("planets", "ships", "starbases")
    )
    if missing or prior_source["ambiguous_duplicate_ids"] or next_source["ambiguous_duplicate_ids"]:
        status = "ABSTAIN_SOURCE_ARRAY_OR_SHIP_ID_AMBIGUOUS"
    elif len(qualified_bases) != 1 or len(before["starbases"]) != 1:
        status = "ABSTAIN_NO_UNIQUE_CURRENT_BASE"
    elif not stable_ids:
        status = "ABSTAIN_NO_PERSISTENT_OWNED_SHIP_REFERENCE"
    else:
        status = "REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS"

    comparable = 0
    matches = 0
    mismatches = 0
    untyped = 0
    if status == "REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS":
        base = qualified_bases[0]
        bh = _pos_int(base, "buildhullid")
        be = _pos_int(base, "buildengineid")
        if bh is None or be is None:
            status = "ABSTAIN_BASE_TEMPLATE_UNTYPED"
        else:
            stable = _typed_owned_qualified(
                before, "ships", stable_ids, key="id",
            )
            for ship in stable:
                sh = _pos_int(ship, "hullid")
                se = _pos_int(ship, "engineid")
                if sh is None or se is None:
                    untyped += 1
                else:
                    comparable += 1
                    if bh == sh and be == se:
                        matches += 1
                    else:
                        mismatches += 1
            if comparable == 0:
                status = "ABSTAIN_NO_TYPED_PERSISTENT_SHIP_SPECS"
    return {
        "schema": SCHEMA,
        "status": status,
        "stratum": (
            "WINDOW_WITH_NEWLY_VISIBLE_OWN_SHIP"
            if new_ids else "WINDOW_WITHOUT_NEWLY_VISIBLE_OWN_SHIP"
        ),
        "stable_owned_ship_id_intersection_count": len(stable_ids),
        "typed_stable_ship_base_template_comparisons": comparable,
        "matches_before_base_hull_and_engine": matches,
        "does_not_match_before_base_hull_and_engine": mismatches,
        "stable_ships_with_untyped_hull_or_engine": untyped,
        "newly_visible_owned_ship_identity_count": len(new_ids),
        "same_frozen_exploratory_windows": True,
        "persistent_ships_are_independent_negative_samples": False,
        "new_ship_is_verified_construction": False,
        "base_template_is_authenticated_accepted_order": False,
        "host_causal_verified": False,
        "private_ids_or_values_emitted": False,
        "evidence": "REPEATED_PERSISTENT_SHIP_TEMPLATE_REFERENCE_NOT_HOST_CAUSAL",
    }
