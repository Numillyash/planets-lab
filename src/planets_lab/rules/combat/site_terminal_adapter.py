"""Replay-generated terminal state for a carried ship-combat site.

This module removes precomputed terminal appearances from the mutable site loop.
It replays the *current* factual VCR using the deterministic NuHost Classic
resolver, but overlays mutable combat state from SiteCombatState before replay.

Evidence boundary:

* current VCR pair/sides, seed and static combat setup remain factual inputs;
* mutable owner/race, shield, damage, crew, ammunition/fighters and effective
  weapon counts come from carried SiteCombatState;
* the factual current-VCR start vector is used only as an exact consistency
  check against carried state before replay;
* no N+1 pair, side, start vector or terminal state is consumed here;
* capture transfer identity is derived from the carried opponent state, not from
  post-combat appearances.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .mutable_queue import ShipCaptureTransfer
from .nu import ReplayUnsupported, replay_nuhost_from_nu_catalog
from .site_state import SiteCombatState


class SiteTerminalReplayUnresolved(ValueError):
    """Current-VCR replay input or carried-state projection is unresolved."""


@dataclass(frozen=True, slots=True)
class SiteVcrStartComparison:
    exact: bool
    left_ship_id: int
    right_ship_id: int
    comparisons: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class SiteTerminalReplayResult:
    resolved: bool | None
    terminals_by_ship_id: Mapping[int, Mapping[str, Any]]
    capture_transfers_by_ship_id: Mapping[int, ShipCaptureTransfer]
    left_ship_id: int | None = None
    right_ship_id: int | None = None
    start_comparison: SiteVcrStartComparison | None = None
    replay_result: Mapping[str, Any] | None = None
    reason: str | None = None


_CARRIED_SIDE_FIELDS: tuple[tuple[str, str], ...] = (
    ("hull_id", "hullid"),
    ("race_id", "raceid"),
    ("shield", "shield"),
    ("damage", "damage"),
    ("crew", "crew"),
    ("torpedoes", "torpedos"),
    ("fighters", "fighters"),
    ("beam_count", "beamcount"),
    ("launcher_count", "launchercount"),
    ("bay_count", "baycount"),
)

_TERMINAL_FIELDS = (
    "shield",
    "damage",
    "crew",
    "torpedoes",
    "fighters",
    "destroyed",
    "captured",
)


def _integer(value: Any, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SiteTerminalReplayUnresolved("required integer state is unresolved")
    result = int(value)
    if positive and result <= 0:
        raise SiteTerminalReplayUnresolved(
            "required positive integer state is unresolved"
        )
    return result


def _side_payload(
    vcr_payload: Mapping[str, Any],
    side_name: str,
) -> Mapping[str, Any]:
    raw = vcr_payload.get(side_name)
    if not isinstance(raw, Mapping):
        raise SiteTerminalReplayUnresolved(
            f"current VCR {side_name} payload missing"
        )
    return raw


def _ship_id_for_side(
    vcr_payload: Mapping[str, Any],
    side_name: str,
) -> int:
    return _integer(
        _side_payload(vcr_payload, side_name).get("objectid"),
        positive=True,
    )


def compare_site_state_to_vcr_start(
    state: SiteCombatState,
    *,
    vcr_payload: Mapping[str, Any],
) -> SiteVcrStartComparison:
    """Compare carried mutable state to the factual current-VCR start vector."""

    left_ship_id = _ship_id_for_side(vcr_payload, "left")
    right_ship_id = _ship_id_for_side(vcr_payload, "right")
    if left_ship_id == right_ship_id:
        raise SiteTerminalReplayUnresolved("current VCR contains duplicate ship ids")

    comparisons: list[Mapping[str, Any]] = []
    for side_name, ship_id, owner_key in (
        ("left", left_ship_id, "leftownerid"),
        ("right", right_ship_id, "rightownerid"),
    ):
        active = state.active_ships.get(ship_id)
        if not isinstance(active, Mapping):
            raise SiteTerminalReplayUnresolved(
                f"ship {ship_id}: missing from carried active state"
            )
        side = _side_payload(vcr_payload, side_name)

        carried_owner = _integer(active.get("owner_id"), positive=True)
        factual_owner = _integer(vcr_payload.get(owner_key), positive=True)
        comparisons.append(
            {
                "ship_id": ship_id,
                "side": side_name,
                "field": "owner_id",
                "carried": carried_owner,
                "factual": factual_owner,
                "exact": carried_owner == factual_owner,
            }
        )

        for active_key, vcr_key in _CARRIED_SIDE_FIELDS:
            carried_value = _integer(
                active.get(active_key),
                positive=active_key in {"hull_id", "race_id"},
            )
            factual_value = _integer(
                side.get(vcr_key),
                positive=active_key in {"hull_id", "race_id"},
            )
            comparisons.append(
                {
                    "ship_id": ship_id,
                    "side": side_name,
                    "field": active_key,
                    "carried": carried_value,
                    "factual": factual_value,
                    "exact": carried_value == factual_value,
                }
            )

    return SiteVcrStartComparison(
        exact=all(row["exact"] is True for row in comparisons),
        left_ship_id=left_ship_id,
        right_ship_id=right_ship_id,
        comparisons=tuple(comparisons),
    )


def _overlay_carried_start(
    state: SiteCombatState,
    *,
    vcr_payload: Mapping[str, Any],
    comparison: SiteVcrStartComparison,
) -> dict[str, Any]:
    payload = deepcopy(dict(vcr_payload))
    for side_name, ship_id, owner_key in (
        ("left", comparison.left_ship_id, "leftownerid"),
        ("right", comparison.right_ship_id, "rightownerid"),
    ):
        active = state.active_ships[ship_id]
        raw_side = payload.get(side_name)
        if not isinstance(raw_side, dict):
            raw_side = dict(_side_payload(payload, side_name))
            payload[side_name] = raw_side

        payload[owner_key] = _integer(active.get("owner_id"), positive=True)
        for active_key, vcr_key in _CARRIED_SIDE_FIELDS:
            raw_side[vcr_key] = _integer(
                active.get(active_key),
                positive=active_key in {"hull_id", "race_id"},
            )
    return payload


def _terminal_from_replay_side(
    replay_side: Mapping[str, Any],
) -> dict[str, Any]:
    terminal: dict[str, Any] = {}
    for field in _TERMINAL_FIELDS:
        value = replay_side.get(field)
        if field in {"destroyed", "captured"}:
            if not isinstance(value, bool):
                raise SiteTerminalReplayUnresolved(
                    f"replay terminal {field} flag unresolved"
                )
            terminal[field] = value
        else:
            terminal[field] = _integer(value)
    return terminal


def build_site_terminal_replay_batch(
    state: SiteCombatState,
    *,
    vcr_payload: Mapping[str, Any],
    beams: Sequence[Mapping[str, Any]],
    torpedoes: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any],
    replay_resolver: Callable[..., Mapping[str, Any]] = replay_nuhost_from_nu_catalog,
) -> SiteTerminalReplayResult:
    """Generate one terminal batch from carried state plus current-VCR setup."""

    try:
        comparison = compare_site_state_to_vcr_start(
            state,
            vcr_payload=vcr_payload,
        )
    except SiteTerminalReplayUnresolved as exc:
        return SiteTerminalReplayResult(
            resolved=None,
            terminals_by_ship_id={},
            capture_transfers_by_ship_id={},
            reason=f"current_vcr_start_unresolved:{exc}",
        )

    if comparison.exact is not True:
        return SiteTerminalReplayResult(
            resolved=None,
            terminals_by_ship_id={},
            capture_transfers_by_ship_id={},
            left_ship_id=comparison.left_ship_id,
            right_ship_id=comparison.right_ship_id,
            start_comparison=comparison,
            reason="carried_start_differs_from_current_vcr",
        )

    payload = _overlay_carried_start(
        state,
        vcr_payload=vcr_payload,
        comparison=comparison,
    )

    try:
        replay = replay_resolver(
            payload,
            beams=beams,
            torpedoes=torpedoes,
            settings=settings,
        )
    except (ReplayUnsupported, KeyError, TypeError, ValueError) as exc:
        return SiteTerminalReplayResult(
            resolved=None,
            terminals_by_ship_id={},
            capture_transfers_by_ship_id={},
            left_ship_id=comparison.left_ship_id,
            right_ship_id=comparison.right_ship_id,
            start_comparison=comparison,
            reason=f"current_vcr_replay_unresolved:{type(exc).__name__}:{exc}",
        )

    terminals: dict[int, Mapping[str, Any]] = {}
    for side_name, ship_id in (
        ("left", comparison.left_ship_id),
        ("right", comparison.right_ship_id),
    ):
        replay_side = replay.get(side_name)
        if not isinstance(replay_side, Mapping):
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id={},
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason=f"current_vcr_replay_{side_name}_missing",
            )
        replay_object_id = replay_side.get("object_id")
        if replay_object_id != ship_id:
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id={},
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason=f"current_vcr_replay_{side_name}_identity_mismatch",
            )
        try:
            terminals[ship_id] = _terminal_from_replay_side(replay_side)
        except SiteTerminalReplayUnresolved as exc:
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id={},
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason=f"current_vcr_terminal_unresolved:{exc}",
            )

    captured = [
        ship_id
        for ship_id, terminal in terminals.items()
        if terminal.get("captured") is True
    ]
    if len(captured) > 1:
        return SiteTerminalReplayResult(
            resolved=None,
            terminals_by_ship_id=terminals,
            capture_transfers_by_ship_id={},
            left_ship_id=comparison.left_ship_id,
            right_ship_id=comparison.right_ship_id,
            start_comparison=comparison,
            replay_result=replay,
            reason="capture_cardinality_unresolved",
        )

    transfers: dict[int, ShipCaptureTransfer] = {}
    if captured:
        prize_ship_id = captured[0]
        captor_ship_id = (
            comparison.right_ship_id
            if prize_ship_id == comparison.left_ship_id
            else comparison.left_ship_id
        )
        captor_terminal = terminals[captor_ship_id]
        if (
            captor_terminal.get("destroyed") is True
            or captor_terminal.get("captured") is True
        ):
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id=terminals,
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason="capture_captor_not_surviving",
            )

        captor = state.active_ships.get(captor_ship_id)
        if not isinstance(captor, Mapping):
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id=terminals,
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason="capture_captor_state_missing",
            )
        try:
            owner_id = _integer(captor.get("owner_id"), positive=True)
            race_id = _integer(captor.get("race_id"), positive=True)
        except SiteTerminalReplayUnresolved as exc:
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id=terminals,
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason=f"capture_captor_identity_unresolved:{exc}",
            )

        fed = captor.get("federation_crew_bonus")
        liz = captor.get("lizard_crew_bonus")
        if not isinstance(fed, bool) or not isinstance(liz, bool):
            return SiteTerminalReplayResult(
                resolved=None,
                terminals_by_ship_id=terminals,
                capture_transfers_by_ship_id={},
                left_ship_id=comparison.left_ship_id,
                right_ship_id=comparison.right_ship_id,
                start_comparison=comparison,
                replay_result=replay,
                reason="capture_captor_bonus_state_unresolved",
            )

        transfers[prize_ship_id] = ShipCaptureTransfer(
            new_owner_id=owner_id,
            new_race_id=race_id,
            new_federation_crew_bonus=fed,
            new_lizard_crew_bonus=liz,
        )

    return SiteTerminalReplayResult(
        resolved=True,
        terminals_by_ship_id=terminals,
        capture_transfers_by_ship_id=transfers,
        left_ship_id=comparison.left_ship_id,
        right_ship_id=comparison.right_ship_id,
        start_comparison=comparison,
        replay_result=replay,
    )
