"""M2 research-only admission audit for a possible real Host differential.

The local client and operator records are deliberately not interchangeable
with an independently authenticated NuHost submission receipt, independently
witnessed Host boundary, or independently sourced complete owner-current
states. Even a perfect model match must retain these three blockers.

No file/network IO. No private source, game/owner/entity IDs, payload
fragments, hashes, HMAC keys, timestamps, or residual values are returned.
The report is suitable for an aggregate-only diagnostic, never for
promoting a mechanics rule to DIFF_VERIFIED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.planetary_client_sequence_audit import (
    ClientSequenceInvalid, audit_atomic_metadata_bundle,
)
from planets_lab.sim.planetary_conditional_reconciliation import (
    _check_bounded_pair,
    reconcile_all_standard_tech_phase_orders,
    reconcile_explicit_orders,
)
from planets_lab.sim.planetary_owner_capture_v2 import (
    aggregate_owner_observations_v2,
)

EXTERNAL_BLOCKERS = (
    "INDEPENDENT_SERVER_ACCEPTED_ORDER_CONTENT_UNVERIFIED",
    "INDEPENDENT_HOST_BOUNDARY_UNVERIFIED",
    "INDEPENDENT_COMPLETE_PRE_AND_POST_HOST_SOURCE_UNVERIFIED",
)
LOCAL_STATUS = "LOCAL_CONDITIONAL_COMPATIBILITY_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class HostDifferentialEvidenceReadiness:
    schema: str = "planets-lab.m2-host-differential-evidence-readiness.v1"
    status: str = "ABSTAIN_LOCAL_EVIDENCE_MISSING"
    client_metadata_self_consistent: bool = False
    structurally_supported_adjacent_state_pair: bool = False
    full_snapshot_coverage_operator_asserted: bool = False
    complete_owner_v2_signatures_admitted: bool = False
    bounded_model_evaluated: bool = False
    bounded_model_status: str = "NOT_EVALUATED"
    conditional_full_match_count: int = 0
    conditional_resource_match_count: int = 0
    conditional_unsupported_placement_count: int = 0
    external_evidence_blockers: tuple[str, ...] = EXTERNAL_BLOCKERS
    server_order_content_independently_verified: bool = False
    host_boundary_independently_witnessed: bool = False
    complete_pre_post_source_independently_verified: bool = False
    nuhost_execution_verified: bool = False
    diff_verified: bool = False
    raw_private_data_returned: bool = False


def assess_host_differential_evidence(
    before: GameState,
    observed_after: GameState,
    owner_v2_envelopes: Sequence[Any],
    specs: NuStaticSpecs,
    *,
    owner_keyrings: Mapping[int, Mapping[str, bytes]],
    claimed_host_start_utc: str | None,
    asserted_full_snapshot_coverage: bool = False,
    standard_tech_level_caps: Mapping[int, int] | None = None,
    client_metadata_bundle: Mapping[str, Any] | None = None,
    seed: int = 0,
) -> HostDifferentialEvidenceReadiness:
    """Admit local evidence and run only the supported conditional model.

    All owner-signed records are checked against the exact prestate. A
    caller-provided Host time and declared complete snapshots do NOT
    independently authenticate their clock, coverage, origin or server
    acceptance. The client bundle has no game/order identity and is
    NEVER correlated with a particular signed owner record.
    """
    if client_metadata_bundle is None:
        client_ok = False
    else:
        try:
            audit_atomic_metadata_bundle(client_metadata_bundle)
            client_ok = True
        except (ClientSequenceInvalid, TypeError, ValueError, KeyError,
                AttributeError, RecursionError):
            return HostDifferentialEvidenceReadiness(
                status="ABSTAIN_INVALID_CLIENT_METADATA",
            )
    common = {"client_metadata_self_consistent": client_ok}
    try:
        _check_bounded_pair(before, observed_after, allow_starbase_tech=True)
    except (ValueError, TypeError, AttributeError, KeyError):
        return HostDifferentialEvidenceReadiness(
            status="ABSTAIN_UNSUPPORTED_OR_INCOMPLETE_STATE_PAIR", **common,
        )
    common["structurally_supported_adjacent_state_pair"] = True
    # An owner's assertion of full observation can only enable the
    # CONDITIONAL replay. It is not external source verification.
    if asserted_full_snapshot_coverage is not True:
        return HostDifferentialEvidenceReadiness(
            status="ABSTAIN_FULL_SNAPSHOT_COVERAGE_NOT_ASSERTED", **common,
        )
    common["full_snapshot_coverage_operator_asserted"] = True
    admission = aggregate_owner_observations_v2(
        owner_v2_envelopes,
        before,
        owner_keyrings=owner_keyrings,
        observed_host_start_utc=claimed_host_start_utc,
    )
    if not admission.admitted or admission.orders is None:
        # The admission status is one of fixed code-defined labels, not
        # arbitrary key ids, payload content or exception text.
        return HostDifferentialEvidenceReadiness(
            status="ABSTAIN_LOCAL_OWNER_V2_ADMISSION",
            bounded_model_status=(
                admission.status if admission.status.startswith("ABSTAIN_")
                else "ABSTAIN_LOCAL_OWNER_V2_ADMISSION"
            ),
            **common,
        )
    common["complete_owner_v2_signatures_admitted"] = True
    has_tech = any(
        owner.starbase_tech_orders
        for owner in admission.orders.by_player.values()
    )
    if has_tech:
        if standard_tech_level_caps is None:
            return HostDifferentialEvidenceReadiness(
                status="ABSTAIN_TECH_LEVEL_ELIGIBILITY_NOT_ASSERTED", **common,
            )
        outcome = reconcile_all_standard_tech_phase_orders(
            before, observed_after, admission.orders, specs,
            complete_orders=True, complete_snapshots=True,
            standard_tech_level_caps=standard_tech_level_caps, seed=seed,
        )
    else:
        if before.starbases or observed_after.starbases:
            return HostDifferentialEvidenceReadiness(
                status="ABSTAIN_UNMODELED_STARBASE_WITHOUT_TECH_ORDERS", **common,
            )
        outcome = reconcile_explicit_orders(
            before, observed_after, admission.orders, specs,
            complete_orders=True, complete_snapshots=True, seed=seed,
        )
    supported = [
        candidate for candidate in outcome.placements
        if candidate.status == "CONDITIONAL_MODELED"
    ]
    full_matches = sum(x.full_model_state_exact for x in supported)
    resource_matches = sum(x.resource_exact for x in supported)
    unsupported = sum(x.status != "CONDITIONAL_MODELED" for x in outcome.placements)
    status = (
        LOCAL_STATUS if supported and full_matches
        else "LOCAL_CONDITIONAL_RESOURCE_ONLY_NOT_HOST_VERIFIED"
        if supported and resource_matches
        else "LOCAL_CONDITIONAL_MISMATCH_NOT_HOST_VERIFIED"
        if supported else "ABSTAIN_NO_SUPPORTED_CONDITIONAL_MODEL"
    )
    return HostDifferentialEvidenceReadiness(
        status=status,
        bounded_model_evaluated=bool(supported),
        bounded_model_status=outcome.status,
        conditional_full_match_count=full_matches,
        conditional_resource_match_count=resource_matches,
        conditional_unsupported_placement_count=unsupported,
        **common,
    )
