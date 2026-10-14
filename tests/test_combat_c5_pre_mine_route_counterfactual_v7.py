from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_pre_mine_route_counterfactual_v7.py"
SPEC=importlib.util.spec_from_file_location("c5_pre_mine_route_v7",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def sample(*,dest=(101,200),source="normal_mine_route_risk"):
    return {"ship_id":46,"owner_id":3,"source":source,"position":None,
            "raw":{"id":46,"ownerid":3,"x":95,"y":200,
                   "targetx":101,"targety":200},
            "diagnostic_no_mine_hit_destination":dest,
            "diagnostic_no_mine_hit_source":"normal_move"}


class NoFutureContext(dict):
    """The evaluator must not reach the factual current/future VCR queue."""
    def get(self,k,*args):
        if k in {"factual","factual_queue","next_vcr","observed_Nplus1"}:
            raise AssertionError("future VCR leakage")
        return super().get(k,*args)


def test_conditional_no_hit_hit_site_and_independent_controls():
    key=(10,20,101,200)
    ctx=NoFutureContext(game_id=10,battle_turn=20,x=101,y=200,
        predictions={
          46:sample(),
          5:{"source":"normal_move","position":(101,200)},
          6:{"source":"normal_move","position":(105,205)},
        },
        factual_queue=object(), observed_Nplus1=object())
    out=M.evaluate_site(context=ctx,site_key=key,
        target_ships={46:{"ship_id":46,"owner_id":3}})
    assert out["witnesses"][0]["status"]=="COUNTERFACTUAL_NO_MINE_ROUTE_ENDS_AT_SITE"
    assert out["witnesses"][0]["actual_N_position_proven"] is False
    assert out["witnesses"][0]["combat_eligibility_proven"] is False
    assert out["Tminus1_normal_route_controls_total_counts"]=={
        "Tminus1_normal_route_ends_at_site":1,
        "Tminus1_normal_route_ends_elsewhere":1}
    assert out["future_VCR_accessed_in_evaluation"] is False


def test_no_hit_route_elsewhere_and_no_candidate_promotion():
    ctx={"game_id":10,"battle_turn":20,"x":101,"y":200,
         "predictions":{46:sample(dest=(99,200))}}
    out=M.evaluate_site(context=ctx,site_key=(10,20,101,200),
                        target_ships={46:{"ship_id":46,"owner_id":3}})
    x=out["witnesses"][0]
    assert x["status"]=="COUNTERFACTUAL_NO_MINE_ROUTE_ENDS_ELSEWHERE"
    assert x["site_match_without_mine_interference"] is False
    assert x["actual_N_position_proven"] is False


def test_missing_planner_and_ship_abstain():
    p=sample()
    p.pop("diagnostic_no_mine_hit_destination")
    ctx={"game_id":10,"battle_turn":20,"x":101,"y":200,
         "predictions":{46:p}}
    out=M.evaluate_site(context=ctx,site_key=(10,20,101,200),
                        target_ships={46:{"ship_id":46,"owner_id":3},
                                      47:{"ship_id":47,"owner_id":4}})
    assert [x["status"] for x in out["witnesses"]]==[
        "ABSTAIN_PRE_MINE_PLANNER_OUTPUT_UNAVAILABLE","ABSTAIN_TMINUS1_SHIP_MISSING"]


def test_source_drift_and_malformed_tminus1_identity_fail_closed():
    ctx={"game_id":10,"battle_turn":20,"x":101,"y":200,
         "predictions":{46:sample()}}
    identity={46:{"ship_id":46,"owner_id":3}}
    ctx["predictions"][46]["owner_id"]=9
    with pytest.raises(ValueError,match="source disagrees"):
        M.evaluate_site(context=ctx,site_key=(10,20,101,200),target_ships=identity)
    ctx["predictions"][46]=sample(source="tow_attempt")
    with pytest.raises(ValueError,match="source disagrees"):
        M.evaluate_site(context=ctx,site_key=(10,20,101,200),target_ships=identity)
    ctx["predictions"][46]=sample()
    ctx["predictions"][46]["raw"]["targetx"]=999
    with pytest.raises(ValueError,match="start/waypoint identity drift"):
        M.evaluate_site(context=ctx,site_key=(10,20,101,200),target_ships=identity)


def test_opt_in_source_honors_original_mine_risk_mask():
    p=ROOT/"tools/diagnostics/combat_public_capture_o_layer_probe.py"
    src=p.read_text(encoding="utf-8")
    assert "collect_pre_mine_counterfactual: bool = False" in src
    assert 'source == "normal_mine_route_risk"' in src
    assert 'predicted = None' in src
    assert 'predicted_rows[ship_id]["diagnostic_no_mine_hit_destination"]' in src


def test_evidence_scripts_read_only_and_pinned():
    run=ROOT/"tools/run-combat-c5-pre-mine-route-counterfactual-v7.sh"
    wrapper=ROOT/"tools/run-combat-c5-pre-mine-route-counterfactual-v7-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert M.V6_SHA1 in run.read_text(encoding="utf-8")
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
    assert "/CURRENT" not in run.read_text(encoding="utf-8")
