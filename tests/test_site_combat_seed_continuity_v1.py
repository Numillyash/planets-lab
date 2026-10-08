from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "diagnostics" / "combat_site_seed_continuity_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_site_seed_continuity_v1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def _case(seed, x=12):
    return SimpleNamespace(
        payload={"seed": seed, "x": x, "y": 14},
        beams=(), torpedoes=(), settings={"combatrng": 0},
    )


def test_seed_report_separates_same_next_and_other_offsets() -> None:
    cases = {
        (141, 592): _case(10),
        (141, 593): _case(20),
        (141, 594): _case(49, x=16),
    }
    finals = {10: 20, 20: 30, 49: 63}

    def replay(payload, *, beams, torpedoes, settings):
        return {"final_seed": finals[payload["seed"]], "cycles": 99}

    report = M.build_report(
        cases=cases, turn=141, game_id=400330,
        db_path="/tmp/synthetic", replay=replay,
    )
    assert report["status"] == "OBSERVATIONAL_NOT_PROMOTED"
    assert report["summary"]["observed_vcrs"] == 3
    assert report["summary"]["adjacent_comparable"] == 2
    assert report["summary"]["adjacent_same"] == 1
    assert report["summary"]["adjacent_neither"] == 1
    assert report["transitions"][1]["same_site_observed"] is False


def test_seed_wrap_and_unresolved_replay() -> None:
    cases = {
        (141, 592): _case(1),
        (141, 593): _case(1),
        (141, 595): _case(75),
    }
    def replay(payload, *, beams, torpedoes, settings):
        if payload["seed"] == 75:
            raise M.ReplayUnsupported("not supported")
        return {"final_seed": 119}

    report = M.build_report(
        cases=cases, turn=141, game_id=400330,
        db_path="/tmp/synthetic", replay=replay,
    )
    assert report["summary"]["adjacent_plus_one"] == 1
    assert report["summary"]["replay_unresolved"] == 1
    assert report["transitions"][1]["globally_adjacent"] is False


def test_seed_bool_fails_closed() -> None:
    with pytest.raises(ValueError, match="invalid seed"):
        M.build_report(
            cases={(141, 1): _case(True)},
            turn=141, game_id=400330, db_path="/tmp/synthetic",
        )


def test_runner_syntax_and_relative_generation() -> None:
    runner = ROOT / "tools" / "run-site-combat-seed-continuity-v1.sh"
    wrapper = ROOT / "tools" / "run-site-combat-seed-continuity-v1-with-evidence.sh"
    subprocess.run(["bash", "-n", str(runner)], check=True)
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    raw = runner.read_text(encoding="utf-8")
    wraw = wrapper.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in raw
    assert '--corpus-db-generation "$DB"' not in raw
    assert r"\\${" not in raw
    assert r"\\${" not in wraw
    assert "run-with-runtime-evidence.sh" in wraw
