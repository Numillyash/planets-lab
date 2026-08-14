from __future__ import annotations

import gzip
import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from planets_lab.core import GameState
from planets_lab.data.nu_loadturn import import_loadturn

from .archive import TurnMember, read_archive_member, turn_members


class CorpusNormalizationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ArchiveTurnSnapshot:
    member: TurnMember
    game_id: int
    player_id: int
    embedded_turn: int
    snapshot_hash: str
    mechanics_payload: Mapping[str, Any]

    @property
    def archive_turn(self) -> int:
        return self.member.turn

    def import_state(self) -> GameState:
        return import_loadturn(
            {"rst": dict(self.mechanics_payload)},
            game_id=self.game_id,
            turn=self.embedded_turn,
        )


@dataclass(frozen=True, slots=True)
class ArchiveTurnTransition:
    before: ArchiveTurnSnapshot
    after: ArchiveTurnSnapshot

    def __post_init__(self) -> None:
        if self.before.game_id != self.after.game_id:
            raise ValueError("transition crosses games")
        if self.before.player_id != self.after.player_id:
            raise ValueError("transition crosses player streams")
        if self.after.archive_turn != self.before.archive_turn + 1:
            raise ValueError("transition is not consecutive in archive order")

    @property
    def embedded_turn_delta(self) -> int:
        return self.after.embedded_turn - self.before.embedded_turn


@dataclass(frozen=True, slots=True)
class ArchiveCorpusSummary:
    snapshots: int
    players: tuple[int, ...]
    archive_turns: tuple[int, ...]
    missing_grid_cells: tuple[tuple[int, int], ...]
    transitions: int
    embedded_consecutive_transitions: int


def _required_int(raw: Mapping[str, Any], key: str, *, label: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CorpusNormalizationError(f"{label}.{key} must be an integer")
    return value


def _decode_member_json(data: bytes, member: TurnMember) -> tuple[dict[str, Any], bytes]:
    raw = read_archive_member(data, member.name)
    decoded = raw
    if decoded[:2] == b"\x1f\x8b":
        try:
            decoded = gzip.decompress(decoded)
        except OSError as exc:
            raise CorpusNormalizationError(
                f"{member.name}: invalid gzip turn payload"
            ) from exc
    try:
        parsed = json.loads(decoded.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusNormalizationError(
            f"{member.name}: turn payload is not UTF-8 JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise CorpusNormalizationError(
            f"{member.name}: turn payload must be a JSON object"
        )
    return parsed, decoded


def _minimal_player(raw: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    result = {"id": _required_int(raw, "id", label=label)}
    race_id = raw.get("raceid")
    if race_id is not None:
        if isinstance(race_id, bool) or not isinstance(race_id, int):
            raise CorpusNormalizationError(f"{label}.raceid must be an integer")
        result["raceid"] = race_id
    return result


def _object_list(raw: Mapping[str, Any], key: str, *, member: str) -> list[dict[str, Any]]:
    value = raw.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise CorpusNormalizationError(f"{member}: {key} must be a list")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise CorpusNormalizationError(
                f"{member}: {key}[{index}] must be an object"
            )
        result.append(dict(item))
    return result


def mechanics_projection(parsed: Mapping[str, Any], *, member: str) -> dict[str, Any]:
    """Keep Host-relevant state while dropping account identity/secrets/messages.

    Finished-game .trn payloads contain fields such as player email, username and
    savekey. The historical corpus must not propagate those fields into derived
    datasets. Player records are therefore reduced to slot/race identity; entity
    records retain their mechanical fields.
    """

    game_raw = parsed.get("game")
    player_raw = parsed.get("player")
    players_raw = parsed.get("players", [])
    if not isinstance(game_raw, Mapping):
        raise CorpusNormalizationError(f"{member}: game must be an object")
    if not isinstance(player_raw, Mapping):
        raise CorpusNormalizationError(f"{member}: player must be an object")
    if not isinstance(players_raw, list):
        raise CorpusNormalizationError(f"{member}: players must be a list")

    game_id = _required_int(game_raw, "id", label=f"{member}.game")
    turn = _required_int(game_raw, "turn", label=f"{member}.game")
    player = _minimal_player(player_raw, label=f"{member}.player")

    players: list[dict[str, Any]] = []
    for index, raw_player in enumerate(players_raw):
        if not isinstance(raw_player, Mapping):
            raise CorpusNormalizationError(
                f"{member}: players[{index}] must be an object"
            )
        players.append(
            _minimal_player(raw_player, label=f"{member}.players[{index}]")
        )

    return {
        "game": {"id": game_id, "turn": turn},
        "player": player,
        "players": players,
        "planets": _object_list(parsed, "planets", member=member),
        "ships": _object_list(parsed, "ships", member=member),
        "starbases": _object_list(parsed, "starbases", member=member),
        "ionstorms": _object_list(parsed, "ionstorms", member=member),
    }


def load_archive_snapshots(data: bytes) -> tuple[ArchiveTurnSnapshot, ...]:
    snapshots: list[ArchiveTurnSnapshot] = []
    for member in turn_members(data):
        parsed, decoded = _decode_member_json(data, member)
        projection = mechanics_projection(parsed, member=member.name)
        game = projection["game"]
        player = projection["player"]
        game_id = _required_int(game, "id", label=f"{member.name}.game")
        player_id = _required_int(player, "id", label=f"{member.name}.player")
        embedded_turn = _required_int(game, "turn", label=f"{member.name}.game")
        if player_id != member.player:
            raise CorpusNormalizationError(
                f"{member.name}: filename player {member.player} != payload player {player_id}"
            )
        snapshots.append(
            ArchiveTurnSnapshot(
                member=member,
                game_id=game_id,
                player_id=player_id,
                embedded_turn=embedded_turn,
                snapshot_hash=hashlib.sha256(decoded).hexdigest(),
                mechanics_payload=projection,
            )
        )

    if snapshots:
        game_ids = {snapshot.game_id for snapshot in snapshots}
        if len(game_ids) != 1:
            raise CorpusNormalizationError(
                f"archive contains multiple game ids: {sorted(game_ids)}"
            )
    return tuple(sorted(snapshots, key=lambda item: (item.player_id, item.archive_turn)))


def consecutive_archive_transitions(
    snapshots: tuple[ArchiveTurnSnapshot, ...] | list[ArchiveTurnSnapshot],
) -> tuple[ArchiveTurnTransition, ...]:
    by_player: dict[int, list[ArchiveTurnSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        by_player[snapshot.player_id].append(snapshot)

    transitions: list[ArchiveTurnTransition] = []
    for player_id in sorted(by_player):
        ordered = sorted(by_player[player_id], key=lambda item: item.archive_turn)
        for before, after in zip(ordered, ordered[1:]):
            if after.archive_turn == before.archive_turn + 1:
                transitions.append(ArchiveTurnTransition(before=before, after=after))
    return tuple(transitions)


def summarize_archive_snapshots(
    snapshots: tuple[ArchiveTurnSnapshot, ...] | list[ArchiveTurnSnapshot],
) -> ArchiveCorpusSummary:
    records = tuple(snapshots)
    players = tuple(sorted({snapshot.player_id for snapshot in records}))
    turns = tuple(sorted({snapshot.archive_turn for snapshot in records}))
    actual = {(snapshot.player_id, snapshot.archive_turn) for snapshot in records}
    expected = {(player, turn) for player in players for turn in turns}
    transitions = consecutive_archive_transitions(records)
    return ArchiveCorpusSummary(
        snapshots=len(records),
        players=players,
        archive_turns=turns,
        missing_grid_cells=tuple(sorted(expected - actual)),
        transitions=len(transitions),
        embedded_consecutive_transitions=sum(
            transition.embedded_turn_delta == 1 for transition in transitions
        ),
    )
