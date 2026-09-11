from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat_host_candidate_set_audit import _serialize
from combat_host_initial_standard_target_cloak_residual_audit import _basic_cloak_fuel_cost
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, SPECIAL_GAME_ID, _static_specs
from combat_host_privateer_rob_initial_decision_audit import run as run_initial_decision


SCHEMA = "planets-lab.combat-host-privateer-rob-effective-cloak-threshold-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 100


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _prior_cloak(value: Any) -> bool | None:
    if value is True or value == "true":
        return True
    if value is False or value == "false":
        return False
    return None


def _candidate_effective_cloak(
    *,
    prior_iscloaked: bool | None,
    fuel: int | None,
    reference_cost: int | None,
    advanced_cloak: bool,
) -> tuple[bool | None, str]:
    """Evidence-scoped candidate only; not a canonical Host rule.

    The low-fuel attribution runtime supports a strict ordinary-cloak threshold:
    archived prior-true ordinary-cloak rows at or below the reference cost all
    transitioned true->false. Advanced cloak is deliberately unresolved here.
    """

    if prior_iscloaked is False:
        return False, "prior_false"
    if prior_iscloaked is not True:
        return None, "prior_unknown"
    if advanced_cloak:
        return None, "advanced_cloak_unresolved"
    if fuel is None or reference_cost is None:
        return None, "fuel_or_reference_unresolved"
    if fuel <= reference_cost:
        return False, "ordinary_prior_true_at_or_below_reference_cost"
    return True, "ordinary_prior_true_above_reference_cost"


def _expected_blocked_from_initial_classification(classification: Any) -> bool | None:
    """Return only queue-supported decisive labels.

    `initial_skip_target_outranks_factual` is the clean missing-state shape: the
    target should have been selected first if eligible, so factual skipping is
    evidence for a blocker. `initial_pair_vcr` proves the pair was combat-eligible.
    Other queue shapes are not decisive for this blocker differential.
    """

    if classification == "initial_skip_target_outranks_factual":
        return True
    if classification == "initial_pair_vcr":
        return False
    return None


def run(args: argparse.Namespace) -> dict[str, Any]:
    base = run_initial_decision(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )

    specs_by_game: dict[int, Any] = {}
    totals: Counter[str] = Counter()
    decisive: Counter[str] = Counter()
    by_prior: Counter[str] = Counter()
    by_candidate: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for raw_row in base.get("examples", ()):
        if not isinstance(raw_row, Mapping):
            continue
        game_id = int(raw_row["game_id"])
        if game_id == SPECIAL_GAME_ID:
            continue
        if game_id not in specs_by_game:
            archive_path = args.archive_dir / f"game-{game_id}.zip"
            if not archive_path.exists():
                totals["missing_archives"] += 1
                continue
            specs_by_game[game_id] = _static_specs(archive_path.read_bytes())

        target = raw_row.get("target")
        target = target if isinstance(target, Mapping) else {}
        hull_id = _int_value(target.get("hull_id"))
        hull = specs_by_game[game_id].hulls.get(hull_id) if hull_id is not None else None
        hull_mass = _int_value(getattr(hull, "mass", None)) if hull is not None else None
        reference_cost = _basic_cloak_fuel_cost(hull_mass)
        special = str(getattr(hull, "special", "") or "") if hull is not None else ""
        advanced_cloak = "advanced cloak" in special.lower()
        fuel = _int_value(target.get("fuel"))
        prior = _prior_cloak(raw_row.get("target_prior_cloak"))
        margin = fuel - reference_cost if fuel is not None and reference_cost is not None else None

        candidate_cloaked, reason = _candidate_effective_cloak(
            prior_iscloaked=prior,
            fuel=fuel,
            reference_cost=reference_cost,
            advanced_cloak=advanced_cloak,
        )
        candidate_blocked = candidate_cloaked if candidate_cloaked is not None else None

        context = raw_row.get("initial_context")
        context = context if isinstance(context, Mapping) else {}
        classification = context.get("classification")
        expected_blocked = _expected_blocked_from_initial_classification(classification)

        totals["opportunities"] += 1
        prior_label = "true" if prior is True else "false" if prior is False else "unknown"
        by_prior[prior_label] += 1
        by_candidate[
            "blocked" if candidate_blocked is True else "eligible" if candidate_blocked is False else "unresolved"
        ] += 1

        match: bool | None = None
        if expected_blocked is not None:
            totals["decisive_rows"] += 1
            if candidate_blocked is None:
                totals["decisive_unresolved"] += 1
                decisive[f"expected_{'blocked' if expected_blocked else 'eligible'}:unresolved"] += 1
            else:
                match = candidate_blocked == expected_blocked
                totals["decisive_match" if match else "decisive_mismatch"] += 1
                decisive[
                    f"expected_{'blocked' if expected_blocked else 'eligible'}:candidate_"
                    f"{'blocked' if candidate_blocked else 'eligible'}"
                ] += 1
        else:
            totals["nondecisive_rows"] += 1

        row = {
            "game_id": game_id,
            "before_turn": int(raw_row["before_turn"]),
            "battle_turn": int(raw_row["battle_turn"]),
            "target_ship_id": int(raw_row["target_ship_id"]),
            "attacker_ship_id": int(raw_row["attacker_ship_id"]),
            "target_hull_id": hull_id,
            "prior_iscloaked": prior,
            "fuel": fuel,
            "reference_cost": reference_cost,
            "fuel_margin": margin,
            "advanced_cloak": advanced_cloak,
            "candidate_effective_cloak": candidate_cloaked,
            "candidate_blocked": candidate_blocked,
            "candidate_reason": reason,
            "initial_classification": classification,
            "expected_blocked": expected_blocked,
            "decisive_match": match,
            "factual_outcome": raw_row.get("factual_outcome"),
            "target_cloak_transition": raw_row.get("target_cloak_transition"),
            "target_after_identity": raw_row.get("target_after_identity"),
            "is_target_residual": raw_row.get("is_target_residual") is True,
        }
        rows.append(row)

    rows.sort(
        key=lambda item: (
            0 if item["expected_blocked"] is not None else 1,
            0 if item["decisive_match"] is False else 1,
            int(item["game_id"]),
            int(item["battle_turn"]),
            int(item["attacker_ship_id"]),
            int(item["target_ship_id"]),
        )
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "decisive_matrix": _serialize(decisive),
            "by_prior_cloak": _serialize(by_prior),
            "by_candidate_state": _serialize(by_candidate),
            "base_initial_decision_summary": base.get("summary"),
        },
        "rows": rows[: args.example_limit],
        "evidence_boundary": (
            "Read-only differential for one explicit evidence-scoped Privateer Rob effective-cloak candidate. "
            "For ordinary cloak-capable hulls only, archived prior iscloaked=true is treated as combat-effective "
            "only when T-1 fuel is strictly greater than the ordinary cloak reference cost; equality and below are "
            "treated as not effectively cloaked. Prior false is eligible; advanced cloak and unresolved inputs fail "
            "closed to unresolved. The candidate is scored only on queue-decisive initial contexts: a target that "
            "strictly outranks the factual first opponent but is skipped is expected blocked, while an actual initial "
            "pair is expected eligible. Other opportunity shapes are controls, not labels. This diagnostic does not "
            "modify canonical selection or assert Host phase causality."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test an evidence-scoped Privateer Rob effective-cloak fuel threshold against initial combat decisions."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB EFFECTIVE-CLOAK THRESHOLD AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: diagnostic candidate only; no canonical combat blocker has been promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
