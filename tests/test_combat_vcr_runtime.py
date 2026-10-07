from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import duckdb
import pytest

from planets_lab.corpus.combat_vcr_runtime import (
    CombatVcrInputConflict,
    combat_vcr_cases_for_turns,
)
from planets_lab.corpus.corpus_db_compact import import_archive_to_compact_database


def _payload(*, player: int, beam_damage: int = 3) -> dict[str, object]:
    return {
        "game": {"id": 42, "turn": 10},
        "player": {"id": player},
        "settings": {"combatrng": 0, "sphere": False},
        "beams": [{"id": 1, "damage": beam_damage, "crewkill": 10, "name": "Laser"}],
        "torpedos": [
            {
                "id": 1,
                "damage": 5,
                "crewkill": 4,
                "combatrange": 300,
                "name": "Torp",
            }
        ],
        "vcrs": [
            {
                "id": 7,
                "turn": 10,
                "seed": 3,
                "leftownerid": 1,
                "rightownerid": 2,
                "left": {"objectid": 100, "hullid": 5},
                "right": {"objectid": 200, "hullid": 6},
            }
        ],
        "ships": [],
        "planets": [],
    }


def _build_db(tmp_path: Path, *, conflict: bool = False) -> duckdb.DuckDBPyConnection:
    archive = tmp_path / "game-42.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for player in (1, 2):
            payload = _payload(
                player=player,
                beam_damage=4 if conflict and player == 2 else 3,
            )
            zf.writestr(
                f"player{player}-turn10.trn",
                json.dumps(payload).encode("utf-8"),
            )
    archive.write_bytes(buffer.getvalue())

    database = tmp_path / "fixture.duckdb"
    import_archive_to_compact_database(
        archive,
        database,
        expected_game_id=42,
        commit_every_members=1,
        arrow_batch_rows=4,
    )
    return duckdb.connect(str(database), read_only=True)


def test_compact_vcr_reader_keeps_only_replay_relevant_inputs(tmp_path: Path) -> None:
    connection = _build_db(tmp_path)
    try:
        cases = combat_vcr_cases_for_turns(
            connection,
            game_id=42,
            battle_turns={10},
        )
    finally:
        connection.close()

    case = cases[(10, 7)]
    assert case.observation_count == 2
    assert len(case.source_members) == 2
    assert case.settings == {"combatrng": 0}
    assert case.beams == ({"id": 1, "damage": 3, "crewkill": 10},)
    assert case.torpedoes == (
        {"id": 1, "damage": 5, "crewkill": 4, "combatrange": 300},
    )
    assert case.payload["seed"] == 3
    assert "ships" not in case.payload


def test_compact_vcr_reader_fails_closed_on_replay_input_conflict(
    tmp_path: Path,
) -> None:
    connection = _build_db(tmp_path, conflict=True)
    try:
        with pytest.raises(CombatVcrInputConflict, match="replay input conflict"):
            combat_vcr_cases_for_turns(
                connection,
                game_id=42,
                battle_turns={10},
            )
    finally:
        connection.close()
