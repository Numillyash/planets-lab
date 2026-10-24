"""Fake only; no existing corpus, server DB or player data is opened."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import duckdb
import pytest

MODULE = (
    Path(__file__).resolve().parents[1]
    / "tools/diagnostics/public68_broad_readonly_census_v1.py"
)
spec = importlib.util.spec_from_file_location("public68_broad_readonly_census_v1", MODULE)
assert spec is not None and spec.loader is not None
survey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survey)


@pytest.fixture
def fake_public_root(tmp_path, monkeypatch):
    root = tmp_path / "corpus-db"
    (root / "generations").mkdir(parents=True)
    monkeypatch.setattr(survey, "PINNED_GENERATION", "synthetic-test.duckdb")
    monkeypatch.setattr(survey, "EXPECTED_GAMES", 2)
    monkeypatch.setattr(survey, "EXPECTED_MEMBERS", 5)
    path = root / "generations" / "synthetic-test.duckdb"
    db = duckdb.connect(str(path))
    db.execute("CREATE TABLE corpus_metadata(schema_version VARCHAR, created_at_utc VARCHAR)")
    db.execute("INSERT INTO corpus_metadata VALUES (?, 'synthetic')", [survey.CORPUS_DB_COMPACT_SCHEMA])
    db.execute("CREATE TABLE source_archives (archive_id BIGINT, game_id BIGINT, archive_bytes BIGINT)")
    db.execute("INSERT INTO source_archives VALUES (1, 77, 110), (2, 88, 120)")
    db.execute("CREATE TABLE zip_members (archive_id BIGINT, member_ordinal BIGINT)")
    db.execute("INSERT INTO zip_members VALUES (1, 0),(1,1),(1,2),(2,0),(2,1)")
    db.execute("CREATE TABLE source_members (member_id BIGINT, archive_id BIGINT, game_id BIGINT, "
               "perspective_player_id BIGINT, embedded_turn BIGINT, archive_turn BIGINT, "
               "decoded_json_bytes BIGINT)")
    db.execute("INSERT INTO source_members VALUES "
               "(1,1,77,9,1,1,100),(2,1,77,9,2,2,100),(3,1,77,9,4,4,100),"
               "(4,2,88,8,1,2,100),(5,2,88,8,1,2,100)")
    db.execute("CREATE TABLE member_fields (member_id BIGINT, field_name VARCHAR)")
    db.execute("INSERT INTO member_fields VALUES (1,'some'),(4,'another')")
    db.execute("CREATE TABLE typed_entity_schema (section_name VARCHAR, schema_json VARCHAR)")
    db.execute("CREATE TABLE typed_minefields (member_id BIGINT, ordinal BIGINT)")
    db.execute("INSERT INTO typed_minefields VALUES (1,0),(1,1),(2,0),(4,0)")
    db.execute("CREATE TABLE typed_ships (member_id BIGINT, ordinal BIGINT)")
    db.execute("INSERT INTO typed_ships VALUES (1,0),(4,0),(5,0)")
    db.close()
    (root / "CURRENT").write_text("generations/synthetic-test.duckdb\n")
    monkeypatch.setattr(survey, "PINNED_SHA256", survey.file_sha256(path))
    return root


def test_pinned_current_accepts_only_known_generation_and_never_other(fake_public_root):
    good = survey.pinned_public68(fake_public_root)
    assert good.name == "synthetic-test.duckdb"
    (fake_public_root / "CURRENT").write_text("generations/other.duckdb\n")
    with pytest.raises(survey.ReadOnlyCensusAbstain, match="CURRENT_NOT_PINNED"):
        survey.pinned_public68(fake_public_root)
    (fake_public_root / "CURRENT").write_text("../../something-private.duckdb")
    with pytest.raises(survey.ReadOnlyCensusAbstain, match="CURRENT_NOT_PINNED"):
        survey.pinned_public68(fake_public_root)


def test_complete_synthetic_metadata_and_temporal_counts(fake_public_root):
    conn = duckdb.connect(str(survey.pinned_public68(fake_public_root)), read_only=True)
    try:
        names = survey.table_sections(conn)
        assert names == ("minefields", "ships")
        meta = survey.metadata_census(conn)
        assert meta["source_archives"] == 2
        assert meta["distinct_games"] == 2
        assert meta["source_members"] == 5
        assert meta["member_fields"] == 2
        assert meta["source_archive_bytes"] == 230
        assert meta["archive_turn_differs_from_embedded"] == 2
        temporal = survey.temporal_census(conn)
        assert temporal["snapshots_scanned"] == 5
        assert temporal["perspective_timelines"] == 2
        assert temporal["consecutive_archival_observation_pairs"] == 1
        assert temporal["nonconsecutive_archival_gaps"] == 1
        assert temporal["duplicate_embedded_turn_observations"] == 1
        sections = survey.section_census(conn, names)
        assert sections["minefields"] == {
            "typed_entity_rows": 4, "members_with_nonempty_section": 3,
        }
        assert sections["ships"] == {
            "typed_entity_rows": 3, "members_with_nonempty_section": 3,
        }
    finally:
        conn.close()


def test_full_synthetic_audit_read_only_and_causal_abstention(fake_public_root):
    file = survey.pinned_public68(fake_public_root)
    before = (file.stat().st_size, file.stat().st_mtime_ns)
    payload = survey.audit(fake_public_root, verify_sha256=True)
    assert payload["status"] == "PASS_DESCRIPTIVE_CENSUS_NO_HOST_PHASE_PROMOTION"
    assert payload["source_generation_sha256_checked"] is True
    assert payload["no_public100_access"] is True
    assert payload["no_db_write_or_current_activation"] is True
    assert payload["source_sections_checked"] == 2
    assert payload["temporal_census"]["consecutive_archival_observation_pairs"] == 1
    assert payload["family_readiness"]["ship_sweeping"]["conditional_new_mechanics_host_audit"] == survey.ABSTAIN
    assert not payload["family_readiness"]["ship_sweeping"]["host_diff_verified_by_this_run"]
    assert (file.stat().st_size, file.stat().st_mtime_ns) == before


def test_missing_expected_members_atomic_abstain(fake_public_root, monkeypatch):
    monkeypatch.setattr(survey, "EXPECTED_MEMBERS", 6)
    with pytest.raises(survey.ReadOnlyCensusAbstain, match="MEMBER_IDENTITY"):
        survey.audit(fake_public_root, verify_sha256=True)


def test_wrong_sha_refuses_before_db_open(fake_public_root, monkeypatch):
    monkeypatch.setattr(survey, "PINNED_SHA256", "0" * 64)
    with pytest.raises(survey.ReadOnlyCensusAbstain, match="SHA256_MISMATCH"):
        survey.audit(fake_public_root, verify_sha256=True)


def test_source_matrix_never_promotes_from_section_presence():
    all_sections = {
        section: {"typed_entity_rows": 500, "members_with_nonempty_section": 100}
        for required in survey.SOURCE_CATEGORIES.values() for section in required
    }
    matrix = survey.observed_family_matrix(all_sections)
    assert set(matrix) == set(survey.SOURCE_CATEGORIES)
    for val in matrix.values():
        assert val["observational_source_sections_present"] is True
        assert not val["independently_authenticated_host_orders"]
        assert not val["independently_authenticated_phase_boundary"]
        assert not val["host_diff_verified_by_this_run"]
        assert val["conditional_new_mechanics_host_audit"] == survey.ABSTAIN
    incomplete = survey.observed_family_matrix({"minefields": {"typed_entity_rows": 4}})
    assert incomplete["movement"]["observational_source_sections_present"] is False
    assert "ships" in incomplete["movement"]["missing_sections"]


def test_source_and_report_contain_only_allowlisted_aggregates():
    assert survey.EXPECTED_GAMES == 68
    assert survey.EXPECTED_MEMBERS == 169569
    assert survey.PINNED_GENERATION.startswith("corpus-v2compact-public68-")
    assert survey.PINNED_SHA256 == "5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a"
