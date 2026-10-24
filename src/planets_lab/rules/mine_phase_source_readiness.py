"""Privacy-safe metadata gate for *claimed* mine natural-decay phase witnesses.

A public archive T-1 -> T or client save ACK cannot authenticate an
IMMEDIATELY_BEFORE -> IMMEDIATELY_AFTER isolated Host phase. This module
never reads raw game entities, personal orders, HAR, .trn or credentials.
It classifies declared metadata only, and never independently verifies
a Host receipt, an accepted order, phase chronology or DIFF_VERIFIED.

No action is taken based on this classification. It cannot promote a
caller-controlled Boolean into a real Host attestation.
"""
from __future__ import annotations
from dataclasses import dataclass

SOURCE_ARCHIVAL = "PUBLIC_ARCHIVAL_CONSECUTIVE_TURNS"
SOURCE_CLIENT_SAVE = "CLIENT_SAVE_ACKNOWLEDGEMENT"
SOURCE_SYNTHETIC = "SYNTHETIC_ISOLATED_PHASE_BOUNDARY"
SOURCE_HOST_CLAIM = "EXTERNALLY_ASSERTED_HOST_PHASE_RECEIPT"
SOURCES = frozenset((
    SOURCE_ARCHIVAL, SOURCE_CLIENT_SAVE, SOURCE_SYNTHETIC, SOURCE_HOST_CLAIM,
))
BEFORE = "IMMEDIATELY_BEFORE_NATURAL_DECAY"
AFTER = "IMMEDIATELY_AFTER_NATURAL_DECAY"
SAME_TURN = "SAME_HOST_TURN"
CONSECUTIVE_TURNS = "CONSECUTIVE_ARCHIVAL_TURNS"
MAX_FIELD_COUNT = 128
EVIDENCE = "SOURCE_METADATA_READINESS_ONLY_NO_HOST_ATTESTATION"


class MinePhaseSourceMetadataAbstain(ValueError):
    """Invalid, ambiguous or unsupported source metadata."""


@dataclass(frozen=True, slots=True)
class MinePhaseSourceManifest:
    source_kind: str
    turn_relation: str
    before_stage: str
    after_stage: str
    before_field_count: int
    after_field_count: int
    full_before_roster_declared: bool
    full_after_roster_declared: bool
    stable_owner_center_and_type_declared: bool
    exact_nebula_membership_declared: bool
    standard_settings_declared: bool
    no_intervening_host_mutations_declared: bool
    phase_adjacency_declared: bool
    server_order_receipt_declared: bool
    receipt_integrity_externally_checked_declared: bool


@dataclass(frozen=True, slots=True)
class MinePhaseSourceAssessment:
    source_kind: str
    classification: str
    blockers: tuple[str, ...]
    declared_input_completeness: bool
    can_consider_for_conditional_isolated_audit: bool
    evidence: str = EVIDENCE
    any_real_host_receipt_authenticated: bool = False
    real_server_orders_accepted_verified: bool = False
    real_host_phase_boundary_verified: bool = False
    host_diff_verified: bool = False


def _integer(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_FIELD_COUNT


def assess_mine_decay_phase_source(
    *, manifest: MinePhaseSourceManifest,
) -> MinePhaseSourceAssessment:
    """Reject impossible/unsafe metadata; expose deterministic blockers.

    A declared HOST receipt is never authenticated here. Even a fully
    declared manifest is at most *eligible for human/external verification*.
    """
    if type(manifest) is not MinePhaseSourceManifest:
        raise MinePhaseSourceMetadataAbstain("typed metadata manifest required")
    if type(manifest.source_kind) is not str or manifest.source_kind not in SOURCES:
        raise MinePhaseSourceMetadataAbstain("unsupported or untyped source category")
    if type(manifest.turn_relation) is not str or manifest.turn_relation not in (
        SAME_TURN, CONSECUTIVE_TURNS,
    ):
        raise MinePhaseSourceMetadataAbstain("unsupported temporal relation")
    if (
        type(manifest.before_stage) is not str
        or type(manifest.after_stage) is not str
    ):
        raise MinePhaseSourceMetadataAbstain("stage labels must be exact strings")
    if not _integer(manifest.before_field_count) or not _integer(manifest.after_field_count):
        raise MinePhaseSourceMetadataAbstain("untyped, negative or unbounded counts")
    fields = (
        "full_before_roster_declared", "full_after_roster_declared",
        "stable_owner_center_and_type_declared", "exact_nebula_membership_declared",
        "standard_settings_declared", "no_intervening_host_mutations_declared",
        "phase_adjacency_declared", "server_order_receipt_declared",
        "receipt_integrity_externally_checked_declared",
    )
    if any(type(getattr(manifest, name)) is not bool for name in fields):
        raise MinePhaseSourceMetadataAbstain("source flags must be exact booleans")

    blockers: list[str] = []
    if manifest.source_kind == SOURCE_ARCHIVAL:
        blockers.append("ARCHIVAL_TURNS_NOT_PHASE_BOUNDARIES")
    elif manifest.source_kind == SOURCE_CLIENT_SAVE:
        blockers.append("CLIENT_SAVE_ACK_NOT_SERVER_HOST_EXECUTION")
    elif manifest.source_kind == SOURCE_SYNTHETIC:
        blockers.append("SYNTHETIC_NOT_REAL_HOST_WITNESS")
    else:
        blockers.append("EXTERNAL_RECEIPT_ASSERTION_UNAUTHENTICATED")

    if manifest.turn_relation != SAME_TURN:
        blockers.append("NOT_SAME_HOST_TURN")
    if manifest.before_stage != BEFORE or manifest.after_stage != AFTER:
        blockers.append("NOT_IMMEDIATE_DECAY_STAGE_PAIR")

    required = (
        ("full_before_roster_declared", "INCOMPLETE_BEFORE_ROSTER"),
        ("full_after_roster_declared", "INCOMPLETE_AFTER_ROSTER"),
        ("stable_owner_center_and_type_declared", "UNPROVEN_FIELD_IDENTITY"),
        ("exact_nebula_membership_declared", "UNPROVEN_NEBULA_MEMBERSHIP"),
        ("standard_settings_declared", "UNKNOWN_STANDARD_GAME_SETTINGS"),
        ("no_intervening_host_mutations_declared", "INTERVENING_PHASES_NOT_EXCLUDED"),
        ("phase_adjacency_declared", "ADJACENT_PHASE_NOT_WITNESSED"),
    )
    for name, issue in required:
        if getattr(manifest, name) is not True:
            blockers.append(issue)
    if manifest.after_field_count > manifest.before_field_count:
        blockers.append("POST_ROSTER_ADDS_FIELDS_IN_DECAY_ONLY_WINDOW")

    if manifest.source_kind == SOURCE_HOST_CLAIM:
        if not manifest.server_order_receipt_declared:
            blockers.append("SERVER_ACCEPTED_ORDERS_NOT_DECLARED")
        if not manifest.receipt_integrity_externally_checked_declared:
            blockers.append("RECEIPT_INTEGRITY_NOT_EXTERNALLY_CHECKED")

    # Readiness is *declarative*; a caller claiming completeness cannot turn
    # archived turns or save ACKs into Host-phase proof.
    structurally_complete = not any(
        issue for issue in blockers
        if issue not in (
            "ARCHIVAL_TURNS_NOT_PHASE_BOUNDARIES",
            "CLIENT_SAVE_ACK_NOT_SERVER_HOST_EXECUTION",
            "SYNTHETIC_NOT_REAL_HOST_WITNESS",
            "EXTERNAL_RECEIPT_ASSERTION_UNAUTHENTICATED",
        )
    )
    if manifest.source_kind == SOURCE_SYNTHETIC and structurally_complete:
        classification = "SYNTHETIC_CONDITIONAL_ONLY"
        conditional = True
    elif manifest.source_kind == SOURCE_HOST_CLAIM and structurally_complete:
        classification = "DECLARED_COMPLETE_NEEDS_INDEPENDENT_AUTHENTICATION"
        conditional = True
    else:
        classification = "NOT_READY"
        conditional = False
    return MinePhaseSourceAssessment(
        source_kind=manifest.source_kind,
        classification=classification,
        blockers=tuple(blockers),
        declared_input_completeness=structurally_complete,
        can_consider_for_conditional_isolated_audit=conditional,
    )
