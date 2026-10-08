from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "diagnostics" / "combat_multigame_conditional_ensemble_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_multigame_conditional_ensemble_v1", PATH)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class FakeQuery:
    def fetchall(self):
        return [
            (400330, 141, 10),
            (591478, 25, 6),
            (620694, 52, 12),
            (620694, 53, 8),
            (622476, 1, 2),
            (680910, 20, 16),
        ]


class FakeConn:
    def execute(self, query):
        assert "FROM vcrs" in query
        assert "GROUP BY" in query
        return FakeQuery()


def test_multi_game_selection_diversifies_and_excludes_known_special() -> None:
    candidates = M.select_game_turn_candidates(FakeConn(), max_candidate_games=4)
    assert candidates == [
        (400330, 141), (620694, 53), (622476, 1), (680910, 20),
    ]


def test_oracle_seed_and_mass_are_stripped_from_simulator_input() -> None:
    source={
        "seed": 27, "leftownerid": 5, "rightownerid": 10,
        "left": {"objectid": 184, "mass": 980, "crew": 100},
        "right": {"objectid": 140, "mass": 510, "crew": 90},
    }
    model=M._strip_oracle_rng_and_mass(source)
    assert "seed" not in model
    assert "mass" not in model["left"]
    assert "mass" not in model["right"]
    assert source["seed"] == 27
    assert source["right"]["mass"] == 510


def test_sample_observed_mass_checked_after_evaluator(monkeypatch) -> None:
    import types

    case = SimpleNamespace(
        vcr_id=592, battle_turn=141,
        payload={
            "seed": 27, "leftownerid": 5, "rightownerid": 10,
            "left": {"objectid": 184, "hullid": 70, "mass": 980},
            "right": {"objectid": 140, "hullid": 89, "mass": 510},
        },
        settings={"combatrng": 0}, beams=(), torpedoes=(),
    )
    called=[]

    def fake_eval(payload, **kwargs):
        called.append(payload)
        assert "seed" not in payload
        assert "mass" not in payload["left"]
        assert "mass" not in payload["right"]
        assert kwargs["right_hull_mass"] == 150
        return {
            "side_ids": {"left":184,"right":140},
            "left_mass":980,
            "mass_scenarios":[
                {"right_mass":150,"assumed_probability":0.4,"branch":"no_bonus"},
                {"right_mass":510,"assumed_probability":0.6,"branch":"carrier_plus_360"},
            ],
            "scenario_count":236,
        }

    monkeypatch.setattr(M,"evaluate_conditional_classic",fake_eval)
    specs=SimpleNamespace(
        hulls={70:SimpleNamespace(mass=980),89:SimpleNamespace(mass=150)}
    )
    row=M._sample_one(case=case,specs=specs,seeds=tuple(range(1,119)))
    assert called
    assert row["observed_mass_inside_scenarios"] is True
    assert row["factual_seed_inside_grid_after_evaluation"] is True
    assert row["input_provenance"].startswith("ORACLE_ASSISTED")


def test_runners_are_shell_valid_sha_pinned_and_relative() -> None:
    runner=ROOT/"tools"/"run-multigame-conditional-combat-pilot-v1.sh"
    wrapper=ROOT/"tools"/"run-multigame-conditional-combat-pilot-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    src=runner.read_text(encoding="utf-8")
    wrap=wrapper.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in src
    assert '--corpus-db-generation "$DB"' not in src
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in src
    assert r"\\${" not in src and r"\\${" not in wrap
    assert "run-with-runtime-evidence.sh" in wrap
