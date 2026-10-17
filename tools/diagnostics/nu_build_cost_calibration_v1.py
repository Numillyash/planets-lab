#!/usr/bin/env python3
"""Compare locally observed Planets.nu client build spending with hypotheses.

Basic (no static catalog needed):
  python tools/diagnostics/nu_build_cost_calibration_v1.py \
      --input /private/starbase_build_costs.csv \
      --output /private/client_build_calibration.json

Optional independently pinned *public* /static/all snapshot:
  ... --catalog /private/static_all.json --catalog-sha256 <64-hex-digest> \
      --hull-map /private/explicit_game_hull_mapping.json

Mapping JSON: {"<game-id>":{"<client-BuildHullId>":<catalog-global-hull-id>}}
Do not infer the mapping from equal numerical IDs. Full results include
private game IDs and MUST NOT be committed. No network API calls occur.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from planets_lab.data.nu_build_cost_calibration import (
    calibrate_client_build_costs, predict_additive_static_build,
    read_client_build_costs_csv,
)
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all


def _load_static(path: Path, expected_sha: str) -> tuple[NuStaticSpecs, dict]:
    if len(expected_sha) != 64 or any(c not in "0123456789abcdef" for c in expected_sha.lower()):
        raise ValueError("catalog SHA256 must be exactly 64 hex digits")
    raw = path.read_bytes()
    if sha256(raw).hexdigest().lower() != expected_sha.lower():
        raise ValueError("catalog SHA256 mismatch; refuse to compare")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("static catalog must be a JSON object")
    return NuStaticSpecs.from_catalog(import_static_all(payload)), payload


def _complete_static_price(raw: dict, collection: str, component_id: int) -> bool:
    values = raw.get(collection)
    if not isinstance(values, list):
        return False
    found = [
        item for item in values
        if isinstance(item, dict) and str(item.get("id")) == str(component_id)
    ]
    if len(found) != 1:
        return False
    obj = found[0]
    if not all(key in obj for key in ("duranium", "tritanium", "molybdenum")):
        return False
    if not ("cost" in obj or (collection == "torpedos" and "launchercost" in obj)):
        return False
    if collection == "hulls" and not all(k in obj for k in ("engines", "beams", "launchers")):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Optional PRIVATE JSON result")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--catalog-sha256", type=str)
    parser.add_argument("--hull-map", type=Path)
    args = parser.parse_args()
    if any(x is not None for x in (args.catalog, args.catalog_sha256, args.hull_map)):
        if not all(x is not None for x in (args.catalog, args.catalog_sha256, args.hull_map)):
            parser.error("--catalog, --catalog-sha256 and --hull-map must all be supplied")

    rows = read_client_build_costs_csv(args.input)
    report = calibrate_client_build_costs(rows)

    if args.catalog:
        specs, raw = _load_static(args.catalog, args.catalog_sha256)
        mapping = json.loads(args.hull_map.read_text(encoding="utf-8"))
        if not isinstance(mapping, dict):
            raise ValueError("hull-map must be an object")
        comparison = []
        for row in rows:
            idmap = mapping.get(row.game)
            candidate = idmap.get(str(row.hull)) if isinstance(idmap, dict) else None
            if type(candidate) is not int or candidate <= 0:
                result = {"status": "ABSTAIN_UNVERIFIED_BUILD_HULL_ID_MAPPING"}
            elif not all([
                _complete_static_price(raw, "hulls", candidate),
                _complete_static_price(raw, "engines", row.engine),
                not row.beam_count or _complete_static_price(raw, "beams", row.beam),
                not row.launcher_count or _complete_static_price(raw, "torpedos", row.launcher),
            ]):
                result = {"status": "ABSTAIN_INCOMPLETE_STATIC_CATALOG"}
            else:
                result = predict_additive_static_build(
                    row, specs, global_hull_id=candidate
                )
            comparison.append({
                "game": row.game, "turn": row.turn,
                "recipe": dict(zip(
                    ("BuildHullId", "BuildEngineId", "BuildBeamId",
                     "BuildBeamCount", "BuildTorpedoId", "BuildTorpCount"),
                    row.recipe,
                )),
                "result": result,
            })
        report["pinned_catalog_sha256"] = args.catalog_sha256.lower()
        report["static_component_sum_comparison"] = comparison
        report["summary"]["static_hypothesis_status_counts"] = dict(sorted(
            Counter(x["result"]["status"] for x in comparison).items()
        ))
    else:
        report["summary"]["static_hypothesis_status"] = "NOT_CHECKED_NO_PINNED_STATIC_CATALOG"

    summary = report["summary"]
    print(f"status: {report['status']}")
    for key in (
        "complete_client_build_cost_observations",
        "without_recorded_tech_change",
        "with_recorded_tech_change",
        "distinct_game_scoped_recipes",
        "stable_game_scoped_recipes",
        "unstable_recipe_groups",
        "identifiable_one_component_contrasts",
    ):
        print(f"{key}: {summary[key]}")
    if args.catalog:
        for status, count in summary["static_hypothesis_status_counts"].items():
            print(f"static_{status}: {count}")
    else:
        print("static_hypothesis_status: NOT_CHECKED_NO_PINNED_STATIC_CATALOG")
    print("NuHost_build_cost_verified: False")
    if args.output:
        if args.output.resolve() in {p.resolve() for p in (args.input, args.catalog, args.hull_map) if p is not None}:
            parser.error("output must not overwrite input/catalog/mapping")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(report, target, ensure_ascii=False, indent=2)
            target.write("\n")
        print("Private calibration report written; do not commit it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
