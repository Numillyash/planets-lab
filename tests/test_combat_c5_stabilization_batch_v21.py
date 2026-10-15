from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"tools/diagnostics/combat_c5_stabilization_batch_v21.py"
SPEC=importlib.util.spec_from_file_location("chunnel_batch_v21",P)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def ship(x,y,*,hull=56,engine=9,warp=0,fuel=50):
    return {
        "x":x,"y":y,"hullid":hull,"engineid":engine,
        "warp":warp,"neutronium":fuel,
    }


def stargate(*,sid=446,owner=6,pos=(1279,1931),engine=9):
    return {
        "ship_id":sid,"owner_id":owner,"hull_id":108,
        "Tminus1_position":list(pos),"Tminus1_engine_id":engine,
        "documentation_field_radius_ly":100+50*engine,
        "archived_catalog_name_confirms_dungeon_stargate":True,
    }


def case(*,g=467386,t=75,a=467,d=80,src=(1141,1459),dst=(1126,1439),owner=6):
    return {
        "game_id":g,"turn":t,"initiator_ship_id":a,
        "target_ship_id":d,"owner_id":owner,
        "Tminus1_source":list(src),"Tminus1_target":list(dst),
        "Tminus1_source_target_distinct":src!=dst,
        "Tminus1_explicit_short_format_rule_flag":None,
    }


def test_verify_stargate_enforces_hull_engine_source_coordinates():
    r={446:(6,ship(1279,1931,hull=108,engine=9))}
    s=stargate()
    M.verify_stargate(r,s)
    r[446][1]["engineid"]=8
    with pytest.raises(ValueError,match="engine drift"):
        M.verify_stargate(r,s)
    r[446][1]["engineid"]=9
    s["documentation_field_radius_ly"]=500
    with pytest.raises(ValueError,match="radius source drift"):
        M.verify_stargate(r,s)
    s["documentation_field_radius_ly"]=550
    r[446]=(7,r[446][1])
    with pytest.raises(ValueError,match="owner/current"):
        M.verify_stargate(r,s)


def test_geometry_separates_source_from_target_and_preserves_no_proof(monkeypatch):
    c={M.CASE467:case()}
    # Synthetic 13-case full cohort: all except original exercise
    # geometry's abstentions, including colocated pairs.
    for j in range(12):
        key=(600000+j,30,j+100,j+300)
        c[key]=case(g=key[0],t=30,a=key[2],d=key[3],
                    src=(100,100),dst=(100,100),owner=9)
    windows=tuple(sorted({key[:2] for key in c}))
    metadata={
        str(g)+"/"+str(t):{
            "Tminus1_stock_dungeon_stargate_inventory":
                [stargate()] if (g,t)==(467386,75) else []
        } for g,t in windows
    }
    def pre(_conn,g,t):
        if (g,t)==(467386,75):
            return {
                467:(6,ship(1141,1459)),
                80:(6,ship(1126,1439)),
                446:(6,ship(1279,1931,hull=108)),
            },()
        return {key[2]:(9,ship(100,100)) for key in c if key[:2]==(g,t)}|{
                key[3]:(9,ship(100,100)) for key in c if key[:2]==(g,t)},()
    monkeypatch.setattr(M,"read_pre",pre)
    out=M.geometry(None,c,windows,metadata)
    assert out["summary"]["frozen_short_edges"]==13
    assert out["summary"]["G467386_T75_467_to_80_source_inside_field"] is True
    assert out["summary"]["G467386_T75_467_to_80_target_inside_field"] is True
    fields=out["G467386_T75_467_to_80"]["Tminus1_fields"]
    assert round(fields[0]["source_distance_ly"],2)==491.76
    assert fields[0]["target_margin_ly"]>0
    assert fields[0]["active_during_actual_Chunnel_unverified"] is True
    assert out["summary"]["T_archives_read"] is False


def test_persistence_freezes_all_pre_states_before_T(monkeypatch):
    windows=((467386,75),(467386,221),(632527,89))
    metadata={
        "467386/75":{"Tminus1_stock_dungeon_stargate_inventory":[stargate()]},
        "467386/221":{"Tminus1_stock_dungeon_stargate_inventory":[stargate(pos=(1278,1931))]},
        "632527/89":{"Tminus1_stock_dungeon_stargate_inventory":[]},
    }
    events=[]
    def pre(_conn,g,t):
        events.append("pre")
        return {446:(6,ship(1279 if t==75 else 1278,1931,hull=108))},()
    def post(_conn,*,game,turn):
        assert events.count("pre")==3
        events.append("post")
        return {446:(6,ship(1279 if turn==75 else 1278,1931,hull=108))}
    monkeypatch.setattr(M,"read_pre",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    out=M.persistence(None,{},windows,metadata)
    assert out["summary"]["Tminus1_Dungeon_ship_appearances"]==2
    assert out["summary"]["T_positions_unchanged"]==2
    assert out["summary"]["all_Tminus1_stargates_frozen_before_first_T"] is True
    assert events==["pre"]*3+["post"]*3


def test_escorts_compare_all_preselected_colocated_ships(monkeypatch):
    cases={
        M.CASE467:case(),
        (338264,50,204,116):case(g=338264,t=50,a=204,d=116,
            src=(2971,1728),dst=(2971,1727),owner=13),
        (467386,75,215,254):case(a=215,d=254,src=(2380,1484),
            dst=(2380,1483),owner=1),
        (632527,89,106,432):case(g=632527,t=89,a=106,d=432,
            src=(1100,1100),dst=(1200,1200),owner=9),
    }
    events=[]
    def pre(_conn,g,t):
        events.append("pre")
        if g==467386:return {
            467:(6,ship(1141,1459)),80:(6,ship(1126,1439)),
            193:(6,ship(1141,1459,hull=17,warp=9,fuel=1)),
            235:(6,ship(1141,1459,hull=17,warp=9,fuel=1)),
            405:(6,ship(1141,1459,hull=17,warp=9,fuel=1)),
            215:(1,ship(2380,1484)),254:(1,ship(2380,1483)),
        },()
        if g==338264:return {204:(13,ship(2971,1728)),116:(13,ship(2971,1727))},()
        return {106:(9,ship(1100,1100)),432:(9,ship(1200,1200))},()
    def post(_conn,*,game,turn):
        assert events.count("pre")==3
        events.append("post")
        if game==467386:return {
            467:(6,ship(1126,1439,fuel=3)),
            193:(6,ship(1126,1439,hull=17,warp=9,fuel=3)),
            235:(6,ship(1126,1439,hull=17,warp=9,fuel=3)),
            405:(6,ship(1126,1439,hull=17,warp=9,fuel=3)),
            215:(1,ship(2380,1484)),
        }
        if game==338264:return {204:(13,ship(2327,1527))}
        return {106:(9,ship(1100,1100))}
    monkeypatch.setattr(M,"read_pre",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    out=M.escorts(None,cases,(),{})
    assert out["summary"]["Tminus1_distinct_short_edges"]==4
    assert out["summary"]["G467386_T75_467_stack_size"]==4
    assert out["summary"]["G467386_T75_467_stack_owner_current_at_target"]==4
    assert events==["pre"]*3+["post"]*3
    assert all(r["passenger_transport_caused_by_Chunnel_proven"] is False for
        r in out["G467386_T75_467_to_80"]["stack_T_comparisons"])


def test_three_report_manifest_rejects_absent_or_tampered_phase(tmp_path):
    import json
    import hashlib
    with pytest.raises(ValueError,match="missing batched phase"):
        M.make_manifest(tmp_path)
    for ph in M.PHASES:
        (tmp_path/(ph+".json")).write_text(json.dumps({**M.base_record(ph),"summary":{}}),
                                          encoding="utf-8")
    out=M.make_manifest(tmp_path)
    assert out["three_experiments_completed"] is True
    assert len(out["phase_reports"])==3
    assert all(len(x["sha256"])==64 for x in out["phase_reports"].values())
    doc=json.loads((tmp_path/"geometry.json").read_text())
    doc["source_v20_git_blob_sha1"]="wrong"
    (tmp_path/"geometry.json").write_text(json.dumps(doc))
    with pytest.raises(ValueError,match="phase report provenance"):
        M.make_manifest(tmp_path)


def test_one_command_runs_three_phases_then_manifest_with_one_evidence_wrapper():
    runner=ROOT/"tools/run-combat-c5-stabilization-batch-v21.sh"
    wrapper=ROOT/"tools/run-combat-c5-stabilization-batch-v21-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    src=runner.read_text()
    assert "geometry persistence escorts" in src
    assert "--phase manifest" in src
    assert M.V20_BLOB in src and M.V19_BLOB in src and M.GENERATION in src
    assert "/CURRENT" not in src
    w=wrapper.read_text()
    assert "run-with-runtime-evidence.sh" in w
    assert "combat-c5-stabilization-batch-v21" in w
    assert "--include artifacts/combat/c5-stabilization-batch-v21/published" in w
