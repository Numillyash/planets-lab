from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"tools"/"diagnostics"
if str(D) not in sys.path:
    sys.path.insert(0,str(D))
SPEC=importlib.util.spec_from_file_location(
    "combat_mass_catalog_owner_provenance_v1",
    D/"combat_mass_catalog_owner_provenance_v1.py")
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def source():
    rows=[
        {"game_id":217591,"turn":75,"vcr_id":756,"side":"right"},
        {"game_id":325434,"turn":149,"vcr_id":1075,"side":"left"},
        {"game_id":617883,"turn":201,"vcr_id":1017,"side":"left"},
    ]
    return {
        "schema":M.SOURCE_SCHEMA,
        "D19c_source_conflicts":rows[:2],
        "unresolved_cases":rows[2:],
    }


def test_exact_case_identity_and_uniqueness_gate():
    assert len(M.select_cases(source()))==3
    doc=source()
    doc["D19c_source_conflicts"][0]["vcr_id"]=9999
    with pytest.raises(ValueError,match="identity mismatch"):
        M.select_cases(doc)
    doc=source()
    doc["unresolved_cases"][0]=dict(doc["D19c_source_conflicts"][0])
    with pytest.raises(ValueError,match="duplicate"):
        M.select_cases(doc)


def test_static_collections_keep_hulls_vs_hullsall_separate():
    member={
        "hulls":[
            {"id":39,"mass":96,"name":"D19b"},
            {"id":1039,"mass":96,"name":"D19c","parentid":39,"cargo":40},
            {"id":2000,"mass":999},
        ],
        "hullsall":[
            {"id":1039,"mass":46,"name":"D19c","parentid":39}
        ],
    }
    rows=M.static_collection_rows(member)
    assert rows["hulls"]["records"][1]["mass"]==96
    assert rows["hullsall"]["records"][0]["mass"]==46
    assert rows["hulls"]["total_records"]==3
    assert M._static_compare([{"static":rows}])["observed_raw_masses_by_collection_and_hull_id"]=={
        "hulls:1039":[96],"hulls:39":[96],"hullsall:1039":[46],
    }


def test_missing_static_is_missing_not_assumed_equal():
    result=M.static_collection_rows({"hulls":[]})
    assert result["hulls"]["collection_status"]=="PRESENT"
    assert result["hullsall"]["collection_status"]=="MISSING"
    with pytest.raises(ValueError,match="not a list"):
        M.static_collection_rows({"hulls":{}})


def test_owner_ship_snapshot_and_same_owner_generator_candidate():
    specs=SimpleNamespace(
        hulls={
            1039:SimpleNamespace(name="D19c",special="Glory Device"),
            1041:SimpleNamespace(name="Saber Shield Generator",
                                 special="Shield Generator")
        },
        engines={9:SimpleNamespace(cost=SimpleNamespace(megacredits=300))},
    )
    member={"ships":[
        {"id":274,"ownerid":4,"hullid":1039,"engineid":9,"x":10,"y":20,
         "targetx":30,"targety":40},
        {"id":15,"ownerid":4,"hullid":1041,"x":10,"y":20},
        {"id":16,"ownerid":5,"hullid":1041,"x":10,"y":20},
        {"id":17,"ownerid":4,"hullid":1041,"x":11,"y":20},
    ]}
    result=M.participant_snapshot(
        member,target_ship=274,target_owner=4,specs=specs)
    assert result["target_ship_seen"]
    row=result["target_ships"][0]
    assert row["engine_mc_cost_from_first_member_catalog"]==300
    assert row["same_owner_shield_generator_ids_at_snapshot_ship_xy"]==[15]
    assert M.participant_snapshot(
        {"ships":[]},target_ship=274,target_owner=4,specs=specs
    )["target_ships"]==[]
    assert M.participant_snapshot(
        {"other":[]},target_ship=274,target_owner=4,specs=specs
    )["ship_list_status"]=="UNAVAILABLE"


def test_archive_snapshot_scope_owner_and_peer_cap():
    refs=[]
    for t in (200,201,202):
        for owner in (4,5,6,7,8):
            refs.append(SimpleNamespace(archive_turn=t,perspective_player_id=owner))
    chosen,scope=M.snapshot_selection(refs,owner=4,turn=201)
    assert scope["owner_source_members_available_by_turn"]=={200:1,201:1,202:1}
    assert sum(r.archive_turn==200 for r in chosen)==4
    assert sum(r.archive_turn==201 for r in chosen)==4
    assert sum(r.archive_turn==202 for r in chosen)==1


def test_frozen_runner_pin_and_evidence_wrapper():
    runner=ROOT/"tools"/"run-combat-mass-catalog-owner-provenance-v1.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-catalog-owner-provenance-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    a=runner.read_text(encoding="utf-8")
    b=wrapper.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in a
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in a
    assert "mass-rulebook-reconciliation-v2/published/report.json" in a
    assert "run-with-runtime-evidence.sh" in b
    assert "--include artifacts/combat/mass-catalog-owner-provenance-v1/published" in b
