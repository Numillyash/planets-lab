from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
DIAG=ROOT/"tools"/"diagnostics"
SPEC=importlib.util.spec_from_file_location(
    "combat_mass_capture_phase_controls_v1",
    DIAG/"combat_mass_capture_phase_controls_v1.py",
)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _case(vcr_id,owner,hull,mass,side,crew):
    participant={"objectid":27,"hullid":hull,"raceid":owner,
                 "mass":mass,"crew":crew,"damage":0,"shield":100}
    other={"objectid":253 if vcr_id==1016 else 167,
           "hullid":35 if vcr_id==1016 else 52,"mass":451}
    body={"x":1455,"y":2615,
          side:participant,
          "left" if side=="right" else "right":other,
          side+"ownerid":owner,
          ("left" if side=="right" else "right")+"ownerid":4 if owner==5 else 5,
          "id":vcr_id,"turn":201}
    return SimpleNamespace(
        vcr_id=vcr_id,payload=body,observation_count=3,
        source_members=(f"player1-turn201.trn",),
    )


def test_capture_vcr_start_order_independent_of_terminal_outcomes(monkeypatch):
    cases={
        (201,1016):_case(1016,5,94,645,"right",150),
        (201,1017):_case(1017,4,94,795,"left",10),
    }
    monkeypatch.setattr(M,"combat_vcr_cases_for_turns",
                        lambda conn,game_id,battle_turns:cases)
    report=M.rush_combat_observations(object())
    assert report["transition"]["owner_change"]==[5,4]
    assert report["transition"]["mass_delta"]==150
    assert report["transition"]["consistent_with_documented_combat_capture"]
    assert not report["transition"]["independent_capture_outcome_proven"]
    assert report["VCRs"][1]["rush_start_state"]["crew"]==10
    assert report["VCRs"][1]["independent_source_perspectives"]==3


def test_capture_frozen_vcr_identity_must_match(monkeypatch):
    cases={(201,1016):_case(1016,5,94,645,"right",150),
           (201,1017):_case(1017,5,94,795,"left",10)}
    monkeypatch.setattr(M,"combat_vcr_cases_for_turns",
                        lambda conn,game_id,battle_turns:cases)
    with pytest.raises(ValueError,match="identity mismatch"):
        M.rush_combat_observations(object())


def test_static_mass_diff_vs_first_source_without_oracle_vcr(monkeypatch):
    refs=[
        SimpleNamespace(perspective_player_id=4,member_id=104,
                        decoded_payload_sha256="a"*64),
        SimpleNamespace(perspective_player_id=5,member_id=105,
                        decoded_payload_sha256="b"*64),
    ]
    monkeypatch.setattr(M,"first_last_member_refs",lambda conn,game_id:(
        SimpleNamespace(member_id=1,archive_turn=0),None
    ))
    monkeypatch.setattr(M,"reconstruct_compact_member",lambda conn,id:{
        "hulls":[{"id":1039,"mass":96},{"id":39,"mass":96}]
    })
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**k:refs)
    monkeypatch.setattr(M,"reconstruct_members",lambda conn,sel:(
        (r,{"hulls":[{"id":1039,"mass":46},{"id":39,"mass":96}]})
        for r in sel
    ))
    report=M.static_control(conn=object(),game=217591,turn=75)
    assert report["status"]=="SAME_CHANGE_SET_ACROSS_AVAILABLE_TMINUS1_PERSPECTIVES"
    assert report["first_member_D19c_mass"]==96
    assert report["Tminus1_D19c_values"]==[46]
    assert report["max_mass_changed_hulls"]==1
    assert len(report["per_perspective"])==2


def test_static_raises_on_conflicting_duplicate_rows():
    with pytest.raises(ValueError,match="duplicate hull"):
        M._hull_mass_map({
            "hulls":[{"id":1039,"mass":96},{"id":1039,"mass":46}]
        })


def test_saber_at_site_requires_own_owner_and_is_not_activity_proof():
    hulls={
        1041:SimpleNamespace(name="Saber Shield Generator",special="Shield Generator"),
        35:SimpleNamespace(name="Victorious",special=""),
    }
    member={"ships":[
        {"id":27,"ownerid":5,"hullid":94,"x":1455,"y":2615},
        {"id":406,"ownerid":4,"hullid":1041,"x":1455,"y":2615,
         "targetx":1455,"targety":2615},
        {"id":607,"ownerid":5,"hullid":1041,"x":1455,"y":2615,
         "targetx":1455,"targety":2615},
    ]}
    result=M._generator_ids(member,4,M.SITE,hulls)
    assert [x["ship_id"] for x in result]==[406]
    assert result[0]["site_exact_at_archive"] is True


def test_static_priorities_keep_both_D19c_anchors():
    digest={"schema":M.DIGEST_SCHEMA,
            "ranked_turns":[{"game_id":1000+i,"turn":10+i} for i in range(16)]}
    chosen=M.select_static_turns({},digest)
    assert chosen[:2]==[(217591,75),(325434,149)]
    assert len(chosen)==14


def test_runner_sha_pin_and_evidence_path():
    a=ROOT/"tools"/"run-combat-mass-capture-phase-controls-v1.sh"
    b=ROOT/"tools"/"run-combat-mass-capture-phase-controls-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(a)],check=True)
    subprocess.run(["bash","-n",str(b)],check=True)
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in a.read_text()
    assert '--corpus-db-generation "$GENERATION"' in a.read_text()
    assert "run-with-runtime-evidence.sh" in b.read_text()
    assert "--include artifacts/combat/mass-capture-phase-controls-v1/published" in b.read_text()
