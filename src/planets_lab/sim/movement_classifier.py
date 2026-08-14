from __future__ import annotations

from dataclasses import dataclass

from planets_lab.core import GameState, Ship


@dataclass(frozen=True, slots=True)
class MovementMissionConvention:
    """Nu mission IDs used to split movement intent before tow resolution.

    The defaults match the observed/classic Nu mission numbering used by
    loadturn: 6 = Try to Tow, 7 = Intercept. Keeping this injectable avoids
    baking the numbering into the phase machinery itself.
    """

    tow_mission_ids: frozenset[int] = frozenset({6})
    intercept_mission_ids: frozenset[int] = frozenset({7})


@dataclass(frozen=True, slots=True)
class MovementIntentClassification:
    """Pre-resolution movement buckets for one GameState.

    `move_most_candidate_ship_ids` are only candidates. A ship successfully
    towed by another vessel must later be removed after tow-lock resolution.
    HYP is separated because it occurs in Move Most but cannot use ordinary
    normal-movement geometry.
    """

    tow_attempt_ship_ids: frozenset[int]
    move_most_candidate_ship_ids: frozenset[int]
    intercept_ship_ids: frozenset[int]
    special_move_most_ship_ids: frozenset[int]

    @property
    def all_ship_ids(self) -> frozenset[int]:
        return frozenset().union(
            self.tow_attempt_ship_ids,
            self.move_most_candidate_ship_ids,
            self.intercept_ship_ids,
            self.special_move_most_ship_ids,
        )


def _mission_id(ship: Ship) -> int | None:
    if ship.mission is None:
        return None
    try:
        return int(ship.mission)
    except (TypeError, ValueError):
        return None


def classify_movement_intents(
    state: GameState,
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> MovementIntentClassification:
    """Classify ships into Host movement intent buckets.

    Host ordering is Tow -> Move Most -> Intercept. This classifier deliberately
    runs before tow-lock contests and therefore does not attempt to determine
    which tow targets are actually locked or moved. Ships with HYP friendly
    code are isolated from ordinary Move Most so they cannot accidentally use
    the normal movement planner.

    Unowned ghost ships cannot execute missions or self-movement. They stay in
    the ordinary Move Most bucket solely so downstream movement can preserve the
    normal warp-zero/external-movement path (for example, a resolved external
    displacement) without honoring stale mission/friendly-code fields.
    """

    tow_attempts: set[int] = set()
    move_most: set[int] = set()
    intercepts: set[int] = set()
    special_move_most: set[int] = set()

    for ship_id, ship in state.ships.items():
        if ship.owner_id is None:
            move_most.add(ship_id)
            continue

        mission_id = _mission_id(ship)

        if mission_id in convention.tow_mission_ids:
            tow_attempts.add(ship_id)
            continue

        if mission_id in convention.intercept_mission_ids:
            intercepts.add(ship_id)
            continue

        if ship.friendly_code.strip().lower() == "hyp":
            special_move_most.add(ship_id)
            continue

        move_most.add(ship_id)

    result = MovementIntentClassification(
        tow_attempt_ship_ids=frozenset(tow_attempts),
        move_most_candidate_ship_ids=frozenset(move_most),
        intercept_ship_ids=frozenset(intercepts),
        special_move_most_ship_ids=frozenset(special_move_most),
    )

    if result.all_ship_ids != frozenset(state.ships):
        raise AssertionError("movement classification did not partition all ships")

    return result
