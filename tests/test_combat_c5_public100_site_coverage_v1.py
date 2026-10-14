from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"tools/diagnostics/combat_c5_public100_site_coverage_v1.py"
SPEC=importlib.util.spec_from_file_location("c5_site_coverage",SRC)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def raw_vcr(vid=12,left=11,right=22,*,x=1,y=2,race=3,
            right_race=4,planet=False):
    return {"id":vid,"x":x,"y":y,"leftownerid":1,"rightownerid":2,
            "left":{"objectid":left,"hullid":95,"raceid":race,"mass":185},
            "right":{"objectid":right,"hullid":0 if planet else 35,
                     "raceid":right_race,"mass":120}}


def observed(v):
    return {"vcr_id":v["id"],"payload":v,"shape":M.classify_vcr(v)}


def test_preselection_deterministic_evenly_spaced_and_no_vcr_body_access():
    p=[(game,turn) for game in range(100,110)
       for turn in range(10,51,5)]
    frozen,meta=M.freeze_windows(p,max_games=4)
    assert meta["selected_games"]==[100,103,106,109]
    assert meta["selection_inputs"].startswith("source_members")
    assert len(frozen)==8
    assert frozen[0]["cohort"]=="EARLY_QUINTILE"
    assert frozen[1]["cohort"]=="LATE_85TH_PERCENTILE"
    assert frozen[0]["turn"]<frozen[1]["turn"]
    # Archive-only metadata never selects by VCR result/mass; no keys for it.
    assert set(frozen[0])=={
        "game_id","turn","cohort","eligible_archived_turns"}
    with pytest.raises(ValueError):
        M.freeze_windows([(0,5)])
    with pytest.raises(ValueError):
        M.freeze_windows([(100,5)],max_games=0)


def test_ship_planet_horwasp_and_malformed_scope_are_explicit():
    assert M.classify_vcr(raw_vcr())=="ORDINARY_SHIP_VS_SHIP"
    assert M.classify_vcr(raw_vcr(planet=True))=="ORDINARY_SHIP_VS_PLANET_CANDIDATE"
    assert M.classify_vcr(raw_vcr(race=12))=="OUT_OF_SCOPE_HORWASP_RACE12"
    assert M.classify_vcr(raw_vcr(right_race=12))=="OUT_OF_SCOPE_HORWASP_RACE12"
    assert M.classify_vcr({"left":None,"right":None})=="ABSTAIN_MALFORMED_VCR_PARTICIPANTS"
    wrong=raw_vcr();wrong["leftownerid"]=None
    assert M.classify_vcr(wrong)=="ABSTAIN_INVALID_LEFT_SHIP_IDENTITY"
    other=raw_vcr();other["rightownerid"]=None
    assert M.classify_vcr(other)=="ABSTAIN_INVALID_RIGHT_SHIP_OWNER"


def test_multiple_ships_repetition_and_gap_count_are_observational():
    r=M.site_population([observed(raw_vcr(10,left=11,right=22)),
                         observed(raw_vcr(11,left=11,right=33)),
                         observed(raw_vcr(14,left=44,right=22))])
    site=r["sites"][0]
    assert site["category"]=="ORDINARY_SHIP_ONLY_MULTIVCR_SITE"
    assert site["all_vcr_ids"]==[10,11,14]
    assert site["observed_ship_VCR_ID_adjacent_pairs"]==1
    assert site["repeated_same_owner_ship_by_VCR_ID"]=={
        "1:11":[10,11],"2:22":[10,14]}
    assert site["queue_pairs_predicted"]==0
    assert site["Host_combat_order_proven"] is False


def test_dont_hide_mixed_planet_horwasp_or_missing_sites():
    p=[observed(raw_vcr(1,x=10,y=10)),
       observed(raw_vcr(2,planet=True,x=10,y=10)),
       observed(raw_vcr(3,race=12,x=20,y=20)),
       observed(raw_vcr(4,x=None,y=20))]
    r=M.site_population(p)
    cats={s["category"] for s in r["sites"]}
    assert "ORDINARY_MIXED_SHIP_PLANET_SITE" in cats
    assert "OUT_OF_SCOPE_HORWASP_SITE" in cats
    assert r["unlocatable_vcr_ids"]==[4]
    assert not any(s["candidate_multi_ship_site"] for s in r["sites"])


def make_history(*ships,owner=1,turn=100,game=999):
    ref=SimpleNamespace(game_id=game,archive_turn=turn-1,
                        embedded_turn=turn-1,perspective_player_id=owner)
    return ref,{"game":{"id":game,"turn":turn-1},"ships":list(ships)}


def record(ship,owner=1,mission=0,enemy=2):
    return {"id":ship,"ownerid":owner,"hullid":94,"mission":mission,
            "enemy":enemy,"friendlycode":"abc"}


def test_tminus1_owner_perspectives_consensus_and_missing_abstain(monkeypatch):
    data=[
        make_history(record(11)),
        make_history(record(11),owner=1),
        make_history(record(22,owner=2),owner=2),
    ]
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**kw:[r for r,m in data])
    monkeypatch.setattr(M,"reconstruct_members",lambda conn,refs:data)
    report=M.tminus1_owner_coverage(
        object(),game=999,turn=100,
        ships=[(1,11),(2,22),(3,33)])
    assert report["owner_ship_order_statuses"]=={
        "TMINUS1_OWNER_ORDER_CONSENSUS":2,
        "ABSTAIN_NO_TMINUS1_OWNER_PERSPECTIVE":1,
    }
    assert len(report["observed_ship_identity_targets"])==3
    data[1]=make_history(record(11,mission=7))
    disputed=M.tminus1_owner_coverage(
        object(),game=999,turn=100,ships=[(1,11)])
    assert disputed["owner_ship_order_statuses"]=={
        "ABSTAIN_OWNER_ORDER_MISSING_OR_CONFLICTING":1}


def test_tminus1_provenance_invalid_is_not_silently_accepted(monkeypatch):
    ref,member=make_history(record(11))
    ref.archive_turn=100
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**kw:[ref])
    monkeypatch.setattr(M,"reconstruct_members",lambda conn,refs:[(ref,member)])
    with pytest.raises(ValueError,match="provenance drift"):
        M.tminus1_owner_coverage(
            object(),game=999,turn=100,ships=[(1,11)])


def test_inspect_window_preserves_no_ship_vcr_and_mixed_cases(monkeypatch):
    rows=[raw_vcr(10,planet=True),raw_vcr(11)]
    cases={(15,x["id"]):SimpleNamespace(payload=x) for x in rows}
    monkeypatch.setattr(M,"combat_vcr_cases_for_turns",lambda *a,**kw:cases)
    called=[]
    def fake_owner(conn,*,game,turn,ships):
        called.append(list(ships))
        return {"member_perspectives":1,"owner_ship_order_statuses":{},
                "observed_ship_identity_targets":[]}
    monkeypatch.setattr(M,"tminus1_owner_coverage",fake_owner)
    w=M.inspect_window(object(),{"game_id":9,"turn":15,"cohort":"EARLY_QUINTILE"})
    assert w["all_vcrs"]==2
    assert w["multi_ordinary_ship_site_count"]==0
    assert w["shape_counts"]["ORDINARY_SHIP_VS_SHIP"]==1
    assert w["shape_counts"]["ORDINARY_SHIP_VS_PLANET_CANDIDATE"]==1
    assert called==[[(1,11),(2,22)]]
    assert w["predicted_next_VCR_pairs"]==0


def test_fixed_runner_and_evidence_script_shell_syntax():
    runner=ROOT/"tools/run-combat-c5-public100-site-coverage-v1.sh"
    wrapper=ROOT/"tools/run-combat-c5-public100-site-coverage-v1-with-evidence.sh"
    for path in (runner,wrapper):
        subprocess.run(["bash","-n",str(path)],check=True)
    assert "CURRENT" not in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "combat_c5_public100_site_coverage_v1.py" in runner.read_text()
