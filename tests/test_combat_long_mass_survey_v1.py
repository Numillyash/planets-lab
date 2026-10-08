from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
DIAG=ROOT/"tools"/"diagnostics"
if str(DIAG) not in sys.path:
    sys.path.insert(0,str(DIAG))
SCRIPT=DIAG/"combat_long_mass_survey_v1.py"
SPEC=importlib.util.spec_from_file_location("combat_long_mass_survey_v1",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def specs():
    return SimpleNamespace(
        hulls={
            39:SimpleNamespace(mass=96,name="D19b",special="",cargo_capacity=40),
            117:SimpleNamespace(mass=145,name="Brood",special="",cargo_capacity=900),
            1041:SimpleNamespace(mass=173,name="Saber Shield Generator",
                                 special="Shield Generator",cargo_capacity=50),
        },
        engines={
            7:SimpleNamespace(name="Quantum",cost=SimpleNamespace(megacredits=170)),
        },
    )


def raw(sid,hull,*,x=10,y=20,tx=30,ty=40,owner=4):
    return {"id":sid,"hullid":hull,"ownerid":owner,"engineid":7,
            "x":x,"y":y,"targetx":tx,"targety":ty,"clans":900}


def test_selector_diverse_and_anchor_preserved():
    class FakeDB:
        def execute(self,sql):
            assert "FROM vcrs" in sql
            return SimpleNamespace(fetchall=lambda:[
                (217591,148,20),(217591,149,70),(217591,150,40),
                (371631,156,18),(400330,141,18),
                (100001,3,5),(100001,4,12),(100001,5,80),
                (200000,20,25),(250000,10,30),(300000,12,35),
                (591478,30,100),
            ])
    rows=M.choose_games_and_turns(FakeDB(),max_games=8,
                                   turns_per_game=3,max_rows_per_turn=150)
    assert [g for g,_ in rows][:3]==[400330,217591,371631]
    assert 591478 not in dict(rows)
    assert dict(rows)[217591][0]==149
    assert dict(rows)[100001]==[5,4,3]


def test_same_origin_waypoint_is_not_combat_colocation():
    own={262:raw(262,39),6:raw(6,1041),386:raw(386,1041),
         88:raw(88,1041,x=30,y=40,tx=30,ty=40)}
    geometry=M.geometric_control(participant=own[262],same_owner=own,
                                 site=(30,37),specs=specs())
    assert geometry["exact_site_generators"]==0
    assert geometry["same_origin_and_waypoint_generators"]==2
    assert geometry["waypoint_to_vcr_offset"]==[0,-3]
    assert geometry["waypoint_to_vcr_distance_sq"]==9
    assert geometry["per_generator_half_engine_cost"]==85
    assert "DO NOT" in geometry["boundary"]


def test_numeric_mass_remains_unknown_without_engine_owner_evidence():
    args=dict(observed=266,base=96,side="left",left_bays=0,
              hull_mass=96,race=4)
    assert M._numeric_class(**args,geo={})=="unexplained_with_available_owner_geometry"
    assert M._numeric_class(**args,geo={"per_generator_half_engine_cost":85})=="engine_shield_2_numeric_match"
    assert M._numeric_class(observed=456,base=96,side="right",left_bays=10,
                            hull_mass=96,race=4,geo={})=="right_plus360_arithmetic"


def test_owner_conflicts_are_not_arbitrarily_resolved(monkeypatch):
    refs=[SimpleNamespace(perspective_player_id=4),
          SimpleNamespace(perspective_player_id=4)]
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**kw:refs)
    monkeypatch.setattr(M,"reconstruct_members",lambda *a,**kw:iter([
        (refs[0],{"ships":[raw(262,39)]}),
        (refs[1],{"ships":[raw(262,39,x=11)]}),
    ]))
    rows,conflicts,counts=M._owner_records(object(),371631,156,{4})
    assert 4 in conflicts
    assert 4 not in rows
    assert counts["conflicting_owner_ship_observation"]==1


def test_horwasp_inversion_is_observational_only(monkeypatch):
    left={"objectid":262,"hullid":39,"raceid":4,"mass":266,"baycount":0}
    right={"objectid":48,"hullid":117,"raceid":12,"mass":287,
           "baycount":6,"fighters":68,"damage":0}
    case=SimpleNamespace(vcr_id=618,payload={
        "x":10,"y":20,"leftownerid":4,"rightownerid":12,
        "left":left,"right":right,
    })
    monkeypatch.setattr(M,"combat_vcr_cases_for_turns",lambda *a,**kw:{(82,618):case})
    own={4:{262:raw(262,39,x=10,y=20,tx=10,ty=20),
            6:raw(6,1041,x=10,y=20,tx=10,ty=20)},
         12:{48:raw(48,117,x=10,y=20,tx=10,ty=20,owner=12)}}
    monkeypatch.setattr(M,"_owner_records",lambda *a,**kw:(own,set(),Counter()))
    report=M.analyze_turn(conn=object(),game=253449,turn=82,
                          specs=specs(),max_vcrs=10,max_examples=20)
    assert report["counts"]["ship_vcrs"]==1
    assert report["counts"]["side_observations"]==2
    horw=report["horwasp_timelines"][0]["appearances"][0]
    assert horw["tminus1_clans"]==900
    assert horw["candidate_clan_intervals"][0]["possible_clans"]==[882,887]
    assert "INVERSE" in horw["boundary"]


def test_atomic_progress_resume_and_rejection_status(tmp_path):
    check=tmp_path/"checkpoints"
    summary=tmp_path/"published"/"summary.json"
    selected=[(1,[10]),(2,[20])]
    identity="sha-fixed"
    M._write_atomic(check/"game-1.json",{
        "schema":M.SCHEMA,"identity":identity,
        "result":{"game_id":1,"status":"ok","errors":[],
                  "turns":[{"turn":10,
                            "counts":{"ship_vcrs":3,"side_observations":6},
                            "examples":[],"horwasp_timelines":[]}]},
    })
    partial=M.publish_snapshot(checkpoint_dir=check,summary_path=summary,
                               selection=selected,identity=identity,
                               config={"source_sha":"test"})
    assert partial["completed_games"]==1
    assert partial["status"]=="PARTIAL_CHECKPOINT_RESUMABLE_NOT_PROMOTED"
    M._write_atomic(check/"game-2.json",{
        "schema":M.SCHEMA,"identity":identity,
        "result":{"game_id":2,"status":"failed","errors":[{"reason":"invalid"}],
                  "turns":[]},
    })
    full=M.publish_snapshot(checkpoint_dir=check,summary_path=summary,
                            selection=selected,identity=identity,
                            config={"source_sha":"test"})
    assert full["status"]=="COMPLETE_WITH_REJECTIONS_OBSERVATIONAL_NOT_PROMOTED"
    assert full["game_status_counts"]["failed"]==1
    assert full["summary"]["ship_vcrs"]==3
    assert json.loads(summary.read_text(encoding="utf-8"))["completed_games"]==2
    assert not list(check.glob("*.tmp"))
    with pytest.raises(ValueError,match="incompatible checkpoint"):
        M.publish_snapshot(checkpoint_dir=check,summary_path=summary,
                           selection=selected,identity="new-sha",
                           config={"source_sha":"different"})


def test_shells_sha_lock_and_publish_only_compact_report():
    runner=ROOT/"tools"/"run-combat-long-mass-survey-v1.sh"
    wrapper=ROOT/"tools"/"run-combat-long-mass-survey-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    shell=runner.read_text(encoding="utf-8")
    wrapper_text=wrapper.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in shell
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in shell
    assert "PLANETS_LONG_MASS_GAMES:-80" in shell
    assert "--checkpoint-dir" in shell and "--published-summary" in shell
    assert "--include artifacts/combat/long-mass-survey-v1/published" in wrapper_text
    assert "--include artifacts/combat/long-mass-survey-v1/checkpoints" not in wrapper_text
