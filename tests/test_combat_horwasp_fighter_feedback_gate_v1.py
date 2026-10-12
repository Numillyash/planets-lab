from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"tools/diagnostics/combat_horwasp_fighter_feedback_gate_v1.py"
SPEC=importlib.util.spec_from_file_location("horwasp_fighter_gate_v1",FILE)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def candidate(**changes):
    args=dict(clans=900,capacity=900,hull_mass=145,hull_id=117,
              start_fighters=70,terminal_fighters=57,
              terminal_damage=0,start_damage=0,
              terminal_destroyed=False,terminal_captured=False,
              feedback_enabled=False)
    args.update(changes)
    return M.branch_step(**args)


def test_fixed_feedback_on_off_falsifiable_negative_control():
    off=candidate()
    on=candidate(feedback_enabled=True)
    assert off["projected_clans"]==900
    assert off["projected_mass_KT"]==290
    assert off["projected_fighters"]==70
    assert on["feedback_clans_lost_hypothesis"]==26
    assert on["projected_clans"]==874
    assert on["projected_mass_KT"]==285
    # G371631 T41 (V314->315) really has mass 290, fighters 70.
    comparison=M.evaluate_only_after(
        {"OFF":off,"ON":on},actual_mass=290,actual_fighters=70)
    assert comparison["OFF"]["mass_exact"] is True
    assert comparison["ON"]["mass_exact"] is False
    assert comparison["OFF"]["fighters_exact"] is True
    assert comparison["ON"]["fighters_exact"] is False


def test_both_branches_keep_classic_damage_assumption_no_ad_hoc_fit():
    off=candidate(clans=24000,capacity=24000,hull_mass=475,hull_id=115,
                  start_fighters=70,terminal_fighters=24,terminal_damage=21)
    on=candidate(clans=24000,capacity=24000,hull_mass=475,hull_id=115,
                 start_fighters=70,terminal_fighters=24,terminal_damage=21,
                 feedback_enabled=True)
    assert off["damage_clans_lost_floor_assumption"]==5040
    assert off["feedback_clans_lost_hypothesis"]==0
    assert on["feedback_clans_lost_hypothesis"]==920
    assert off["projected_mass_KT"]==850
    assert on["projected_mass_KT"]==832
    assert 893-off["projected_mass_KT"]==43
    assert 893-on["projected_mass_KT"]==61


def test_branch_selection_does_not_depend_on_observed_comparator():
    off=candidate()
    on=candidate(feedback_enabled=True)
    c={"OFF":off,"ON":on}
    assert M.evaluate_only_after(c,actual_mass=290,actual_fighters=70)!=(M.evaluate_only_after(
        c,actual_mass=220,actual_fighters=50))
    assert c["OFF"]["projected_clans"]==900
    assert c["ON"]["projected_clans"]==874
    assert "actual_mass" not in M.branch_step.__code__.co_varnames
    assert "actual_fighters" not in M.branch_step.__code__.co_varnames


@pytest.mark.parametrize("kwargs,status",[
    ({"clans":None},"ABSTAIN_MISSING_PRECOMBAT_OR_CLASSIC_FIELDS"),
    ({"start_damage":12},"ABSTAIN_INVALID_MODEL_PRESTATE"),
    ({"terminal_fighters":71},"ABSTAIN_INVALID_MODEL_PRESTATE"),
    ({"terminal_captured":True},"ABSTAIN_CLASSIC_TERMINAL_DEFEAT"),
    ({"clans":10,"terminal_damage":60},"ABSTAIN_INSUFFICIENT_CLANS_FULL_REPAIR"),
])
def test_no_unsafe_fallback_for_invalid_prestate(kwargs,status):
    x=candidate(**kwargs)
    assert x["status"]==status
    assert x["projected_clans"] is None


def historical(field=None,value=None,*,year=2020,owner=4):
    ref=SimpleNamespace(game_id=350094,archive_turn=152,embedded_turn=152,
                        member_id=100+owner,perspective_player_id=owner)
    game={"id":350094,"turn":152}
    if field is not None:game[field]=value
    return ref,{"game":game}


def test_documented_2021_cutoff_requires_direct_creation_field():
    before=M.game_creation_provenance(
        [historical("datecreated","2020-12-31T19:00:00Z"),
         historical("datecreated","2020-12-31",owner=5)],
        game=350094,turn=153)
    assert before["status"]=="ARCHIVED_GAME_CREATION_DATE_CANDIDATE"
    assert before["rule_applies_since_2021"] is False
    after=M.game_creation_provenance(
        [historical("datecreated","2021-01-01")],
        game=350094,turn=153)
    assert after["rule_applies_since_2021"] is True
    # Turn year, game ID, Nu year, and ambiguous 'created' must NOT be
    # silently treated as authoritative generation-date evidence.
    missing=M.game_creation_provenance(
        [historical("yearfrom","2022")],game=350094,turn=153)
    assert missing["rule_applies_since_2021"] is None
    ambiguous=M.game_creation_provenance(
        [historical("created","2021-01-01")],game=350094,turn=153)
    assert ambiguous["rule_applies_since_2021"] is None


def test_conflicting_or_partially_missing_dates_fail_closed():
    conflicting=M.game_creation_provenance(
        [historical("datecreated","2020-12-31"),
         historical("datecreated","2021-01-01",owner=5)],
        game=350094,turn=153)
    assert conflicting["status"]=="ABSTAIN_GAME_CREATED_DATE_CONFLICT"
    assert conflicting["rule_applies_since_2021"] is None
    missing=M.game_creation_provenance(
        [historical("datecreated","2021-01-01"),historical(owner=5)],
        game=350094,turn=153)
    assert missing["status"]=="ABSTAIN_GAME_CREATED_DATE_NOT_AUTHENTICATED"
    invalid=M.game_creation_provenance(
        [(SimpleNamespace(game_id=350094,archive_turn=153,embedded_turn=153,
                          member_id=99,perspective_player_id=4),
          {"game":{"id":350094,"turn":153,"datecreated":"2021-01-01"}})],
        game=350094,turn=153)
    assert invalid["status"]=="ABSTAIN_TMINUS1_PROVENANCE_INVALID"


def test_runner_evidence_wrapper_and_static_syntax():
    for name in ("tools/run-combat-horwasp-fighter-feedback-gate-v1.sh",
                 "tools/run-combat-horwasp-fighter-feedback-gate-v1-with-evidence.sh"):
        path=ROOT/name
        subprocess.run(["bash","-n",str(path)],check=True)
    runner=(ROOT/"tools/run-combat-horwasp-fighter-feedback-gate-v1.sh").read_text()
    wrapper=(ROOT/"tools/run-combat-horwasp-fighter-feedback-gate-v1-with-evidence.sh").read_text()
    assert M.SOURCE_BLOB in runner
    assert "CURRENT" not in runner
    assert "run-with-runtime-evidence.sh" in wrapper
