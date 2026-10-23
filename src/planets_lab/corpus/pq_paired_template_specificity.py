"""Non-independent within-window specificity contrast for PPQ observations.

Compare two categorical observations on the *same approved consecutive
archive pair*: the prior current base's configured template versus one
newly visible own-current ship, and the SAME base template versus
previously observed, continuously fresh own ships in that window.

Never report entity IDs or raw specs; never infer build causality, odds
ratios, p-values, or statistical independence from overlapping windows.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SCHEMA = "planets-lab.pq-paired-template-specificity.v1"
FULL_NEW_MATCH = "OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH"
NEW_OBSERVED = {
    FULL_NEW_MATCH,
    "OBSERVED_HULL_ONLY_ENGINE_MISMATCH",
    "OBSERVED_ENGINE_ONLY_HULL_MISMATCH",
    "OBSERVED_HULL_AND_ENGINE_MISMATCH",
}
NEW_REFUSALS = {
    "ABSTAIN_UNQUALIFIED_ARCHIVE_SOURCE",
    "ABSTAIN_MULTIPLE_APPEARANCES",
    "ABSTAIN_NO_UNIQUE_CURRENT_BASE",
    "ABSTAIN_BUILD_TEMPLATE_FIELD_NOT_TYPED_POSITIVE",
}
BASELINE_STATUS = {
    "REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS",
    "ABSTAIN_SOURCE_ARRAY_OR_SHIP_ID_AMBIGUOUS",
    "ABSTAIN_NO_UNIQUE_CURRENT_BASE",
    "ABSTAIN_NO_PERSISTENT_OWNED_SHIP_REFERENCE",
    "ABSTAIN_BASE_TEMPLATE_UNTYPED",
    "ABSTAIN_NO_TYPED_PERSISTENT_SHIP_SPECS",
}


def paired_template_specificity(
    new_ship: Mapping[str, Any],
    existing_ships: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(new_ship) is not dict or type(existing_ships) is not dict
        or new_ship.get("host_causal_verified") is not False
        or existing_ships.get("host_causal_verified") is not False
        or new_ship.get("hull_engine_match_proves_construction") is not False
        or existing_ships.get("persistent_ships_are_independent_negative_samples") is not False
    ):
        raise ValueError("unsupported causality or provenance contract")
    n = new_ship.get("newly_visible_owned_current_ship_count")
    n_ref = existing_ships.get("newly_visible_owned_ship_identity_count")
    status = new_ship.get("before_current_base_vs_new_ship")
    reference_status = existing_ships.get("status")
    total = existing_ships.get("typed_stable_ship_base_template_comparisons")
    matching = existing_ships.get("matches_before_base_hull_and_engine")
    mismatching = existing_ships.get("does_not_match_before_base_hull_and_engine")
    untyped = existing_ships.get("stable_ships_with_untyped_hull_or_engine")
    stable = existing_ships.get("stable_owned_ship_id_intersection_count")
    if (
        type(n) is not int or n < 0 or type(n_ref) is not int or n != n_ref
        or status not in NEW_OBSERVED | NEW_REFUSALS | {"NO_NEW_OWN_CURRENT_IDENTITY"}
        or reference_status not in BASELINE_STATUS
        or any(type(v) is not int or v < 0 for v in (
            total, matching, mismatching, untyped, stable,
        ))
        or matching + mismatching != total
        or total + untyped > stable
    ):
        raise ValueError("inconsistent source-qualified pairing counts")

    if n != 1:
        category = "ABSTAIN_NOT_EXACTLY_ONE_APPEARING_SHIP"
    elif status not in NEW_OBSERVED:
        category = "ABSTAIN_NEW_SHIP_BASE_COMPARISON_UNQUALIFIED"
    elif reference_status != "REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS":
        category = "ABSTAIN_PERSISTENT_REFERENCE_UNQUALIFIED"
    elif total == 0:
        category = "ABSTAIN_NO_TYPED_PERSISTENT_SHIP_REFERENCE"
    elif status == FULL_NEW_MATCH and matching == 0:
        category = "NEW_SHIP_MATCHES_BASE_NONE_OF_PERSISTENT_SHIPS_MATCH"
    elif status == FULL_NEW_MATCH:
        category = "NEW_SHIP_MATCHES_BASE_SOME_PERSISTENT_SHIPS_MATCH"
    elif matching == 0:
        category = "NEW_SHIP_DOES_NOT_FULLY_MATCH_NO_PERSISTENT_SHIPS_MATCH"
    else:
        category = "NEW_SHIP_DOES_NOT_FULLY_MATCH_SOME_PERSISTENT_SHIPS_MATCH"

    return {
        "schema": SCHEMA,
        "paired_observational_category": category,
        "one_newly_visible_ship_template_compared": n == 1 and status in NEW_OBSERVED,
        "new_ship_matches_full_prior_base_template": (
            n == 1 and status == FULL_NEW_MATCH
        ),
        "same_window_persistent_ship_comparison_count": total,
        "same_window_persistent_ship_template_match_count": matching,
        "same_window_persistent_ship_template_mismatch_count": mismatching,
        "same_window_persistent_ship_untyped_spec_count": untyped,
        "same_window_persistent_ship_reference_status": reference_status,
        "same_window_control_is_independent": False,
        "across_window_independence_established": False,
        "pairing_is_independent_statistical_validation": False,
        "observed_appearance_proves_construction": False,
        "base_configuration_is_host_accepted_order": False,
        "host_causal_verified": False,
        "raw_entity_ids_or_values_emitted": False,
        "evidence": "WITHIN_WINDOW_SOURCE_QUALIFIED_EXPLORATORY_PAIRING_NOT_HOST_PARITY",
    }
