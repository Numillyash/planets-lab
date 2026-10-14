from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_site_disjoint_movement_validation_v9.py"
SPEC=importlib.util.spec_from_file_location("c5_disjoint_movement_v9",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def test_metadata_only_game_selection_is_site_disjoint_and_deterministic():
    # No VCRs, ships, coordinates or T outcomes are exposed to this selector.
    rows=[(g,t) for g in range(1,29) for t in range(1,9)]
    excluded=frozenset(range(1,18))
    result=M.select_holdout_windows(rows,excluded)
    assert result==M.select_holdout_windows(list(reversed(rows)),excluded)
    assert len(result)==16
    assert len({g for g,_ in result})==8
    assert all(g not in excluded and t>=2 for g,t in result)
    assert len(result)==len(set(result))
    with pytest.raises(ValueError,match="insufficient C5-disjoint"):
        M.select_holdout_windows([(1,2),(1,3),(2,2),(2,3)],frozenset({1}))
    with pytest.raises(ValueError,match="malformed"):
        M.select_holdout_windows([(1,True)],frozenset())


def v6_identity():
    # 27 frozen site IDs, 17 pre-existing games.
    sites=[{"game_id":(i%17)+1,"turn":20,"x":150+i,"y":205+i}
           for i in range(27)]
    return {"sites":sites}


def test_frozen_protocol_excludes_all_c5_game_ids():
    excluded=M.c5_games(v6_identity())
    assert excluded==frozenset(range(1,18))
    sites=v6_identity()
    sites["sites"].append(dict(sites["sites"][0]))
    with pytest.raises(ValueError,match="population changed"):
        M.c5_games(sites)


def test_heldout_forecasts_freeze_completely_before_any_T_comparators(monkeypatch):
    events=[]
    class Conn:
        def execute(self,query):
            assert "source_members" in query
            assert "vcr" not in query.lower()
            events.append("metadata")
            return self
        def fetchall(self):
            return [(game,turn) for game in range(101,121)
                    for turn in (1,2,3,4,5)]
    def pre(conn,*,game,before):
        events.append("pre")
        return (("pre",),("pre",))
    def forecast(game,turn,_snap,_raw):
        events.append("forecast")
        rows=[{
            "game_id":game,"before_turn":turn-1,"after_turn":turn,
            "ship_id":sid,"Tminus1_owner_id":10,"Tminus1_hull_id":35,
            "Tminus1_source":"normal_move",
            "cohort":M.NORMAL,
            "conditional_or_model_endpoint":[15,25],
            "frozen_v7_witness":False,"conditional_no_mine_only":False,
        } for sid in range(1,11)]
        return rows,Counter(),10
    def post(conn,*,game,turn):
        assert events.count("forecast")==16  # ALL pre forecasts before first T
        events.append("after")
        return {sid:(10,{"x":15,"y":25,"hullid":35}) for sid in range(1,11)}
    monkeypatch.setattr(M,"pre_snapshots",pre)
    monkeypatch.setattr(M,"forecast_pre_window",forecast)
    monkeypatch.setattr(M,"after_owner_current",post)
    report=M.build_report(Conn(),v6_identity())
    assert report["summary"]["selected_games"]==8
    assert report["summary"]["selected_windows"]==16
    assert report["summary"]["selected_games_overlap_with_C5"]==0
    assert report["summary"]["pre_forecast_rows"]==160
    assert report["summary"]["posthost_compared_rows"]==160
    assert report["summary"]["cohort_posthost_status_counts"][M.NORMAL]=={
        "POSTHOST_ENDPOINT_MATCH":160}
    assert report["summary"]["Nplus1_VCR_read"] is False
    assert report["summary"]["new_Host_combat_predictions"]==0
    assert events.index("after")>max(i for i,e in enumerate(events) if e=="forecast")


def test_tminus1_normal_planner_mine_risk_never_promoted(monkeypatch):
    before=34
    monkeypatch.setattr(M,"resolve_pre_context",lambda *_args,**_kw:{
        "specs":object(),"planets":(),"warp_wells_enabled":False,
        "eligible_warp_well_planet_ids":frozenset(),
        "topology":SimpleNamespace(sphere=False),
        "storms":(),"nuionstorms":False,"mine_context":object()})
    monkeypatch.setattr(M,"group_perspective_records",lambda *_args,_kind=None:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_args:{
        1:(10,{"hullid":35,"x":10,"y":20}),
        2:(10,{"hullid":35,"x":30,"y":40}),
    })
    monkeypatch.setattr(M,"_player_races",lambda *_args:({10:4},{}))
    monkeypatch.setattr(M,"_tow_target_ids",lambda *_:frozenset())
    monkeypatch.setattr(M,"_potential_chunnel_source_sites",lambda *_:frozenset())
    monkeypatch.setattr(M,"_inbound_transfer_targets",lambda *_:frozenset())
    monkeypatch.setattr(M,"_normal_position_prediction",
        lambda **kwargs:((101,201),"normal_move"))
    monkeypatch.setattr(M,"_foreign_mine_route_risk",
        lambda **kwargs:"normal_mine_route_risk" if kwargs["raw"]["x"]==10 else None)
    rows,excluded,seen=M.forecast_pre_window(42,before+1,(),())
    assert seen==2 and not excluded
    assert [r["cohort"] for r in rows]==[M.MINE,M.NORMAL]
    assert rows[0]["conditional_or_model_endpoint"]==[101,201]
    assert rows[0]["conditional_no_mine_only"] is True
    assert rows[1]["conditional_no_mine_only"] is False


def test_pre_forecast_rejects_conflicting_exact_tminus1_static(monkeypatch):
    # Every T-1 archive perspective must agree on hull/engine specs.
    pre=[SimpleNamespace(member=SimpleNamespace(name=f"owner-{i}.trn"))
         for i in (1,2)]
    monkeypatch.setattr(M,"import_static_all",lambda raw:raw)
    class Specs:
        def __init__(self,i):
            self.hulls={1:i}
            self.engines={1:"engine"}
        @staticmethod
        def from_catalog(raw):
            return Specs(raw["catalog_mass"])
    monkeypatch.setattr(M,"NuStaticSpecs",Specs)
    with pytest.raises(ValueError,match="conflicting exact Tminus1 static"):
        M.resolve_pre_context(1,4,pre,(
            {"catalog_mass":96},{"catalog_mass":46}
        ))


def test_runner_evidence_and_pinned_db():
    script=ROOT/"tools/run-combat-c5-site-disjoint-movement-validation-v9.sh"
    wrapper=ROOT/"tools/run-combat-c5-site-disjoint-movement-validation-v9-with-evidence.sh"
    subprocess.run(["bash","-n",str(script)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert M.V6_BLOB in script.read_text()
    assert M.GENERATION in script.read_text()
    assert "/CURRENT" not in script.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
