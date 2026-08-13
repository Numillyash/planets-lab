from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from planets_lab.core import GameState
from planets_lab.data.nu_loadturn import import_loadturn


SCHEMA = "planets-intel.validation-observation.v1"


class RealGameDatasetError(ValueError):
    pass


@dataclass(frozen=True, slots=True, order=True)
class ObservationStreamKey:
    observer_planets_account_id: int
    source_player_slot_id: int
    source: str


@dataclass(frozen=True, slots=True)
class ObservationBatch:
    game_id: int
    turn: int
    batch_id: int
    stream: ObservationStreamKey
    snapshot_hash: str
    players: tuple[Mapping[str, Any], ...]
    planets: tuple[Mapping[str, Any], ...]
    ships: tuple[Mapping[str, Any], ...]
    starbases: tuple[Mapping[str, Any], ...]

    def as_loadturn_payload(self) -> dict[str, Any]:
        source_player = next(
            (
                dict(player)
                for player in self.players
                if _required_int(player, "id") == self.stream.source_player_slot_id
            ),
            {"id": self.stream.source_player_slot_id},
        )
        return {
            "rst": {
                "game": {"id": self.game_id, "turn": self.turn},
                "player": source_player,
                "players": [dict(player) for player in self.players],
                "planets": [dict(planet) for planet in self.planets],
                "ships": [dict(ship) for ship in self.ships],
                "starbases": [dict(starbase) for starbase in self.starbases],
            }
        }

    def import_state(self) -> GameState:
        return import_loadturn(self.as_loadturn_payload())


@dataclass(frozen=True, slots=True)
class RealGameTransition:
    before: ObservationBatch
    after: ObservationBatch

    def __post_init__(self) -> None:
        if self.before.game_id != self.after.game_id:
            raise ValueError("transition crosses games")
        if self.before.stream != self.after.stream:
            raise ValueError("transition crosses observation streams")
        if self.after.turn != self.before.turn + 1:
            raise ValueError("transition is not consecutive")


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    records: int
    streams: int
    min_turn: int | None
    max_turn: int | None
    duplicate_turn_snapshots: int
    consecutive_transitions: int


def _required_int(raw: Mapping[str, Any], key: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RealGameDatasetError(f"{key} must be an integer")
    return value


def _required_str(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise RealGameDatasetError(f"{key} must be a non-empty string")
    return value


def _object_list(raw: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise RealGameDatasetError(f"{key} must be a list")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise RealGameDatasetError(f"{key}[{index}] must be an object")
        result.append(item)
    return tuple(result)


def parse_record(raw: Mapping[str, Any]) -> ObservationBatch:
    if raw.get("schema") != SCHEMA:
        raise RealGameDatasetError(
            f"unsupported schema {raw.get('schema')!r}; expected {SCHEMA!r}"
        )
    return ObservationBatch(
        game_id=_required_int(raw, "game_id"),
        turn=_required_int(raw, "turn"),
        batch_id=_required_int(raw, "batch_id"),
        stream=ObservationStreamKey(
            observer_planets_account_id=_required_int(
                raw, "observer_planets_account_id"
            ),
            source_player_slot_id=_required_int(raw, "source_player_slot_id"),
            source=_required_str(raw, "source"),
        ),
        snapshot_hash=_required_str(raw, "snapshot_hash"),
        players=_object_list(raw, "players"),
        planets=_object_list(raw, "planets"),
        ships=_object_list(raw, "ships"),
        starbases=_object_list(raw, "starbases"),
    )


def load_jsonl(path: str | Path) -> tuple[ObservationBatch, ...]:
    batches: list[ObservationBatch] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RealGameDatasetError(
                    f"line {line_number}: invalid JSON: {exc}"
                ) from exc
            if not isinstance(raw, Mapping):
                raise RealGameDatasetError(
                    f"line {line_number}: record must be an object"
                )
            try:
                batches.append(parse_record(raw))
            except RealGameDatasetError as exc:
                raise RealGameDatasetError(f"line {line_number}: {exc}") from exc
    return tuple(batches)


def latest_batches_by_stream_turn(
    batches: Iterable[ObservationBatch],
) -> tuple[ObservationBatch, ...]:
    latest: dict[tuple[ObservationStreamKey, int], ObservationBatch] = {}
    for batch in batches:
        key = (batch.stream, batch.turn)
        previous = latest.get(key)
        if previous is None or batch.batch_id > previous.batch_id:
            latest[key] = batch
    return tuple(
        sorted(
            latest.values(),
            key=lambda batch: (batch.stream, batch.turn, batch.batch_id),
        )
    )


def consecutive_transitions(
    batches: Iterable[ObservationBatch],
) -> tuple[RealGameTransition, ...]:
    by_stream: dict[ObservationStreamKey, list[ObservationBatch]] = defaultdict(list)
    for batch in latest_batches_by_stream_turn(batches):
        by_stream[batch.stream].append(batch)

    result: list[RealGameTransition] = []
    for stream in sorted(by_stream):
        ordered = sorted(by_stream[stream], key=lambda batch: batch.turn)
        for before, after in zip(ordered, ordered[1:]):
            if after.turn == before.turn + 1:
                result.append(RealGameTransition(before=before, after=after))
    return tuple(result)


def summarize(batches: Iterable[ObservationBatch]) -> DatasetSummary:
    records = tuple(batches)
    turns = [batch.turn for batch in records]
    unique = latest_batches_by_stream_turn(records)
    return DatasetSummary(
        records=len(records),
        streams=len({batch.stream for batch in records}),
        min_turn=min(turns) if turns else None,
        max_turn=max(turns) if turns else None,
        duplicate_turn_snapshots=len(records) - len(unique),
        consecutive_transitions=len(consecutive_transitions(records)),
    )
