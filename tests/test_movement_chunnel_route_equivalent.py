from __future__ import annotations

from planets_lab.corpus.compiled_movement_labels import COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA
from planets_lab.corpus.movement_chunnel_context import (
    MOVEMENT_CHUNNEL_CONTEXT_GAME_SCHEMA,
    ObservedChunnelEvent,
)
from planets_lab.corpus.movement_chunnel_match import route_equivalent_chunnel_category


def _event(*, initiator: int, owner: int = 1) -> ObservedChunnelEvent:
    return ObservedChunnelEvent(
        before_archive_turn=10,
        after_archive_turn=11,
        initiator_ship_id=initiator,
        target_ship_id=456,
        owner_id=owner,
        pre_chunnel_position=(100, 100),
        destination=(300, 300),
    )


def test_route_equivalent_semantics_bump_cache_schemas() -> None:
    # The compiled context-label schema can advance when later L2 mechanics are
    # added. Chunnel's standalone cache schema remains v2 because its own
    # route-equivalent semantics have not changed since that bump.
    assert COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA == "planets-lab.compiled-movement-context-labels.v5"
    assert MOVEMENT_CHUNNEL_CONTEXT_GAME_SCHEMA == "planets-lab.movement-chunnel-context-game.v2"


def test_empty_route_equivalent_match_set_is_unexplained() -> None:
    assert route_equivalent_chunnel_category([], ship_id=10, owner_id=1) is None


def test_duplicate_same_route_events_still_explain_same_owner_passenger() -> None:
    matches = [_event(initiator=123), _event(initiator=124)]

    assert route_equivalent_chunnel_category(
        matches,
        ship_id=10,
        owner_id=1,
    ) == "passenger_same_owner"


def test_duplicate_same_route_events_still_explain_other_owner_passenger() -> None:
    matches = [_event(initiator=123), _event(initiator=124)]

    assert route_equivalent_chunnel_category(
        matches,
        ship_id=10,
        owner_id=2,
    ) == "passenger_other_owner"


def test_role_ambiguity_does_not_make_route_ambiguous() -> None:
    matches = [_event(initiator=123), _event(initiator=124)]

    # Ship 123 is the initiator of one valid event and a same-owner passenger
    # of the other. Movement is still explained; only the descriptive role is
    # ambiguous.
    assert route_equivalent_chunnel_category(
        matches,
        ship_id=123,
        owner_id=1,
    ) == "route_equivalent_multiple_roles"
