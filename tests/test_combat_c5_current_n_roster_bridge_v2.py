from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"tools/diagnostics/combat_c5_current_n_roster_bridge_v2.py"
SPEC=importlib.util.spec_from_file_location("c5_n_roster_bridge_v2",SRC)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def side(ship=12,*,hull=35,race=3):
    return {
        "objectid":ship,"hullid":hull,"raceid":race,
        "shield":100,"damage":0,"crew":200,
        "torpedos":5,"fighters":0,"beamcount":4,
        "launchercount":2,"baycount":0,
    }


def current(*,sid1=12,sid2=23):
    return SimpleNamespace(
        payload={"leftownerid":4,"rightownerid":8,
                 "left":side(sid1),"right":side(sid2,hull=17,race=7)},
        beams=(),torpedoes=(),settings={})


def prediction(ship=12,*,owner=4,hull=35,race=3,pos=(50,60)):
    return {"owner_id":owner,"hull_id":hull,"race_id":race,
            "position":pos,
            "raw":{"id":ship,"ownerid":owner,"hullid":hull,
                   "mission":0,"enemy":8}}


def test_only_missing_N_ship_anchored_by_matching_Tminus1_identity():
    ctx={"x":10,"y":20,"predictions":{12:prediction(),
                                     23:prediction(23,owner=8,hull=17,race=7)}}
    prior=M.SiteCombatState(active_ships={})
    updated, bridges=M.prepare_current_state(
        state=prior,current_case=current(),context=ctx,history=[])
    assert set(updated.active_ships)=={12,23}
    assert len(bridges)==2
    assert updated.active_ships[12]["torpedoes"]==5
    assert updated.active_ships[12]["owner_id"]==4
    assert updated.active_ships[23]["hull_id"]==17
    assert not bridges[0]["Tminus1_predicted_at_current_N_site"]
    assert not bridges[0]["dynamic_state_independently_predicted"]
    assert bridges[0]["Nplus1_fields_used"] is False
    assert prior.active_ships=={}


def test_previously_fought_missing_ship_cannot_be_resurrected():
    ctx={"x":10,"y":20,"predictions":{
        12:prediction(),23:prediction(23,owner=8,hull=17,race=7)}}
    with pytest.raises(ValueError,match="no_resurrection"):
        M.prepare_current_state(
            state=M.SiteCombatState(active_ships={}),
            current_case=current(),context=ctx,
            history=[{"left_ship_id":12,"right_ship_id":40}])


def test_unknown_or_conflicting_Tminus1_owner_abstains():
    ctx={"x":10,"y":20,"predictions":{
        12:prediction(owner=5),
        23:prediction(23,owner=8,hull=17,race=7)}}
    with pytest.raises(ValueError,match="identity_inconsistent"):
        M.prepare_current_state(
            state=M.SiteCombatState(active_ships={}),
            current_case=current(),context=ctx,history=[])
    ctx["predictions"].pop(12)
    with pytest.raises(ValueError,match="absent_from_Tminus1"):
        M.prepare_current_state(
            state=M.SiteCombatState(active_ships={}),
            current_case=current(),context=ctx,history=[])


def test_no_replacement_of_existing_carried_fields_even_when_different():
    existing=M.anchored_ship_from_N(
        side="left",ship_id=12,owner_id=4,hull_id=35,race_id=3,
        payload=current().payload,entry=prediction(),site=(10,20))[0]
    existing["damage"]=51  # must stay 51, not silently copy N damage=0
    ctx={"x":10,"y":20,"predictions":{
        12:prediction(),23:prediction(23,owner=8,hull=17,race=7)}}
    state=M.SiteCombatState(active_ships={12:existing})
    new,bridges=M.prepare_current_state(
        state=state,current_case=current(),context=ctx,history=[])
    assert new.active_ships[12]["damage"]==51
    assert [b["ship_id"] for b in bridges]==[23]
    assert state.active_ships[12]["damage"]==51


def test_no_future_data_in_predictor_or_in_bridge_signature(monkeypatch):
    ctx={"x":10,"y":20,"factual_queue":[
        {"vcr_id":10,"pair":(12,23),"left_ship_id":12,"right_ship_id":23}
    ],"predictions":{12:prediction(),23:prediction(23,owner=8,hull=17,race=7)}}
    base=M.SiteCombatState(active_ships={})
    monkeypatch.setattr(M.differential,"_initial_state_before_window",
                        lambda **kw:base)
    monkeypatch.setattr(M,"record_factual_site_pair",lambda state,**kw:state)
    def fake_replay(state,**kw):
        return SimpleNamespace(resolved=True,reason=None,
                               terminals_by_ship_id={},
                               capture_transfers_by_ship_id={})
    monkeypatch.setattr(M.differential,"build_site_terminal_replay_batch",fake_replay)
    monkeypatch.setattr(M,"apply_site_terminal_batch",lambda state,**kw:
                        SimpleNamespace(resolved=True,state=state))
    monkeypatch.setattr(M,"build_parent_standard_pair_inputs",lambda **kw:
                        SimpleNamespace(pair_inputs=(1,2)))
    monkeypatch.setattr(M,"select_parent_resume",lambda state,**kw:
                        SimpleNamespace(status="resolved",pair=(12,23),
                                        left_ship_id=12,right_ship_id=23,
                                        occurrence_index=1))
    r=M.predict_bridge(context=ctx,appearances={},cases={(30,10):current()},
                       game=7,turn=30,n=10)
    assert r["status"]=="CONDITIONAL_PARENT_STANDARD_N_TO_NPLUS1"
    assert r["prediction"]["current_N_roster_conditioned"] is True
    assert len(r["anchored_ships"])==2
    assert r["factual_comparison"] is None
    assert "nplus1" not in M.predict_bridge.__code__.co_varnames
    ctx["factual_queue"].append({"vcr_id":11,"pair":(12,31)})
    with pytest.raises(ValueError,match="future VCR leaked"):
        M.predict_bridge(context=ctx,appearances={},cases={(30,10):current()},
                         game=7,turn=30,n=10)


def test_current_capture_remains_abstain_and_never_selects_parent(monkeypatch):
    ctx={"x":10,"y":20,"factual_queue":[
        {"vcr_id":10,"pair":(12,23),"left_ship_id":12,"right_ship_id":23}
    ],"predictions":{12:prediction(),23:prediction(23,owner=8,hull=17,race=7)}}
    monkeypatch.setattr(M.differential,"_initial_state_before_window",
                        lambda **kw:M.SiteCombatState(active_ships={}))
    monkeypatch.setattr(M,"record_factual_site_pair",lambda state,**kw:state)
    monkeypatch.setattr(M.differential,"build_site_terminal_replay_batch",
        lambda state,**kw:SimpleNamespace(
            resolved=True,reason=None,terminals_by_ship_id={},
            capture_transfers_by_ship_id={12:"captured"}))
    monkeypatch.setattr(M,"apply_site_terminal_batch",lambda state,**kw:
                        SimpleNamespace(resolved=True,state=state))
    monkeypatch.setattr(M,"build_parent_standard_pair_inputs",lambda **kw:
                        pytest.fail("parent selector must not run after capture"))
    r=M.predict_bridge(context=ctx,appearances={},cases={(30,10):current()},
                       game=7,turn=30,n=10)
    assert r["status"]=="ABSTAIN_CAPTURE_TEMPORARY_ORDER_NOT_INDEPENDENT"


def test_untrusted_source_absence_returns_explicit_abstention(monkeypatch):
    ctx={"x":10,"y":20,"factual_queue":[
        {"vcr_id":10,"pair":(12,23),"left_ship_id":12,"right_ship_id":23}
    ],"predictions":{}}
    monkeypatch.setattr(M.differential,"_initial_state_before_window",
                        lambda **kw:M.SiteCombatState(active_ships={}))
    r=M.predict_bridge(context=ctx,appearances={},cases={(30,10):current()},
                       game=7,turn=30,n=10)
    assert r["status"]=="ABSTAIN_TMINUS1_OR_CURRENT_N_BRIDGE_UNRESOLVED"
    assert r["prediction"] is None


def test_runners_and_pins():
    for name in ("tools/run-combat-c5-current-n-roster-bridge-v2.sh",
                 "tools/run-combat-c5-current-n-roster-bridge-v2-with-evidence.sh"):
        subprocess.run(["bash","-n",str(ROOT/name)],check=True)
    run=(ROOT/"tools/run-combat-c5-current-n-roster-bridge-v2.sh").read_text()
    wrap=(ROOT/"tools/run-combat-c5-current-n-roster-bridge-v2-with-evidence.sh").read_text()
    assert M.STRICT_V1_BLOB in run
    assert M.CENSUS_BLOB in run
    assert "/CURRENT" not in run
    assert "connect_current_compact" not in run
    assert "run-with-runtime-evidence.sh" in wrap
