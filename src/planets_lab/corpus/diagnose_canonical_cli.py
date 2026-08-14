from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .normalizer import (
    ArchiveTurnSnapshot,
    CorpusNormalizationError,
    load_archive_snapshots,
    ownerless_ship_diagnostics,
)


STARBASE_OWNER_RE = re.compile(r"starbase on planet (?P<planet>\d+) has no resolvable owner")


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _failure_kind(exc: Exception) -> str:
    message = str(exc)
    if STARBASE_OWNER_RE.search(message):
        return "starbase_no_resolvable_owner"
    if "unowned ghost ship" in message and "non-zero warp" in message:
        return "ghost_nonzero_warp"
    if "unowned ship" in message and "non-zero crew" in message:
        return "ghost_nonzero_crew"
    if "negative crew" in message:
        return "negative_crew"
    if "unknown owner" in message:
        return "unknown_owner"
    return f"{type(exc).__name__}:{message}"


def _owner_value(raw: Mapping[str, Any]) -> int | None:
    if "ownerid" in raw:
        return _intish(raw.get("ownerid"))
    return _intish(raw.get("owner_id"))


def _starbase_planet_id(raw: Mapping[str, Any]) -> int | None:
    if "planetid" in raw:
        return _intish(raw.get("planetid"))
    return _intish(raw.get("planet_id"))


def _unresolved_starbase_diagnostics(
    snapshot: ArchiveTurnSnapshot,
) -> tuple[dict[str, Any], ...]:
    payload = snapshot.mechanics_payload
    raw_planets = payload.get("planets", [])
    raw_starbases = payload.get("starbases", [])
    if not isinstance(raw_planets, list) or not isinstance(raw_starbases, list):
        return ()

    planets: dict[int, Mapping[str, Any]] = {}
    for raw in raw_planets:
        if not isinstance(raw, Mapping):
            continue
        planet_id = _intish(raw.get("id"))
        if planet_id is not None:
            planets[planet_id] = raw

    result: list[dict[str, Any]] = []
    for raw_base in raw_starbases:
        if not isinstance(raw_base, Mapping):
            continue
        planet_id = _starbase_planet_id(raw_base)
        if planet_id is None:
            continue
        base_owner = _owner_value(raw_base)
        raw_planet = planets.get(planet_id)
        planet_owner = _owner_value(raw_planet) if raw_planet is not None else None
        if (base_owner or 0) > 0 or (planet_owner or 0) > 0:
            continue

        excerpt: dict[str, Any] = {
            "player": snapshot.player_id,
            "archive_turn": snapshot.archive_turn,
            "embedded_turn": snapshot.embedded_turn,
            "planet_id": planet_id,
            "starbase_ownerid": base_owner,
            "planet_ownerid": planet_owner,
            "planet_record_present": raw_planet is not None,
            "starbase_present_keys": sorted(str(key) for key in raw_base.keys()),
        }
        if raw_planet is not None:
            excerpt["planet_present_keys"] = sorted(str(key) for key in raw_planet.keys())
            for key in ("clans", "defense", "factories", "mines", "starbase"):
                if key in raw_planet:
                    value = raw_planet[key]
                    if isinstance(value, (int, float, bool)) or value is None:
                        excerpt[f"planet_{key}"] = value
        for key in (
            "fighters",
            "defense",
            "damage",
            "hulltechlevel",
            "enginetechlevel",
            "beamtechlevel",
            "torptechlevel",
        ):
            if key in raw_base:
                value = raw_base[key]
                if isinstance(value, (int, float, bool)) or value is None:
                    excerpt[f"starbase_{key}"] = value
        result.append(excerpt)
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose canonical import failures in a cached /game/loadall archive "
            "using privacy-safe mechanical excerpts only."
        )
    )
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()

    try:
        snapshots = load_archive_snapshots(args.archive.read_bytes())
    except (OSError, ValueError, CorpusNormalizationError) as exc:
        print(str(exc))
        return 2

    failures: list[tuple[ArchiveTurnSnapshot, Exception, str]] = []
    kinds: Counter[str] = Counter()
    types: Counter[str] = Counter()
    players: Counter[int] = Counter()
    starbase_groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)

    for snapshot in snapshots:
        try:
            snapshot.import_state()
        except Exception as exc:  # diagnostic/reporting boundary
            kind = _failure_kind(exc)
            failures.append((snapshot, exc, kind))
            kinds[kind] += 1
            types[type(exc).__name__] += 1
            players[snapshot.player_id] += 1

            for diag in _unresolved_starbase_diagnostics(snapshot):
                key = (
                    diag.get("player"),
                    diag.get("planet_id"),
                    diag.get("starbase_ownerid"),
                    diag.get("planet_ownerid"),
                    diag.get("planet_record_present"),
                    diag.get("planet_clans"),
                )
                starbase_groups[key].append(snapshot.archive_turn)

    print("===== CANONICAL FAILURE DIAGNOSTICS =====")
    print(f"archive:        {args.archive}")
    print(f"snapshots:      {len(snapshots)}")
    print(f"failures:       {len(failures)}")
    print(f"failure_types:  {dict(sorted(types.items()))}")
    print(f"failure_kinds:  {dict(sorted(kinds.items()))}")
    print(f"failures_by_player: {dict(sorted(players.items()))}")

    if starbase_groups:
        print("unresolved_starbase_groups:")
        for key, turns in sorted(starbase_groups.items(), key=lambda item: (item[0][0], item[0][1])):
            player, planet_id, base_owner, planet_owner, planet_present, planet_clans = key
            print(
                "  "
                f"count={len(turns)} player={player} planet={planet_id} "
                f"archive_turns={min(turns)}..{max(turns)} "
                f"starbase_ownerid={base_owner!r} planet_ownerid={planet_owner!r} "
                f"planet_present={planet_present} planet_clans={planet_clans!r}"
            )

    if failures:
        print("failures_detail:")
        for snapshot, exc, kind in failures:
            print(
                "  "
                f"player={snapshot.player_id} "
                f"archive_turn={snapshot.archive_turn} "
                f"embedded_turn={snapshot.embedded_turn} "
                f"kind={kind} {type(exc).__name__}: {exc}"
            )
            if kind == "starbase_no_resolvable_owner":
                for diag in _unresolved_starbase_diagnostics(snapshot):
                    print(
                        "    starbase="
                        + json.dumps(diag, ensure_ascii=False, sort_keys=True)
                    )
            elif kind.startswith("ghost_") or kind == "unknown_owner":
                for diag in ownerless_ship_diagnostics(snapshot):
                    print(
                        "    ship="
                        + json.dumps(diag, ensure_ascii=False, sort_keys=True)
                    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
