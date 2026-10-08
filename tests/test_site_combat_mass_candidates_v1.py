from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

PATH = DIAGNOSTICS / "combat_site_mass_candidates_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_site_mass_candidates_v1", PATH)
assert SPEC is not None and SPEC.loader is not None
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def _specs():
    return SimpleNamespace(
        hulls={
            89: SimpleNamespace(mass=150),
            70: SimpleNamespace(mass=980),
            5: SimpleNamespace(mass=139),
        }
    )


def _ship(ship_id, hull, mass, bays=0, race=5):
    return {
        "objectid": ship_id, "hullid": hull, "mass": mass,
        "raceid": race, "baycount": bays,
    }


def test_mass_candidates_match_360_bonus_without_promoting_rng() -> None:
    left = _ship(184, 70, 980, bays=10)
    right = _ship(140, 89, 510)
    candidate = MOD.side_combat_mass_candidates(
        side_name="right", side=right, left=left, specs=_specs()
    )
    assert candidate["right_carrier_bonus_eligible_candidate"] is True
    assert [v["mass"] for v in candidate["allowed_candidates"]] == [150, 510]
    assert candidate["match"] == "right_vs_left_carrier_random_plus_360"

    no_bonus_observed = _ship(140, 89, 150)
    candidate = MOD.side_combat_mass_candidates(
        side_name="right", side=no_bonus_observed, left=left,
        specs=_specs(),
    )
    assert candidate["status"] == "documented_candidate_match"
    assert candidate["match"] == "base_hull_mass_plus_documented_fed_if_applicable"


def test_mass_candidate_excludes_small_right_ship_and_noncarrier_left() -> None:
    left = _ship(140, 89, 150)
    right = _ship(170, 89, 510)
    candidate = MOD.side_combat_mass_candidates(
        side_name="right", side=right, left=left, specs=_specs()
    )
    assert candidate["allowed_candidates"] == [
        {"scenario": "base_hull_mass_plus_documented_fed_if_applicable", "mass": 150}
    ]
    assert candidate["status"] == "outside_documented_candidate_set"

    small = _ship(171, 5, 499)
    candidate = MOD.side_combat_mass_candidates(
        side_name="right", side=small,
        left=_ship(184, 70, 980, bays=10), specs=_specs(),
    )
    assert candidate["right_carrier_bonus_eligible_candidate"] is False
    assert candidate["status"] == "outside_documented_candidate_set"


def test_mass_candidate_fed_bonus_is_scoped_to_factual_race() -> None:
    left = _ship(184, 70, 1030, bays=10, race=1)
    candidate = MOD.side_combat_mass_candidates(
        side_name="left", side=left, left=left, specs=_specs()
    )
    assert candidate["match"] == "base_hull_mass_plus_documented_fed_if_applicable"
    assert candidate["allowed_candidates"][0]["mass"] == 1030


def test_build_report_keeps_contradictions_and_seed_factual() -> None:
    cases = {
        (141, 592): SimpleNamespace(payload={
            "left": _ship(184, 70, 980, bays=10),
            "right": _ship(140, 89, 510), "seed": 27,
        }),
        (141, 593): SimpleNamespace(payload={
            "left": _ship(140, 89, 150),
            "right": _ship(170, 89, 999), "seed": 81,
        }),
    }
    result = MOD.build_report(
        game_id=400330, turn=141, cases=cases,
        specs=_specs(), database_path="/tmp/example.duckdb",
    )
    assert result["status"] == "OBSERVATIONAL_NOT_PROMOTED"
    assert result["summary"]["ship_vs_ship_vcrs"] == 2
    assert result["summary"]["outside_documented_candidate_set"] == 1
    assert result["rows"][0]["seed_observed_only"] == 27


def test_runner_shell_syntax_and_public100_relative() -> None:
    runner = REPO_ROOT / "tools" / "run-site-combat-mass-candidates-v1.sh"
    wrapper = REPO_ROOT / "tools" / "run-site-combat-mass-candidates-v1-with-evidence.sh"
    subprocess.run(["bash", "-n", str(runner)], check=True)
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    source = runner.read_text(encoding="utf-8")
    wrap = wrapper.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in source
    assert '--corpus-db-generation "$DB"' not in source
    assert r"\\${" not in source and r"\\${" not in wrap
    assert "tools/run-with-runtime-evidence.sh" in wrap
