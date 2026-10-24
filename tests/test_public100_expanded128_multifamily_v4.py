"""Synthetic expanded public100/baseline68 read-only sampling and sanitized evidence."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from planets_lab.corpus.m2_economy_coverage import (
    Member, census_members, MAX_PAIRS_PER_GAME, MAX_SELECTED_PAIRS,
)
from tools.diagnostics.public100_pytest_failed_modules_v4 import (
    classify_module_failures, SCHEMA,
)


def test_frozen_sample_spreads_128_pairs_across_each_of_68_allowed_games():
    members = [
        Member(idx * 1000 + turn, idx, idx + 1, turn, turn)
        for idx in range(1, 101)
        for turn in range(1, 132)
    ]
    selected_ids = set(range(1, 69))
    meta, chosen = census_members(
        members, max_games=68, pairs_per_game=128,
        allowed_games=selected_ids,
    )
    assert MAX_PAIRS_PER_GAME == 128
    assert MAX_SELECTED_PAIRS >= 8704
    assert meta["all_games_in_source_metadata"] == 100
    assert meta["metadata_selected_game_count"] == 68
    assert meta["metadata_frozen_sample_pairs"] == 8704
    assert len(chosen) == 8704
    assert all(row.game in selected_ids for row in chosen)
    assert all(row.after_turn >= 2 for row in chosen)
    assert len({(p.game, p.after_turn) for p in chosen}) == 8704
    meta2, chosen2 = census_members(
        list(reversed(members)), max_games=68, pairs_per_game=128,
        allowed_games=selected_ids,
    )
    assert meta == meta2
    assert chosen == chosen2


def test_cannot_exceed_frozen_128_per_game_budget():
    records = [Member(i, 12, 44, i, i) for i in range(1, 150)]
    with pytest.raises(ValueError, match="pairs_per_game out of bounds"):
        census_members(records, max_games=1, pairs_per_game=129, allowed_games={12})


def test_junit_failed_modules_only_from_allowlisted_git_files():
    known={"tests/test_public100_deep_batch_safe_counts_v2.py",
           "tests/test_m2_corpus_economy_coverage_v1.py"}
    xml=(
        b'<testsuites><testsuite tests="5" failures="2" errors="2" skipped="0">'
        b'<testcase classname="tests.test_m2_corpus_economy_coverage_v1" name="private-planet-101">'
        b'<failure message="owner orders PRIVATE">stack PRIVATE</failure></testcase>'
        b'<testcase classname="tests.test_m2_corpus_economy_coverage_v1" name="private-planet-202">'
        b'<error>private traceback</error></testcase>'
        b'<testcase classname="tests.test_public100_deep_batch_safe_counts_v2" name="abc[secret]">'
        b'<failure>private order</failure></testcase>'
        b'<testcase classname="tests.test_private_project" name="secret">'
        b'<error>other private source</error></testcase>'
        b'</testsuite></testsuites>'
    )
    report=classify_module_failures(xml,known)
    assert report["schema"]==SCHEMA
    assert report["status"]=="PASS_SAFE_FAILURE_COUNTS_ONLY"
    assert report["allowlisted_failed_modules"]==[
        {"module":"tests/test_m2_corpus_economy_coverage_v1.py","failures":1,"errors":1},
        {"module":"tests/test_public100_deep_batch_safe_counts_v2.py","failures":1,"errors":0},
    ]
    assert report["unmapped_failures_or_errors"]==1
    assert report["raw_test_names_or_traces_exported"] is False
    for term in ("PRIVATE","private-planet","secret","owner orders","private_project"):
        assert term not in json.dumps(report)


def test_invalid_junit_and_unknown_module_do_not_leak_data():
    known={"tests/test_m2_corpus_economy_coverage_v1.py"}
    for bad in (None,b"",b"<testcase",b"<private><testcase /></private>"):
        assert classify_module_failures(bad,known)["status"]=="ABSTAIN_INVALID_JUNIT"
    raw=(b'<testsuite><testcase classname="tests.test_m2_corpus_economy_coverage_v1">'
         b'<failure>bad</failure></testcase>'
         b'<testcase classname="tests.test_m2_corpus_economy_coverage_v1.secret">'
         b'<failure>bad</failure></testcase></testsuite>')
    report=classify_module_failures(raw,known)
    assert report["allowlisted_failed_modules"][0]["failures"]==1
    assert report["unmapped_failures_or_errors"]==1


def test_shell_syntax_and_one_command_evidence_boundary():
    root=Path(__file__).resolve().parents[1]
    for path in (
        "tools/run-public100-baseline68-expanded128-v4.sh",
        "tools/run-public100-baseline68-expanded128-v4-with-evidence.sh",
    ):
        check=subprocess.run(["bash","-n",str(root/path)],capture_output=True,
                             text=True,check=False)
        assert check.returncode==0,path
    runner=(root/"tools/run-public100-baseline68-expanded128-v4.sh").read_text()
    launcher=(root/"tools/run-public100-baseline68-expanded128-v4-with-evidence.sh").read_text()
    assert "--pairs-per-game 128" in runner
    assert "--expected-baseline-games 68" in runner
    assert "--max-games 68" in runner
    assert "public100_baseline68_cohort_guard_v3.py" in runner
    assert "m2_validate_corpus_aggregate_evidence_v1.py" in runner
    assert "public100_pytest_failed_modules_v4.py" in runner
    assert "tools/run-with-runtime-evidence.sh" in launcher
    assert "pytest-failed-modules.json" in launcher
    assert "private-local" not in launcher
