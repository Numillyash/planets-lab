"""Read-only historical PQ/PPQ feasibility triage from an EXISTING feature index.

No archive load, no turn/member extraction, no owner-order inference.
A frozen, explicit cohort is mandatory. Unknown feature values fail closed
and every output is a metadata candidate ONLY, never DIFF_VERIFIED.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from planets_lab.corpus.feature_index import (
    FEATURE_INDEX_SCHEMA, feature_value, load_feature_rows,
)

REPORT_SCHEMA = "planets-lab.pq-historical-readiness.v1"
COHORT_SCHEMA = "planets-lab.pq-historical-frozen-cohort.v1"
QUEUE_MODES = ("PQ", "PPQ")
REQUIRED_FIELDS = (
    "game.status", "settings.productionqueue",
    "settings.planetaryproductionqueue",
)
ARCHIVE_FIELDS = (
    "coverage.archive_present",
    "coverage.rectangular_grid_complete",
    "evidence.archive_transition_count",
)


def _positive_game_id(item: object) -> int:
    if type(item) is not int or item <= 0:
        raise ValueError("cohort/index game IDs must be positive integers, not bool")
    return item


def parse_frozen_cohort(raw: bytes) -> tuple[int, ...]:
    """Accepted input is strictly a declared subset; never discover a holdout."""
    parsed = json.loads(raw)
    if (
        type(parsed) is not dict or set(parsed) != {"schema", "game_ids"}
        or parsed["schema"] != COHORT_SCHEMA
        or type(parsed["game_ids"]) is not list
        or not parsed["game_ids"]
    ):
        raise ValueError("invalid explicit frozen cohort schema or empty game_ids")
    ids = tuple(_positive_game_id(x) for x in parsed["game_ids"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate IDs in frozen cohort")
    if len(ids) > 10000:
        raise ValueError("cohort exceeds bounded read-only report size")
    return tuple(sorted(ids))


def _typed_feature(
    by_feature: Mapping[str, Mapping[str, Any]], field: str, expected: type,
) -> tuple[bool, Any]:
    row = by_feature.get(field)
    if row is None or row.get("known") is not True:
        return False, None
    value = feature_value(row)
    if type(value) is not expected:
        # Never coerce int 1 into true, or vice versa.
        return False, None
    return True, value


def _classify_game(
    game_id: int, game: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "game_id": game_id,
        "mode": "UNKNOWN",
        "scope": "NOT_INDEXED" if game is None else "SCOPE_UNKNOWN",
        "archive": "NOT_EVALUATED",
        "observational_candidate": False,
        "missing_or_unknown": [],
        "excluded_by": [],
        "host_causal_verified": False,
    }
    if game is None:
        record["missing_or_unknown"] = list(REQUIRED_FIELDS)
        return record

    missing: list[str] = []
    excluded: list[str] = []
    known = {}
    for field, typ in (
        ("game.status", int),
        ("settings.productionqueue", bool),
        ("settings.planetaryproductionqueue", bool),
    ):
        valid, value = _typed_feature(game, field, typ)
        if not valid:
            missing.append(field)
        else:
            known[field] = value

    pq = known.get("settings.productionqueue")
    ppq = known.get("settings.planetaryproductionqueue")
    # Never silently interpret a contradictory pair of settings.
    if type(pq) is bool and type(ppq) is bool:
        if ppq and not pq:
            excluded.append("PQ_AND_PPQ_SETTINGS_CONFLICT")
        elif ppq:
            record["mode"] = "PPQ"
        elif pq:
            record["mode"] = "PQ"
        else:
            record["mode"] = "CLASSIC_OR_OTHER"
            excluded.append("QUEUE_DISABLED")

    if known.get("game.status") != 3 and "game.status" in known:
        excluded.append("NOT_COMPLETED_GAME")

    record["missing_or_unknown"] = missing
    record["excluded_by"] = excluded
    if excluded:
        record["scope"] = "EXCLUDED"
        return record
    if missing:
        record["scope"] = "SCOPE_UNKNOWN"
        return record

    record["scope"] = "QUEUE_METADATA_MATCH"
    archive_missing: list[str] = []
    archive_mismatch: list[str] = []
    for field, typ in (
        ("coverage.archive_present", bool),
        ("coverage.rectangular_grid_complete", bool),
        ("evidence.archive_transition_count", int),
    ):
        valid, value = _typed_feature(game, field, typ)
        if not valid:
            archive_missing.append(field)
        elif field == "evidence.archive_transition_count":
            if value <= 0:
                archive_mismatch.append("NO_ADJACENT_ARCHIVE_TRANSITIONS")
        elif value is not True:
            archive_mismatch.append(
                "ARCHIVE_MISSING" if field == "coverage.archive_present"
                else "NONRECTANGULAR_ARCHIVE_GRID"
            )
    record["missing_or_unknown"] += archive_missing
    record["excluded_by"] += archive_mismatch
    # Missing archives do not become known "no events", and a complete
    # grid does not imply full ship/planet/PP/order observability.
    if archive_mismatch:
        record["archive"] = "ARCHIVE_NOT_READY"
    elif archive_missing:
        record["archive"] = "ARCHIVE_UNKNOWN"
    else:
        record["archive"] = "ADJACENT_COVERAGE_CANDIDATE"
        record["observational_candidate"] = True
    return record


def build_pq_readiness_report(
    rows: Sequence[Mapping[str, Any]],
    frozen_game_ids: Sequence[int],
    *,
    frozen_cohort_sha256: str,
    index_sha256: str,
) -> dict[str, Any]:
    if (
        type(frozen_cohort_sha256) is not str or len(frozen_cohort_sha256) != 64
        or type(index_sha256) is not str or len(index_sha256) != 64
        or any(c not in "0123456789abcdef" for c in (
            frozen_cohort_sha256 + index_sha256
        ))
    ):
        raise ValueError("strict sha256 provenance required for report")
    cohort = tuple(_positive_game_id(x) for x in frozen_game_ids)
    if not cohort or len(cohort) > 10000 or len(set(cohort)) != len(cohort):
        raise ValueError("invalid or duplicate frozen cohort")
    by_game: dict[int, dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        if type(row) is not dict:
            raise ValueError("feature rows must be typed mappings")
        if row.get("schema_version") != FEATURE_INDEX_SCHEMA:
            raise ValueError("unexpected feature index schema")
        gid = _positive_game_id(row.get("game_id"))
        feature = row.get("feature")
        if type(feature) is not str or not feature:
            raise ValueError("malformed feature name")
        # Do not use indexed records outside the frozen requested set.
        if gid not in cohort:
            continue
        seen = by_game.setdefault(gid, {})
        if feature in seen:
            raise ValueError("duplicate feature within a frozen game")
        seen[feature] = row
    cases = [
        _classify_game(gid, by_game.get(gid))
        for gid in sorted(cohort)
    ]
    scope_counts = Counter(x["scope"] for x in cases)
    archive_counts = Counter(x["archive"] for x in cases)
    mode_counts = Counter(x["mode"] for x in cases)
    candidate_ids = [
        x["game_id"] for x in cases if x["observational_candidate"]
    ]
    return {
        "schema": REPORT_SCHEMA,
        "feature_index_schema": FEATURE_INDEX_SCHEMA,
        "cohort_sha256": frozen_cohort_sha256,
        "index_sha256": index_sha256,
        "cohort_game_count": len(cohort),
        "indexed_cohort_games": len(by_game),
        "scope_counts": dict(sorted(scope_counts.items())),
        "archive_counts": dict(sorted(archive_counts.items())),
        "mode_counts": dict(sorted(mode_counts.items())),
        "observational_candidate_ids": candidate_ids,
        "games": cases,
        "rejected_for_host_causal": True,
        "host_causal_verified_games": 0,
        "unverified_requirements": [
            "independent server-accepted exact ship/base orders",
            "authentic full before/after owner-current snapshots",
            "independent Host boundary and phase-placement evidence",
            "observable queued starbase intentions and component warehouses",
            "complete PP ledgers and unambiguous ship-ID/base selection",
        ],
        "evidence": "CORPUS_METADATA_TRIAGE_ONLY_NOT_DIFF_VERIFIED",
        "archives_or_turn_payloads_read": False,
        "sealed_holdout_opened": False,
    }


def report_from_paths(
    index_path: Path, cohort_path: Path,
) -> dict[str, Any]:
    # Cohort is parsed before the index is accessed.
    cohort_raw = cohort_path.read_bytes()
    game_ids = parse_frozen_cohort(cohort_raw)
    index_sha = hashlib.sha256(index_path.read_bytes()).hexdigest()
    return build_pq_readiness_report(
        load_feature_rows(index_path), game_ids,
        frozen_cohort_sha256=hashlib.sha256(cohort_raw).hexdigest(),
        index_sha256=index_sha,
    )
