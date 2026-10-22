"""Predeclared PQ/PPQ two-member archival window, no personal/entity output."""
from __future__ import annotations

import gzip
import json
import subprocess
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


def make_fixture(tmp_path, *, has_ships=True, gzip_after=False, embedded_offset=0):
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
                "game": {"id": game_id, "turn": turn + embedded_offset},
                "player": {
                    "id": 2, "email": "private@example.com",
                    "savekey": "SUPER_SECRET_DO_NOT_LEAK",
                },
                "planets": [
                    {"id": 20, "ownerid": 2, "infoturn": turn + embedded_offset,
                     "megacredits": 300, "name": "Secret planet"},
                    {"id": 40, "ownerid": 3, "infoturn": turn},
                ],
                "starbases": [
                    {"planetid": 20, "ownerid": 2, "infoturn": turn + embedded_offset,
                     "buildhullid": 7},
                ],
                "ships": [
                    {"id": 9, "ownerid": 2, "infoturn": turn + embedded_offset,
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
    assert result["turn_identity_relation"] == "EXACT"
    assert result["archive_to_embedded_turn_offset"] == 0
    assert (result["before_embedded_turn"], result["after_embedded_turn"]) == (7, 8)
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
                      "PRIVATE raw order", "megacredits"):
        assert forbidden not in encoded
    assert result["starbase_provenance"]["before"]["source_key_presence_counts"]["buildhullid"] == 1
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


def test_tracked_public_control12_cohort_is_frozen_to_existing_manifest():
    from planets_lab.corpus.indexer import load_manifest_jsonl
    from planets_lab.corpus.pq_historical_readiness import parse_frozen_cohort
    base = Path("validation/corpus/manifests")
    rows = load_manifest_jsonl(
        (base / "accounts-recent-finished.jsonl").read_text(encoding="utf-8")
    )
    frozen = parse_frozen_cohort(
        (base / "pq-public-control12-frozen-cohort.v1.json").read_bytes()
    )
    assert len(frozen) == len(rows) == 12
    assert frozen == tuple(sorted(x["game_id"] for x in rows))
    assert all(x["game"]["status"] == 3 for x in rows)
    assert sum(
        x["settings"]["productionqueue"] is True
        and x["settings"]["planetaryproductionqueue"] is True
        for x in rows
    ) == 8


@pytest.mark.parametrize("offset", (-1, 1, 4))
def test_archive_filename_turn_and_embedded_turn_are_distinct_but_consecutive(
    tmp_path, offset,
):
    # Corpus normalizer records both; the original PQ validator wrongly
    # asserted they must be identical and rejected genuine archive windows.
    paths = make_fixture(tmp_path, embedded_offset=offset)
    report_data = report(paths)
    assert report_data["turn_identity_relation"] == "CONSISTENT_OFFSET"
    assert report_data["archive_to_embedded_turn_offset"] == offset
    assert report_data["before_embedded_turn"] == 7 + offset
    assert report_data["after_embedded_turn"] == 8 + offset
    assert report_data["before"]["planets"]["explicit_owner_fresh_rows"] == 1
    assert report_data["after"]["ships"]["explicit_owner_fresh_rows"] == 1
    assert not report_data["causal_queue_replay_admitted"]
    assert not report_data["host_accepted_orders_verified"]


def _rewrite_selected_turn(paths, *, target_turn, change):
    # Test-only ZIP rewriting: preserve all other members untouched while
    # mutating precisely the selected member's embedded identity.
    archive_path = paths[2] / "game-510234.zip"
    with zipfile.ZipFile(archive_path) as original:
        members = {item.filename: original.read(item)
                   for item in original.infolist()}
    name = f"player2-turn{target_turn}.trn"
    payload = json.loads(members[name].decode("utf-8"))
    change(payload)
    members[name] = json.dumps(payload).encode("utf-8")
    with zipfile.ZipFile(archive_path, "w") as archive:
        for key, contents in members.items():
            archive.writestr(key, contents)


@pytest.mark.parametrize("corrupt", (
    "wrong_game", "wrong_player", "nonconsecutive_embedded",
    "boolean_game_id", "boolean_embedded_turn",
))
def test_embedded_identity_is_still_checked_independently_of_archive_ordinal(
    tmp_path, corrupt,
):
    paths = make_fixture(tmp_path, embedded_offset=1)
    def change(payload):
        if corrupt == "wrong_game":
            payload["game"]["id"] = 510235
        elif corrupt == "wrong_player":
            payload["player"]["id"] = 3
        elif corrupt == "nonconsecutive_embedded":
            payload["game"]["turn"] = 12
        elif corrupt == "boolean_game_id":
            payload["game"]["id"] = True
        else:
            payload["game"]["turn"] = True
    _rewrite_selected_turn(paths, target_turn=8, change=change)
    with pytest.raises(ValueError, match="embedded"):
        report(paths)


def test_one_command_corpus_runner_delegates_to_existing_runtime_branch_wrapper():
    root = Path(__file__).resolve().parents[1]
    gate = root / "tools" / "run-pq-public-window-gate.sh"
    launcher = root / "tools" / "run-pq-public-window-with-evidence.sh"
    for path in (gate, launcher):
        assert path.is_file()
        subprocess.run(["bash", "-n", str(path)], check=True)
    runner = launcher.read_text(encoding="utf-8")
    assert "run-with-runtime-evidence.sh" in runner
    assert "run-pq-public-window-gate.sh" in runner
    assert "--include" in runner
    assert "artifacts/pq/windows/" in runner
    assert "git push" not in runner and "git checkout" not in runner
    assert "--build" not in gate.read_text(encoding="utf-8")
