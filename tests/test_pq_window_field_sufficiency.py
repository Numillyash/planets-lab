"""Predeclared PQ/PPQ two-member archival window, no personal/entity output."""
from __future__ import annotations

import gzip
import json
import zipfile
from pathlib import Path

import pytest

from planets_lab.corpus.feature_index import feature_row, write_feature_index
from planets_lab.corpus.pq_historical_readiness import COHORT_SCHEMA
from planets_lab.corpus.pq_window_field_sufficiency import (
    SCHEMA, scan_single_pq_window,
)
from tools.diagnostics.pq_window_field_sufficiency import main


def row(game_id, key, value):
    return feature_row(game_id=game_id, feature=key, value=value,
                       known=True, source_kind="synthetic",
                       source_location="synthetic-public-index")


def make_fixture(tmp_path, *, has_ships=True, gzip_after=False):
    game_id = 510234
    rows = [
        row(game_id, "game.status", 3),
        row(game_id, "settings.productionqueue", True),
        row(game_id, "settings.planetaryproductionqueue", True),
        row(game_id, "coverage.archive_present", True),
        row(game_id, "coverage.rectangular_grid_complete", True),
        row(game_id, "evidence.archive_transition_count", 2),
        row(510235, "game.status", 3),
    ]
    parquet = tmp_path / "features.parquet"
    write_feature_index(rows=rows, parquet_path=parquet,
                        database_path=tmp_path / "meta.duckdb")
    cohort = tmp_path / "frozen.json"
    cohort.write_text(json.dumps({
        "schema": COHORT_SCHEMA, "game_ids": [game_id]
    }), encoding="utf-8")
    folder = tmp_path / "archives"
    folder.mkdir()
    archive = folder / f"game-{game_id}.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for turn in (7, 8):
            payload = {
                "game": {"id": game_id, "turn": turn},
                "player": {
                    "id": 2, "email": "private@example.com",
                    "savekey": "SUPER_SECRET_DO_NOT_LEAK",
                },
                "planets": [
                    {"id": 20, "ownerid": 2, "infoturn": turn,
                     "megacredits": 300, "name": "Secret planet"},
                    {"id": 40, "ownerid": 3, "infoturn": turn},
                ],
                "starbases": [
                    {"planetid": 20, "ownerid": 2, "infoturn": turn,
                     "buildhullid": 7},
                ],
                "ships": [
                    {"id": 9, "ownerid": 2, "infoturn": turn,
                     "hullid": 7},
                    {"id": 8, "ownerid": 2},
                ],
                "messages": [{"text": "PRIVATE raw order"}],
            }
            if not has_ships and turn == 8:
                del payload["ships"]
            blob = json.dumps(payload).encode("utf-8")
            if gzip_after and turn == 8:
                blob = gzip.compress(blob)
            z.writestr(f"player2-turn{turn}.trn", blob)
        # Not selected: must never be decoded or included in report.
        z.writestr("player3-turn7.trn", b"INVALID_OTHER_PERSPECTIVE_PRIVATE")
    return parquet, cohort, folder


def report(paths, *, game_id=510234, player=2, turn=7):
    p, c, a = paths
    return scan_single_pq_window(
        feature_index=p, frozen_cohort=c, archive_dir=a,
        game_id=game_id, player_id=player, t_before=turn,
    )


@pytest.mark.parametrize("gzip_after", (False, True))
def test_actual_two_archive_members_only_privacy_minimal_shape(tmp_path, gzip_after):
    paths = make_fixture(tmp_path, gzip_after=gzip_after)
    result = report(paths)
    assert result["schema"] == SCHEMA
    assert result["queue_mode"] == "PPQ"
    assert result["before_archive_turn"] == 7 and result["after_archive_turn"] == 8
    assert result["archive_members_read"] == 2
    assert result["before"]["planets"]["visible_rows"] == 2
    assert result["before"]["planets"]["explicit_owner_fresh_rows"] == 1
    assert result["before"]["ships"]["explicit_owner_fresh_rows"] == 1
    assert result["before"]["ships"]["explicit_owner_without_infoturn_rows"] == 1
    assert result["after"]["starbases"]["explicit_owner_fresh_rows"] == 1
    assert result["missing_or_invalid_arrays"] == []
    assert result["observational_shape_available"]
    assert not result["causal_queue_replay_admitted"]
    assert not result["host_accepted_orders_verified"]
    assert not result["owner_pp_ledger_independently_complete"]
    assert not result["starbase_component_warehouses_independently_complete"]
    assert not result["host_phase_boundary_independent"]
    encoded = json.dumps(result, sort_keys=True)
    for forbidden in ("private@example.com", "SUPER_SECRET", "Secret planet",
                      "PRIVATE raw order", "buildhullid", "megacredits"):
        assert forbidden not in encoded
    out = tmp_path / "reports" / "two-member.json"
    assert main(["--feature-index", str(paths[0]), "--frozen-cohort", str(paths[1]),
                 "--archive-dir", str(paths[2]), "--game-id", "510234",
                 "--player-slot", "2", "--turn-before", "7", "--output", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == result


def test_missing_array_is_explicit_unknown_not_zero(tmp_path):
    out = report(make_fixture(tmp_path, has_ships=False))
    assert "ABSTAIN_SHIPS_ARRAY_MISSING" in out["missing_or_invalid_arrays"]
    assert out["after"]["ships"]["visible_rows"] is None
    assert not out["observational_shape_available"]


@pytest.mark.parametrize("case", (
    "not_in_cohort", "not_in_index", "wrong_player", "missing_before",
    "negative_turn", "boolean_game_id", "malformed_selected",
    "identity_mismatch", "invalid_gzip", "missing_archive",
))
def test_unknown_or_unapproved_public_window_fails_closed(tmp_path, case):
    paths = make_fixture(tmp_path)
    p, c, archive_dir = paths
    options = {}
    if case == "not_in_cohort":
        options["game_id"] = 510235
    elif case == "not_in_index":
        options["game_id"] = 999999
    elif case == "wrong_player":
        options["player"] = 1
    elif case == "missing_before":
        options["turn"] = 4
    elif case == "negative_turn":
        options["turn"] = -1
    elif case == "boolean_game_id":
        options["game_id"] = True
    elif case == "malformed_selected":
        path = archive_dir / "game-510234.zip"
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("player2-turn8.trn", b"not-json")
        # Duplicate filenames are accepted by ZIP, but latest member is invalid.
    elif case == "identity_mismatch":
        path = archive_dir / "game-510234.zip"
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("player2-turn8.trn",
                       json.dumps({"game": {"id": 510234, "turn": 9},
                                   "player": {"id": 2}}).encode())
    elif case == "invalid_gzip":
        path = archive_dir / "game-510234.zip"
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("player2-turn8.trn", b"\x1f\x8bNOT_VALID")
    elif case == "missing_archive":
        (archive_dir / "game-510234.zip").unlink()
    with pytest.raises((ValueError, OSError, json.JSONDecodeError, UnicodeDecodeError,
                        EOFError)):
        report(paths, **options)


def test_cli_invalid_input_preserves_previous_report_bytes(tmp_path):
    p, c, archive_dir = make_fixture(tmp_path)
    target = tmp_path / "existing.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    args = ["--feature-index", str(p), "--frozen-cohort", str(c),
            "--archive-dir", str(archive_dir), "--game-id", "510234",
            "--player-slot", "2", "--turn-before", "99",
            "--output", str(target)]
    assert main(args) == 2
    assert target.read_text(encoding="utf-8") == '{"old":true}\n'
