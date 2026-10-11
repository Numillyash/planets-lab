from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"tools/diagnostics/combat_horwasp_postcombat_clan_projection_v1.py"
SPEC=importlib.util.spec_from_file_location("postcombat_horwasp_v1",SRC)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def prediction(*,clans=24000,cap=24000,hull=115,start=70,
               terminal=50,damage=10,start_damage=0,dead=False):
    return M.documented_damage_and_fighter_loss_candidate(
        previous_clans=clans,capacity=cap,hull_id=hull,
        current_vcr_start_fighters=start,
        classic_replay_terminal_fighters=terminal,
        classic_replay_terminal_damage=damage,
        classic_replay_destroyed=dead,classic_replay_captured=False,
        previous_vcr_start_damage=start_damage,
    )


def test_documented_hive_feedback_and_damage_rule_are_independent_components():
    x=prediction()
    assert x["status"]=="CONDITIONAL_DOCUMENTED_POSTCOMBAT_CLAN_PROJECTION"
    assert x["detail"]["lost_fighters_from_Classic_replay"]==20
    assert x["detail"]["hypothetical_fighter_clans_killed"]==400
    assert x["detail"]["hypothetical_damage_clans_killed"]==2400
    assert x["projected_clans"]==21200
    assert x["full_combat_mass_prediction"] is False
    y=M.next_mass_and_fighters(x,hull_mass=475,hull_id=115,capacity=24000)
    assert y["projected_next_mass_KT"]==475+475*21200//24000
    assert y["projected_next_fighters"]==10+60*21200//24000


def test_soldier_and_brood_feedback_is_two_clans_per_fighter():
    for hull,capacity,mass in [(119,300,185),(117,900,145)]:
        x=prediction(clans=capacity,cap=capacity,hull=hull,
                     start=40,terminal=37,damage=5)
        assert x["detail"]["hypothetical_fighter_clans_killed"]==6
        assert x["detail"]["hypothetical_damage_clans_killed"]==capacity*5//100
        y=M.next_mass_and_fighters(x,hull_mass=mass,
                                   hull_id=hull,capacity=capacity)
        assert y["projected_next_mass_KT"]==(
            mass+mass*y["projected_clans"]//capacity
        )


@pytest.mark.parametrize("kwargs,status",[
    ({"clans":None},"ABSTAIN_INVALID_PRESTATE"),
    ({"clans":24001},"ABSTAIN_INVALID_PRESTATE"),
    ({"terminal":None},"ABSTAIN_UNSUPPORTED_CLASSIC_FIELDS"),
    ({"terminal":71},"ABSTAIN_NONBASELINE_VCR_DAMAGE_OR_FIGHTER_COUNTS"),
    ({"damage":101},"ABSTAIN_NONBASELINE_VCR_DAMAGE_OR_FIGHTER_COUNTS"),
    ({"start_damage":10},"ABSTAIN_NONBASELINE_VCR_DAMAGE_OR_FIGHTER_COUNTS"),
    ({"dead":True},"ABSTAIN_CLASSIC_REPLAY_TERMINAL_DEFEAT"),
    ({"clans":12,"terminal":20,"damage":90},"ABSTAIN_INSUFFICIENT_CLANS_FOR_FULL_REPAIR"),
])
def test_incomplete_nonbaseline_and_clan_exhaustion_abstain(kwargs,status):
    x=prediction(**kwargs)
    assert x["status"]==status
    assert x["projected_clans"] is None
    assert x["projected_next_mass_KT"] is None


def test_clan_loss_is_oneway_and_current_vcr_mass_cannot_tune_it():
    x=prediction(clans=24000,terminal=24,damage=21,start=70)
    expected=24000-(70-24)*20-24000*21//100
    assert x["projected_clans"]==expected
    # No observed next mass, next fighters, or inverted clans in signature.
    assert "next_vcr_mass" not in M.documented_damage_and_fighter_loss_candidate.__code__.co_varnames
    a=M.next_mass_and_fighters(x,hull_mass=475,hull_id=115,capacity=24000)
    assert a["projected_next_mass_KT"]==475+475*expected//24000
    assert a["projected_next_fighters"]==10+60*expected//24000


def test_unknown_fighter_formula_stays_null_while_mass_stays_evaluable():
    x=prediction(clans=300,cap=300,hull=210,start=0,terminal=0,damage=5)
    y=M.next_mass_and_fighters(x,hull_mass=75,hull_id=210,capacity=300)
    assert y["projected_next_mass_KT"]==75+75*285//300
    assert y["projected_next_fighters"] is None


def test_frozen_terminal_reset_signature_is_descriptive_not_forecast():
    row={"terminal_next_continuity":{"fields":{
        "shield":{"previous_replay_terminal":0,"next_factual_start":0},
        "damage":{"previous_replay_terminal":21,"next_factual_start":0},
        "crew":{"previous_replay_terminal":1,"next_factual_start":1},
        "torpedoes":{"previous_replay_terminal":9988,"next_factual_start":10000},
        "fighters":{"previous_replay_terminal":24,"next_factual_start":62},
    }}}
    out=M.field_reset_signature(row)
    assert out["damage"]["next_reset_zero"]
    assert out["torpedoes"]["next_reset_10000"]
    assert out["fighters"]["increased_from_classic_terminal"]
    assert not out["crew"]["increased_from_classic_terminal"]
    row["terminal_next_continuity"]["fields"].pop("crew")
    with pytest.raises(ValueError,match="five-field"):
        M.field_reset_signature(row)


def test_frozen_source_bytes_pinned_and_bash_scripts_exist():
    raw=b"published frozen evidence"
    assert M.continuity.blob_sha1(raw)==hashlib.sha1(
        b"blob "+str(len(raw)).encode()+b"\0"+raw
    ).hexdigest()
    assert M.TERMINAL_V1_BLOB!="?" and M.HORWASP_V1_BLOB!="?"
    for file in [
        ROOT/"tools/run-combat-horwasp-postcombat-clan-projection-v1.sh",
        ROOT/"tools/run-combat-horwasp-postcombat-clan-projection-v1-with-evidence.sh",
    ]:
        subprocess.run(["bash","-n",str(file)],check=True)
    runner=(ROOT/"tools/run-combat-horwasp-postcombat-clan-projection-v1.sh").read_text()
    wrapper=(ROOT/"tools/run-combat-horwasp-postcombat-clan-projection-v1-with-evidence.sh").read_text()
    assert "CURRENT" not in runner
    assert M.TERMINAL_V1_BLOB in runner
    assert M.HORWASP_V1_BLOB in runner
    assert "run-with-runtime-evidence.sh" in wrapper
