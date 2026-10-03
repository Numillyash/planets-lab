from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import combat_public_capture_o_layer_probe_db as module
from planets_lab.corpus.corpus_db_compact import CORPUS_DB_COMPACT_SCHEMA


def test_corpus_db_root_uses_explicit_then_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = tmp_path / "explicit"
    assert module._corpus_db_root(explicit) == explicit

    env_root = tmp_path / "env"
    monkeypatch.setenv(module.CORPUS_DB_ROOT_ENV, str(env_root))
    assert module._corpus_db_root(None) == env_root

    monkeypatch.delenv(module.CORPUS_DB_ROOT_ENV)
    with pytest.raises(ValueError, match=module.CORPUS_DB_ROOT_ENV):
        module._corpus_db_root(None)


def test_open_current_compact_is_read_only_and_validates_schema(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    generations = root / "generations"
    generations.mkdir(parents=True)
    database = generations / "test.duckdb"

    con = duckdb.connect(str(database))
    con.execute("CREATE TABLE corpus_metadata(schema_version VARCHAR NOT NULL)")
    con.execute("INSERT INTO corpus_metadata VALUES (?)", [CORPUS_DB_COMPACT_SCHEMA])
    con.execute(
        "CREATE TABLE typed_entity_schema(section_name VARCHAR, schema_json VARCHAR)"
    )
    con.close()
    (root / "CURRENT").write_text("generations/test.duckdb\n", encoding="utf-8")

    opened, resolved, specs = module._open_current_compact(root)
    try:
        assert resolved == database.resolve()
        assert specs == {}
        assert opened.execute("SELECT schema_version FROM corpus_metadata").fetchone()[0] == CORPUS_DB_COMPACT_SCHEMA
    finally:
        opened.close()


def test_member_rows_filter_target_turns(tmp_path: Path) -> None:
    database = tmp_path / "rows.duckdb"
    con = duckdb.connect(str(database))
    con.execute(
        """
        CREATE TABLE source_members(
            member_id BIGINT,
            source_member_name VARCHAR,
            perspective_player_id BIGINT,
            archive_turn BIGINT,
            embedded_turn BIGINT,
            decoded_payload_sha256 VARCHAR,
            member_ordinal BIGINT,
            game_id BIGINT
        )
        """
    )
    con.executemany(
        "INSERT INTO source_members VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "player1-turn4.trn", 1, 4, 5, "a", 4, 42),
            (2, "player1-turn5.trn", 1, 5, 6, "b", 5, 42),
            (3, "player2-turn5.trn", 2, 5, 6, "c", 6, 42),
            (4, "player1-turn5.trn", 1, 5, 6, "d", 7, 99),
        ],
    )
    try:
        rows = module._member_rows(
            con,
            game_id=42,
            archive_turns={5},
        )
        assert [int(row[0]) for row in rows] == [2, 3]
    finally:
        con.close()


def test_targeted_vcr_appearances_deduplicates_perspectives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_vcr = {
        "id": 9,
        "turn": 7,
        "x": 100,
        "y": 200,
        "left": {"objectid": 11, "hullid": 1, "raceid": 1},
        "right": {"objectid": 22, "hullid": 2, "raceid": 2},
    }
    payload = {
        "game": {"turn": 7},
        "beams": [],
        "torpedos": [],
        "settings": {},
        "vcrs": [raw_vcr],
    }

    def fake_replay(vcr, *, beams, torpedoes, settings):
        assert vcr["id"] == 9
        return {
            "left": {"owner_id": 1, "destroyed": False, "captured": False},
            "right": {"owner_id": 2, "destroyed": False, "captured": False},
        }

    monkeypatch.setattr(module, "replay_nuhost_from_nu_catalog", fake_replay)
    appearances, summary = module._targeted_vcr_appearances(
        game_id=42,
        records=[{"payload": payload}, {"payload": payload}],
        battle_turns={7},
    )

    assert summary["raw_vcr_observations"] == 2
    assert summary["unique_vcrs"] == 1
    assert summary["payload_conflicts"] == 0
    assert summary["ship_appearances"] == 2
    assert {(row["ship_id"], row["side"]) for row in appearances} == {
        (11, "left"),
        (22, "right"),
    }


def test_targeted_vcr_appearances_fails_closed_on_payload_conflict() -> None:
    first = {
        "game": {"turn": 7},
        "beams": [],
        "torpedos": [],
        "settings": {},
        "vcrs": [
            {
                "id": 9,
                "turn": 7,
                "x": 100,
                "y": 200,
                "left": {"objectid": 11, "hullid": 1, "raceid": 1},
                "right": {"objectid": 22, "hullid": 2, "raceid": 2},
            }
        ],
    }
    second = {
        **first,
        "vcrs": [
            {
                **first["vcrs"][0],
                "x": 101,
            }
        ],
    }

    with pytest.raises(ValueError, match="payload conflicts"):
        module._targeted_vcr_appearances(
            game_id=42,
            records=[{"payload": first}, {"payload": second}],
            battle_turns={7},
        )


def test_db_runner_uses_shared_read_only_corpus_backend() -> None:
    root = Path(__file__).resolve().parents[1]
    runner = (
        root / "tools/run-public-capture-o-layer-discovery-db.sh"
    ).read_text(encoding="utf-8")

    assert "compose.corpus-db.yaml" in runner
    assert "PLANETS_CORPUS_DB_ROOT" in runner
    assert "combat_public_capture_o_layer_probe_db.py" in runner
    assert "validation/corpus/cache/loadall" not in runner
