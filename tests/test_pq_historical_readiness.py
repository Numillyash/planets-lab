"""Read-only PQ/PPQ feature-index readiness; no archive/entity sampling."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from planets_lab.corpus.feature_index import feature_row, write_feature_index
from planets_lab.corpus.pq_historical_readiness import (
    COHORT_SCHEMA, REPORT_SCHEMA,
    build_pq_readiness_report, parse_frozen_cohort, report_from_paths,
)
from tools.diagnostics.pq_historical_readiness import main


def record(game_id, *, status=3, pq=True, ppq=False,
           present=True, rectangular=True, transitions=20, omit=()):
    vals = {
        "game.status": status,
        "settings.productionqueue": pq,
        "settings.planetaryproductionqueue": ppq,
        "coverage.archive_present": present,
        "coverage.rectangular_grid_complete": rectangular,
        "evidence.archive_transition_count": transitions,
    }
    return [
        feature_row(
            game_id=game_id, feature=key, known=key not in omit,
            value=value if key not in omit else None,
            source_kind="synthetic_feature_index",
            source_location=f"synthetic:{game_id}:{key}",
        )
        for key, value in vals.items()
    ]


def triage(rows, cohort):
    return build_pq_readiness_report(
        rows, cohort, frozen_cohort_sha256="a"*64,
        index_sha256="b"*64,
    )


def test_realistic_pq_ppq_readiness_has_no_host_causal_promotion():
    rows = [
        *record(1), *record(2, pq=True, ppq=True),
        *record(3, pq=False, ppq=False),
        *record(4, present=False, omit=("coverage.rectangular_grid_complete",)),
        *record(5, pq=True, ppq=True, transitions=0),
        *record(6, omit=("settings.productionqueue",)),
        *record(7, ppq=True, pq=False),
        *record(8, status=2),
        *record(9, rectangular=False),
        *record(10, omit=("evidence.archive_transition_count",)),
        *record(999),  # outside frozen cohort never opened or shown
    ]
    data = triage(rows, tuple(range(1, 12)))
    assert data["schema"] == REPORT_SCHEMA
    assert data["cohort_game_count"] == 11
    assert data["observational_candidate_ids"] == [1, 2]
    by = {r["game_id"]: r for r in data["games"]}
    assert by[1]["mode"] == "PQ"
    assert by[2]["mode"] == "PPQ"
    assert by[3]["scope"] == "EXCLUDED"
    assert by[4]["archive"] == "ARCHIVE_NOT_READY"
    assert by[5]["archive"] == "ARCHIVE_NOT_READY"
    assert by[6]["scope"] == "SCOPE_UNKNOWN"
    assert by[7]["scope"] == "EXCLUDED"
    assert by[8]["scope"] == "EXCLUDED"
    assert by[9]["archive"] == "ARCHIVE_NOT_READY"
    assert by[10]["archive"] == "ARCHIVE_UNKNOWN"
    assert by[11]["scope"] == "NOT_INDEXED"
    assert 999 not in [r["game_id"] for r in data["games"]]
    assert data["host_causal_verified_games"] == 0
    assert data["rejected_for_host_causal"] is True
    assert data["evidence"] == "CORPUS_METADATA_TRIAGE_ONLY_NOT_DIFF_VERIFIED"
    assert not data["archives_or_turn_payloads_read"]
    assert not data["sealed_holdout_opened"]


@pytest.mark.parametrize("bad", [
    b"", b"null", b"[]", b"{}", b'{"schema":"other","game_ids":[1]}',
    b'{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":[]}',
    b'{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":[1,1]}',
    b'{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":[true]}',
    b'{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":[-1]}',
    b'{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":["12"]}',
    b'{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":[1],"extra":"x"}',
])
def test_cohort_contract_refuses_unfrozen_or_invalid_population(bad):
    with pytest.raises((ValueError, json.JSONDecodeError)):
        parse_frozen_cohort(bad)


def test_missing_or_bad_feature_rows_fail_closed():
    with pytest.raises(ValueError, match="duplicate feature"):
        triage(record(1) + record(1), [1])
    with pytest.raises(ValueError, match="schema"):
        bad = record(1)
        bad[0]["schema_version"] = "untrusted"
        triage(bad, [1])
    with pytest.raises(ValueError, match="positive"):
        triage(record(1), [True])
    with pytest.raises(ValueError, match="duplicate frozen"):
        triage(record(1), [1, 1])
    with pytest.raises(ValueError, match="sha256"):
        build_pq_readiness_report(record(1), [1], frozen_cohort_sha256="bad",
                                  index_sha256="b"*64)


def test_unknown_archive_fields_never_turn_into_false_or_zero():
    data = triage(record(10, omit=("coverage.archive_present", "coverage.rectangular_grid_complete",
                                   "evidence.archive_transition_count")), [10])
    case = data["games"][0]
    assert case["scope"] == "QUEUE_METADATA_MATCH"
    assert case["archive"] == "ARCHIVE_UNKNOWN"
    assert case["missing_or_unknown"] == [
        "coverage.archive_present",
        "coverage.rectangular_grid_complete",
        "evidence.archive_transition_count",
    ]
    assert not case["observational_candidate"]


def test_cohort_first_parquet_selection_is_deterministic_and_repeatable(tmp_path):
    rows = [*record(4, pq=True, ppq=True), *record(9), *record(15, status=1)]
    index = tmp_path / "features.parquet"
    database = tmp_path / "features.duckdb"
    write_feature_index(rows=rows, parquet_path=index, database_path=database)
    cohort = tmp_path / "cohort.json"
    payload = {"schema": COHORT_SCHEMA, "game_ids": [15, 9, 4, 26]}
    cohort.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    first = report_from_paths(index, cohort)
    assert first == report_from_paths(index, cohort)
    assert first["cohort_sha256"] == hashlib.sha256(cohort.read_bytes()).hexdigest()
    assert first["index_sha256"] == hashlib.sha256(index.read_bytes()).hexdigest()
    assert first["observational_candidate_ids"] == [4, 9]
    assert first["indexed_cohort_games"] == 3
    assert first["games"][-1]["scope"] == "NOT_INDEXED"
    target = tmp_path / "out" / "report.json"
    assert main(["--feature-index", str(index), "--frozen-cohort", str(cohort),
                 "--output", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8")) == first
    assert main(["--feature-index", str(index), "--frozen-cohort",
                 str(tmp_path / "missing.json"), "--output", str(target)]) == 2
    # Atomic failure: a preexisting report is never overwritten.
    assert json.loads(target.read_text(encoding="utf-8")) == first


def test_all_inputs_unknown_or_without_archive_do_not_claim_observational_candidates():
    rows = [*record(1, omit=("settings.planetaryproductionqueue",)),
            *record(2, present=False)]
    data = triage(rows, [1, 2, 3])
    assert data["observational_candidate_ids"] == []
    assert all(not x["host_causal_verified"] for x in data["games"])
