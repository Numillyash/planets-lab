from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from planets_lab.sim.movement_classifier import MovementMissionConvention

from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import PerspectiveRecord, group_perspective_records

MOVE_MOST_CANDIDATE = "move_most_candidate"
TOW_ATTEMPT = "tow_attempt"
INTERCEPT = "intercept"
HYP = "hyp"
GHOST = "ghost"

MOVEMENT_CONTEXT_GAME_SCHEMA = "planets-lab.movement-context-game.v1"
MOVEMENT_CONTEXT_STATS_SCHEMA = "planets-lab.movement-context-stats.v1"


@dataclass(frozen=True, slots=True)
class MovementContextSummary:
    geometry_ready: int
    classified: int
    valid_turn_pairs: int
    skipped_turn_pairs: int
    intent_counts: Mapping[str, int]
    issue_counts: Mapping[str, int]


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _raw_owner(record: PerspectiveRecord) -> int | None:
    raw = record.raw
    value = raw.get("ownerid", raw.get("owner_id"))
    owner = _intish(value)
    if owner is None or owner < 0:
        return None
    return owner


def _resolved_owner_from_current(
    records: Sequence[PerspectiveRecord],
) -> tuple[int | None, str | None]:
    current = tuple(record for record in records if record.is_current)
    known = tuple((record, _raw_owner(record)) for record in current)
    known = tuple((record, owner) for record, owner in known if owner is not None)
    if not known:
        return None, "before.ship.owner_context.no_current_owner_value"

    positive = {owner for _, owner in known if owner > 0}
    if len(positive) > 1:
        return None, "before.ship.owner_context.multiple_positive_owner_claims"

    if len(positive) == 1:
        owner = next(iter(positive))
        owner_records = tuple(record for record, _ in known if record.player_id == owner)
        if owner_records:
            if any(_raw_owner(record) == owner for record in owner_records):
                return owner, None
            return None, "before.ship.owner_context.owner_self_claim_mismatch"

        values = {value for _, value in known}
        if values == {owner}:
            return owner, None
        return None, "before.ship.owner_context.owner_perspective_missing"

    values = {value for _, value in known}
    if values == {0}:
        return 0, None
    return None, "before.ship.owner_context.unresolved_owner"


def _mission_id(value: Any) -> int | None:
    return _intish(value)


def _classify_owner_record(
    record: PerspectiveRecord,
    *,
    convention: MovementMissionConvention,
) -> str:
    mission = _mission_id(record.raw.get("mission"))
    if mission in convention.tow_mission_ids:
        return TOW_ATTEMPT
    if mission in convention.intercept_mission_ids:
        return INTERCEPT
    friendly_code = record.raw.get("friendlycode", record.raw.get("friendly_code", ""))
    if isinstance(friendly_code, str) and friendly_code.strip().lower() == "hyp":
        return HYP
    return MOVE_MOST_CANDIDATE


def evaluate_movement_context(
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> MovementContextSummary:
    records = tuple(snapshots)
    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    ship_groups = group_perspective_records(records, "ship")
    intents: Counter[str] = Counter()
    issues: Counter[str] = Counter()

    geometry_ready = 0
    classified = 0

    for transition in readiness.results:
        if transition.status != READY:
            continue
        geometry_ready += 1
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner_issue = _resolved_owner_from_current(group)
        if owner_issue is not None:
            issues[owner_issue] += 1
            continue
        if owner_id is None:
            issues["before.ship.owner_context.unresolved_owner"] += 1
            continue

        if owner_id == 0:
            intents[GHOST] += 1
            classified += 1
            continue

        owner_records = tuple(
            record
            for record in group
            if record.is_current and record.player_id == owner_id
        )
        if len(owner_records) != 1:
            issues["before.ship.owner_context.owner_record_count"] += 1
            continue
        owner_record = owner_records[0]
        if _raw_owner(owner_record) != owner_id:
            issues["before.ship.owner_context.owner_record_mismatch"] += 1
            continue

        intents[_classify_owner_record(owner_record, convention=convention)] += 1
        classified += 1

    return MovementContextSummary(
        geometry_ready=geometry_ready,
        classified=classified,
        valid_turn_pairs=readiness.valid_turn_pairs,
        skipped_turn_pairs=readiness.skipped_turn_pairs,
        intent_counts=dict(sorted(intents.items())),
        issue_counts=dict(sorted(issues.items())),
    )


def summarize_movement_context_game(
    *,
    game_id: int,
    settings_hash: str,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> dict[str, Any]:
    summary = evaluate_movement_context(snapshots)
    return {
        "schema": MOVEMENT_CONTEXT_GAME_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        "geometry_ready": summary.geometry_ready,
        "classified": summary.classified,
        "valid_turn_pairs": summary.valid_turn_pairs,
        "skipped_turn_pairs": summary.skipped_turn_pairs,
        "intent_counts": dict(summary.intent_counts),
        "issue_counts": dict(summary.issue_counts),
    }


def aggregate_movement_context_games(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    totals: Counter[str] = Counter()
    intents: Counter[str] = Counter()
    issues: Counter[str] = Counter()
    settings_hashes: Counter[str] = Counter()
    by_settings: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        settings_hash = row.get("settings_hash")
        if isinstance(settings_hash, str):
            settings_hashes[settings_hash] += 1
        else:
            settings_hash = "unknown"

        for key in (
            "snapshots",
            "geometry_ready",
            "classified",
            "valid_turn_pairs",
            "skipped_turn_pairs",
        ):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value

        intent_counts = row.get("intent_counts", {})
        if isinstance(intent_counts, Mapping):
            for intent, count in intent_counts.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    intents[str(intent)] += count
                    by_settings[str(settings_hash)][str(intent)] += count

        issue_counts = row.get("issue_counts", {})
        if isinstance(issue_counts, Mapping):
            for issue, count in issue_counts.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    issues[str(issue)] += count

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": MOVEMENT_CONTEXT_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "settings_hashes": len(settings_hashes),
        "totals": dict(sorted(totals.items())),
        "intent_counts": dict(sorted(intents.items())),
        "issue_counts": dict(sorted(issues.items())),
        "intent_counts_by_settings_hash": {
            settings_hash: dict(sorted(counts.items()))
            for settings_hash, counts in sorted(by_settings.items())
        },
    }
