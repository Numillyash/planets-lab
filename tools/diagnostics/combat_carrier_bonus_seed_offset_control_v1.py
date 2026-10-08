"""Bounded counterexample check: VCR seed, Classic table, anti-carrier +360.

Read-only frozen factual observations. Test every constant offset against
both 60%-style threshold orientations. No search result is promoted as
a universal RNG law, and no Host-global state is reconstructed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from planets_lab.rules.combat.classic import RANDOM_1_100, RANDOM_SIZE

SCHEMA = "planets-lab.carrier-bonus-seed-offset-control.v1"


def audit_fixed_offsets(fixture: Mapping[str, Any]) -> dict[str, Any]:
    if fixture.get("schema") != "planets-lab.carrier-bonus-seed-offset-observations.v1":
        raise ValueError("unexpected mass bonus fixture schema")
    rows = fixture.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("fixture observations missing")
    seeds_and_outcomes: list[tuple[int, bool]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("malformed row")
        seed=row.get("vcr_seed")
        bonus=row.get("bonus_360")
        hull_mass=row.get("hull_mass")
        observed_mass=row.get("observed_mass")
        if (
            isinstance(seed, bool) or not isinstance(seed, int)
            or seed < 1 or seed > RANDOM_SIZE
            or not isinstance(bonus, bool)
            or isinstance(hull_mass, bool) or not isinstance(hull_mass,int)
            or isinstance(observed_mass,bool) or not isinstance(observed_mass,int)
            or observed_mass != hull_mass + (360 if bonus else 0)
        ):
            raise ValueError("fixture source observation invalid")
        seeds_and_outcomes.append((seed,bonus))

    hypotheses = {}
    for rule, condition in (
        ("table_value_le_60", lambda n: n <= 60),
        ("table_value_ge_41", lambda n: n >= 41),
    ):
        results = []
        for offset in range(RANDOM_SIZE):
            hits=0
            for seed, observed_bonus in seeds_and_outcomes:
                value=RANDOM_1_100[(seed + offset - 1) % RANDOM_SIZE]
                hits += (condition(value) == observed_bonus)
            results.append({"offset":offset, "hits":hits})
        best=max(r["hits"] for r in results)
        hypotheses[rule]={
            "candidate_offsets_119": RANDOM_SIZE,
            "exact_offsets": [r["offset"] for r in results if r["hits"]==len(rows)],
            "best_matched_rows":best,
            "offsets_at_best":[r["offset"] for r in results if r["hits"]==best],
        }

    return {
        "schema":SCHEMA,
        "status":"OBSERVATIONAL_NOT_PROMOTED",
        "fixture_source":fixture.get("source"),
        "observations":len(rows),
        "positive_360":sum(b for _,b in seeds_and_outcomes),
        "no_bonus":sum(not b for _,b in seeds_and_outcomes),
        "hypotheses":hypotheses,
        "evidence_boundary":(
            "Only rejects a constant cyclic offset into the within-VCR "
            "Classic random table with one threshold orientation. It does "
            "not exclude Host-global RNG, differing draw counts, or a "
            "distinct random generator. The observed outcome labels and "
            "seeds come from the same T141 factual VCR corpus; there is "
            "no held-out prediction."
        ),
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--fixture",type=Path,required=True)
    p.add_argument("--output",type=Path,default=None)
    args=p.parse_args()
    try:
        report=audit_fixed_offsets(json.loads(args.fixture.read_text(encoding="utf-8")))
    except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("===== CARRIER BONUS SEED OFFSET CONTROL V1 =====")
    print("status:",report["status"])
    print("observations:",report["observations"])
    print("positives:",report["positive_360"])
    for name,summary in report["hypotheses"].items():
        print(f"{name}: exact_offsets={summary['exact_offsets']} best={summary['best_matched_rows']}/{report['observations']}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
