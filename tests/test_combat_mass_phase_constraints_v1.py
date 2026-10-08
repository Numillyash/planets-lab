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
SCRIPT=DIAG/"combat_mass_phase_constraints_v1.py"
SPEC=importlib.util.spec_from_file_location("combat_mass_phase_constraints_v1",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _specs():
    return SimpleNamespace(
        hulls={
            117:SimpleNamespace(mass=145,cargo_capacity=900,name="Brood",special=""),
            115:SimpleNamespace(mass=475,cargo_capacity=24000,name="Hive",special=""),
            39:SimpleNamespace(mass=96,cargo_capacity=40,name="D19b",special=""),
            1041:SimpleNamespace(mass=180,cargo_capacity=100,
                                 name="Saber Shield Generator",special="Shield Generator"),
        }
    )


def _vcr(vcr_id,mass,fighters,site=(20,30),side="right",bays=6):
    brood={"objectid":48,"raceid":12,"hullid":117,"mass":mass,
           "fighters":fighters,"baycount":6,"damage":0}
    opponent={"objectid":346,"raceid":3,"hullid":39,"mass":96,"baycount":bays}
    return ((82,vcr_id),SimpleNamespace(payload={
        "x":site[0],"y":site[1],
        "left":opponent if side=="right" else brood,
        "right":brood if side=="right" else opponent,
    }))


def test_inverse_mass_integer_interval_at_287_is_882_to_887():
    assert M.inverse_clan_interval(287,145,900)==[882,887]
    assert M.inverse_clan_interval(290,145,900)==[900,900]
    assert M.inverse_clan_interval(650,145,900,360)==[900,900]
    assert M.inverse_clan_interval(200,145,900,360) is None


def test_partial_hive_clans_and_catalog_mismatch_explicit():
    assert M.inverse_clan_interval(628,475,24000) is not None
    assert 7752 in range(
        M.inverse_clan_interval(628,475,24000)[0],
        M.inverse_clan_interval(628,475,24000)[1]+1,
    )
    vals=M.mass_intervals(
        observed=290,hull_mass=125,capacity=900,
        hull_id=117,side="left",left_bays=6,
    )
    assert [v["base_source"] for v in vals]==["EXTERNAL_BROOD_145_UNVERIFIED"]
    assert vals[0]["possible_clans"]==[900,900]


def test_carrier_branch_must_have_right_side_and_actual_left_bays():
    args=dict(observed=650,hull_mass=145,capacity=900,hull_id=117)
    assert M.mass_intervals(side="left",left_bays=6,**args)==[]
    assert M.mass_intervals(side="right",left_bays=0,**args)==[]
    good=M.mass_intervals(side="right",left_bays=6,**args)
    assert good[0]["carrier_plus360_branch"]==360


def test_horwasp_sequence_constrains_loss_without_fabricating_terminal():
    cases=dict([
        _vcr(611,290,70),
        _vcr(614,650,70),
        _vcr(618,287,68),
    ])
    seq=M.sequence(
        game=253449,turn=82,ship_id=48,cases=cases,
        specs=_specs(),owner_tminus1_clans=900,
    )
    assert len(seq["events"])==3
    assert len(seq["transitions"])==2
    assert seq["events"][1]["candidate_intervals"][0]["possible_clans"]==[900,900]
    last=seq["transitions"][-1]
    assert last["same_site"] is True
    assert last["vcr_id_gap"]==4
    assert last["observed_fighter_start_delta"]==-2
    assert last["possible_clan_loss_ranges"]==[
        {
            "base_source":"game_static_catalog",
            "possible_clan_loss_min":13,
            "possible_clan_loss_max":18,
            "loss_nonnegative_possible":True,
            "branch_before":360,
            "branch_after":0,
        }
    ]


def test_generator_waypoints_not_conflated_with_actual_movement():
    specs=_specs()
    members=[(
        SimpleNamespace(archive_turn=148,perspective_player_id=4),
        {"ships":[
            {"id":262,"ownerid":4,"hullid":39,"x":15,"y":30,"targetx":20,"targety":30,"warp":7},
            {"id":6,"ownerid":4,"hullid":1041,"x":15,"y":30,"targetx":20,"targety":30,"warp":7},
            {"id":386,"ownerid":4,"hullid":1041,"x":20,"y":30,"targetx":20,"targety":30,"warp":0},
            {"id":999,"ownerid":3,"hullid":1041,"x":20,"y":30,"targetx":20,"targety":30,"warp":0},
        ]}
    )]
    out=M.shield_route_context(
        members=members,owner=4,site=(20,30),ship_ids={262},specs=specs
    )
    assert len(out)==1
    s=out[0]
    assert s["total_generators"]==2
    assert s["at_site_tminus1"]==1
    assert s["waypoint_to_site"]==2
    assert s["combat_ships"][0]["at_site_in_snapshot"] is False
    assert s["combat_ships"][0]["waypoint_is_site"] is True
    assert s["owner_generators"][0]["waypoint_is_site"] is True


def test_missing_fields_and_bounds_fail_closed():
    with pytest.raises(ValueError):
        M.inverse_clan_interval(True,145,900)
    with pytest.raises(ValueError):
        M.inverse_clan_interval(287,145,0)
    with pytest.raises(ValueError,match="wrong v3"):
        M.build_report(db=None,source={"schema":"bad"},dbpath="db")


def test_shell_runners_pin_relative_public100_and_publish_evidence():
    runner=ROOT/"tools"/"run-combat-mass-phase-constraints-v1.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-phase-constraints-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    source=runner.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in source
    assert '--corpus-db-generation "$DB"' not in source
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in source
    assert "--v3-input" in source
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
