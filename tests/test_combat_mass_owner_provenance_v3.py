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
SOURCE=DIAG/"combat_mass_owner_provenance_v3.py"
SPEC=importlib.util.spec_from_file_location("combat_mass_owner_provenance_v3", SOURCE)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _example(vcr=100, ship=48, mass=290, signature="unresolved_nonadditive"):
    return {"game_id":217591,"turn":149,"vcr_id":vcr,
            "ship_id":ship,"hull_id":117,"factual_mass":mass,
            "side":"right","signature":signature}


def _summary():
    return {
        "schema":M.SOURCE,
        "examples_by_signature":{
            "unresolved_nonadditive":[_example(i,i,290) for i in range(100,106)],
            "two_transwarp_shield_generators_numeric_candidate":[
                _example(200,200,751)],
        },
    }


def test_select_exact_six_unresolved_plus_bounded_controls():
    selected=M.select_observations(_summary())
    assert len(selected)==7
    assert sum(x["signature"]=="unresolved_nonadditive" for x in selected)==6
    assert selected[-1]["signature"]=="two_transwarp_shield_generators_numeric_candidate"
    bad=_summary()
    bad["examples_by_signature"]["unresolved_nonadditive"].pop()
    with pytest.raises(ValueError,match="six unresolved"):
        M.select_observations(bad)


def _specs():
    return SimpleNamespace(
        hulls={
            117:SimpleNamespace(mass=125,cargo_capacity=900,
                name="Brood",special=""),
            1041:SimpleNamespace(mass=173,cargo_capacity=50,
                name="Saber Class Shield Generator",special="Shield Generator"),
        },
        engines={
            9:SimpleNamespace(name="Transwarp",cost=SimpleNamespace(megacredits=300)),
        },
    )


def test_owner_snapshot_tracks_engine_clans_and_generator_without_promoting_phase():
    refs=[
        SimpleNamespace(archive_turn=148,perspective_player_id=12),
        SimpleNamespace(archive_turn=148,perspective_player_id=8),
    ]
    member={
        "ships":[
            {"id":48,"ownerid":12,"hullid":117,"engineid":9,
             "clans":900,"x":20,"y":30},
            {"id":88,"ownerid":12,"hullid":1041,"x":20,"y":30},
            {"id":89,"ownerid":12,"hullid":1041,"x":20,"y":31},
        ]
    }
    items=M.owner_evidence(
        members=[(refs[0],member),(refs[1],member)],
        owner_id=12,ship_id=48,site=(20,30),specs=_specs(),
    )
    assert len(items)==1
    row=items[0]
    assert row["participant"]["clans"]==900
    assert row["participant"]["clans_fraction_of_catalog_capacity"]==1
    assert row["participant"]["numeric_shield_bonus_half_engine_cost"]==150
    assert row["owner_shield_generator_inventory_count"]==2
    assert len(row["owner_shield_generators_at_vcr_coordinates"])==1
    assert "not precombat" in row["temporal_boundary"]


def test_report_rejects_factual_vcr_identity_mismatch(monkeypatch):
    examples=_summary()
    monkeypatch.setattr(M,"_independent_hull_specs",
                        lambda conn,gid:_specs())
    monkeypatch.setattr(
        M,"combat_vcr_cases_for_turns",
        lambda *a,**kw:{
            (149,vcr):SimpleNamespace(payload={
                "leftownerid":8,"rightownerid":12,
                "right":{"objectid":vcr,"hullid":117,
                         "mass":290 if vcr!=104 else 291},
                "x":20,"y":30,
            }) for vcr in list(range(100,106))+[200]
        }
    )
    monkeypatch.setattr(M,"member_refs_for_turns",lambda *a,**kw:[])
    monkeypatch.setattr(M,"reconstruct_members",lambda *a,**kw:iter(()))
    with pytest.raises(ValueError,match="conflicts with frozen signature"):
        M.build_report(object(),examples,"/tmp/synthetic.duckdb")


def test_shell_runners_use_explicit_sha_pinned_public100():
    runner=ROOT/"tools"/"run-combat-mass-owner-provenance-v3.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-owner-provenance-v3-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    contents=runner.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in contents
    assert '--corpus-db-generation "$DB"' not in contents
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in contents
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
