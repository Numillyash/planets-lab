#!/usr/bin/env python3
"""Executable transcription of the frozen AFSim 1.31 queue candidate AFSIM-R1.

Evidence authority: EXTERNAL_IMPLEMENTATION only.

This module intentionally models AFSim, not NuHost.  It is suitable for
bounded differential tests after the rule has been frozen from binary evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class AFSimShip:
    ship_id: int
    owner: int
    friendly_code: str = ""
    fuel: bool = True
    kill: bool = False
    primary_enemy: int = 0
    crew: int = 1
    damage: int = 0
    beam_count: int = 0
    torpedo_tubes: int = 0
    torpedoes: int = 0
    fighter_bays: int = 0
    fighters: int = 0

    def can_fight(self) -> bool:
        return (
            self.beam_count > 0
            or (self.torpedo_tubes > 0 and self.torpedoes > 0)
            or (self.fighter_bays > 0 and self.fighters > 0)
        )


@dataclass(frozen=True)
class AFSimPreparedShip:
    ship: AFSimShip
    attack_value: int
    effective_kill: bool
    effective_primary_enemy: int

    @property
    def sort_key(self) -> tuple[int, int, int, int]:
        return (
            0 if self.effective_kill else 1,
            self.ship.owner,
            self.attack_value,
            self.ship.ship_id,
        )


@dataclass(frozen=True)
class AFSimPair:
    initiator_id: int
    opponent_id: int
    left_id: int
    right_id: int
    phase: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def attack_value_from_friendly_code(value: Any) -> int:
    """Reproduce AFSim's 0x5627 friendly-code attack-value normalization.

    AFSim copies the 3-character FC, requires the first character to be a
    decimal digit, removes trailing non-digits, then converts the remaining
    string as a decimal integer.  Conversion failure or zero maps to 1000.

    This matches the AFSim manual examples:
      xxx -> 1000
      1xx -> 1
      10x -> 10
      01x -> 1
      999 -> 999
      18x -> 18
      x23 -> 1000
    """

    if not isinstance(value, str):
        return 1000
    code = value[:3]
    if not code or not code[0].isdigit():
        return 1000
    while code and not code[-1].isdigit():
        code = code[:-1]
    if not code or not code.isdigit():
        return 1000
    parsed = int(code, 10)
    return parsed if parsed > 0 else 1000


def prepare_ship(ship: AFSimShip) -> AFSimPreparedShip:
    """Apply the ordinary 0x5627 pre-sort metadata normalization."""

    pe = int(ship.primary_enemy)
    if pe == ship.owner:
        pe = 0
    return AFSimPreparedShip(
        ship=ship,
        attack_value=attack_value_from_friendly_code(ship.friendly_code),
        effective_kill=bool(ship.kill and ship.fuel),
        effective_primary_enemy=pe,
    )


def sort_ships(ships: Iterable[AFSimShip]) -> list[AFSimPreparedShip]:
    prepared = [prepare_ship(ship) for ship in ships]
    return sorted(prepared, key=lambda row: row.sort_key)


def select_next_pair(ships: Iterable[AFSimShip]) -> AFSimPair | None:
    """Return AFSim's next ship-vs-ship pair after a full re-sort/restart.

    This is the frozen 0x5627 -> 0x51c6 path:
      * sort complete persistent entries;
      * restart selector from index 1;
      * KILL phase using the first sorted entry only;
      * otherwise Primary Enemy phase scanning initiators from the beginning;
      * canonicalize selected VCR sides by ascending ship ID.
    """

    ordered = sort_ships(ships)
    if len(ordered) < 2:
        return None

    def valid_pair(a: AFSimPreparedShip, b: AFSimPreparedShip) -> bool:
        return (
            a.ship.ship_id != b.ship.ship_id
            and a.ship.owner != b.ship.owner
            and b.ship.fuel
            and (a.ship.can_fight() or b.ship.can_fight())
        )

    first = ordered[0]
    if first.effective_kill and first.ship.fuel:
        for candidate in ordered:
            if valid_pair(first, candidate):
                return _pair(first.ship.ship_id, candidate.ship.ship_id, "kill")

    for initiator in ordered:
        pe = initiator.effective_primary_enemy
        if pe <= 0 or not initiator.ship.fuel:
            continue
        for candidate in ordered:
            if candidate.ship.owner != pe:
                continue
            if not valid_pair(initiator, candidate):
                continue
            return _pair(
                initiator.ship.ship_id,
                candidate.ship.ship_id,
                "primary_enemy",
            )

    return None


def _pair(initiator_id: int, opponent_id: int, phase: str) -> AFSimPair:
    left_id = min(initiator_id, opponent_id)
    right_id = max(initiator_id, opponent_id)
    return AFSimPair(
        initiator_id=initiator_id,
        opponent_id=opponent_id,
        left_id=left_id,
        right_id=right_id,
        phase=phase,
    )


def apply_capture(
    ships: Iterable[AFSimShip],
    *,
    captured_ship_id: int,
    captor_ship_id: int,
) -> list[AFSimShip]:
    """Apply AFSim's recovered VCR capture mutation to persistent state.

    Only owner and crew are changed by the capture handler itself.
    Fuel/KILL/PE/friendly-code metadata remain attached to the captured entry;
    ordinary prepare_ship() normalization applies on the next re-sort.
    """

    rows = list(ships)
    by_id = {ship.ship_id: ship for ship in rows}
    captured = by_id.get(captured_ship_id)
    captor = by_id.get(captor_ship_id)
    if captured is None:
        raise ValueError(f"captured ship {captured_ship_id} is missing")
    if captor is None:
        raise ValueError(f"captor ship {captor_ship_id} is missing")

    result: list[AFSimShip] = []
    for ship in rows:
        if ship.ship_id == captured_ship_id:
            result.append(replace(ship, owner=captor.owner, crew=10))
        else:
            result.append(ship)
    return result


def ship_from_mapping(row: Mapping[str, Any]) -> AFSimShip:
    def integer(name: str, default: int = 0) -> int:
        value = row.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return int(value)

    ship_id = integer("ship_id")
    owner = integer("owner")
    if ship_id <= 0:
        raise ValueError("ship_id must be positive")
    if owner <= 0:
        raise ValueError(f"ship {ship_id}: owner must be positive")
    return AFSimShip(
        ship_id=ship_id,
        owner=owner,
        friendly_code=str(row.get("friendly_code", "")),
        fuel=bool(row.get("fuel", False)),
        kill=bool(row.get("kill", False)),
        primary_enemy=integer("primary_enemy"),
        crew=integer("crew", 1),
        damage=integer("damage"),
        beam_count=integer("beam_count"),
        torpedo_tubes=integer("torpedo_tubes"),
        torpedoes=integer("torpedoes"),
        fighter_bays=integer("fighter_bays"),
        fighters=integer("fighters"),
    )


def evaluate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_ships = payload.get("ships")
    if (
        not isinstance(raw_ships, Sequence)
        or isinstance(raw_ships, (str, bytes))
        or not all(isinstance(row, Mapping) for row in raw_ships)
    ):
        raise ValueError("payload.ships must be a list of objects")

    ships = [ship_from_mapping(row) for row in raw_ships]
    capture = payload.get("capture")
    if capture is not None:
        if not isinstance(capture, Mapping):
            raise ValueError("payload.capture must be an object or null")
        captured_ship_id = capture.get("captured_ship_id")
        captor_ship_id = capture.get("captor_ship_id")
        if (
            isinstance(captured_ship_id, bool)
            or not isinstance(captured_ship_id, int)
            or isinstance(captor_ship_id, bool)
            or not isinstance(captor_ship_id, int)
        ):
            raise ValueError("capture ids must be integers")
        ships = apply_capture(
            ships,
            captured_ship_id=int(captured_ship_id),
            captor_ship_id=int(captor_ship_id),
        )

    prepared = sort_ships(ships)
    pair = select_next_pair(ships)
    return {
        "model": "AFSIM-R1",
        "authority": "EXTERNAL_IMPLEMENTATION",
        "sorted": [
            {
                **asdict(row.ship),
                "attack_value": row.attack_value,
                "effective_kill": row.effective_kill,
                "effective_primary_enemy": row.effective_primary_enemy,
                "sort_key": list(row.sort_key),
            }
            for row in prepared
        ],
        "next_pair": pair.as_dict() if pair is not None else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the frozen external AFSim 1.31 AFSIM-R1 queue model."
    )
    parser.add_argument("input", type=Path, help="JSON payload containing ships")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("input must contain a JSON object")
        report = evaluate_payload(payload)
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"output: {args.output}")
        else:
            print(rendered, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
