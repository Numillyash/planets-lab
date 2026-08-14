from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .normalizer import ArchiveTurnSnapshot
from .readiness import evaluate_default_profiles


READINESS_GAME_SCHEMA = "planets-lab.readiness-game.v1"
READINESS_STATS_SCHEMA = "planets-lab.readiness-stats.v1"


def summarize_readiness_game(
    *,
    game_id: int,
    settings_hash: str,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> dict[str, Any]:
    profiles = evaluate_default_profiles(snapshots)
    profile_rows: dict[str, Any] = {}
    for name, summary in profiles.items():
        profile_rows[name] = {
            "valid_turn_pairs": summary.valid_turn_pairs,
            "skipped_turn_pairs": summary.skipped_turn_pairs,
            "evaluated_entities": summary.evaluated_entities,
            "status_counts": dict(summary.status_counts),
            "issue_counts": dict(summary.issue_counts),
        }
    return {
        "schema": READINESS_GAME_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        "profiles": profile_rows,
    }


def aggregate_readiness_games(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    profile_statuses: dict[str, Counter[str]] = defaultdict(Counter)
    profile_issues: dict[str, Counter[str]] = defaultdict(Counter)
    profile_totals: dict[str, Counter[str]] = defaultdict(Counter)
    by_settings: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    settings_hashes: Counter[str] = Counter()
    snapshots = 0

    for row in rows:
        value = row.get("snapshots")
        if isinstance(value, int) and not isinstance(value, bool):
            snapshots += value
        settings_hash = row.get("settings_hash")
        if isinstance(settings_hash, str):
            settings_hashes[settings_hash] += 1
        else:
            settings_hash = "unknown"

        profiles = row.get("profiles", {})
        if not isinstance(profiles, Mapping):
            continue
        for profile_name, payload in profiles.items():
            if not isinstance(payload, Mapping):
                continue
            name = str(profile_name)
            for key in ("valid_turn_pairs", "skipped_turn_pairs", "evaluated_entities"):
                count = payload.get(key)
                if isinstance(count, int) and not isinstance(count, bool):
                    profile_totals[name][key] += count

            status_counts = payload.get("status_counts", {})
            if isinstance(status_counts, Mapping):
                for status, count in status_counts.items():
                    if isinstance(count, int) and not isinstance(count, bool):
                        profile_statuses[name][str(status)] += count
                        by_settings[str(settings_hash)][name][str(status)] += count

            issue_counts = payload.get("issue_counts", {})
            if isinstance(issue_counts, Mapping):
                for issue, count in issue_counts.items():
                    if isinstance(count, int) and not isinstance(count, bool):
                        profile_issues[name][str(issue)] += count

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": READINESS_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "settings_hashes": len(settings_hashes),
        "snapshots": snapshots,
        "profiles": {
            name: {
                "totals": dict(sorted(profile_totals[name].items())),
                "status_counts": dict(sorted(profile_statuses[name].items())),
                "issue_counts": dict(sorted(profile_issues[name].items())),
            }
            for name in sorted(set(profile_totals) | set(profile_statuses) | set(profile_issues))
        },
        "profiles_by_settings_hash": {
            settings_hash: {
                profile: dict(sorted(counts.items()))
                for profile, counts in sorted(profiles.items())
            }
            for settings_hash, profiles in sorted(by_settings.items())
        },
    }
