"""Documented combat-mass candidate-set audit, not a predictive setter.

Read-only corpus evidence. The right-vs-left-carrier mass bonus is random in
documented Classic rules, so the audit checks an allowable set, never infers
the bonus outcome or uses VCR seed as a Host RNG progression rule.

Does not edit, seed, or call SiteCombatState/site_executor.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for path in (ROOT / "src", DIAGNOSTICS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.data.nu_specs import NuStaticSpecs

import combat_public_capture_o_layer_probe as site_module


SCHEMA = "planets-lab.combat-mass-candidate-audit.v1"
DOCUMENTATION = "https://help.planets.nu/combat-mass"


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def side_combat_mass_candidates(
    *,
    side_name: str,
    side: Mapping[str, Any],
    left: Mapping[str, Any],
    specs: NuStaticSpecs,
) -> dict[str, Any]:
    """Return documented *possible* mass values, not a predicted RNG branch.

    Hull mass is from the game static catalog, not T-1 ship.mass.
    Classic right-vs-left-carrier bonus is a *possible* +360 with 60% chance.
    Federation +50 is a documented candidate based on effective VCR race.
    Other mass modifiers (e.g. Shield Generator) are not reconstructed here.
    """

    hull_id = _integer(side.get("hullid"))
    observed = _integer(side.get("mass"))
    race_id = _integer(side.get("raceid"))
    left_hull = _integer(left.get("hullid"))
    left_bays = _integer(left.get("baycount"))
    left_carrier_candidate = (
        left_hull is not None and left_hull > 0
        and left_bays is not None and left_bays > 0
    )
    hull = specs.hulls.get(hull_id) if hull_id is not None else None

    row: dict[str, Any] = {
        "ship_id": _integer(side.get("objectid")),
        "side": side_name,
        "hull_id": hull_id,
        "vcr_race_id": race_id,
        "factual_combat_mass": observed,
        "hull_catalog_mass": hull.mass if hull is not None else None,
        "left_has_effective_bays": left_carrier_candidate,
        "right_carrier_bonus_eligible_candidate": False,
        "allowed_candidates": [],
        "match": None,
        "status": "unresolved_hull_or_mass",
        "documentation": DOCUMENTATION,
    }
    if hull is None or observed is None or hull_id is None or hull_id <= 0:
        return row
    if side_name not in {"left", "right"}:
        raise ValueError(f"invalid combat side: {side_name!r}")

    base = hull.mass + (50 if race_id == 1 else 0)
    candidates = [
        {
            "scenario": "base_hull_mass_plus_documented_fed_if_applicable",
            "mass": base,
        }
    ]
    eligible = side_name == "right" and hull.mass >= 140 and left_carrier_candidate
    row["right_carrier_bonus_eligible_candidate"] = eligible
    if eligible:
        candidates.append({
            "scenario": "right_vs_left_carrier_random_plus_360",
            "mass": base + 360,
        })
    row["allowed_candidates"] = candidates
    row["match"] = next(
        (entry["scenario"] for entry in candidates if entry["mass"] == observed),
        None,
    )
    row["status"] = (
        "documented_candidate_match"
        if row["match"] is not None else "outside_documented_candidate_set"
    )
    return row


def build_report(
    *,
    game_id: int,
    turn: int,
    cases: Mapping[tuple[int, int], Any],
    specs: NuStaticSpecs,
    database_path: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for (battle_turn, vcr_id), case in sorted(cases.items()):
        if battle_turn != turn:
            continue
        payload = case.payload
        left = payload.get("left") if isinstance(payload, Mapping) else None
        right = payload.get("right") if isinstance(payload, Mapping) else None
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            counts["invalid_payload"] += 1
            continue
        if (
            _integer(left.get("hullid")) is None
            or _integer(right.get("hullid")) is None
        ):
            counts["invalid_hull_ids"] += 1
            continue

        if int(left["hullid"]) <= 0 or int(right["hullid"]) <= 0:
            counts["non_ship_vs_ship"] += 1
            continue

        sides = [
            side_combat_mass_candidates(
                side_name="left", side=left, left=left, specs=specs,
            ),
            side_combat_mass_candidates(
                side_name="right", side=right, left=left, specs=specs,
            ),
        ]
        for row in sides:
            counts[row["status"]] += 1
            if row["right_carrier_bonus_eligible_candidate"]:
                counts["right_carrier_bonus_eligible"] += 1
                if row["match"] == "right_vs_left_carrier_random_plus_360":
                    counts["right_carrier_bonus_observed"] += 1

        rows.append({
            "battle_turn": battle_turn,
            "vcr_id": vcr_id,
            "seed_observed_only": _integer(payload.get("seed")),
            "pair": [sides[0]["ship_id"], sides[1]["ship_id"]],
            "sides": sides,
        })
        counts["ship_vs_ship_vcrs"] += 1

    return {
        "schema": SCHEMA,
        "status": "OBSERVATIONAL_NOT_PROMOTED",
        "game_id": game_id,
        "turn": turn,
        "database_path": database_path,
        "summary": dict(sorted(counts.items())),
        "rows": rows,
        "documented_rules_considered": {
            "ship_combat_mass": "hull catalog base mass",
            "federation_bonus": "+50 (candidate if current VCR raceid=1)",
            "right_vs_left_carrier": (
                "right hull mass >=140, left effective bays >0, "
                "possible +360, documented 60% chance"
            ),
        },
        "evidence_boundary": (
            "Read-only documented candidate SET checked against factual VCR "
            "mass. Hull mass comes from independent static ship catalog, NOT "
            "T-1 loadturn ship.mass. VCR raceid and effective left bays are "
            "current factual inputs; no causal proof of the random branch. "
            "No shield-generator/other mass modifiers reconstructed, and no "
            "mass, seed, side, or other VCR field supplied to an executor. "
            "All VCRs in this turn are observational comparators, not held-out "
            "predictions. O and special mechanics are not promoted."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-db-root", type=Path, required=True)
    parser.add_argument("--corpus-db-generation", required=True)
    parser.add_argument("--game-id", type=int, default=400330)
    parser.add_argument("--turn", type=int, default=141)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        connection, dbpath = connect_compact_generation_read_only(
            args.corpus_db_generation, args.corpus_db_root
        )
        try:
            cases = combat_vcr_cases_for_turns(
                connection, game_id=args.game_id, battle_turns={args.turn}
            )
            targeted = site_module._targeted_db_context(
                connection=connection, game_id=args.game_id,
                battle_turns={args.turn},
            )
            specs = targeted.get("specs")
            if not isinstance(specs, NuStaticSpecs):
                raise ValueError("game hull static specs missing")
            report = build_report(
                game_id=args.game_id, turn=args.turn, cases=cases,
                specs=specs, database_path=str(dbpath),
            )
        finally:
            connection.close()
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("===== DOCUMENTED COMBAT MASS CANDIDATES V1 =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    for row in report["rows"]:
        print(f"V{row['vcr_id']} pair={row['pair']}")
        for s in row["sides"]:
            print(
                f"  {s['side']} ship={s['ship_id']} "
                f"hullmass={s['hull_catalog_mass']} "
                f"observed={s['factual_combat_mass']} "
                f"bonus_eligible={s['right_carrier_bonus_eligible_candidate']} "
                f"match={s['match'] or 'NONE'} "
                f"status={s['status']}"
            )
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
