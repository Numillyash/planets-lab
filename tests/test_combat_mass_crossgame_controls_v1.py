from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "tools" / "diagnostics"
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))

SOURCE = DIR / "combat_mass_crossgame_controls_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_mass_crossgame_controls_v1", SOURCE)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def _specs():
    return SimpleNamespace(
        hulls={
            70: SimpleNamespace(name="Gorbie", mass=980, cargo_capacity=500),
            2006: SimpleNamespace(name="Wild Banshee", mass=120, cargo_capacity=100),
            117: SimpleNamespace(name="Brood", mass=145, cargo_capacity=900),
            47: SimpleNamespace(name="Red Wind", mass=70, cargo_capacity=200),
        }
    )


def _ship(ship_id, hull, race, mass, bays):
    return {
        "objectid":ship_id, "hullid":hull, "raceid":race,
        "mass":mass, "baycount":bays,
    }


def test_fed_effective_threshold_candidate_separate_from_documented_hull_threshold() -> None:
    left=_ship(16,70,8,980,10)
    right=_ship(220,2006,1,530,0)
    value=M._side(
        side_name="right",side=right,left=left,specs=_specs()
    )
    assert value["hull_mass"]==120
    assert value["federation_adjusted_base"]==170
    assert value["factual_mass"]==530
    assert value["original_candidates"]==[170]
    assert value["adjusted_threshold_candidates"]==[170,530]
    assert value["hull_threshold_bonus_eligible"] is False
    assert value["adjusted_threshold_bonus_eligible"] is True
    assert value["category"]=="federation_adjusted_threshold_candidate"

    # Non-Federation 120 KT ship still never crosses the threshold.
    under=M._side(
        side_name="right",
        side=_ship(221,2006,5,120,0),
        left=left,specs=_specs(),
    )
    assert under["original_candidates"]==[120]
    assert under["adjusted_threshold_candidates"]==[120]
    assert under["category"]=="classic_hull_threshold"


def test_horwasp_double_mass_is_endpoint_only_not_general_formula() -> None:
    left=_ship(346,47,3,70,2)
    right=_ship(48,117,12,290,6)
    result=M._side(
        side_name="right",side=right,left=left,specs=_specs()
    )
    assert result["hull_mass"]==145
    assert result["horwasp_full_load_endpoint"]==290
    assert result["horwasp_cargo_capacity"]==900
    assert result["original_candidates"]==[145,505]
    assert result["category"]=="horwasp_full_load_endpoint_candidate"

    partial=M._side(
        side_name="right",side=_ship(48,117,12,200,6),
        left=left,specs=_specs()
    )
    assert partial["category"]=="unresolved_mass_residual"


def test_no_modifiers_no_carrier_stays_classic() -> None:
    left=_ship(346,47,3,70,2)
    value=M._side(
        side_name="left",side=left,left=left,specs=_specs()
    )
    assert value["original_candidates"]==[70]
    assert value["category"]=="classic_hull_threshold"


def test_precombat_clans_owner_perspective_not_non_owner() -> None:
    def make_member(clans):
        return {
            "ships":[{"id":48,"ownerid":12,"hullid":117,"clans":clans,"mass":1197}]
        }
    refs=[
        (SimpleNamespace(archive_turn=81,perspective_player_id=3),make_member(0)),
        (SimpleNamespace(archive_turn=81,perspective_player_id=12),make_member(900)),
    ]
    import builtins
    source=M._brood_before_turn_context
    class Dummy:
        def __init__(self):self.refs=refs
    # Patch imports at module level to simulate corpus source.
    old_refs=M.member_refs_for_turns
    old_reconstruct=M.reconstruct_members
    M.member_refs_for_turns=lambda *a,**kw:["dummy"]
    M.reconstruct_members=lambda *a,**kw:iter(refs)
    try:
        result=source(Dummy(),_specs())
    finally:
        M.member_refs_for_turns=old_refs
        M.reconstruct_members=old_reconstruct
    assert len(result["owner_perspective_rows"])==1
    assert result["owner_perspective_rows"][0]["observed_clans"]==900
    assert result["owner_perspective_rows"][0]["observed_full_load_at_tminus1"] is True


def test_invalid_hull_fails_closed() -> None:
    with pytest.raises(ValueError,match="hull"):
        M._side(
            side_name="left",
            side=_ship(1,999,1,170,0),
            left=_ship(1,999,1,170,0),specs=_specs(),
        )


def test_runner_bash_and_explicit_relative_public100() -> None:
    runner=ROOT/"tools"/"run-combat-mass-crossgame-controls-v1.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-crossgame-controls-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    script=runner.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$GENERATION"' in script
    assert '--corpus-db-generation "$DB"' not in script
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in script
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
