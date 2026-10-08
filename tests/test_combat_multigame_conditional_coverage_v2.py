from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

SCRIPT = DIAGNOSTICS / "combat_multigame_conditional_coverage_v2.py"
SPEC = importlib.util.spec_from_file_location("combat_multigame_conditional_coverage_v2", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class FakeQuery:
    def fetchall(self):
        # Deliberately unsorted, with multiple turns, to test deterministic sorting.
        return [
            (620694, 52, 18),
            (400330, 141, 24),
            (591478, 25, 90),
            (230354, 8, 4),
            (620694, 53, 32),
            (680910, 20, 20),
            (245123, 12, 16),
            (233558, 9, 8),
        ]


class FakeDB:
    def execute(self, sql):
        assert "FROM vcrs" in sql
        assert "perspective_vcr_rows" in sql
        return FakeQuery()


def test_selects_anchor_then_spreads_games_and_ranks_multiple_turns() -> None:
    games = MOD.choose_game_turns(
        FakeDB(), max_candidate_games=4, turns_per_game=2
    )
    assert [g for g, _ in games] == [400330, 230354, 245123, 680910]
    assert games[0][1][0].turn == 141
    assert games[0][1][0].selection == "previously_verified_anchor"

    many = MOD.choose_game_turns(
        FakeDB(), max_candidate_games=8, turns_per_game=2
    )
    rows = dict(many)
    assert [t.turn for t in rows[620694]] == [53, 52]
    assert 591478 not in rows


def test_multi_turn_backfill_and_partial_coverage_are_distinct(monkeypatch) -> None:
    monkeypatch.setattr(MOD, "choose_game_turns", lambda *a, **kw: [
        (100, [
            MOD.TurnCandidate(100, 8, 10),
            MOD.TurnCandidate(100, 9, 8),
        ]),
        (200, [
            MOD.TurnCandidate(200, 5, 8),
            MOD.TurnCandidate(200, 6, 6),
        ]),
    ])
    monkeypatch.setattr(MOD, "_independent_hull_specs",
                        lambda conn, gid: SimpleNamespace(hulls={}))

    def fake_case(vcr_id, turn):
        return SimpleNamespace(vcr_id=vcr_id, battle_turn=turn)

    def fake_cases(conn, *, game_id, battle_turns):
        turn = next(iter(battle_turns))
        if (game_id, turn) == (100, 8):
            return {(8, 1): fake_case(1, 8)}  # planet battle
        if (game_id, turn) == (100, 9):
            return {(9, 2): fake_case(2, 9), (9, 3): fake_case(3, 9)}
        if (game_id, turn) == (200, 5):
            return {(5, 4): fake_case(4, 5)}
        return {(6, 5): fake_case(5, 6)}

    monkeypatch.setattr(MOD, "combat_vcr_cases_for_turns", fake_cases)
    def fake_sample(*, case, specs, seeds):
        if case.vcr_id in (1, 4, 5):
            raise MOD.ReplayUnsupported("unsupported planet/RNG")
        return {
            "vcr_id":case.vcr_id,
            "battle_turn":case.battle_turn,
            "observed_mass_inside_scenarios":True,
            "ensemble":{"scenario_count":len(seeds), "carrier_eligible":False},
        }

    monkeypatch.setattr(MOD, "_sample_one", fake_sample)
    report = MOD.build_coverage_report(
        connection=object(), db_path="/tmp/fixture",
        max_games=2, cases_per_game=2, max_candidate_games=2,
        turns_per_game=2, seeds=(1, 2),
    )
    assert report["status"] == "PARTIAL_GAME_OR_CASE_COVERAGE"
    summary = report["summary"]
    assert summary["games_selected"] == 1
    assert summary["cases_evaluated"] == 2
    assert summary["full_case_quota_games"] == 1
    assert summary["observed_mass_inside_scenarios"] == 2
    assert summary["scenario_replays"] == 4
    assert summary["turns_attempted"] == 4
    assert summary["vcrs_attempted"] == 5
    assert summary["games_rejected"] == 1
    assert report["selected_games"][0]["attempted_turns"][0]["unsupported"] == {
        "unsupported planet/RNG":1
    }
    assert report["rejected_games"][0]["game_id"] == 200


def test_success_requires_both_game_and_case_targets(monkeypatch) -> None:
    monkeypatch.setattr(MOD, "choose_game_turns", lambda *a, **kw: [
        (100, [MOD.TurnCandidate(100, 1, 12)]),
    ])
    monkeypatch.setattr(MOD, "_independent_hull_specs",
                        lambda conn, gid: SimpleNamespace(hulls={}))
    monkeypatch.setattr(
        MOD, "combat_vcr_cases_for_turns",
        lambda conn, **kw: {
            (1, 1): SimpleNamespace(vcr_id=1,battle_turn=1),
            (1, 2): SimpleNamespace(vcr_id=2,battle_turn=1),
        }
    )
    monkeypatch.setattr(MOD, "_sample_one",
                        lambda **kw: {
                            "vcr_id":kw["case"].vcr_id,
                            "battle_turn":1,
                            "observed_mass_inside_scenarios":False,
                            "ensemble":{"scenario_count":2},
                        })
    report = MOD.build_coverage_report(
        connection=object(), db_path="/tmp/test",
        max_games=1, cases_per_game=2,
        max_candidate_games=1, turns_per_game=1,seeds=(1,2),
    )
    assert report["status"] == "CONDITIONAL_MULTIGAME_COVERAGE_TARGET_MET"
    assert report["summary"]["observed_mass_outside_scenarios"] == 2


def test_invalid_bounds_fail_closed() -> None:
    with pytest.raises(ValueError, match="invalid"):
        MOD.build_coverage_report(
            connection=object(),db_path="n/a",
            max_games=10,max_candidate_games=5,
        )


def test_bounded_runner_shell_and_immutable_public100_generation() -> None:
    runner = ROOT / "tools" / "run-multigame-conditional-combat-coverage-v2.sh"
    wrapper = ROOT / "tools" / "run-multigame-conditional-combat-coverage-v2-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    source = runner.read_text(encoding="utf-8")
    wsource = wrapper.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in source
    assert '--corpus-db-generation "$DB"' not in source
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in source
    assert r"\\${" not in source
    assert r"\\${" not in wsource
    assert "run-with-runtime-evidence.sh" in wsource
