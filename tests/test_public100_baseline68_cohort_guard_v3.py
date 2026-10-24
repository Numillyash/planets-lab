"""Test cohort attestation using only fake tiny DuckDB games, never private corpora."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from planets_lab.corpus.corpus_db_compact import CORPUS_DB_COMPACT_SCHEMA
from tools.diagnostics.public100_baseline68_cohort_guard_v3 import (
    CohortGateAbstain, digest_file, enforce_cohort_identity, manifest_ids,
    validate, SCHEMA,
)


def _db(path: Path, ids: list[int], members: int) -> None:
    conn=duckdb.connect(str(path))
    conn.execute("CREATE TABLE corpus_metadata(schema_version VARCHAR, created_at_utc VARCHAR)")
    conn.execute("INSERT INTO corpus_metadata VALUES (?, 'fake')", [CORPUS_DB_COMPACT_SCHEMA])
    conn.execute("CREATE TABLE source_archives(archive_id BIGINT, game_id BIGINT)")
    conn.executemany("INSERT INTO source_archives VALUES (?, ?)",
                     [(i+1, v) for i,v in enumerate(ids)])
    conn.execute("CREATE TABLE source_members(member_id BIGINT, game_id BIGINT)")
    conn.executemany("INSERT INTO source_members VALUES (?, ?)",
                     [(i+1, ids[i%len(ids)]) for i in range(members)])
    conn.close()


def _manifest(path: Path, ids: list[int]) -> None:
    path.write_text("".join(json.dumps({"game_id": x, "not_exported": "fictional"})
                            + "\n" for x in ids), encoding="utf-8")


@pytest.fixture
def synthetic_scope(tmp_path):
    root=tmp_path/"corpus"
    directory=root/"generations"
    directory.mkdir(parents=True)
    baseline="synthetic-baseline.duckdb"
    universe="synthetic-universe.duckdb"
    _db(directory/baseline,[101,202],4)
    _db(directory/universe,[101,202,303],6)
    (root/"CURRENT").write_text("generations/"+baseline+"\n",encoding="utf-8")
    manifest=tmp_path/"untracked-server-local.jsonl"
    _manifest(manifest,[101,202])
    kw=dict(root=root,manifest=manifest,
            expected_baseline_sha=digest_file(directory/baseline),
            baseline_gen=baseline, all_gen=universe,
            baseline_games=2, all_games=3,
            baseline_members=4,all_members=6)
    return kw


def test_same_ids_any_jsonl_format_attests_without_historical_file_hash(synthetic_scope):
    kw=synthetic_scope
    first=validate(**kw)
    assert first["status"]=="PASS_EXACT_MANIFEST_GAME_IDS_MATCH_SHA_PINNED_PUBLIC68"
    assert first["schema"]==SCHEMA
    assert first["baseline_game_count"]==2
    assert first["all_metadata_game_count"]==3
    assert first["heldout_entity_sampling"] is False
    assert first["current_modified"] is False
    assert "101" not in json.dumps(first)
    assert "202" not in json.dumps(first)
    path=kw["manifest"]
    # Equivalent set, changed bytes/SHA: still ACCEPT, not silently weaken
    # cohort: official published public68 DB is the immutable trust anchor.
    path.write_text('{"game_id":202}\n{"game_id":101}\n',encoding="utf-8")
    second=validate(**kw)
    assert second["manifest_sha256"] != first["manifest_sha256"]
    assert second["baseline_db_sha256"] == first["baseline_db_sha256"]


def test_manifest_wrong_game_id_with_same_count_cannot_sample_sealed_holdout(synthetic_scope):
    kw=synthetic_scope
    _manifest(kw["manifest"],[101,303])  # 303 is a heldout-only fake game
    with pytest.raises(CohortGateAbstain,match="NOT_APPROVED"):
        validate(**kw)


def test_manifest_shall_be_subset_of_published_100_metadata(synthetic_scope):
    kw=synthetic_scope
    # The manifest is still exactly baseline, but public100 lacks one ID.
    allpath=kw["root"]/"generations"/kw["all_gen"]
    allpath.unlink()
    _db(allpath,[101,303,404],6)
    with pytest.raises(CohortGateAbstain,match="NOT_APPROVED"):
        validate(**kw)


def test_malformed_duplicates_wrong_type_and_count_abstain():
    bad=[
        b"",b'{"game_id":101}\n{"game_id":101}\n',
        b'{"game_id":true}\n{"game_id":202}\n',
        b'{"game_id":101}\n',
        b'{"game_id":101}\n{"game_id":"202"}\n',
        b"garbage",b"x"*1000001,
    ]
    for item in bad:
        with pytest.raises(CohortGateAbstain):
            manifest_ids(item, expected_games=2)


def test_boolean_identity_or_wrong_cardinality_refuses():
    with pytest.raises(CohortGateAbstain):
        enforce_cohort_identity({101,202},{101,202},{101,202},
                                baseline_games=2,all_games=3)
    with pytest.raises(CohortGateAbstain):
        enforce_cohort_identity({101,202},{101,303},{101,202,303},
                                baseline_games=2,all_games=3)


def test_sha_attestation_cannot_be_bypassed(synthetic_scope):
    kw=dict(synthetic_scope)
    kw["expected_baseline_sha"]="0"*64
    with pytest.raises(CohortGateAbstain,match="SHA256_MISMATCH"):
        validate(**kw)


def test_unexpected_current_fails_before_db_read(synthetic_scope):
    kw=synthetic_scope
    (kw["root"]/"CURRENT").write_text("generations/synthetic-universe.duckdb\n")
    with pytest.raises(CohortGateAbstain,match="UNEXPECTED_CURRENT"):
        validate(**kw)


def test_runner_checks_cohort_before_pytest_and_entity_decoding():
    base=Path(__file__).resolve().parents[1]
    run=(base/"tools/run-public100-baseline68-deep-v2.sh").read_text()
    assert "BASE_SHA=" not in run
    assert "ABSTAIN_BASELINE_MANIFEST_SHA" not in run
    assert "public100_baseline68_cohort_guard_v3.py" in run
    assert "ABSTAIN_BASELINE_COHORT_GUARD" in run
    assert "--expected-baseline-manifest-sha256" in run
    assert run.index("public100_baseline68_cohort_guard_v3.py") < run.index("stage=full_pytest started")
    assert run.index("public100_baseline68_cohort_guard_v3.py") < run.index("stage=deep_m2_100_metadata_68_baseline begin")
    assert "m2_validate_corpus_aggregate_evidence_v1.py" in run
    pub=(base/"tools/run-public100-baseline68-deep-v2-with-evidence.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in pub
    assert "baseline-cohort-attestation.json" in pub
    assert "private-local" not in pub


def test_m2_diagnostic_declares_expected_manifest_hash_guard():
    src=(Path(__file__).resolve().parents[1]/
         "tools/diagnostics/m2_public_corpus_economy_coverage_v1.py").read_text()
    assert "--expected-baseline-manifest-sha256" in src
    assert "ATTESTED_BASELINE_MANIFEST_CHANGED" in src
