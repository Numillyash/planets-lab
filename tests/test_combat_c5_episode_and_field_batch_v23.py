from __future__ import annotations

import importlib.util
import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_episode_and_field_batch_v23.py"
SPEC=importlib.util.spec_from_file_location("c5_episode_field_v23",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def edge(*,actor=467,target=80,owner=6,src=(100,100),dst=(125,100),gate="DISTANCE_BELOW_100_AT_TMINUS1"):
    return {
        "initiator_ship_id":actor,"target_ship_id":target,"owner_id":owner,
        "source":list(src),"target":list(dst),
        "cohort":"ONE_TMINUS1_GATE_FAILS" if gate else "ALL_TMINUS1_GATES_PASS",
        "single_failing_gate":gate,
        "Tminus1_distance_ly":25 if gate else 300,
        "actor_Tminus1_fuel":100,"target_Tminus1_fuel":80,
        "actor_Tminus1_warp":0,"target_Tminus1_warp":0,
    }


def test_unused_games_selected_by_metadata_only_and_quantiles():
    metadata=[(g,t) for g in range(100,113) for t in range(1,61)]
    prior=frozenset(range(100,103))
    windows=M.select_unused_metadata(metadata,prior)
    assert {g for g,t in windows}==set(range(103,113))
    assert len(windows)==10*24
    assert all(t>=2 for g,t in windows)
    assert len(set(windows))==len(windows)
    for g in range(103,113):
        ts=[t for k,t in windows if k==g]
        assert ts==sorted(ts) and len(ts)==24
    with pytest.raises(ValueError,match="too few remaining"):
        M.select_unused_metadata(metadata,frozenset(range(100,111)))


def test_stargate_field_witness_is_Tminus1_only_and_missing_is_abstain():
    candidate=edge()
    radius=[{
        "ship_id":446,"owner_id":6,
        "archived_catalog_name_confirms_dungeon_stargate":True,
        "Tminus1_position":[120,120],
        "documentation_field_radius_ly":150,
    }]
    result=M.source_field_witness(candidate,{},radius,{}, {})
    assert result["Tminus1_documented_field_witnesses"][0]["same_owner"] is True
    assert result["Tminus1_documented_field_witnesses"][0]["Host_field_actually_active_proven"] is False
    empty=M.source_field_witness(candidate,{},[],{}, {})
    assert empty["Tminus1_documented_field_witnesses"]==[]
    assert empty["Tminus1_field_absence_not_proven"] is True
    short=M.source_field_witness(candidate,{},[],{"settings.shortformatrules":True},{6:6})
    assert short["Tminus1_short_format_cyborg_rule_explicit"] is True
    foreign=M.source_field_witness(candidate,{},radius,{"settings.shortformatrules":True},{6:4})
    assert foreign["Tminus1_short_format_cyborg_rule_explicit"] is False


def test_frozen_short_discriminability_and_control_comparator():
    pre={"game_id":200,"turn":50,
         "Tminus1_short_distinct":[{
             **edge(),"game_id":200,"turn":50,
             "Tminus1_field_witness_status":"TMINUS1_DOCUMENTED_FIELD_WITNESS",
             "Tminus1_documented_field_witnesses":[],
         }],
         "Tminus1_long_control":[edge(actor=300,target=301,gate=None,
                                      src=(100,100),dst=(400,100))]}
    after={
        467:(6,{"x":125,"y":100,"hullid":56}),
        300:(6,{"x":100,"y":100,"hullid":56}),
    }
    rows=M.compare_scan(pre,after)
    assert len(rows)==2
    assert rows[0]["T_observation_status"]=="AT_DISTINCT_FROZEN_TARGET"
    assert rows[1]["T_observation_status"]=="AT_FROZEN_SOURCE"
    assert rows[0]["Host_Chunnel_activation_proven"] is False
    after[467]=(7,after[467][1])
    rows=M.compare_scan(pre,after)
    assert rows[0]["T_observation_status"]=="ABSTAIN_T_OWNER_DRIFT"


def test_field_scan_absolute_all_pre_before_first_T(monkeypatch):
    exclusions=frozenset(range(100,103))
    metadata=[(g,t) for g in range(100,110) for t in range(1,10)]
    expected=M.select_unused_metadata(metadata,exclusions)
    events=[]
    def pre(_conn,g,t):
        events.append("PRE")
        return {"game_id":g,"turn":t,
                "Tminus1_short_distinct":[{
                    **edge(),"game_id":g,"turn":t,
                    "Tminus1_field_witness_status":"ABSTAIN_NO_DOCUMENTED_FIELD_WITNESS",
                }],"Tminus1_long_control":[]}
    def post(_conn,*,game,turn):
        assert events.count("PRE")==len(expected)
        events.append("POST")
        return {467:(6,{"x":100,"y":100,"hullid":56})}
    monkeypatch.setattr(M,"pre_scan",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    result=M.field_discovery(None,metadata,exclusions)
    assert result["summary"]["all_unused_game_Tminus1_freezes_before_first_T"] is True
    assert result["summary"]["short_with_Tminus1_documented_field_witness"]==0
    assert result["summary"]["zero_exposure_not_rule_refutation"] is True
    assert events.count("POST")==len(expected)
    assert events.index("POST")>max(i for i,x in enumerate(events) if x=="PRE")


def fixture_v22():
    base=[]
    for i in range(57):
        cohort="LONG_CONVENTIONAL_PASS" if i<36 else (
            "OTHER_ONE_FAILED_TMINUS1_GATE" if i<49 else "NON_DISCRIMINATIVE_COLOCATED")
        result=("T_ACTOR_AT_DISTINCT_TARGET" if i<36 else
                "T_ACTOR_AT_SOURCE" if i<49 else "NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET")
        base.append({
            "game_id":100+(i%16),"turn":20+3*(i//16),
            "initiator_ship_id":i+1,"target_ship_id":i+101,
            "Tminus1_ruleaware_cohort":cohort,"T_actor_status":result,
            "single_failing_gate":None if i<36 else
                "INITIATOR_FUEL_LT50" if i<49 else "DISTANCE_BELOW_100_AT_TMINUS1",
        })
    stacks=[]
    for i in range(36):
        ships=[{
            "ship_id":i+1 if j==0 else 10000+i*12+j,
            "same_owner":j!=1,
            "T_at_source_edge_target":True,
            "T_owner_current_status":"OWNER_CURRENT_T_OBSERVED",
        } for j in range(10 if i<27 else 9)]
        stacks.append({
            "game_id":base[i]["game_id"],"turn":base[i]["turn"],
            "initiator_ship_id":base[i]["initiator_ship_id"],
            "target_ship_id":base[i]["target_ship_id"],
            "Tminus1_ruleaware_cohort":"LONG_CONVENTIONAL_PASS",
            "Tminus1_stack_size":len(ships),"T_members":ships,
        })
    assert sum(x["Tminus1_stack_size"] for x in stacks)==351
    actor_doc={"actor_Tminus1_to_T_comparisons":base}
    escort_doc={"episode_preselected_source_stacks":stacks}
    return actor_doc,escort_doc


def test_episode_counting_ownership_and_tamper_detection():
    actor_doc,escort_doc=fixture_v22()
    a=M.episode_reconciliation(actor_doc)
    assert a["summary"]["LONG_CONVENTIONAL_PASS_actor_rows"]==36
    assert a["summary"]["OTHER_SINGLE_GATE_FAIL_actor_rows"]==13
    e=M.ownership_analysis(escort_doc,actor_doc)
    assert e["summary"]["frozen_episode_count"]==36
    assert e["summary"]["frozen_source_ship_appearances"]==351
    assert e["summary"]["different_owner_appearances"]==36
    assert e["summary"]["different_owner_at_frozen_target"]==36
    escort_doc["episode_preselected_source_stacks"][0]["T_members"][0]["ship_id"]=99999
    with pytest.raises(ValueError,match="actor missing"):
        M.ownership_analysis(escort_doc,actor_doc)


def test_one_command_and_evidence_wrapper_shell_lint():
    script=ROOT/"tools/run-combat-c5-episode-field-batch-v23.sh"
    wrapper=ROOT/"tools/run-combat-c5-episode-field-batch-v23-with-evidence.sh"
    subprocess.run(["bash","-n",str(script)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    content=script.read_text()
    for digest in (M.V22_MANIFEST_BLOB,M.V22_ACTORS_BLOB,M.V22_ESCORTS_BLOB,M.V22_STABILIZERS_BLOB):
        assert digest in content
    assert M.GENERATION in content and "/CURRENT" not in content
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/combat/c5-episode-field-batch-v23/published" in wrapper.read_text()


def test_three_reports_and_sha256_manifest(tmp_path):
    docs=tuple({
        **M.report_base(name),"summary":{},
    } for name in M.REPORTS)
    M.publish(tmp_path,docs)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["status"]=="V23_EPISODES_OWNERSHIP_FIELD_SCAN_COMPLETE"
    assert manifest["all_three_complete"] is True
    for name in M.REPORTS:
        assert manifest["phase_reports"][name]["sha256"]==hashlib.sha256(
            (tmp_path/(name+".json")).read_bytes()).hexdigest()
