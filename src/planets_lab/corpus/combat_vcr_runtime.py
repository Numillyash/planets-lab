from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .corpus_db_runtime import member_refs_for_turns, reconstruct_members


class CombatVcrInputConflict(ValueError):
    """Multiple source members disagree on replay-relevant current-VCR input."""


@dataclass(frozen=True, slots=True)
class CompactCombatVcrCase:
    game_id: int
    battle_turn: int
    vcr_id: int
    payload: Mapping[str, Any]
    beams: tuple[Mapping[str, Any], ...]
    torpedoes: tuple[Mapping[str, Any], ...]
    settings: Mapping[str, Any]
    observation_count: int
    source_members: tuple[str, ...]


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _objects(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _minimal_records(
    rows: Sequence[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for row in rows:
        reduced = {key: deepcopy(row[key]) for key in keys if key in row}
        result.append(reduced)
    result.sort(
        key=lambda row: (
            _integer(row.get("id")) is None,
            _integer(row.get("id")) or 0,
            json.dumps(row, sort_keys=True, separators=(",", ":")),
        )
    )
    return tuple(result)


def _minimal_settings(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    for key, value in raw.items():
        folded = str(key).casefold()
        if folded in {"combatrng", "combat_rng"}:
            return {"combatrng": deepcopy(value)}
    return {}


def _signature(
    *,
    payload: Mapping[str, Any],
    beams: Sequence[Mapping[str, Any]],
    torpedoes: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any],
) -> str:
    encoded = json.dumps(
        {
            "payload": payload,
            "beams": list(beams),
            "torpedoes": list(torpedoes),
            "settings": settings,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def combat_vcr_cases_for_turns(
    connection: Any,
    *,
    game_id: int,
    battle_turns: set[int],
) -> dict[tuple[int, int], CompactCombatVcrCase]:
    """Return unique replay-relevant VCR inputs from compact corpus members.

    Only current-VCR payload, minimal weapon catalog fields and combat RNG are
    retained. Ship/planet snapshots and other post-state fields are deliberately
    not exposed through this adapter.

    Duplicate perspective observations must agree on every retained replay input
    or the VCR fails closed with CombatVcrInputConflict.
    """

    if not battle_turns:
        return {}

    refs = member_refs_for_turns(
        connection,
        game_id=game_id,
        turns=set(int(turn) for turn in battle_turns),
        include_embedded_turn=True,
    )

    observations: dict[
        tuple[int, int],
        list[tuple[str, str, Mapping[str, Any], tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...], Mapping[str, Any]]],
    ] = {}

    for ref, member_payload in reconstruct_members(connection, refs):
        game = member_payload.get("game")
        if not isinstance(game, Mapping):
            continue
        observed_game_id = _integer(game.get("id"))
        embedded_turn = _integer(game.get("turn"))
        if observed_game_id != game_id or embedded_turn is None:
            continue

        beams = _minimal_records(
            _objects(member_payload, "beams"),
            ("id", "damage", "crewkill"),
        )
        torpedoes = _minimal_records(
            _objects(member_payload, "torpedos"),
            ("id", "damage", "crewkill", "combatrange"),
        )
        settings = _minimal_settings(member_payload.get("settings"))

        for raw_vcr in _objects(member_payload, "vcrs"):
            vcr_id = _integer(raw_vcr.get("id"))
            battle_turn = _integer(raw_vcr.get("turn"))
            if battle_turn is None:
                battle_turn = embedded_turn
            if vcr_id is None or battle_turn not in battle_turns:
                continue

            signature = _signature(
                payload=raw_vcr,
                beams=beams,
                torpedoes=torpedoes,
                settings=settings,
            )
            observations.setdefault((battle_turn, vcr_id), []).append(
                (
                    signature,
                    ref.source_member_name,
                    deepcopy(raw_vcr),
                    beams,
                    torpedoes,
                    deepcopy(settings),
                )
            )

    result: dict[tuple[int, int], CompactCombatVcrCase] = {}
    for key, rows in sorted(observations.items()):
        signatures = {row[0] for row in rows}
        if len(signatures) != 1:
            turn, vcr_id = key
            raise CombatVcrInputConflict(
                f"game {game_id} turn {turn} VCR {vcr_id}: "
                "replay input conflict across source members"
            )

        _signature_value, _member, payload, beams, torpedoes, settings = rows[0]
        turn, vcr_id = key
        result[key] = CompactCombatVcrCase(
            game_id=game_id,
            battle_turn=turn,
            vcr_id=vcr_id,
            payload=payload,
            beams=tuple(deepcopy(list(beams))),
            torpedoes=tuple(deepcopy(list(torpedoes))),
            settings=deepcopy(dict(settings)),
            observation_count=len(rows),
            source_members=tuple(sorted({row[1] for row in rows})),
        )

    return result
