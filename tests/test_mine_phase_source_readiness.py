"""Only safe metadata. Positive readiness never means Host authentication."""
from dataclasses import FrozenInstanceError, replace
import pytest

from planets_lab.rules.mine_phase_source_readiness import (
    AFTER, BEFORE, CONSECUTIVE_TURNS, EVIDENCE, SAME_TURN,
    SOURCE_ARCHIVAL, SOURCE_CLIENT_SAVE, SOURCE_SYNTHETIC, SOURCE_HOST_CLAIM,
    MinePhaseSourceManifest, MinePhaseSourceMetadataAbstain,
    assess_mine_decay_phase_source,
)


def sample(**kw):
    kwargs = dict(
        source_kind=SOURCE_SYNTHETIC,
        turn_relation=SAME_TURN,
        before_stage=BEFORE,
        after_stage=AFTER,
        before_field_count=2,
        after_field_count=1,
        full_before_roster_declared=True,
        full_after_roster_declared=True,
        stable_owner_center_and_type_declared=True,
        exact_nebula_membership_declared=True,
        standard_settings_declared=True,
        no_intervening_host_mutations_declared=True,
        phase_adjacency_declared=True,
        server_order_receipt_declared=False,
        receipt_integrity_externally_checked_declared=False,
    )
    kwargs.update(kw)
    return MinePhaseSourceManifest(**kwargs)


def assess(**kw):
    return assess_mine_decay_phase_source(manifest=sample(**kw))


def test_complete_synthetic_source_only_conditional():
    result = assess()
    assert result.classification == "SYNTHETIC_CONDITIONAL_ONLY"
    assert result.blockers == ("SYNTHETIC_NOT_REAL_HOST_WITNESS",)
    assert result.declared_input_completeness
    assert result.can_consider_for_conditional_isolated_audit
    assert result.evidence == EVIDENCE
    assert not result.any_real_host_receipt_authenticated
    assert not result.real_server_orders_accepted_verified
    assert not result.real_host_phase_boundary_verified
    assert not result.host_diff_verified


def test_fully_asserted_host_receipt_remains_unverified_even_if_flags_all_true():
    result = assess(
        source_kind=SOURCE_HOST_CLAIM,
        server_order_receipt_declared=True,
        receipt_integrity_externally_checked_declared=True,
    )
    assert result.classification == "DECLARED_COMPLETE_NEEDS_INDEPENDENT_AUTHENTICATION"
    assert result.blockers == ("EXTERNAL_RECEIPT_ASSERTION_UNAUTHENTICATED",)
    assert result.can_consider_for_conditional_isolated_audit
    assert not result.any_real_host_receipt_authenticated
    assert not result.real_server_orders_accepted_verified
    assert not result.host_diff_verified


@pytest.mark.parametrize("kind,reason", [
    (SOURCE_ARCHIVAL, "ARCHIVAL_TURNS_NOT_PHASE_BOUNDARIES"),
    (SOURCE_CLIENT_SAVE, "CLIENT_SAVE_ACK_NOT_SERVER_HOST_EXECUTION"),
])
def test_archive_and_client_save_never_promote_even_with_claimed_perfect_flags(kind, reason):
    result = assess(
        source_kind=kind,
        server_order_receipt_declared=True,
        receipt_integrity_externally_checked_declared=True,
    )
    assert result.classification == "NOT_READY"
    assert reason in result.blockers
    assert not result.can_consider_for_conditional_isolated_audit
    assert not result.host_diff_verified


def test_consecutive_turns_cannot_be_passed_as_adjacent_host_phase():
    result = assess(
        source_kind=SOURCE_ARCHIVAL,
        turn_relation=CONSECUTIVE_TURNS,
        before_stage="START_OF_TURN",
        after_stage="END_OF_TURN",
    )
    assert result.classification == "NOT_READY"
    assert "NOT_SAME_HOST_TURN" in result.blockers
    assert "NOT_IMMEDIATE_DECAY_STAGE_PAIR" in result.blockers


@pytest.mark.parametrize("name,reason", [
    ("full_before_roster_declared", "INCOMPLETE_BEFORE_ROSTER"),
    ("full_after_roster_declared", "INCOMPLETE_AFTER_ROSTER"),
    ("stable_owner_center_and_type_declared", "UNPROVEN_FIELD_IDENTITY"),
    ("exact_nebula_membership_declared", "UNPROVEN_NEBULA_MEMBERSHIP"),
    ("standard_settings_declared", "UNKNOWN_STANDARD_GAME_SETTINGS"),
    ("no_intervening_host_mutations_declared", "INTERVENING_PHASES_NOT_EXCLUDED"),
    ("phase_adjacency_declared", "ADJACENT_PHASE_NOT_WITNESSED"),
])
def test_required_source_dimensions_are_machine_readable_blockers(name, reason):
    result = assess(**{name: False})
    assert result.classification == "NOT_READY"
    assert reason in result.blockers
    assert not result.can_consider_for_conditional_isolated_audit


def test_unauthenticated_real_host_source_requires_receipt_metadata_but_not_provenance_proof():
    result = assess(source_kind=SOURCE_HOST_CLAIM)
    assert "SERVER_ACCEPTED_ORDERS_NOT_DECLARED" in result.blockers
    assert "RECEIPT_INTEGRITY_NOT_EXTERNALLY_CHECKED" in result.blockers
    assert result.classification == "NOT_READY"
    assert not result.real_server_orders_accepted_verified


def test_field_creation_during_isolated_decay_is_unsupported():
    result = assess(before_field_count=2, after_field_count=3)
    assert "POST_ROSTER_ADDS_FIELDS_IN_DECAY_ONLY_WINDOW" in result.blockers
    assert result.classification == "NOT_READY"


def test_determinism_and_read_only_metadata():
    manifest = sample()
    r = assess_mine_decay_phase_source(manifest=manifest)
    assert r == assess_mine_decay_phase_source(manifest=manifest)
    with pytest.raises(FrozenInstanceError):
        r.classification = "DIFF_VERIFIED"
    with pytest.raises(FrozenInstanceError):
        manifest.source_kind = SOURCE_HOST_CLAIM


@pytest.mark.parametrize("changes", [
    {"source_kind": "PUBLIC_REPLAY_PROVEN_HOST"},
    {"source_kind": None},
    {"source_kind": True},
    {"turn_relation": "TWELVE_TURNS"},
    {"turn_relation": None},
    {"before_stage": None},
    {"before_stage": 10},
    {"after_stage": None},
    {"before_field_count": True},
    {"before_field_count": -1},
    {"before_field_count": 129},
    {"after_field_count": "1"},
    {"after_field_count": 1.0},
    {"full_before_roster_declared": 1},
    {"full_after_roster_declared": None},
    {"stable_owner_center_and_type_declared": "true"},
    {"exact_nebula_membership_declared": 1},
    {"standard_settings_declared": None},
    {"no_intervening_host_mutations_declared": 0},
    {"phase_adjacency_declared": 1},
    {"server_order_receipt_declared": None},
    {"receipt_integrity_externally_checked_declared": 1},
])
def test_untyped_ambiguous_or_unbounded_manifest_rejected(changes):
    with pytest.raises(MinePhaseSourceMetadataAbstain):
        assess(**changes)


def test_bare_dict_manifest_refused_no_raw_capture_or_dynamic_fields():
    with pytest.raises(MinePhaseSourceMetadataAbstain, match="typed"):
        assess_mine_decay_phase_source(manifest=sample().__dict__ if hasattr(sample(), "__dict__") else {})
