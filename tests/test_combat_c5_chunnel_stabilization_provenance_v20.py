from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_chunnel_stabilization_provenance_v20.py"
SPEC=importlib.util.spec_from_file_location("c5_stabilization_v20",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def ship(x,y,*,hull=56,engine=9,owner=6):
    return {"x":x,"y":y,"hullid":hull,"engineid":engine,
            "warp":0,"neutronium":100}


def edges():
    data=[
        (221008,100,78,443,(100,100),(100,100)),
        (227887,72,441,413,(100,100),(100,100)),
        (227887,72,512,152,(100,100),(100,100)),
        (338264,50,204,116,(2971,1728),(2971,1727)),
        (373830,38,407,129,(100,100),(100,100)),
        (467386,75,215,254,(2380,1484),(2380,1483)),
        (467386,75,467,80,(1141,1459),(1126,1439)),
        (467386,221,142,496,(100,100),(100,100)),
        (521834,34,200,265,(100,100),(100,100)),
        (632527,60,69,286,(100,100),(100,100)),
        (632527,60,509,99,(100,100),(100,100)),
        (632527,89,88,199,(100,100),(100,100)),
        (632527,89,106,432,(100,100),(110,127)),
    ]
    return [{
        "game_id":g,"turn":t,"initiator_ship_id":a,"target_ship_id":b,
        "owner_id":6 if a==467 else 13,
        "source":list(src),"target":list(dst),
        "cohort":"ONE_TMINUS1_GATE_FAILS",
        "single_failing_gate":M.SHORT_GATE,
        "Tminus1_source_target_distinct":src!=dst,
        "Tminus1_source_differs_from_target":src!=dst,
        "Tminus1_distance_ly":25 if a==467 else 1 if src!=dst else 0,
        "T_actor_status":"T_ACTOR_AT_DISTINCT_FROZEN_TARGET",
        "T_actor_position":list(dst),
        "Host_Chunnel_activation_or_inactivation_proven":False,
    } for g,t,a,b,src,dst in data]


def test_documented_stargate_field_radius():
    roster={
        1:(6,ship(1141,1459,hull=108,engine=1)),
        2:(6,ship(1200,1500,hull=108,engine=9)),
        3:(6,ship(1300,1500,hull=108,engine=0)),
    }
    seen=M.stabilizer_inventory(roster,{108:"Dungeon Class Stargate"})
    assert [x["documentation_field_radius_ly"] for x in seen]==[150,550,None]
    assert all(x["archived_catalog_name_confirms_dungeon_stargate"] for x in seen)
    assert all(x["Tminus1_field_activation_verified"] is False for x in seen)
    nonstock=M.stabilizer_inventory(roster,{108:"Unrelated hull"})
    assert all(x["documentation_field_radius_ly"] is None for x in nonstock)


def test_unknown_game_settings_cannot_be_interpreted_as_disabled():
    src=[{"game":{"id":467386,"turn":74},
          "settings":{"name":"secret-game-name","password":"secret",
                      "shortformatrules":True,"nowarpwells":False},
          "player":{"id":6,"raceid":6},
          "players":[{"id":6,"raceid":6}]}]
    m,r=M.game_rules_markers(src,467386,75)
    assert m["settings.shortformatrules"] is True and r[6]==6
    assert not any("password" in key or "name" in key for key in m)
    alt=[{"game":{"id":467386,"turn":74},"settings":{"password":"secret"},
          "players":[{"id":6,"raceid":6}]}]
    m,r=M.game_rules_markers(alt,467386,75)
    assert "settings.shortformatrules" not in m and r[6]==6
    with pytest.raises(ValueError,match="conflicting"):
        M.game_rules_markers([src[0],{**src[0],"settings":{"shortformatrules":False}}],467386,75)


def test_frozen_short_edge_race6_with_explicit_short_rule(monkeypatch):
    rows={467:(6,ship(1141,1459)),80:(6,ship(1126,1439))}
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *_args,**_kw:
        ((),({"game":{"id":467386,"turn":74},
             "settings":{"shortformatrules":True},
             "players":[{"id":6,"raceid":6}],
             "hulls":[{"id":56,"name":"Firecloud"}]},)))
    monkeypatch.setattr(M,"group_perspective_records",lambda *_:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_:rows)
    case=next(x for x in edges() if x["initiator_ship_id"]==467)
    result=M.freeze_window(None,467386,75,{
        (467386,75,467,80):case})
    x=result["Tminus1_short_edge_features"][0]
    assert x["Tminus1_explicit_short_format_rule_flag"] is True
    assert x["Tminus1_stabilization_coverage_status"]=="TMINUS1_EXPLICIT_SHORT_FORMAT_FIELD_FLAG_FOR_CYBORG"


def test_dungeon_field_coverage_distinct_from_proven_activation(monkeypatch):
    r={467:(6,ship(1141,1459)),80:(6,ship(1126,1439)),
       100:(6,ship(1150,1450,hull=108,engine=1))}
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *_args,**_kw:
        ((),({"game":{"id":467386,"turn":74},
             "players":[{"id":6,"raceid":6}],
             "hulls":[{"id":56,"name":"Firecloud"},{"id":108,"name":"Dungeon Class Stargate"}]},)))
    monkeypatch.setattr(M,"group_perspective_records",lambda *_:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_:r)
    source=next(e for e in edges() if e["initiator_ship_id"]==467)
    out=M.freeze_window(None,467386,75,{(467386,75,467,80):source})
    e=out["Tminus1_short_edge_features"][0]
    assert e["Tminus1_stabilization_coverage_status"]=="TMINUS1_STARGATE_FIELD_POSSIBLE_WITHIN_DOCUMENTED_RADIUS"
    assert len(e["Tminus1_documented_stabilizer_coverage_candidates"])==1
    assert e["Tminus1_documented_stabilizer_coverage_candidates"][0]["field_active_at_Chunnel_phase_proven"] is False


def test_final_T_source_replay_cannot_change_frozen_case():
    c=next(e for e in edges() if e["initiator_ship_id"]==467)
    frozen={
        "Tminus1_short_edge_features":[{
            "game_id":467386,"turn":75,"initiator_ship_id":467,
            "target_ship_id":80,"owner_id":6,"Tminus1_target":[1126,1439],
            "Tminus1_source_target_distinct":True,
        }]
    }
    cases={(467386,75,467,80):c}
    good=M.compare_posthost(frozen,{467:(6,ship(1126,1439))},cases)
    assert good[0]["T_actor_at_distinct_Tminus1_target"] is True
    assert good[0]["actual_host_stabilization_or_short_Chunnel_proven"] is False
    with pytest.raises(ValueError,match="coordinate drift"):
        M.compare_posthost(frozen,{467:(6,ship(1141,1459))},cases)


def test_original_thirteen_reselected_without_posthost_positions():
    vals=edges()
    windows={}
    for x in vals:
        windows.setdefault((x["game_id"],x["turn"]),[]).append(x)
    source={
        "schema":M.v17.SCHEMA,"status":M.v17.STATUS,
        "source_db_sha256":M.SHA256,
        "summary":{"candidate_stock_firecloud_edges":113,
                   "selected_window_count":48,"Nplus1_VCR_used":False},
        "windows":[{"game_id":g,"turn":t,"edges":xs} for (g,t),xs in windows.items()]
                 +[{"game_id":900+i,"turn":10,"edges":[]} for i in range(39)],
    }
    other={
        "schema":M.v19.SCHEMA,"status":M.v19.STATUS,
        "source_v17_git_blob_sha1":M.V17_BLOB,
        "source_db_sha256":M.SHA256,
        "summary":{"Tminus1_eligible_short_to_long_graph_chains":2,
                   "G467386_T75_467_to_80_has_outgoing_eligible_long_edge":False,
                   "Nplus1_VCR_used":False},
    }
    assert len(windows)==9
    cases,selected=M.preselect(source,other)
    assert len(cases)==13 and len(selected)==9
    source["windows"][0]["edges"][0]["Host_Chunnel_activation_or_inactivation_proven"]=True
    with pytest.raises(ValueError,match="identity corrupted"):
        M.preselect(source,other)


def test_runner_pins_and_corpus_current_unchanged():
    runner=ROOT/"tools/run-combat-c5-chunnel-stabilization-provenance-v20.sh"
    wrapper=ROOT/"tools/run-combat-c5-chunnel-stabilization-provenance-v20-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    text=runner.read_text()
    assert M.V17_BLOB in text and M.V19_BLOB in text
    assert M.GENERATION in text and "/CURRENT" not in text
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
