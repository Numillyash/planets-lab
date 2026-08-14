from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .normalizer import ArchiveTurnSnapshot, CorpusNormalizationError, load_archive_snapshots

STARBASE_OWNER_RE = re.compile(r"starbase on planet (?P<planet>\d+) has no resolvable owner")
SHIP_RE = re.compile(r"unowned (?:ghost )?ship (?P<ship>\d+)")


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _records(snapshot: ArchiveTurnSnapshot, key: str) -> list[Mapping[str, Any]]:
    value = snapshot.mechanics_payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _find_id(snapshot: ArchiveTurnSnapshot, key: str, entity_id: int) -> Mapping[str, Any] | None:
    for raw in _records(snapshot, key):
        if _intish(raw.get("id")) == entity_id:
            return raw
    return None


def _find_starbase(snapshot: ArchiveTurnSnapshot, planet_id: int) -> Mapping[str, Any] | None:
    for raw in _records(snapshot, "starbases"):
        candidate = _intish(raw.get("planetid", raw.get("planet_id")))
        if candidate == planet_id:
            return raw
    return None


def _owner(raw: Mapping[str, Any] | None) -> int | None:
    if raw is None:
        return None
    if "ownerid" in raw:
        return _intish(raw.get("ownerid"))
    return _intish(raw.get("owner_id"))


def _freshness(raw: Mapping[str, Any] | None, embedded_turn: int) -> tuple[int | None, bool | None]:
    if raw is None:
        return None, None
    infoturn = _intish(raw.get("infoturn"))
    if infoturn is None:
        return None, None
    return infoturn, infoturn < embedded_turn


def _compact_turns(turns: list[int]) -> str:
    if not turns:
        return "-"
    ordered = sorted(set(turns))
    if len(ordered) == 1:
        return str(ordered[0])
    return f"{ordered[0]}..{ordered[-1]}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose whether canonical import failures in a finished-game /loadall "
            "archive are stale player-perspective observations, and compare the same "
            "entities across player perspectives without printing identity fields."
        )
    )
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()

    try:
        snapshots = load_archive_snapshots(args.archive.read_bytes())
    except (OSError, ValueError, CorpusNormalizationError) as exc:
        print(str(exc))
        return 2

    by_turn: dict[int, list[ArchiveTurnSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        by_turn[snapshot.archive_turn].append(snapshot)

    starbase_failures: list[tuple[ArchiveTurnSnapshot, int]] = []
    ship_failures: list[tuple[ArchiveTurnSnapshot, int]] = []
    other_failures: Counter[str] = Counter()

    for snapshot in snapshots:
        try:
            snapshot.import_state()
        except Exception as exc:  # diagnostic boundary
            message = str(exc)
            starbase_match = STARBASE_OWNER_RE.search(message)
            ship_match = SHIP_RE.search(message)
            if starbase_match:
                starbase_failures.append((snapshot, int(starbase_match.group("planet"))))
            elif ship_match:
                ship_failures.append((snapshot, int(ship_match.group("ship"))))
            else:
                other_failures[f"{type(exc).__name__}: {message}"] += 1

    print("===== CORPUS FRESHNESS / CROSS-PERSPECTIVE DIAGNOSTICS =====")
    print(f"archive:                    {args.archive}")
    print(f"snapshots:                  {len(snapshots)}")
    print(f"starbase_failures:          {len(starbase_failures)}")
    print(f"ship_failures:              {len(ship_failures)}")
    print(f"other_failures:             {sum(other_failures.values())}")

    base_failure_freshness: Counter[tuple[Any, ...]] = Counter()
    for snapshot, planet_id in starbase_failures:
        base = _find_starbase(snapshot, planet_id)
        planet = _find_id(snapshot, "planets", planet_id)
        base_info, base_stale = _freshness(base, snapshot.embedded_turn)
        planet_info, planet_stale = _freshness(planet, snapshot.embedded_turn)
        base_failure_freshness[(
            snapshot.player_id,
            planet_id,
            base_info,
            base_stale,
            planet_info,
            planet_stale,
            _intish(base.get("raceid")) if base is not None else None,
            _owner(base),
            _owner(planet),
            _intish(planet.get("clans")) if planet is not None else None,
        )] += 1

    if base_failure_freshness:
        print("starbase_failure_freshness:")
        for key, count in sorted(base_failure_freshness.items(), key=lambda item: repr(item[0])):
            (
                player,
                planet_id,
                base_info,
                base_stale,
                planet_info,
                planet_stale,
                race_id,
                base_owner,
                planet_owner,
                clans,
            ) = key
            print(
                "  "
                f"count={count} player={player} planet={planet_id} "
                f"base_infoturn={base_info!r} base_stale={base_stale!r} "
                f"planet_infoturn={planet_info!r} planet_stale={planet_stale!r} "
                f"starbase_raceid={race_id!r} starbase_ownerid={base_owner!r} "
                f"planet_ownerid={planet_owner!r} planet_clans={clans!r}"
            )

    ship_failure_freshness: Counter[tuple[Any, ...]] = Counter()
    for snapshot, ship_id in ship_failures:
        ship = _find_id(snapshot, "ships", ship_id)
        info, stale = _freshness(ship, snapshot.embedded_turn)
        ship_failure_freshness[(
            snapshot.player_id,
            ship_id,
            info,
            stale,
            _owner(ship),
            _intish(ship.get("crew")) if ship is not None else None,
            _intish(ship.get("warp")) if ship is not None else None,
            _intish(ship.get("x")) if ship is not None else None,
            _intish(ship.get("y")) if ship is not None else None,
        )] += 1

    if ship_failure_freshness:
        print("ship_failure_freshness:")
        for key, count in sorted(ship_failure_freshness.items(), key=lambda item: repr(item[0])):
            player, ship_id, info, stale, owner, crew, warp, x, y = key
            print(
                "  "
                f"count={count} player={player} ship={ship_id} infoturn={info!r} "
                f"stale={stale!r} ownerid={owner!r} crew={crew!r} warp={warp!r} "
                f"x={x!r} y={y!r}"
            )

    implicated_bases = sorted({planet_id for _, planet_id in starbase_failures})
    if implicated_bases:
        print("starbase_cross_perspective_signatures:")
        signatures: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        failure_turns = {snapshot.archive_turn for snapshot, _ in starbase_failures}
        for turn in sorted(failure_turns):
            for snapshot in sorted(by_turn[turn], key=lambda item: item.player_id):
                for planet_id in implicated_bases:
                    base = _find_starbase(snapshot, planet_id)
                    planet = _find_id(snapshot, "planets", planet_id)
                    if base is None and planet is None:
                        continue
                    base_info, _ = _freshness(base, snapshot.embedded_turn)
                    planet_info, _ = _freshness(planet, snapshot.embedded_turn)
                    signature = (
                        snapshot.player_id,
                        planet_id,
                        base is not None,
                        base_info,
                        _intish(base.get("raceid")) if base is not None else None,
                        _owner(base),
                        planet is not None,
                        planet_info,
                        _owner(planet),
                        _intish(planet.get("clans")) if planet is not None else None,
                    )
                    signatures[signature].append(turn)
        for signature, turns in sorted(signatures.items(), key=lambda item: repr(item[0])):
            (
                player,
                planet_id,
                base_present,
                base_info,
                race_id,
                base_owner,
                planet_present,
                planet_info,
                planet_owner,
                clans,
            ) = signature
            print(
                "  "
                f"turns={_compact_turns(turns)} count={len(turns)} player={player} "
                f"planet={planet_id} base_present={base_present} base_infoturn={base_info!r} "
                f"starbase_raceid={race_id!r} starbase_ownerid={base_owner!r} "
                f"planet_present={planet_present} planet_infoturn={planet_info!r} "
                f"planet_ownerid={planet_owner!r} planet_clans={clans!r}"
            )

    implicated_ships = sorted({ship_id for _, ship_id in ship_failures})
    if implicated_ships:
        print("ship_cross_perspective_signatures:")
        signatures: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        failure_turns = {snapshot.archive_turn for snapshot, _ in ship_failures}
        for turn in sorted(failure_turns):
            for snapshot in sorted(by_turn[turn], key=lambda item: item.player_id):
                for ship_id in implicated_ships:
                    ship = _find_id(snapshot, "ships", ship_id)
                    if ship is None:
                        continue
                    info, _ = _freshness(ship, snapshot.embedded_turn)
                    signature = (
                        snapshot.player_id,
                        ship_id,
                        info,
                        _owner(ship),
                        _intish(ship.get("crew")),
                        _intish(ship.get("warp")),
                        _intish(ship.get("x")),
                        _intish(ship.get("y")),
                    )
                    signatures[signature].append(turn)
        for signature, turns in sorted(signatures.items(), key=lambda item: repr(item[0])):
            player, ship_id, info, owner, crew, warp, x, y = signature
            print(
                "  "
                f"turns={_compact_turns(turns)} count={len(turns)} player={player} ship={ship_id} "
                f"infoturn={info!r} ownerid={owner!r} crew={crew!r} warp={warp!r} "
                f"x={x!r} y={y!r}"
            )

    if other_failures:
        print(f"other_failure_types: {dict(sorted(other_failures.items()))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
