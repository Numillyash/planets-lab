"""Bounded actual embedded-turn selection with sanitized runtime evidence."""
from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from planets_lab.corpus.pq_bounded_window_selection import (
    REPORT_SCHEMA, select_bounded_pq_windows,
)
from tools.diagnostics.pq_bounded_window_selection import main
from test_pq_window_field_sufficiency import make_fixture


def with_turn_six(tmp_path, *, embedded=7, foreign_game=False):
    paths = make_fixture(tmp_path)
    _, _, folder = paths
    source = folder / "game-510234.zip"
    # Only synthetic data in fixture; no credentials or real archive rows.
    payload = {
        "game": {"id": 999999 if foreign_game else 510234, "turn": embedded},
        "player": {"id": 2, "email": "NEVER_PUBLIC_EMAIL"},
        "planets": [{"id": 5, "ownerid": 2, "infoturn": embedded}],
        "ships": [],
        "starbases": [],
        "messages": [{"text": "PRIVATE_NEVER_PUBLISH"}],
    }
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr("player2-turn6.trn", json.dumps(payload))
    return paths


def select(paths, **overrides):
    idx, cohort, archives = paths
    kwargs = {
        "feature_index": idx, "frozen_cohort": cohort,
        "archive_dir": archives, "game_id": 510234, "player_slot": 2,
        "first_archive_turn": 6, "max_pairs": 2, "max_accepted": 5,
    }
    kwargs.update(overrides)
    return select_bounded_pq_windows(**kwargs)


@pytest.mark.parametrize("early_embedded,category", [
    (7, "EMBEDDED_TURN_REPEATED"),
    (9, "EMBEDDED_TURN_BACKWARDS"),
    (4, "EMBEDDED_TURN_SKIPPED_FORWARD"),
])
def test_skips_invalid_early_pair_then_finds_authenticated_identity_window(
    tmp_path, early_embedded, category,
):
    paths = with_turn_six(tmp_path, embedded=early_embedded)
    report = select(paths)
    assert report["schema"] == REPORT_SCHEMA
    assert report["archive_name_adjacent_pairs_in_bounded_range"] == 2
    assert report["actually_checked_pairs"] == 2
    assert report["admissible_consecutive_embedded_pairs"] == 1
    assert report["refusal_counts"] == {category: 1}
    assert report["first_approved_archive_turn"] == 7
    assert report["admissible_window_reports"][0]["before_embedded_turn"] == 7
    assert report["admissible_window_reports"][0]["after_embedded_turn"] == 8
    assert not report["nuhost_execution_verified"]
    assert not report["pp_warehouse_queue_parity_verified"]
    assert not report["raw_turn_payloads_emitted"]
    encoded = json.dumps(report)
    assert "PRIVATE_NEVER_PUBLISH" not in encoded
    assert "NEVER_PUBLIC_EMAIL" not in encoded


def test_invalid_game_identity_is_refused_but_not_reclassified_as_nonconsecutive(tmp_path):
    paths = with_turn_six(tmp_path, foreign_game=True)
    report = select(paths, max_pairs=1)
    assert report["admissible_consecutive_embedded_pairs"] == 0
    assert report["refusal_counts"] == {"EMBEDDED_GAME_IDENTITY_MISMATCH": 1}
    assert report["no_eligible_pair_in_checked_scope"] is True


def test_bounded_no_candidate_still_writes_atomic_sanitized_report(tmp_path):
    paths = with_turn_six(tmp_path, embedded=7)
    target = tmp_path / "artifacts" / "results.json"
    idx, cohort, archive = paths
    argv = [
        "--feature-index", str(idx), "--frozen-cohort", str(cohort),
        "--archive-dir", str(archive), "--game-id", "510234",
        "--player-slot", "2", "--first-archive-turn", "6",
        "--max-pairs", "1", "--max-accepted", "1", "--output", str(target),
    ]
    assert main(argv) == 2
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["refusal_counts"] == {"EMBEDDED_TURN_REPEATED": 1}
    assert report["no_eligible_pair_in_checked_scope"] is True
    assert report["actually_checked_pairs"] == 1
    assert main(argv[:-4] + ["--max-pairs", "2", "--max-accepted", "1",
                             "--output", str(target)]) == 0
    assert json.loads(target.read_text())["first_approved_archive_turn"] == 7


@pytest.mark.parametrize("bad", [
    {"game_id": 510235},
    {"player_slot": True},
    {"first_archive_turn": -1},
    {"max_pairs": 0},
    {"max_pairs": 65},
    {"max_accepted": 9},
])
def test_scope_and_limits_fail_closed_prior_to_archive_access(tmp_path, bad):
    paths = make_fixture(tmp_path)
    with pytest.raises(ValueError):
        select(paths, **bad)


def test_missing_second_archive_file_not_interpreted_as_empty_game(tmp_path):
    paths = make_fixture(tmp_path)
    out = select(paths, first_archive_turn=200)
    assert out["archive_name_adjacent_pairs_in_bounded_range"] == 0
    assert out["admissible_consecutive_embedded_pairs"] == 0
    assert out["no_eligible_pair_in_checked_scope"]


def test_existing_window_reader_still_rejects_nonconsecutive_embedded_turns(tmp_path):
    from planets_lab.corpus.pq_window_field_sufficiency import scan_single_pq_window
    paths = with_turn_six(tmp_path, embedded=7)
    with pytest.raises(ValueError, match="embedded turns are not consecutive"):
        scan_single_pq_window(
            feature_index=paths[0], frozen_cohort=paths[1],
            archive_dir=paths[2], game_id=510234, player_id=2,
            t_before=6,
        )


def test_evidence_script_uses_only_existing_runtime_worktree_wrapper():
    root = Path(__file__).resolve().parents[1]
    gate = root / "tools" / "run-pq-window-selection-gate.sh"
    launch = root / "tools" / "run-pq-window-selection-with-evidence.sh"
    for path in (gate, launch):
        subprocess.run(["bash", "-n", str(path)], check=True)
    assert "run-with-runtime-evidence.sh" in launch.read_text()
    assert "--include" in launch.read_text()
    assert "pq_bounded_window_selection" in gate.read_text()
    assert "--build" not in gate.read_text()
    assert "runtime-logs" not in gate.read_text()
