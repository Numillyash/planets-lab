from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))
SOURCE = DIAGNOSTICS / "combat_site_payload_provenance_v1.py"
SPEC = importlib.util.spec_from_file_location("site_payload_provenance_v1", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
RUNNER = REPO_ROOT / "tools" / "run-site-combat-payload-provenance-v1.sh"
WRAPPER = REPO_ROOT / "tools" / "run-site-combat-payload-provenance-v1-with-evidence.sh"


def _prediction(*, ammo=20, torps=2, bays=0):
    return {
        "owner_id": 10,
        "source": "normal_move",
        "raw": {
            "hullid": 89,
            "beams": 4,
            "beamid": 5,
            "torpedoid": 10,
            "torps": torps,
            "bays": bays,
            "mass": 231,
            "ammo": ammo,
        },
    }


def _side(*, ship_id=140, ammo=20):
    return {
        "objectid": ship_id,
        "hullid": 89,
        "beamid": 5,
        "torpedoid": 10,
        "beamcount": 4,
        "launchercount": 2,
        "baycount": 0,
        "mass": 250,
        "torpedos": ammo,
        "fighters": 0,
        "beamkillbonus": 1,
        "beamchargerate": 1,
        "torpchargerate": 1,
        "torpmisspercent": 35,
        "crewdefensepercent": 0,
    }


def test_side_provenance_is_observational_and_classifies_mass_delta() -> None:
    row = MODULE.side_provenance(
        side_name="right", vcr_side=_side(), prediction=_prediction()
    )
    fields = {item["field"]: item for item in row["direct_field_observations"]}
    assert fields["hullid"]["status"] == "observed_equal"
    assert fields["torpedos"]["status"] == "observed_equal"
    assert fields["mass"]["status"] == "observed_different"
    assert fields["mass"]["delta_current_minus_tminus1"] == 19
    assert all(
        item["classification"] == "unresolved_host_combat_setup"
        for item in row["host_rate_fields"]
    )


def test_missing_and_hybrid_ammo_fail_as_unresolved_not_zero() -> None:
    missing = MODULE.side_provenance(
        side_name="left", vcr_side=_side(), prediction=None
    )
    assert missing["tminus1_ammo_classification"] == "missing_tminus1_ammo"
    assert next(
        x for x in missing["direct_field_observations"]
        if x["field"] == "torpedos"
    )["status"] == "unresolved_prior"

    invalid = MODULE.side_provenance(
        side_name="left", vcr_side=_side(),
        prediction=_prediction(ammo="n/a"),
    )
    assert invalid["tminus1_ammo_classification"] == "invalid_tminus1_ammo"

    hybrid = MODULE.side_provenance(
        side_name="left", vcr_side=_side(), prediction=_prediction(bays=2)
    )
    assert hybrid["tminus1_ammo_classification"] == "ambiguous_nu_ammo"
    assert next(
        x for x in hybrid["direct_field_observations"]
        if x["field"] == "fighters"
    )["status"] == "unresolved_prior"


def test_report_rejects_unrelated_site_vcr_and_retains_seed_as_fact() -> None:
    case = SimpleNamespace(
        payload={
            "seed": 51,
            "battletype": 1,
            "left": _side(ship_id=140),
            "right": _side(ship_id=170),
        },
        beams=(), torpedoes=(), settings={"combatrng": 0},
        observation_count=2,
    )
    context = {
        "x": 1674, "y": 2363,
        "predictions": {140: _prediction(), 170: _prediction()},
        "factual_queue": [{"vcr_id": 592, "pair": (140, 170)}],
    }
    report = MODULE.build_report(
        context=context, cases={(141, 592): case},
        game_id=400330, turn=141, vcr_ids=(592,),
        database_path="/tmp/fake.duckdb",
    )
    assert report["status"] == "OBSERVATIONAL_NOT_PROMOTED"
    assert report["summary"]["seed_observations"] == [
        {"vcr_id": 592, "seed": 51}
    ]

    context["factual_queue"] = [{"vcr_id": 592, "pair": (140, 184)}]
    import pytest
    with pytest.raises(ValueError, match="target-site pair mismatch"):
        MODULE.build_report(
            context=context, cases={(141, 592): case},
            game_id=400330, turn=141, vcr_ids=(592,),
            database_path="/tmp/fake.duckdb",
        )


def test_provenance_scripts_are_shell_valid_and_use_relative_public100() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    source = RUNNER.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert '--corpus-db-generation "$PUBLIC100_REL"' in source
    assert '--corpus-db-generation "$DB"' not in source
    assert r"\\${" not in source
    assert r"\\${" not in wrapper
    assert "run-with-runtime-evidence.sh" in wrapper
