"""M2 client ship-build price contrasts: synthetic repeats and fail-closed specs."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.data.nu_build_cost_calibration import (
    BuildCostObservation, calibrate_client_build_costs,
    predict_additive_static_build, read_client_build_costs_csv,
)
from planets_lab.data.nu_static import import_static_all
from planets_lab.data.nu_specs import NuStaticSpecs

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = [
    "game", "turn", "is_complete_cost_pair", "tech_change",
    "BuildHullId", "BuildEngineId", "BuildBeamId", "BuildBeamCount",
    "BuildTorpedoId", "BuildTorpCount",
    "spent_MegaCredits", "spent_Duranium", "spent_Tritanium",
    "spent_Molybdenum",
]


def make_rows() -> list[BuildCostObservation]:
    result = []
    # Values are the published *economic test vectors* with synthetic
    # game IDs: actual player captures and IDs are never checked in.
    samples = [
        ("101001", (5, 7, 8, 4, 8, 4), (1190, 104, 75, 235), 10, ""),
        ("101001", (17, 7, 0, 0, 0, 0), (500, 91, 13, 38), 2, ""),
        ("202002", (16, 9, 0, 0, 0, 0), (365, 20, 7, 41), 2, ""),
        ("202002", (4, 9, 2, 4, 4, 4), (802, 56, 37, 131), 2, ""),
        ("202002", (4, 9, 2, 4, 6, 4), (858, 60, 37, 131), 1, ""),
        ("202002", (4, 9, 6, 4, 6, 4), (902, 108, 37, 135), 2, ""),
        ("202002", (4, 9, 6, 4, 6, 4), (3302, 108, 37, 135), 1,
         "EngineTechLevel:7->10;EngineTechUp:0->3"),
    ]
    for game, recipe, costs, n, tech in samples:
        for i in range(n):
            result.append(BuildCostObservation(
                game=game, turn=i + 1,
                hull=recipe[0], engine=recipe[1],
                beam=recipe[2], beam_count=recipe[3],
                launcher=recipe[4], launcher_count=recipe[5],
                spending=costs, tech_change=tech,
            ))
    return result


def csv_file(path: Path, rows: list[BuildCostObservation]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "game": r.game, "turn": r.turn,
                "is_complete_cost_pair": "True", "tech_change": r.tech_change,
                **dict(zip(COLUMNS[4:10], r.recipe)),
                **dict(zip(COLUMNS[10:], r.spending)),
            })


def test_observed_client_contrasts_repeatability_and_nonidentifiability():
    result = calibrate_client_build_costs(make_rows())
    summary = result["summary"]
    assert summary == {
        "complete_client_build_cost_observations": 20,
        "without_recorded_tech_change": 19,
        "with_recorded_tech_change": 1,
        "distinct_game_scoped_recipes": 6,
        "stable_game_scoped_recipes": 6,
        "unstable_recipe_groups": 0,
        "identifiable_one_component_contrasts": 2,
        "NuHost_build_cost_verified": False,
        "Host_execution_verified": False,
    }
    contrast = {
        (x["component"], x["from_id"], x["to_id"]):
        x["per_component_cost_delta"]
        for x in result["component_contrasts"]
    }
    assert contrast == {
        ("Beam", 2, 6):
            {"MegaCredits": 11, "Duranium": 12, "Tritanium": 0, "Molybdenum": 1},
        ("TorpedoLauncher", 4, 6):
            {"MegaCredits": 14, "Duranium": 1, "Tritanium": 0, "Molybdenum": 0},
    }
    upgrade = [
        r for r in result["game_scoped_recipes"]
        if r["tech_change_observations"]
    ][0]["tech_associated_observations"][0]
    assert upgrade["same_recipe_no_tech_change_reference_delta"] == {
        "MegaCredits": 2400, "Duranium": 0,
        "Tritanium": 0, "Molybdenum": 0,
    }
    assert upgrade["status"] == "CLIENT_COMPOUND_TECH_ASSOCIATED_COST_DELTA"
    # The apparent 20 exact observations are only SIX unique recipes.
    # This design is underdetermined even if the additive model is true.
    assert sorted(
        (w["stable_recipes"], w["linear_equation_rank"],
         w["opaque_hull_engine_bundles_plus_beam_launcher_prices"],
         w["unidentified_degrees_of_freedom"])
        for w in result["identifiability"]
    ) == [(2, 2, 4, 2), (4, 4, 6, 2)]
    assert all(
        x["individual_hull_engine_beam_launcher_prices_unique"] is False
        for x in result["identifiability"]
    )


def test_same_recipe_nonconstant_spending_does_not_become_price_evidence():
    obs = make_rows()
    changed = BuildCostObservation(
        game="101001", turn=200, hull=5, engine=7, beam=8,
        beam_count=4, launcher=8, launcher_count=4,
        spending=(1191, 104, 75, 235), tech_change="",
    )
    summary = calibrate_client_build_costs([*obs, changed])
    assert summary["summary"]["unstable_recipe_groups"] == 1
    affected = next(
        x for x in summary["game_scoped_recipes"]
        if x["game"] == "101001" and x["recipe"]["BuildHullId"] == 5
    )
    assert affected["client_total_cost_reference"] is None
    assert affected["status"] == "ABSTAIN_DIFFERENT_SPENDING_FOR_SAME_RECIPE"


def test_component_contrast_never_crosses_game_ids_or_changes_two_components():
    base = BuildCostObservation("101001", 1, 4, 9, 2, 4, 4, 4, (802, 56, 37, 131), "")
    different_game = BuildCostObservation("202002", 1, 4, 9, 6, 4, 4, 4,
                                          (846, 104, 37, 135), "")
    changed_both = BuildCostObservation("101001", 2, 4, 9, 6, 4, 6, 4,
                                        (902, 108, 37, 135), "")
    assert calibrate_client_build_costs([base, different_game, changed_both])[
        "component_contrasts"
    ] == []


def fake_catalog() -> dict:
    return {
        "hulls": [{
            "id": 99, "name": "synthetic", "engines": 1,
            "beams": 4, "launchers": 4, "cost": 600,
            "duranium": 52, "tritanium": 37, "molybdenum": 131,
        }],
        "engines": [{
            "id": 9, "cost": 102, "duranium": 0,
            "tritanium": 0, "molybdenum": 0,
            **{f"warp{i}": 1 for i in range(1, 10)},
        }],
        "beams": [
            {"id": 2, "cost": 10, "duranium": 1, "tritanium": 0, "molybdenum": 0},
            {"id": 6, "cost": 21, "duranium": 13, "tritanium": 0, "molybdenum": 1},
        ],
        "torpedos": [
            {"id": 4, "launchercost": 15, "duranium": 0, "tritanium": 0, "molybdenum": 0},
            {"id": 6, "launchercost": 29, "duranium": 1, "tritanium": 0, "molybdenum": 0},
        ],
    }


def test_additive_static_candidate_explicit_hull_mapping_only():
    specs = NuStaticSpecs.from_catalog(import_static_all(fake_catalog()))
    obs = next(
        x for x in make_rows()
        if x.game == "202002" and x.recipe == (4, 9, 6, 4, 6, 4)
        and not x.tech_change
    )
    assert predict_additive_static_build(obs, specs, global_hull_id=None)["status"] == (
        "ABSTAIN_UNVERIFIED_BUILD_HULL_ID_MAPPING"
    )
    exact = predict_additive_static_build(obs, specs, global_hull_id=99)
    assert exact["status"] == "HYPOTHESIS_STATIC_SUM_EXACT_ON_CLIENT_COST"
    assert exact["candidate_additive_total"] == {
        "MegaCredits": 902, "Duranium": 108,
        "Tritanium": 37, "Molybdenum": 135,
    }
    assert exact["NuHost_formula_verified"] is False
    tech = next(x for x in make_rows() if x.tech_change)
    result = predict_additive_static_build(tech, specs, global_hull_id=99)
    assert result["status"] == "ABSTAIN_COMPOUND_TECH_UPGRADE_COST"
    assert result["residual_observed_minus_candidate"]["MegaCredits"] == 2400
    assert predict_additive_static_build(obs, specs, global_hull_id=9999)[
        "status"
    ] == "ABSTAIN_STATIC_COMPONENT_NOT_FOUND"


def test_offline_cli_reads_bom_csv_and_prints_no_player_id(tmp_path):
    source = tmp_path / "PRIVATE-real-style-observation.csv"
    output = tmp_path / "PRIVATE-calibration.json"
    csv_file(source, make_rows())
    actual = read_client_build_costs_csv(source)
    assert len(actual) == 20
    run = subprocess.run(
        [sys.executable, str(ROOT / "tools/diagnostics/nu_build_cost_calibration_v1.py"),
         "--input", str(source), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert "identifiable_one_component_contrasts: 2" in run.stdout
    assert "NOT_CHECKED_NO_PINNED_STATIC_CATALOG" in run.stdout
    assert "101001" not in run.stdout and "202002" not in run.stdout
    assert json.loads(output.read_text(encoding="utf-8"))["summary"][
        "without_recorded_tech_change"
    ] == 19
    repeat = subprocess.run(
        [sys.executable, str(ROOT / "tools/diagnostics/nu_build_cost_calibration_v1.py"),
         "--input", str(source), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert repeat.returncode != 0  # fail closed on overwrite


def test_optional_static_comparison_requires_sha_and_mapping(tmp_path):
    csv_path = tmp_path / "builds.csv"
    catalog_path = tmp_path / "public-static.json"
    mapping_path = tmp_path / "explicit-ids.json"
    output = tmp_path / "private_result.json"
    rows = [x for x in make_rows() if x.game == "202002" and
            x.recipe == (4, 9, 6, 4, 6, 4) and not x.tech_change]
    csv_file(csv_path, rows)
    data = json.dumps(fake_catalog()).encode()
    catalog_path.write_bytes(data)
    mapping_path.write_text(json.dumps({"202002": {"4": 99}}))
    args = [
        sys.executable, str(ROOT / "tools/diagnostics/nu_build_cost_calibration_v1.py"),
        "--input", str(csv_path), "--catalog", str(catalog_path),
        "--hull-map", str(mapping_path), "--catalog-sha256",
        hashlib.sha256(data).hexdigest(), "--output", str(output),
    ]
    run = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["summary"]["static_hypothesis_status_counts"] == {
        "HYPOTHESIS_STATIC_SUM_EXACT_ON_CLIENT_COST": 2,
    }
    output.unlink()
    args[args.index("--catalog-sha256") + 1] = "0" * 64
    wrong = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert wrong.returncode != 0
    assert not output.exists()


def test_rejects_incomplete_or_malformed_cost_row(tmp_path):
    p = tmp_path / "capture.csv"
    csv_file(p, make_rows()[:1])
    text = p.read_text(encoding="utf-8-sig")
    p.write_text(text.replace("1190,104,75,235", "-1,104,75,235"), encoding="utf-8")
    with pytest.raises(ValueError, match="unsigned"):
        read_client_build_costs_csv(p)
