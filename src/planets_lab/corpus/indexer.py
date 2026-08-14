from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from planets_lab.data import NuLoadTurnError

from .archive import archive_members
from .manifest import MANIFEST_SCHEMA
from .normalizer import (
    ArchiveTurnSnapshot,
    consecutive_archive_transitions,
    load_archive_snapshots,
    summarize_archive_snapshots,
)

INDEX_SCHEMA = "planets-lab.corpus-index.v1"
STATS_SCHEMA = "planets-lab.corpus-stats.v1"


class CorpusIndexError(ValueError):
    pass


def load_manifest_jsonl(text: str) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    seen_game_ids: set[int] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusIndexError(f"manifest line {line_number} is not valid JSON") from exc
        if not isinstance(record, dict):
            raise CorpusIndexError(f"manifest line {line_number} must be an object")
        if record.get("schema") != MANIFEST_SCHEMA:
            raise CorpusIndexError(
                f"manifest line {line_number} has unsupported schema {record.get('schema')!r}"
            )
        game_id = record.get("game_id")
        if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
            raise CorpusIndexError(f"manifest line {line_number} has invalid game_id")
        if game_id in seen_game_ids:
            raise CorpusIndexError(f"manifest contains duplicate game_id {game_id}")
        seen_game_ids.add(game_id)
        if not isinstance(record.get("settings_hash"), str):
            raise CorpusIndexError(f"manifest game {game_id} has no settings_hash")
        if not isinstance(record.get("game"), dict):
            raise CorpusIndexError(f"manifest game {game_id} has no game object")
        if not isinstance(record.get("player_slots"), list):
            raise CorpusIndexError(f"manifest game {game_id} has no player_slots list")
        records.append(record)
    return tuple(records)


def _year(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"(?:19|20)\d{2}", value)
    return int(match.group(0)) if match else None


def _owner_value(ship: Mapping[str, Any]) -> Any:
    if "ownerid" in ship:
        return ship.get("ownerid")
    return ship.get("owner_id")


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mechanic_counts(snapshot: ArchiveTurnSnapshot) -> Counter[str]:
    counts: Counter[str] = Counter()
    payload = snapshot.mechanics_payload

    ionstorms = payload.get("ionstorms", [])
    if isinstance(ionstorms, list):
        counts["ionstorm_records"] += len(ionstorms)
        if ionstorms:
            counts["snapshots_with_ionstorms"] += 1

    minefields = payload.get("minefields", [])
    if isinstance(minefields, list):
        counts["minefield_records"] += len(minefields)
        if minefields:
            counts["snapshots_with_minefields"] += 1

    ships = payload.get("ships", [])
    if not isinstance(ships, list):
        return counts

    snapshot_has_ghost = False
    snapshot_has_tow = False
    snapshot_has_intercept = False
    snapshot_has_hyp = False
    for ship in ships:
        if not isinstance(ship, Mapping):
            continue
        if _owner_value(ship) == 0:
            counts["ghost_ship_records"] += 1
            snapshot_has_ghost = True

        mission = _intish(ship.get("mission"))
        if mission == 6:
            counts["tow_order_candidates"] += 1
            snapshot_has_tow = True
        elif mission == 7:
            counts["intercept_order_candidates"] += 1
            snapshot_has_intercept = True

        friendly_code = ship.get("friendlycode", ship.get("friendly_code", ""))
        if isinstance(friendly_code, str) and friendly_code.strip().lower() == "hyp":
            counts["hyp_order_candidates"] += 1
            snapshot_has_hyp = True

    if snapshot_has_ghost:
        counts["snapshots_with_ghost_ships"] += 1
    if snapshot_has_tow:
        counts["snapshots_with_tow_candidates"] += 1
    if snapshot_has_intercept:
        counts["snapshots_with_intercept_candidates"] += 1
    if snapshot_has_hyp:
        counts["snapshots_with_hyp_candidates"] += 1
    return counts


def _race_slot_counts(manifest: Mapping[str, Any]) -> Counter[int]:
    result: Counter[int] = Counter()
    player_slots = manifest.get("player_slots", [])
    if not isinstance(player_slots, list):
        return result
    for slot in player_slots:
        if not isinstance(slot, Mapping):
            continue
        race_id = _intish(slot.get("raceid"))
        if race_id is not None and race_id > 0:
            result[race_id] += 1
    return result


def index_game_archive(
    manifest: Mapping[str, Any],
    data: bytes,
    *,
    cache_path: str,
    acquisition_source: str,
) -> dict[str, Any]:
    game_id = manifest.get("game_id")
    if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
        raise CorpusIndexError("manifest game_id must be a positive integer")

    members = archive_members(data)
    snapshots = load_archive_snapshots(data)
    if not snapshots:
        raise CorpusIndexError(f"game {game_id} archive has no turn snapshots")
    if {snapshot.game_id for snapshot in snapshots} != {game_id}:
        raise CorpusIndexError(f"game {game_id} archive payload game id mismatch")

    summary = summarize_archive_snapshots(snapshots)
    transitions = consecutive_archive_transitions(snapshots)
    canonical_ok = 0
    canonical_failures: Counter[str] = Counter()
    mechanics: Counter[str] = Counter()
    turn_offsets: Counter[int] = Counter()

    for snapshot in snapshots:
        mechanics.update(_mechanic_counts(snapshot))
        turn_offsets[snapshot.embedded_turn - snapshot.archive_turn] += 1
        try:
            snapshot.import_state()
        except (NuLoadTurnError, ValueError, TypeError, KeyError) as exc:
            canonical_failures[type(exc).__name__] += 1
        else:
            canonical_ok += 1

    game = manifest.get("game", {})
    if not isinstance(game, Mapping):
        game = {}
    race_slots = _race_slot_counts(manifest)
    ended_year = _year(game.get("dateended"))

    return {
        "schema": INDEX_SCHEMA,
        "game_id": game_id,
        "tier": manifest.get("tier"),
        "settings_hash": manifest.get("settings_hash"),
        "ended_year": ended_year,
        "game_type": game.get("gametype"),
        "is_custom": bool(game.get("iscustom", False)),
        "is_private": bool(game.get("isprivate", False)),
        "final_turn": game.get("turn"),
        "race_slots": {str(key): value for key, value in sorted(race_slots.items())},
        "archive": {
            "source": acquisition_source,
            "cache_path": cache_path,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "members": len(members),
        },
        "snapshots": summary.snapshots,
        "players": list(summary.players),
        "archive_turns": list(summary.archive_turns),
        "missing_grid_cells": len(summary.missing_grid_cells),
        "transitions": summary.transitions,
        "embedded_consecutive": summary.embedded_consecutive_transitions,
        "turn_offset_counts": {
            str(key): value for key, value in sorted(turn_offsets.items())
        },
        "canonical_import": {
            "ok": canonical_ok,
            "failed": len(snapshots) - canonical_ok,
            "failure_types": dict(sorted(canonical_failures.items())),
        },
        "candidate_mechanics": dict(sorted(mechanics.items())),
    }


def aggregate_corpus_index(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    by_tier: Counter[str] = Counter()
    by_era: Counter[str] = Counter()
    by_settings: Counter[str] = Counter()
    by_race: Counter[str] = Counter()
    mechanics: Counter[str] = Counter()
    totals: Counter[str] = Counter()

    for row in rows:
        tier = row.get("tier")
        if tier is not None:
            by_tier[str(tier)] += 1
        year = row.get("ended_year")
        by_era[str(year) if year is not None else "unknown"] += 1
        settings_hash = row.get("settings_hash")
        if isinstance(settings_hash, str):
            by_settings[settings_hash] += 1

        race_slots = row.get("race_slots", {})
        if isinstance(race_slots, Mapping):
            for race_id, count in race_slots.items():
                value = _intish(count)
                if value is not None:
                    by_race[str(race_id)] += value

        candidate = row.get("candidate_mechanics", {})
        if isinstance(candidate, Mapping):
            for key, count in candidate.items():
                value = _intish(count)
                if value is not None:
                    mechanics[str(key)] += value

        canonical = row.get("canonical_import", {})
        if isinstance(canonical, Mapping):
            totals["canonical_ok"] += _intish(canonical.get("ok")) or 0
            totals["canonical_failed"] += _intish(canonical.get("failed")) or 0
        archive = row.get("archive", {})
        if isinstance(archive, Mapping):
            totals["archive_bytes"] += _intish(archive.get("bytes")) or 0
        for key in ("snapshots", "transitions", "embedded_consecutive"):
            totals[key] += _intish(row.get(key)) or 0

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "totals": dict(sorted(totals.items())),
        "games_by_tier": dict(sorted(by_tier.items())),
        "games_by_ended_year": dict(sorted(by_era.items())),
        "games_by_settings_hash": dict(sorted(by_settings.items())),
        "player_slots_by_race": dict(sorted(by_race.items(), key=lambda item: int(item[0]))),
        "candidate_mechanics": dict(sorted(mechanics.items())),
    }
