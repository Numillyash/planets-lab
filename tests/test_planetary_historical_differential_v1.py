from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/planetary_historical_differential_v1.py"
SPEC=importlib.util.spec_from_file_location("planetary_historical_diff_v1",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def planet(*,turn=4,owner=1,infoturn=None):
    return {
        "id":1,"ownerid":owner,"infoturn":turn if infoturn is None else infoturn,
        "x":100,"y":200,"temp":50,
        "clans":100,"supplies":10,"megacredits":1,
        "factories":20,"mines":5,"defense":0,
        "colonisthappypoints":90,"colonisttaxrate":0,
        "nativeclans":0,
        "neutronium":0,"duranium":0,"tritanium":0,"molybdenum":0,
        "groundneutronium":500,"groundduranium":500,
        "groundtritanium":500,"groundmolybdenum":500,
        "densityneutronium":20,"densityduranium":30,
        "densitytritanium":40,"densitymolybdenum":50,
    }


def snapshot(raw,*,turn=4,player_id=1,race=1):
    return SimpleNamespace(
        player_id=player_id,archive_turn=turn,embedded_turn=turn,
        mechanics_payload={
            "player":{"id":player_id,"raceid":race},
            "planets":[raw],
            "ships":[],"starbases":[],
        })


def test_archive_window_selection_metadata_only_and_disjoint():
    selected=tuple(range(201,209))
    rows=[(game,turn) for game in selected for turn in range(1,60)]
    windows=M.choose_metadata_windows(rows,selected)
    assert len(windows)==32
    assert len(set(windows))==32
    assert {g for g,t in windows}==set(selected)
    assert all(t>=2 for g,t in windows)
    with pytest.raises(ValueError,match="missing source metadata"):
        M.choose_metadata_windows(rows[:-59],selected)
    with pytest.raises(ValueError,match="insufficient adjacent"):
        M.choose_metadata_windows([(g,t) for g in selected for t in (1,3)],selected)


def test_owner_perspective_and_infostaleness_fail_closed():
    current=planet(turn=4)
    rows,counts=M.raw_owner_current_planets(
        [snapshot(current,turn=4)],4)
    assert rows[1][0]==1
    assert counts=={}
    stale=dict(current,infoturn=3)
    rows,counts=M.raw_owner_current_planets([snapshot(stale,turn=4)],4)
    assert rows=={} and counts["ABSTAIN_PLANET_STALE"]==1
    different=snapshot(current,turn=4,player_id=2)
    rows,counts=M.raw_owner_current_planets([different],4)
    assert rows=={} and counts["ABSTAIN_NO_UNIQUE_OWNER_CURRENT"]==1
    conflicting=dict(current,ownerid=2)
    rows,counts=M.raw_owner_current_planets(
        [snapshot(current,turn=4),snapshot(conflicting,turn=4,player_id=2)],4)
    assert rows=={} and counts["ABSTAIN_OWNER_UNKNOWN_OR_CONFLICT"]==1


def test_independent_canonical_phases_infer_conditional_frozen_predictions(monkeypatch):
    s=snapshot(planet())
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *a,**kw: ((s,),()))
    pre=M.pre_window(None,game=301,turn=5)
    assert len(pre["Tminus1_planets"])==1
    row=pre["Tminus1_planets"][0]
    assert row["Tminus1_status"]=="MODEL_CONDITIONAL"
    assert row["Tminus1_input_selected_without_T_observation"]
    assert row["expected"]["supplies"]["supplies"]==30
    assert row["before"]["taxes"]["megacredits"]==1
    assert row["expected"]["minerals"]["groundneutronium"]>=0
    assert row["source_missing"]["supplies"]==[]
    assert row["source_missing"]["taxes"]==[]
    assert row["source_missing"]["minerals"]==[]
    assert row["source_missing"]["populations"]==[]


def test_exact_comparison_and_mismatch_stay_conditional(monkeypatch):
    s=snapshot(planet())
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *a,**kw: ((s,),()))
    pre=M.pre_window(None,game=301,turn=5)
    frozen=pre["Tminus1_planets"][0]
    source=planet(turn=5)
    for fields in frozen["expected"].values():
        for k,v in fields.items():
            source[k]=v
    result=M.compare(pre,{1:(1,source)})
    assert all(result[k][0]["status"]=="CONDITIONAL_EXACT_ALL_FIELDS" for k in M.FAMILIES)
    assert all(result[k][0]["Tminus1_to_T_phase_attribution_proven"] is False
               for k in M.FAMILIES)
    source["supplies"]+=1
    changed=M.compare(pre,{1:(1,source)})
    assert changed["supplies"][0]["status"]=="CONDITIONAL_MISMATCH_UNATTRIBUTED"
    assert changed["taxes"][0]["status"]=="CONDITIONAL_EXACT_ALL_FIELDS"
    assert M.compare(pre,{1:(2,source)})["supplies"][0]["status"]=="ABSTAIN_OWNER_CHANGED"
    assert M.compare(pre,{})["taxes"][0]["status"]=="ABSTAIN_T_OWNER_CURRENT_MISSING"
    del source["supplies"]
    assert M.compare(pre,{1:(1,source)})["supplies"][0]["status"]=="ABSTAIN_T_REQUIRED_FIELDS_MISSING"


def test_missing_raw_fields_never_default_to_verified_prediction(monkeypatch):
    bad=planet()
    del bad["factories"]
    s=snapshot(bad)
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *a,**kw: ((s,),()))
    pre=M.pre_window(None,game=301,turn=5)
    compared=M.compare(pre,{1:(1,planet(turn=5))})
    assert compared["supplies"][0]["status"]=="ABSTAIN_TMINUS1_REQUIRED_FIELDS_MISSING"
    assert "factories" in compared["supplies"][0]["missing_fields"]


def test_whole_32_window_source_freeze_before_first_T(monkeypatch):
    windows=tuple((g,t) for g in range(1,9) for t in (20,40,60,80))
    events=[]
    def source(_conn,g,t):
        events.append(("PRE",g,t))
        return {"Tminus1_planets":[
            {"game_id":g,"turn":t,"planet_id":1,"owner_id":1,"race_id":None,
             "Tminus1_status":"ABSTAIN_RACE_UNAVAILABLE",
             "expected":{},"before":{},"source_missing":{}}]}
    def post(_conn,g,t):
        assert sum(x[0]=="PRE" for x in events)==len(windows)
        events.append(("POST",g,t))
        return {}
    monkeypatch.setattr(M,"pre_window",source)
    monkeypatch.setattr(M,"post_window",post)
    pre,comparisons=M.run_windows(None,windows)
    assert len(pre)==32
    assert events[:32]==[("PRE",g,t) for g,t in windows]
    assert events[32:]==[("POST",g,t) for g,t in windows]
    assert all(len(comparisons[k])==32 for k in M.FAMILIES)
    items=M.reports(tuple(range(1,9)),windows,pre,comparisons)
    assert all(items[k]["summary"]["abstention_count"]==32 for k in M.FAMILIES)


def test_no_fabricated_causal_matches_and_sha256_manifest(tmp_path):
    windows=((1,20),)
    fake={k:[{"game_id":1,"turn":20,"planet_id":1,"status":"CONDITIONAL_MISMATCH_UNATTRIBUTED"}]
          for k in M.FAMILIES}
    r=M.reports((1,),windows,{},fake)
    for family in M.FAMILIES:
        assert r[family]["summary"]["conditionally_all_field_mismatch"]==1
        assert r[family]["summary"]["NuHost_component_formulas_verified_causally"] is False
        assert r[family]["new_C5_rule_or_combat_executor_changes"]==0
    M.publish(tmp_path,r)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["all_four_complete"]
    assert manifest["causal_NuHost_parity_claimed"] is False
    assert manifest["C5_frozen_not_reopened"]
    for family in M.FAMILIES:
        assert manifest["reports"][family]["sha256"]==hashlib.sha256(
            (tmp_path/(family+".json")).read_bytes()).hexdigest()


def test_single_evidence_command_sha_pin_and_bash_lint():
    runner=ROOT/"tools/run-planetary-historical-differential-v1.sh"
    wrapper=ROOT/"tools/run-planetary-historical-differential-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    body=runner.read_text()
    assert M.GENERATION in body
    assert M.V25_MANIFEST_BLOB in body
    assert "planetary_historical_differential_v1.py" in body
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/planetary/historical-differential-v1/published" in wrapper.read_text()
    assert "/CURRENT" not in body and "run-combat" not in body
