from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
DIAG=ROOT/"tools"/"diagnostics"
if str(DIAG) not in sys.path:
    sys.path.insert(0,str(DIAG))
SPEC=importlib.util.spec_from_file_location(
    "combat_mass_temporal_static_identity_v2",
    DIAG/"combat_mass_temporal_static_identity_v2.py",
)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _ref(t,p=4,n=None):
    return SimpleNamespace(
        archive_turn=t,embedded_turn=t,perspective_player_id=p,
        member_id=n if n is not None else t*100+p,
        source_member_name=f"player{p}-turn{t}.trn",
        decoded_payload_sha256="a"*64,
    )


def _member(mass):
    return {"hulls":[{"id":39,"mass":96,"name":"D19b"},
                     {"id":1039,"mass":mass,"name":"D19c","parentid":39,
                      "engines":1,"cargo":40}]}


def test_single_hull_record_preserved_and_hullsall_not_fabricated():
    raw=M._records(_member(46))
    assert raw["hulls"]["records"][0]["mass"]==46
    assert raw["hullsall"]["status"]=="MISSING_COLLECTION"
    assert M._single_hull_mass(_member(96))==96
    with pytest.raises(ValueError,match="multiple static hull"):
        M._single_hull_mass({"hulls":[
            {"id":1039,"mass":96},{"id":1039,"mass":46}
        ]})


def test_owner_static_time_series_finds_switch_without_using_vcr_mass(monkeypatch):
    refs=[_ref(t) for t in range(0,5)]
    refs.extend([_ref(3,p=2),_ref(4,p=3)])
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**k:refs)
    monkeypatch.setattr(M,"reconstruct_members",lambda db,chosen:(
        (r,_member(96 if r.archive_turn<=1 else 46))
        for r in chosen
    ))
    data=M.temporal_static_rows(conn=object(),game=217591,owner=4,last_turn=4)
    assert data["T0_owner_static_mass_values"]==[96]
    assert data["Tminus1_owner_static_mass_values"]==[46]
    assert [(x["mass"],x["first_observed_turn"],x["last_observed_turn"])
            for x in data["transition_segments_in_member_order"]]==[
                (96,0,1),(46,2,4)
            ]
    assert len(data["all_owner_static_history"])==5
    assert data["conflicting_owner_static_same_turn"]==[]


def test_multiple_owner_samples_conflict_is_retained(monkeypatch):
    refs=[_ref(0),_ref(1),_ref(1,n=1010),_ref(2)]
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**k:refs)
    monkeypatch.setattr(M,"reconstruct_members",lambda db,chosen:(
        (r,_member(96 if r.member_id!=1010 else 46))
        for r in chosen
    ))
    report=M.temporal_static_rows(conn=object(),game=1,owner=4,last_turn=2)
    assert report["conflicting_owner_static_same_turn"][0]["archive_turn"]==1


def test_rush_id_may_change_hull_and_owner_but_not_engine_continuity():
    case={
        "archive_snapshots":[
            {"provenance":{"archive_turn":200,"member_id":111,"perspective_player_id":1},
             "perspective_is_owner":False,
             "target":{"target_ships":[{"id":27,"hullid":94,"ownerid":5,"engineid":0}]}},
            {"provenance":{"archive_turn":201,"member_id":222,"perspective_player_id":4},
             "perspective_is_owner":True,
             "target":{"target_ships":[{"id":27,"hullid":35,"ownerid":4,"engineid":9}]}},
        ],
    }
    states=M.archive_ship_id_states(case)
    assert states[0]["engine_id"] is None
    assert states[0]["engine_id_masked_or_untrusted_from_foreign_perspective"]
    assert states[1]["engine_id"]==9
    assert states[1]["hull_id"]==35
    assert states[0]["hull_id"]==94


def test_vcr_id_history_keeps_distinct_hulls(monkeypatch):
    def vc(t,mass,hull,owner):
        return SimpleNamespace(
            vcr_id=t*10+1,observation_count=1,
            payload={
                "left":{"objectid":27,"hullid":hull,"raceid":4,"mass":mass},
                "right":{"objectid":88,"hullid":35,"mass":451},
                "leftownerid":owner,"rightownerid":5,
                "x":1455,"y":2615,
            },
        )
    monkeypatch.setattr(M,"combat_vcr_cases_for_turns",
                        lambda db,game_id,battle_turns:{
                            (t,t*10+1):vc(t,795,94,4) for t in battle_turns
                        })
    hist=M.vcr_id_history(conn=object(),game=617883,turn=201,ship_id=27)
    assert len(hist["vcr_appearances"])==3
    assert [a["turn"] for a in hist["vcr_appearances"]]==[200,201,202]
    assert all(a["hull_id"]==94 for a in hist["vcr_appearances"])


def test_pinned_shell_runners_and_publish():
    runner=ROOT/"tools"/"run-combat-mass-temporal-static-identity-v2.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-temporal-static-identity-v2-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    source=runner.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in source
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in source
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
