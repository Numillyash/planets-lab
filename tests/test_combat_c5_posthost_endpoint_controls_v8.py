from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_posthost_endpoint_controls_v8.py"
SPEC=importlib.util.spec_from_file_location("c5_posthost_endpoint_v8",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def pred(sid=46,owner=10,source="normal_mine_route_risk"):
    return {
        "ship_id":sid,"owner_id":owner,"hull_id":35,"race_id":4,
        "source":source,
        "position":None if source=="normal_mine_route_risk" else (2178,1105),
        "diagnostic_no_mine_hit_destination":(2178,1105),
        "diagnostic_no_mine_hit_source":"normal_move",
        "raw":{"id":sid,"ownerid":owner,"x":2110,"y":1105,"targetx":2178,"targety":1105},
    }


class TLeakSentinel(dict):
    def get(self,key,*args):
        if key in {"T_archive","after_records","observed_T","next_vcr","factual_queue"}:
            raise AssertionError("T/future leak into T-1 forecast")
        return super().get(key,*args)


def test_pre_t_forecasts_do_not_look_up_future_or_current_vcr():
    before=TLeakSentinel({46:pred(),77:pred(77,source="normal_move"),
                          "T_archive":object(),"next_vcr":object()})
    frozen=M.freeze_tminus1_forecast(
        game=421276,turn=115,predictions=before,v7_target={46:10})
    assert frozen[46]["cohort"]==M.MINE
    assert frozen[46]["conditional_or_model_endpoint"]==[2178,1105]
    assert frozen[46]["conditional_no_mine_only"] is True
    assert frozen[77]["cohort"]==M.NORMAL
    assert frozen[77]["frozen_v7_witness"] is False
    assert len(frozen)==2


def test_posthost_observed_match_is_not_host_combat_membership():
    row=M.freeze_tminus1_forecast(
        game=1,turn=20,predictions={46:pred()},v7_target={46:10})[46]
    result=M.compare_posthost(row,{46:(10,{"x":2178,"y":1105,"hullid":35})})
    assert result["comparison_status"]=="POSTHOST_ENDPOINT_MATCH"
    assert result["precombat_site_membership_proven"] is False
    assert result["mine_hit_or_nonhit_proven"] is False
    assert result["Nplus1_vcr_used"] is False
    mismatch=M.compare_posthost(row,{46:(10,{"x":2150,"y":1105,"hullid":35})})
    assert mismatch["comparison_status"]=="POSTHOST_ENDPOINT_MISMATCH"
    assert mismatch["mine_hit_or_nonhit_proven"] is False


def test_missing_stale_owner_change_hull_change_are_abstentions():
    row=M.freeze_tminus1_forecast(
        game=1,turn=20,predictions={46:pred()},v7_target={46:10})[46]
    examples=[
        ({}, "ABSTAIN_T_ARCHIVE_OWNER_CURRENT_UNAVAILABLE"),
        ({46:(10,None)}, "ABSTAIN_T_ARCHIVE_OWNER_CURRENT_UNAVAILABLE"),
        ({46:(11,{"x":2178,"y":1105,"hullid":35})}, "ABSTAIN_OWNER_DRIFT_AT_T"),
        ({46:(10,{"x":2178,"y":1105,"hullid":36})}, "ABSTAIN_HULL_IDENTITY_DRIFT_AT_T"),
        ({46:(10,{"x":None,"y":1105,"hullid":35})}, "ABSTAIN_T_ARCHIVE_POSITION_UNAVAILABLE"),
    ]
    for observed,status in examples:
        assert M.compare_posthost(row,observed)["comparison_status"]==status


def test_missing_conditional_baseline_is_not_reported_as_mismatch():
    item=pred()
    item.pop("diagnostic_no_mine_hit_destination")
    row=M.freeze_tminus1_forecast(
        game=1,turn=20,predictions={46:item},v7_target={46:10})[46]
    result=M.compare_posthost(row,{46:(10,{"x":2178,"y":1105,"hullid":35})})
    assert result["comparison_status"]=="ABSTAIN_TMINUS1_NORMAL_ENDPOINT_UNAVAILABLE"


def test_v7_target_owner_source_and_original_mine_mask_fail_closed():
    with pytest.raises(ValueError,match="owner/source changed"):
        M.freeze_tminus1_forecast(
            game=1,turn=2,predictions={46:pred(owner=11)},v7_target={46:10})
    x=pred(source="tow_attempt")
    with pytest.raises(ValueError,match="risk witness source changed"):
        M.freeze_tminus1_forecast(
            game=1,turn=2,predictions={46:x},v7_target={46:10})
    x=pred()
    x["position"]=(2178,1105)
    with pytest.raises(ValueError,match="risk-masked"):
        M.freeze_tminus1_forecast(
            game=1,turn=2,predictions={46:x},v7_target={46:10})


def test_after_owner_current_accessor_does_not_use_stale_only_record(monkeypatch):
    class Record:
        def __init__(self,owner,current):
            self.player_id=owner
            self.raw={"ownerid":owner,"x":25,"y":35}
            self.is_current=current
    monkeypatch.setattr(M,"group_perspective_records",
        lambda _snap,_kind:{(20,46):(Record(10,False),)})
    monkeypatch.setattr(M,"_owner_record",lambda group:(10,None))
    records=M.owner_current_after_records((),20)
    assert records[46]==(10,None)


def test_script_sources_and_wrapper_are_pinned():
    run=ROOT/"tools/run-combat-c5-posthost-endpoint-controls-v8.sh"
    wrapper=ROOT/"tools/run-combat-c5-posthost-endpoint-controls-v8-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    script=run.read_text()
    assert M.V6_BLOB in script and M.V7_BLOB in script
    assert "/CURRENT" not in script
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
