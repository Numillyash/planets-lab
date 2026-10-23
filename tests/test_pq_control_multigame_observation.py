"""Frozen public-control PPQ multi-game bounded corpus survey, with zero raw IDs."""
from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from planets_lab.corpus.pq_control_multigame_observation import (
    SCHEMA, survey_frozen_public_ppq,
)
from tools.diagnostics.pq_control_multigame_observation import main
from test_pq_window_field_sufficiency import make_fixture


def run(paths, **kwargs):
    index, cohort, archives = paths
    opts = {
        "feature_index": index, "frozen_cohort": cohort,
        "archive_dir": archives, "player_slot": 2,
        "first_archive_turn": 7, "max_pairs_per_game": 4,
        "max_accepted_per_game": 2,
    }
    opts.update(kwargs)
    return survey_frozen_public_ppq(**opts)


def test_one_allowed_ppq_game_with_one_real_strict_embedded_pair(tmp_path):
    paths = make_fixture(tmp_path)
    result = run(paths)
    assert result["schema"] == SCHEMA
    assert result["scoped_games"] == 1
    assert result["archive_adjacent_pairs_checked"] == 1
    assert result["embedded_consecutive_pairs_admitted"] == 1
    assert result["owner_current_source_qualified_pairs"] == 1
    assert result["owner_current_source_abstain_pairs"] == 0
    assert result["games_with_qualified_observations"] == 1
    assert result["games_with_newly_visible_owned_fresh_ship_identity"] == 0
    row = result["by_game"][0]
    assert row["queue_mode"] == "PPQ"
    assert row["game_id"] == 510234
    assert row["entity_identity_counts"]["ships"]["observed_in_both"] == 1
    assert row["entity_identity_counts"]["starbases"]["observed_in_both"] == 1
    assert row["entity_identity_counts"]["planets"]["observed_in_both"] == 1
    assert row["starbase_provenance_observations"]["fresh_owned_planet_linked_bases"] == 2
    assert row["has_newly_visible_owned_fresh_ship_identity"] is False
    assert all(
        result[f] is False for f in (
            "independently_complete_owner_ship_roster",
            "ship_appearance_is_construction_verified",
            "ship_disappearance_is_loss_verified",
            "planet_gained_is_colonization_verified",
            "queue_component_warehouse_and_pp_verified",
            "server_accepted_orders_verified",
            "host_causal_verified",
        )
    )
    assert result["only_predeclared_public_control_games"]
    assert result["no_sealed_holdout_or_public100_scan"]
    assert result["no_individual_entity_identifiers_emitted"]
    assert result == run(paths)


def test_fresh_owned_appearance_count_not_build_event(tmp_path):
    paths = make_fixture(tmp_path)
    archive = paths[2] / "game-510234.zip"
    with zipfile.ZipFile(archive) as previous:
        data = {i.filename: previous.read(i) for i in previous.infolist()}
    newer = json.loads(data["player2-turn8.trn"])
    newer["ships"].append({
        "id": 41, "ownerid": 2, "infoturn": 8,
        "friendlycode": "NEVER_UPLOAD_SECRET",
        "savekey": "PRIVATE_SECRET",
    })
    data["player2-turn8.trn"] = json.dumps(newer).encode()
    with zipfile.ZipFile(archive, "w") as new:
        for name, blob in data.items():
            new.writestr(name, blob)
    result = run(paths)
    assert result["games_with_newly_visible_owned_fresh_ship_identity"] == 1
    ships = result["entity_identity_counts"]["ships"]
    assert ships["newly_visible_owned_fresh_ids"] == 1
    assert ships["observed_in_both"] == 1
    assert result["ship_appearance_is_construction_verified"] is False
    serialized = json.dumps(result)
    assert "NEVER_UPLOAD_SECRET" not in serialized
    assert "PRIVATE_SECRET" not in serialized
    assert '"41"' not in serialized
    assert "friendlycode" not in serialized


def test_missing_approved_game_archive_is_explicit_abstention_not_zero_events(tmp_path):
    paths = make_fixture(tmp_path)
    (paths[2] / "game-510234.zip").unlink()
    result = run(paths)
    assert result["by_game"][0]["status"] == "ABSTAIN_ARCHIVE_MISSING"
    assert result["game_level_failures"] == {"APPROVED_GAME_ARCHIVE_MISSING": 1}
    assert result["owner_current_source_qualified_pairs"] == 0
    assert result["games_with_qualified_observations"] == 0
    assert result["host_causal_verified"] is False


@pytest.mark.parametrize("bad", [
    {"player_slot": True}, {"player_slot": 0}, {"player_slot": 51},
    {"first_archive_turn": -1}, {"max_pairs_per_game": 0},
    {"max_pairs_per_game": 65}, {"max_accepted_per_game": 9},
])
def test_survey_strict_limits_before_member_access(tmp_path, bad):
    paths = make_fixture(tmp_path)
    with pytest.raises(ValueError, match="scope"):
        run(paths, **bad)


def test_survey_cli_writes_and_rejects_invalid_input_without_overwriting(tmp_path):
    paths = make_fixture(tmp_path)
    target = tmp_path / "private" / "surveys" / "summary.json"
    command = [
        "--feature-index", str(paths[0]), "--frozen-cohort", str(paths[1]),
        "--archive-dir", str(paths[2]), "--perspective", "2",
        "--first-archive-turn", "7", "--max-pairs-per-game", "4",
        "--max-accepted-per-game", "2", "--output", str(target),
    ]
    assert main(command) == 0
    decoded = json.loads(target.read_text(encoding="utf-8"))
    assert decoded == run(paths)
    assert main(command[:-1] + [str(tmp_path / "blocked"), "--perspective", "0"]) == 2
    assert json.loads(target.read_text(encoding="utf-8")) == decoded


def test_one_command_evidence_launcher_and_no_docker_rebuild():
    root = Path(__file__).resolve().parents[1]
    launch = root / "tools" / "run-pq-control-multigame-with-evidence.sh"
    gate = root / "tools" / "run-pq-control-multigame-gate.sh"
    for file in (launch, gate):
        assert file.exists()
        subprocess.run(["bash", "-n", str(file)], check=True)
    a, b = launch.read_text(), gate.read_text()
    assert "run-with-runtime-evidence.sh" in a and "--include" in a
    assert "pq_control_multigame_observation" in b
    assert "pq-public-control12-frozen-cohort.v1.json" in b
    assert "--max-pairs-per-game 48" in b
    assert "--max-accepted-per-game 8" in b
    assert "--build" not in b
    assert "git push" not in a and "git checkout" not in a


def test_scanner_admits_no_other_indexed_game_outside_explicit_cohort(tmp_path):
    paths = make_fixture(tmp_path)
    result = run(paths)
    assert result["scoped_games"] == 1
    assert [r["game_id"] for r in result["by_game"]] == [510234]
    assert result["source_feature_index_sha256"]
    assert result["frozen_cohort_sha256"]
