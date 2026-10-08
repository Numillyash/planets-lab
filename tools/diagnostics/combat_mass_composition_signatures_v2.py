"""Pure, read-only post-processing of frozen public100 mass-control evidence.

This is an additive *numeric signature* classifier. It is not a recovered
Host formula: Shield Generator counts/position, Horwasp precombat clans and
Fed threshold ordering are unresolved. No candidate is wired to the executor.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA = "planets-lab.combat-mass-composition-signatures.v2"
INPUT_SCHEMA = "planets-lab.combat-mass-crossgame-controls.v1"


def classify_side(side: Mapping[str, Any]) -> dict[str, Any]:
    """Classify without creating numerical mass rules or changing input."""
    required = (
        "category", "race_id", "hull_mass", "federation_adjusted_base",
        "factual_mass", "side", "left_carrier_observed", "hull_id", "ship_id",
    )
    if any(key not in side for key in required):
        raise ValueError("mass side is missing required provenance fields")
    for key in ("race_id", "hull_mass", "federation_adjusted_base",
                "factual_mass", "hull_id", "ship_id"):
        value = side[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"invalid mass side integer {key}")
    if side["side"] not in ("left", "right"):
        raise ValueError("invalid side name")
    if not isinstance(side["left_carrier_observed"], bool):
        raise ValueError("invalid observed left carrier flag")
    hull = side["hull_mass"]
    base = side["federation_adjusted_base"]
    actual = side["factual_mass"]
    race = side["race_id"]
    on_right_against_carrier = (
        side["side"] == "right" and side["left_carrier_observed"]
    )
    adjusted_eligible = on_right_against_carrier and base >= 140
    prefix = {
        "category_before": side["category"],
        "race_id": race, "ship_id": side["ship_id"],
        "hull_id": side["hull_id"], "side": side["side"],
        "hull_mass": hull, "base_mass": base, "factual_mass": actual,
        "delta_from_base": actual-base,
    }
    # Preserve original matching outcomes rather than re-labelling them as
    # discovered new Host mechanics.
    if side["category"] == "classic_hull_threshold":
        status = "original_classic_candidate"
        arithmetic = "existing_hull_fed_and_right_carrier_set"
    elif side["category"] == "federation_adjusted_threshold_candidate":
        status = "fed_threshold_ordering_hypothesis"
        arithmetic = "federation_base_plus_360"
    elif side["category"] == "horwasp_full_load_endpoint_candidate":
        status = "horwasp_full_cargo_endpoint_candidate"
        arithmetic = "two_times_hull_mass"
    elif race == 12:
        if on_right_against_carrier and 2*hull >= 140 and actual == 2*hull+360:
            status = "horwasp_double_plus_360_candidate"
            arithmetic = "two_times_hull_plus_360"
        elif hull < actual < 2*hull:
            status = "horwasp_partial_load_numeric_candidate"
            arithmetic = "between_hull_and_two_times_hull"
        elif (on_right_against_carrier and 2*hull>=140
              and hull < actual-360 < 2*hull):
            status = "horwasp_partial_plus_360_numeric_candidate"
            arithmetic = "between_hull_and_two_times_hull_plus_360"
        else:
            status = "unresolved_nonadditive"
            arithmetic = None
    else:
        difference = actual-base
        # This 150 KT per generator holds ONLY for Transwarp Drive 9.
        # We have not independently observed effective engine type or number
        # of co-located Shield Generators at the time of combat.
        possible: list[tuple[str, int]] = [
            ("one_transwarp_shield_generator_numeric_candidate",150),
            ("two_transwarp_shield_generators_numeric_candidate",300),
        ]
        if adjusted_eligible:
            possible.extend([
                ("one_generator_plus_360_numeric_candidate",510),
                ("two_generators_plus_360_numeric_candidate",660),
            ])
        found = next((label for label, delta in possible if difference==delta),None)
        status = found if found is not None else "unresolved_nonadditive"
        arithmetic = (
            "hypothetical_transwarp_generator_additivity"
            if found is not None else None
        )
    return {
        **prefix, "signature": status, "arithmetic": arithmetic,
        "candidate_only": status not in (
            "original_classic_candidate",
        ),
        "evidence_boundary": (
            "Numerical equality is NOT independent observation of "
            "Shield Generator presence, engine type, precombat Horwasp "
            "clans, or the +360 RNG branch. Do not promote these patterns "
            "to Host mechanics."
        ),
    }


def build_signature_report(
    original: Mapping[str, Any], *,
    source_path: str,
    max_examples_per_signature: int = 6,
) -> dict[str, Any]:
    if original.get("schema") != INPUT_SCHEMA:
        raise ValueError("wrong mass input schema")
    original_summary = original.get("summary")
    turns = original.get("per_turn")
    if not isinstance(original_summary, Mapping) or not isinstance(turns, list):
        raise ValueError("original mass evidence incomplete")
    if max_examples_per_signature < 1:
        raise ValueError("invalid example bound")

    signature_count: Counter[str] = Counter()
    per_game: defaultdict[str, Counter[str]] = defaultdict(Counter)
    per_race: defaultdict[str, Counter[str]] = defaultdict(Counter)
    examples: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    side_count = 0
    ship_vcrs = 0
    for record in turns:
        if not isinstance(record, Mapping) or not isinstance(record.get("rows"),list):
            raise ValueError("malformed per-turn data")
        for vcr in record["rows"]:
            sides = vcr.get("sides")
            if not isinstance(sides,list) or len(sides)!=2:
                raise ValueError("expected 2 ship sides per factual VCR")
            ship_vcrs += 1
            for side in sides:
                item = classify_side(side)
                side_count += 1
                category=item["signature"]
                signature_count[category] += 1
                per_game[str(record["game_id"])][category] += 1
                per_race[str(item["race_id"])][category] += 1
                if len(examples[category]) < max_examples_per_signature:
                    examples[category].append({
                        "game_id":record["game_id"], "turn":record["turn"],
                        "vcr_id":vcr["vcr_id"], **{
                            k:item[k] for k in (
                                "side","ship_id","race_id","hull_id",
                                "hull_mass","base_mass","factual_mass",
                                "delta_from_base","arithmetic"
                            )
                        },
                    })
    if side_count != 2*ship_vcrs:
        raise ValueError("ship sides have inconsistent total")
    if original_summary.get("ship_vs_ship_vcrs_compared") != ship_vcrs:
        raise ValueError("original counted VCRs mismatch")
    original_counts = {
        key: original_summary.get(key,0)
        for key in (
            "classic_hull_threshold",
            "federation_adjusted_threshold_candidate",
            "horwasp_full_load_endpoint_candidate",
            "unresolved_mass_residual",
        )
    }
    if sum(original_counts.values()) != side_count:
        raise ValueError("original side categories do not sum to all sides")
    retained_unexplained = signature_count["unresolved_nonadditive"]
    return {
        "schema":SCHEMA,
        "status":"OBSERVATIONAL_NUMERIC_SIGNATURES_NOT_PROMOTED",
        "source_input_path":source_path,
        "original_schema":INPUT_SCHEMA,
        "original_summary":dict(original_counts),
        "summary":{
            "turns_checked":len(turns),
            "ship_vs_ship_vcrs":ship_vcrs,
            "ship_side_observations":side_count,
            "original_unresolved_mass_sides":original_counts["unresolved_mass_residual"],
            "remaining_unresolved_numeric_sides":retained_unexplained,
            "newly_grouped_as_numeric_candidates":(
                original_counts["unresolved_mass_residual"]-retained_unexplained
            ),
        },
        "numeric_signature_counts":dict(sorted(signature_count.items())),
        "by_race":{
            k:dict(sorted(v.items())) for k,v in sorted(per_race.items(),key=lambda x:int(x[0]))
        },
        "by_game":{
            k:dict(sorted(v.items())) for k,v in sorted(per_game.items(),key=lambda x:int(x[0]))
        },
        "examples_by_signature":dict(sorted(examples.items())),
        "references":[
            "https://help.planets.nu/combat-mass",
            "https://help.planets.nu/abil-shield-generator",
            "https://help.planets.nu/horwasp-ships",
        ],
        "evidence_boundary":(
            "All categories are numerical comparisons of OBSERVED factual "
            "VCR masses with existing hull catalog masses. Only source-v1 "
            "Classic/endpoint labels are retained; additive patterns do not "
            "prove effective engine tech, active Shield Generators, precombat "
            "clans, current-side eligibility, or any RNG decision. This is "
            "not a predictive or generative mass projection."
        ),
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        report=build_signature_report(
            json.loads(args.input.read_text(encoding="utf-8")),
            source_path=str(args.input),
        )
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc)
        return 2
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("===== COMBAT MASS COMPOSITION SIGNATURES V2 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("signatures:",report["numeric_signature_counts"])
    for key,examples in report["examples_by_signature"].items():
        if key in ("original_classic_candidate","horwasp_full_cargo_endpoint_candidate"):
            continue
        print("  ",key,examples[:2])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
