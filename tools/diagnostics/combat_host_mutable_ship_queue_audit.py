from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.rules.combat.mutable_queue import apply_ship_terminal_batch

import combat_ship_chain_audit as chain_module
from combat_host_priority_intercept_audit import SPECIAL_GAME_ID


SCHEMA = "planets-lab.combat-host-mutable-ship-queue-audit.v1"


def _ordinary_archive_paths(args: argparse.Namespace) -> list[Path]:
    """Return the ordinary corpus, keeping game 591478 out of promotion gates."""

    raw_paths = (
        [Path(value) for value in args.archive]
        if getattr(args, "archive", None)
        else sorted(args.archive_dir.glob("game-*.zip"))
    )
    result: list[Path] = []
    for path in raw_paths:
        try:
            game_id = int(path.stem.split("-")[-1])
        except ValueError:
            result.append(path)
            continue
        if game_id != SPECIAL_GAME_ID:
            result.append(path)
    return result


def _dummy_active_ship(previous: Mapping[str, Any]) -> dict[str, Any]:
    """Build only the structural state needed by the production carry helper.

    Exact terminal->next-start field differential remains the independent C3
    audit's responsibility. This C5 gate tests membership/continuation only.
    """

    ship_id = previous.get("ship_id")
    race_id = previous.get("race_id")
    return {
        "id": int(ship_id),
        "hull_id": int(previous.get("hull_id") or 1),
        "shield": 100,
        "damage": 0,
        "crew": 1,
        "beam_count": 0,
        "tube_count": 0,
        "torpedoes": 0,
        "fighters": 0,
        "federation_crew_bonus": race_id == 1,
    }


def _mutation_projection(previous: Mapping[str, Any]) -> dict[str, Any]:
    terminal = previous.get("terminal")
    ship_id = previous.get("ship_id")
    if not isinstance(terminal, Mapping):
        return {"status": "unresolved", "reason": "terminal_missing"}
    if isinstance(ship_id, bool) or not isinstance(ship_id, int) or ship_id <= 0:
        return {"status": "unresolved", "reason": "ship_id_missing"}

    try:
        result = apply_ship_terminal_batch(
            active_ships={ship_id: _dummy_active_ship(previous)},
            terminals_by_ship_id={ship_id: terminal},
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "reason": f"{type(exc).__name__}:{exc}"}

    return {
        "status": "resolved" if result.resolved is True else "unresolved",
        "resolved": result.resolved,
        "ship_remains_active": ship_id in result.active_ships,
        "removed_ship_ids": list(result.removed_ship_ids),
        "carried_ship_ids": list(result.carried_ship_ids),
        "unresolved_reasons": list(result.unresolved_reasons),
        "terminal_destroyed": terminal.get("destroyed"),
        "terminal_captured": terminal.get("captured"),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    original_transition = chain_module._transition_comparison

    def wrapped_transition(
        previous: Mapping[str, Any],
        current: Mapping[str, Any],
    ) -> dict[str, Any]:
        baseline = original_transition(previous, current)
        if previous.get("game_id") == SPECIAL_GAME_ID:
            counts["special_game_transitions_excluded"] += 1
            return baseline

        projection = _mutation_projection(previous)
        counts["same_location_reappearance_transitions"] += 1

        terminal = previous.get("terminal")
        terminal = terminal if isinstance(terminal, Mapping) else {}
        destroyed = terminal.get("destroyed")
        captured = terminal.get("captured")
        mismatch = False

        if projection.get("status") == "error":
            counts["production_mutation_errors"] += 1
            mismatch = True
        elif captured is True:
            counts["captured_predecessor_transitions"] += 1
            exact = (
                projection.get("resolved") is None
                and projection.get("ship_remains_active") is True
            )
            counts["captured_fail_closed_exact" if exact else "captured_fail_closed_mismatch"] += 1
            mismatch = not exact
        elif destroyed is True:
            counts["destroyed_predecessor_reappearances"] += 1
            exact = (
                projection.get("resolved") is True
                and projection.get("ship_remains_active") is False
            )
            counts["destroyed_removal_exact" if exact else "destroyed_removal_mismatch"] += 1
            mismatch = True
        elif destroyed is False and captured is False:
            counts["survivor_transitions"] += 1
            exact = (
                projection.get("resolved") is True
                and projection.get("ship_remains_active") is True
            )
            counts["survivor_membership_exact" if exact else "survivor_membership_mismatch"] += 1
            mismatch = not exact
        else:
            counts["terminal_flags_unresolved"] += 1
            mismatch = True

        if mismatch and len(examples) < args.example_limit:
            examples.append(
                {
                    "game_id": previous.get("game_id"),
                    "turn": previous.get("turn"),
                    "ship_id": previous.get("ship_id"),
                    "previous_vcr_id": previous.get("vcr_id"),
                    "current_vcr_id": current.get("vcr_id"),
                    "baseline": baseline,
                    "production_mutation": projection,
                }
            )
        return baseline

    chain_module._transition_comparison = wrapped_transition
    try:
        ordinary_archives = _ordinary_archive_paths(args)
        chain_report = chain_module.run(
            argparse.Namespace(
                archive=[str(path) for path in ordinary_archives],
                archive_dir=args.archive_dir,
                detail_limit=args.example_limit,
                sample_limit=min(args.example_limit, 20),
            )
        )
    finally:
        chain_module._transition_comparison = original_transition

    survivors = int(counts["survivor_transitions"])
    captures = int(counts["captured_predecessor_transitions"])
    destroyed_reappearances = int(counts["destroyed_predecessor_reappearances"])
    acceptance = {
        "survivor_population_present": survivors > 0,
        "survivor_membership_exact": (
            int(counts["survivor_membership_exact"]) == survivors
            and int(counts["survivor_membership_mismatch"]) == 0
        ),
        "capture_fail_closed_if_observed": (
            int(counts["captured_fail_closed_exact"]) == captures
            and int(counts["captured_fail_closed_mismatch"]) == 0
        ),
        "destroyed_removal_if_reappearance_observed": (
            int(counts["destroyed_removal_exact"]) == destroyed_reappearances
            and int(counts["destroyed_removal_mismatch"]) == 0
        ),
        "no_destroyed_predecessor_reappearances": destroyed_reappearances == 0,
        "no_production_mutation_errors": int(counts["production_mutation_errors"]) == 0,
        "no_terminal_flag_unknowns": int(counts["terminal_flags_unresolved"]) == 0,
    }
    acceptance["mutable_ship_queue_transition_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "special_game_591478_excluded": True,
            "counts": dict(sorted(counts.items())),
            "chain_audit_summary": chain_report.get("summary"),
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "C5 membership/continuation differential over the existing C3 same-turn same-location ship-chain reconstruction. "
            "Game 591478 is excluded from the ordinary promotion population, matching the other C5 corpus gates. "
            "Exact dynamic field carry remains established by the independent C3 chain audit; this gate asks only whether the "
            "new production mutable-queue primitive retains replay survivors, removes replay-destroyed predecessors and fails "
            "closed on capture. A destroyed predecessor followed by another factual VCR is a hard reappearance contradiction "
            "for this bounded queue model. Absence of such rows is not treated as independent population proof of destruction "
            "order. No next-pair selection, repeated-pair occurrence counter, capture ownership, planet combat or Host T state "
            "is modeled."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit production mutable ship-queue membership against C3 ship-chain transitions."
    )
    parser.add_argument("--archive", action="append", default=None)
    parser.add_argument("--archive-dir", type=Path, default=chain_module.DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--example-limit", type=int, default=80)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT MUTABLE SHIP QUEUE AUDIT =====")
    print("summary:", report["summary"])
    if report["examples"]:
        print()
        print("EXAMPLES:")
        for row in report["examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("output:", args.output)
    print("NOTE: membership/continuation gate only; capture and next-pair selection remain separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
