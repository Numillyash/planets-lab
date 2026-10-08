from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "diagnostics" / "combat_mass_residual_triage_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_mass_residual_triage_v1", PATH)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def _specs():
    cost = SimpleNamespace(megacredits=300)
    return SimpleNamespace(
        hulls={
            70: SimpleNamespace(mass=980, name="Big Carrier", special=""),
            89: SimpleNamespace(mass=170, name="Torpedo Ship", special=""),
            90: SimpleNamespace(mass=60, name="Saber Shield Generator", special="Shield Generator"),
        },
        engines={
            9: SimpleNamespace(name="Transwarp Drive", cost=cost),
        },
    )


def _payload():
    return {
        "seed": 39,
        "x": 1674, "y": 2363,
        "leftownerid": 5, "rightownerid": 10,
        "left": {
            "objectid": 16, "hullid": 70, "raceid": 5,
            "mass": 980, "baycount": 10, "shield": 100,
        },
        "right": {
            "objectid": 220, "hullid": 89, "raceid": 10,
            "mass": 470, "baycount": 0, "shield": 90,
        },
    }


def _member(ship_rows, *, settings=None):
    return {
        "game": {"id": 217591, "turn": 149},
        "ships": ship_rows,
        "settings": settings or {},
    }


def _ref(turn, perspective):
    return SimpleNamespace(archive_turn=turn, perspective_player_id=perspective)


def test_triage_preserves_exact_residual_and_raw_context() -> None:
    payload = _payload()
    members = [
        (_ref(148, 10), _member([
            {"id": 220, "ownerid": 10, "hullid": 89, "engineid": 9, "x": 1670, "y": 2350},
            {"id": 444, "ownerid": 10, "hullid": 90, "x": 1674, "y": 2363},
        ], settings={"combatrng": 0, "engineshieldbonus": 0})),
        (_ref(149, 5), _member([
            {"id": 16, "ownerid": 5, "hullid": 70, "x": 1674, "y": 2363}
        ])),
    ]
    row = M.triage_case(
        game_id=217591, turn=149, vcr_id=2390,
        payload=payload, specs=_specs(), archived_members=members,
    )
    assert row["vcr_id"] == 2390
    right = row["sides"][1]
    assert right["factual_mass"] == 470
    assert right["catalog_plus_fed_base"] == 170
    assert right["mass_inside_candidates"] is False
    assert right["residuals_after_possible_branches"] == [
        {"candidate_mass":170,"unexplained_delta":300},
        {"candidate_mass":530,"unexplained_delta":-60},
    ]
    assert right["observed_engine_ids"] == [9]
    assert right["engine_costs_from_catalog"][0]["possible_shield_generator_bonus_half_mc"] == 150
    assert len(right["shield_generator_candidates_at_vcr_xy"]) == 1
    assert row["sides"][0]["shield_generator_candidates_at_vcr_xy"] == []
    assert row["sampled_relevant_settings"][0]["selected_game_settings"] == {
        "combatrng":0,"engineshieldbonus":0
    }
    assert payload["right"]["mass"] == 470


def test_missing_catalog_hull_fails_closed() -> None:
    payload = _payload()
    payload["right"]["hullid"] = 999
    with pytest.raises(ValueError, match="hull catalog missing"):
        M.triage_case(
            game_id=217591,turn=149,vcr_id=2390,
            payload=payload,specs=_specs(),archived_members=[],
        )


def test_t1_t_context_stays_observational() -> None:
    row = M.triage_case(
        game_id=217591,turn=149,vcr_id=2390,
        payload=_payload(),specs=_specs(),archived_members=[],
    )
    assert all("candidate" in x["provenance"] or "raw_snapshot" in x["provenance"]
               for side in row["sides"]
               for x in side["shield_generator_candidates_at_vcr_xy"])
    assert all(
        side["factual_mass"] is not None
        for side in row["sides"]
    )


def test_runner_has_sha_pinned_relative_explicit_generation() -> None:
    runner = ROOT/"tools"/"run-combat-mass-residual-triage-v1.sh"
    wrapper = ROOT/"tools"/"run-combat-mass-residual-triage-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    text = runner.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in text
    assert '--corpus-db-generation "$DB"' not in text
    assert 'SHA_EXPECTED="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in text
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
