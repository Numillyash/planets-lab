from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"tools/diagnostics/combat_c5_new_game_corpus_batch_v25.py"
SPEC=importlib.util.spec_from_file_location("c5_new_games_v25",SOURCE)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def write_manifest(path:Path,game_ids):
    path.write_text("".join(json.dumps({"game_id":g})+"\n" for g in game_ids),
                    encoding="utf-8")


def test_population_only_new_games_and_exact_compact_membership(tmp_path):
    old=tmp_path/"baseline.jsonl"
    new=tmp_path/"selected.jsonl"
    write_manifest(old,range(1,101))
    write_manifest(new,range(101,109))
    class Db:
        def execute(self,sql):
            assert "source_archives" in sql
            return self
        def fetchall(self):
            return [(g,) for g in range(101,109)]
    selected,baseline=M.audit_population(new,old,Db())
    assert len(selected)==8 and len(baseline)==100
    write_manifest(new,[101,102,103,104,105,106,107,100])
    with pytest.raises(ValueError,match="disjoint"):
        M.audit_population(new,old,Db())
    write_manifest(new,[101,102,103,104,105,106,107,107])
    with pytest.raises(ValueError,match="duplicate"):
        M.audit_population(new,old,Db())


def test_adjacent_windows_selection_is_game_and_turn_metadata_only():
    metadata=[(g,t) for g in range(101,109) for t in range(1,61)]
    result=M.windows_from_metadata(metadata,frozenset(range(101,109)))
    assert len(result)==192
    assert len(set(result))==192
    assert all(t>=2 for _,t in result)
    for g in range(101,109):
        matches=[t for x,t in result if x==g]
        assert len(matches)==24 and matches==sorted(matches)
    with pytest.raises(ValueError,match="missing source members"):
        M.windows_from_metadata(metadata[:-60],frozenset(range(101,109)))


def test_documented_short_field_and_unproven_actual_activation():
    edge={"owner_id":6,"source":[1141,1459],"target":[1126,1439]}
    gate={
        "ship_id":446,"owner_id":6,
        "archived_catalog_name_confirms_dungeon_stargate":True,
        "Tminus1_position":[1279,1931],
        "documentation_field_radius_ly":550,
    }
    r=M.field_evidence(edge,[gate],{}, {6:6})
    assert r["Tminus1_short_field_witness"] is True
    assert round(r["Tminus1_stargate_coverage"][0]["source_distance_ly"],2)==491.76
    assert r["Tminus1_stargate_coverage"][0]["target_also_inside_field"] is True
    assert r["Tminus1_stargate_coverage"][0]["active_at_actual_Host_phase_proven"] is False
    unknown=M.field_evidence(edge,[],{}, {6:6})
    assert unknown["Tminus1_short_field_witness"] is False
    assert unknown["Tminus1_stabilizer_absence_unproven"] is True
    short=M.field_evidence(edge,[],{"settings.shortformatrules":True},{6:6})
    assert short["Tminus1_explicit_cyborg_stabilization"] is True
    not_cyborg=M.field_evidence(edge,[],{"settings.shortformatrules":True},{6:7})
    assert not_cyborg["Tminus1_explicit_cyborg_stabilization"]


def test_source_preselection_frozen_before_any_owner_current_T(monkeypatch):
    events=[]
    class FakeConn:
        def execute(self,sql):
            assert "source_members" in sql
            events.append("metadata")
            return self
        def fetchall(self):
            return [(g,t) for g in range(101,109) for t in range(1,9)]
    def fake_pre(_conn,g,t):
        events.append("pre")
        return {
            "game_id":g,"turn":t,
            "Tminus1_candidates":[{
                "game_id":g,"turn":t,"initiator_ship_id":5,
                "target_ship_id":6,"owner_id":3,
                "source":[100,100],"target":[300,100],
                "actor_Tminus1_fuel":100,
                "Tminus1_cohort":"LONG_CONVENTIONAL_PASS",
                "Tminus1_short_field_witness":False,
            }],
            "Tminus1_gates":[],
            "Tminus1_escort_exposures":[],
            "Tminus1_rule_safe_scalars":{},
        }
    def fake_post(_conn,*,game,turn):
        assert events.count("pre")==len(result_windows)
        events.append("post")
        return {5:(3,{"x":300,"y":100,"hullid":56,"neutronium":50})}
    result_windows=M.windows_from_metadata(
        [(g,t) for g in range(101,109) for t in range(1,9)],
        frozenset(range(101,109)))
    monkeypatch.setattr(M,"pre_window",fake_pre)
    monkeypatch.setattr(M.v9,"after_owner_current",fake_post)
    reports=M.run(FakeConn(),frozenset(range(101,109)),frozenset(range(1,101)),
                  "/some-explicit-generation.duckdb","verified-sha")
    assert events.index("post")>max(i for i,x in enumerate(events) if x=="pre")
    assert events.count("pre")==len(result_windows)
    assert events.count("post")==len(result_windows)
    assert len(reports)==3
    assert all(r["Tminus1_frozen_before_first_T"] is True for r in reports)
    assert reports[0]["summary"]["Tminus1_stock_chunnel_candidate_edges"]==len(result_windows)
    assert reports[0]["summary"]["short_Tminus1_documented_field_witnesses"]==0


def test_owner_drift_is_abstain_not_successful_endpoint():
    frozen={
        "game_id":101,"turn":20,
        "Tminus1_candidates":[{
            "game_id":101,"turn":20,
            "initiator_ship_id":467,"target_ship_id":80,"owner_id":6,
            "source":[1141,1459],"target":[1126,1439],
            "actor_Tminus1_fuel":51,
            "Tminus1_cohort":"SHORT_ONE_GATE_FAILED",
            "Tminus1_short_field_witness":True,
        }],
        "Tminus1_gates":[],
        "Tminus1_escort_exposures":[],
    }
    current={467:(7,{"x":1126,"y":1439,"hullid":56,"neutronium":1})}
    actors,fields,passengers=M.compare_window(frozen,current)
    assert fields==passengers==[]
    assert actors[0]["T_status"]=="ABSTAIN_T_OWNER_DRIFT"
    assert actors[0]["T_position"] is None
    assert actors[0]["Host_Chunnel_activation_proven"] is False


def test_bounded_source_stack_and_no_foreign_owner_promotion(monkeypatch):
    # This is a synthetic pre-window; no attempt to infer a chunnel from T.
    source={
        467:(6,{"x":1141,"y":1459,"hullid":56,"warp":0,"neutronium":51}),
        80:(6,{"x":1126,"y":1439,"hullid":56,"warp":0,"neutronium":1}),
        193:(9,{"x":1141,"y":1459,"hullid":17,"warp":9,"neutronium":8}),
    }
    row={
        "initiator_ship_id":467,"target_ship_id":80,"owner_id":6,
        "source":[1141,1459],"target":[1126,1439],
        "actor_Tminus1_fuel":51,"target_Tminus1_fuel":1,
        "actor_Tminus1_warp":0,"target_Tminus1_warp":0,
        "Tminus1_distance_ly":25,
        "cohort":"ONE_TMINUS1_GATE_FAILS",
        "single_failing_gate":"DISTANCE_BELOW_100_AT_TMINUS1",
    }
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *_args,**_kw:((),()))
    monkeypatch.setattr(M,"group_perspective_records",lambda *_args:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_args:source)
    monkeypatch.setattr(M.v16,"potential_stock_edges",lambda *_args:((row,),{}))
    monkeypatch.setattr(M.v20,"game_rules_markers",lambda *_args:({},{}))
    monkeypatch.setattr(M.v11,"hull_name_inventory",lambda *_args:{})
    monkeypatch.setattr(M.v20,"stabilizer_inventory",lambda *_args:[])
    pre=M.pre_window(None,101,20)
    assert len(pre["Tminus1_candidates"])==1
    assert pre["Tminus1_candidates"][0]["Tminus1_cohort"]=="SHORT_ONE_GATE_FAILED"
    assert len(pre["Tminus1_escort_exposures"])==1
    stack=pre["Tminus1_escort_exposures"][0]["Tminus1_source_stack"]
    assert len(stack)==2
    assert sum(not s["same_owner_as_actor"] for s in stack)==1
    assert all("friendlycode" not in str(x) for x in pre["Tminus1_candidates"])


def test_three_outputs_complete_and_manifest_sha256(tmp_path):
    selected=frozenset(range(101,109))
    frozen={(g,20):{
        "game_id":g,"turn":20,"Tminus1_candidates":[],
        "Tminus1_gates":[],"Tminus1_escort_exposures":[],
        "Tminus1_rule_safe_scalars":{}}
        for g in selected}
    reports=M.create_reports(
        selected,frozenset(range(1,101)),"/explicit.duckdb","sha",
        tuple(sorted(frozen)),frozen,[([],[],[])],[])
    M.publish(tmp_path,reports)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["all_three_complete"] is True
    assert sorted(manifest["reports"])==sorted(M.REPORTS)
    assert manifest["CURRENT_modified"] is False
    for phase in M.REPORTS:
        assert manifest["reports"][phase]["sha256"]==hashlib.sha256(
            (tmp_path/(phase+".json")).read_bytes()).hexdigest()


def test_one_server_command_never_activates_or_overwrites_current():
    runner=ROOT/"tools/run-combat-c5-new-game-corpus-batch-v25.sh"
    wrapper=ROOT/"tools/run-combat-c5-new-game-corpus-batch-v25-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    content=runner.read_text()
    assert "public-postindependent-validation-with-public68.jsonl" in content
    assert "SELECT_COUNT=8" in content
    assert "EXPECTED_COUNT" not in content
    assert "--expected-count 8" in content
    assert "compact-c5-v25-public8-resume" in content
    assert "--activate-current" not in content.lower()
    assert "CURRENT_BEFORE" in content
    assert "run-public-validation-corpus-acquisition.sh" in content
    assert "combat_c5_new_game_corpus_batch_v25.py" in content
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/combat/c5-new-game-corpus-batch-v25/published" in wrapper.read_text()
