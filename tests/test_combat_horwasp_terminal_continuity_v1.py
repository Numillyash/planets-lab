from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_horwasp_terminal_continuity_v1.py"
SPEC=importlib.util.spec_from_file_location("horwasp_terminal_continuity",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def case(vid, *, lhs=27, rhs=82, ldmg=0, rdmg=0, lmass=950, rmass=180,
         left_owner=30, right_owner=4, left_race=12, right_race=4):
    def ship(sid,hull,race,damage,mass):
        return {
            "objectid":sid,"hullid":hull,"raceid":race,
            "shield":100,"damage":damage,"crew":100,"torpedos":5,
            "fighters":10,"mass":mass,
        }
    return SimpleNamespace(
        payload={
            "id":vid,"turn":153,"seed":1,"leftownerid":left_owner,
            "rightownerid":right_owner,
            "left":ship(lhs,115,left_race,ldmg,lmass),
            "right":ship(rhs,35,right_race,rdmg,rmass),
        },
        beams=(),torpedoes=(),settings={"combatrng":0},
    )


def frozen_pair(ids=(1778,1779),masses=(950,893)):
    return {(350094,153,30,513):[
        {"vcr_id":i,"side":"left","observed_VCR_mass_KT":mass}
        for i,mass in zip(ids,masses)
    ]}


def test_only_metadata_selects_ship_chains_with_owner_and_race_continuity():
    cases={
        (153,1778):case(1778,lhs=513,rhs=95,lmass=950),
        (153,1779):case(1779,lhs=513,rhs=95,lmass=893),
        (153,1780):case(1780,lhs=513,rhs=96,lmass=725),
    }
    groups=M.ship_chain_groups(cases,game=350094,turn=153)
    assert [(x["vcr_id"],x["side"]) for x in groups[(350094,153,30,513)]] == [
        (1778,"left"),(1779,"left"),(1780,"left")
    ]
    assert [(x["vcr_id"],x["side"]) for x in groups[(350094,153,4,95)]] == [
        (1778,"right"),(1779,"right")
    ]
    assert (350094,153,4,96) not in groups
    # Masses cannot change identity/selection.
    cases[(153,1779)].payload["left"]["mass"]=9999
    assert M.ship_chain_groups(cases,game=350094,turn=153)==groups


def replay_result(payload,**kwargs):
    left=payload["left"];right=payload["right"]
    def end(row):
        return {
            "object_id":row["objectid"],"destroyed":False,"captured":False,
            "shield":row["shield"],"damage":row["damage"]+5,
            "crew":row["crew"],"torpedoes":row["torpedos"],
            "fighters":row["fighters"],
        }
    return {"engine":"nuhost_classic_119","basis":"deterministic_vcr_replay",
            "left":end(left),"right":end(right)}


def test_prior_replay_matches_next_start_without_next_mass_oracle():
    prev=case(1778,lhs=513,rhs=95,ldmg=0,lmass=950)
    nxt=case(1779,lhs=513,rhs=95,ldmg=5,lmass=893,rdmg=5)
    calls=[]
    def engine(payload,**kw):
        calls.append(payload["id"])
        return replay_result(payload,**kw)
    out=M.audit_window(
        {(153,1778):prev,(153,1779):nxt},game=350094,turn=153,
        frozen=frozen_pair(),replay_resolver=engine,
    )
    assert calls==[1778]  # replay once even with Horwasp and ordinary control
    assert out["frozen_horwasp_chains"]==1
    assert out["all_same_turn_identity_chains"]==2
    target=[x for x in out["transitions"] if x["cohort"]=="FROZEN_HORWASP_REPEAT"]
    other=[x for x in out["transitions"] if x["cohort"]=="SAME_GAME_TURN_CONTROL"]
    assert len(target)==len(other)==1
    assert target[0]["terminal_next_continuity"]["status"] == (
        "EXACT_CLASSIC_REPLAY_TERMINAL_TO_NEXT_START"
    )
    assert target[0]["observed_VCR_mass_delta_NEXT_minus_PRIOR_KT"]==-57
    assert target[0]["terminal_clans_reconstructed"] is False
    assert other[0]["terminal_next_continuity"]["status"] == (
        "EXACT_CLASSIC_REPLAY_TERMINAL_TO_NEXT_START"
    )


def test_mismatch_and_negative_control_not_repaired_by_mass():
    prev=case(1778,lhs=513,rhs=95,ldmg=0,lmass=950)
    nxt=case(1779,lhs=513,rhs=95,ldmg=14,lmass=893,rdmg=5)
    o=M.audit_window({(153,1778):prev,(153,1779):nxt},
                     game=350094,turn=153,frozen=frozen_pair(),
                     replay_resolver=replay_result)
    target=next(x for x in o["transitions"] if x["cohort"]=="FROZEN_HORWASP_REPEAT")
    assert target["terminal_next_continuity"]["status"]==(
        "CLASSIC_REPLAY_TERMINAL_TO_NEXT_START_MISMATCH"
    )
    assert target["terminal_next_continuity"]["fields"]["damage"]=={
        "previous_replay_terminal":5,"next_factual_start":14,"equal":False
    }


def test_destroyed_or_captured_reappearance_is_flagged_not_silent():
    prev=case(1778,lhs=513)
    nxt=case(1779,lhs=513,ldmg=5,lmass=893)
    def defeated(payload,**kw):
        r=replay_result(payload,**kw);r["left"]["captured"]=True;return r
    result=M.audit_window(
        {(153,1778):prev,(153,1779):nxt},
        game=350094,turn=153,frozen=frozen_pair(),replay_resolver=defeated,
    )
    row=next(x for x in result["transitions"] if x["cohort"]=="FROZEN_HORWASP_REPEAT")
    assert row["terminal_next_continuity"]["status"]=="REAPPEARANCE_AFTER_REPLAY_DEFEAT"


def test_unsupported_classic_rng_explicit_abstention_no_fabricated_continuity():
    prev=case(1778,lhs=513)
    nxt=case(1779,lhs=513,ldmg=5,lmass=893)
    def impossible(payload,**kw):
        raise M.ReplayUnsupported("RNG not Classic")
    o=M.audit_window(
        {(153,1778):prev,(153,1779):nxt},
        game=350094,turn=153,frozen=frozen_pair(),
        replay_resolver=impossible,
    )
    assert all(
        x["terminal_next_continuity"]["status"]=="ABSTAIN_CLASSIC_REPLAY_UNAVAILABLE"
        for x in o["transitions"]
    )


def test_fail_closed_frozen_mass_and_owner_race_drift():
    p=case(1778,lhs=513,lmass=950)
    n=case(1779,lhs=513,lmass=893,left_owner=21)
    with pytest.raises(ValueError,match="frozen Horwasp chain missing"):
        M.audit_window(
            {(153,1778):p,(153,1779):n},game=350094,turn=153,
            frozen=frozen_pair(),replay_resolver=replay_result,
        )
    n.payload["leftownerid"]=30
    n.payload["left"]["mass"]=894
    with pytest.raises(ValueError,match="frozen Horwasp current-VCR mass mismatch"):
        M.audit_window(
            {(153,1778):p,(153,1779):n},game=350094,turn=153,
            frozen=frozen_pair(),replay_resolver=replay_result,
        )


def test_frozen_source_requires_chain_integrity():
    keys=[(350094,153,30,34),(350094,153,30,513),
          (371631,41,3,19),(449095,134,1,1022)]
    ids=[[1776,1777],[1778,1779,1780],[314,315],[1700,1701]]
    masses=[[370,336],[950,893,725],[290,290],[150,146]]
    chains=[]
    rows=[]
    for key,seq,vals in zip(keys,ids,masses):
        entries=[]
        for i,m in zip(seq,vals):
            entries.append({"vcr_id":i,"side":"left",
                            "observed_VCR_mass_KT":m})
            rows.append({"game_id":key[0],"turn":key[1],
                         "owner_id":key[2],"ship_id":key[3],
                         "vcr_id":i,"side":"left",
                         "evaluation":{"observed_vcr_mass_KT":m}})
        chains.append(dict(zip(("game_id","turn","owner_id","ship_id"),key)) | {
            "VCRs_by_id_NOT_proven_execution_sequence":entries
        })
    rows+= [
        {"game_id":700+i,"turn":20,"owner_id":4,"ship_id":i+1,
         "vcr_id":i+1,"side":"right",
         "evaluation":{"observed_vcr_mass_KT":10}}
        for i in range(17)
    ]
    assert len(rows)==26
    payload={
        "schema":M.SOURCE_SCHEMA,"status":M.SOURCE_STATUS,
        "population":{"original_horwasp_sides":26,
                      "distinct_horwasp_ships_by_game_turn_owner":21},
        "summary_repeated_by_VCR_ID":{"sides":5},
        "repeated_ship_VCR_ID_chains":chains,
        "frozen_horwasp_side_evaluations":rows,
    }
    assert len(M.frozen_horwasp_chains(payload))==4
    payload["repeated_ship_VCR_ID_chains"][0][
        "VCRs_by_id_NOT_proven_execution_sequence"][1][
        "observed_VCR_mass_KT"]=999
    with pytest.raises(ValueError,match="detail/chain evidence mismatch"):
        M.frozen_horwasp_chains(payload)


def test_runner_evidence_and_pins():
    raw=b"verifiable source"
    assert M.blob_sha1(raw)==hashlib.sha1(
        b"blob "+str(len(raw)).encode()+b"\0"+raw
    ).hexdigest()
    runner=ROOT/"tools/run-combat-horwasp-terminal-continuity-v1.sh"
    wrapper=ROOT/"tools/run-combat-horwasp-terminal-continuity-v1-with-evidence.sh"
    for p in (runner,wrapper):
        subprocess.run(["bash","-n",str(p)],check=True)
    assert M.SOURCE_BLOB in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "CURRENT" not in runner.read_text()
