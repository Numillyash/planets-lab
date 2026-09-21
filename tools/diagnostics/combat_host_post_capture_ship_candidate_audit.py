from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.feature_scope import DEFAULT_FEATURE_INDEX_PATH
from planets_lab.corpus.movement_differential import _intish
from planets_lab.rules.combat.order import standard_battle_priority_key

import combat_host_capture_continuation_audit as capture_module
import combat_host_initial_standard_target_audit as baseline_module
from combat_host_candidate_set_audit import (
    _independent_permission,
    _pair,
    _requests_combat,
)
from combat_host_matching_fc_suppression_audit import _relation_signature
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-post-capture-ship-candidate-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _priority(raw: Mapping[str, Any], ship_id: int) -> tuple[int, int, int] | None:
    return standard_battle_priority_key(
        ship_id=ship_id,
        mission=_intish(raw.get("mission")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
    )


def _capture_targets(
    capture_report: Mapping[str, Any],
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    result: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    rows = capture_report.get("examples")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return result
    for row in rows:
        if (
            not isinstance(row, Mapping)
            or row.get("status") != "capture_continuation"
            or row.get("current_opponent_is_planet") is True
        ):
            continue
        position = row.get("position")
        if (
            not isinstance(position, Sequence)
            or isinstance(position, (str, bytes))
            or len(position) != 2
        ):
            continue
        key = (
            int(row["game_id"]),
            int(row["turn"]),
            int(position[0]),
            int(position[1]),
        )
        result[key] = row
    return result


def _analyze_site(
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    site_rows = context.get("site_ship_rows")
    if not isinstance(site_rows, Mapping):
        return {"status": "unresolved", "reason": "site_ship_rows_missing"}

    captured_ship_id = int(capture["ship_id"])
    new_owner_id = int(capture["captor_owner_id"])
    factual_opponent_id = capture.get("current_opponent_ship_id")
    if (
        isinstance(factual_opponent_id, bool)
        or not isinstance(factual_opponent_id, int)
        or factual_opponent_id <= 0
    ):
        return {"status": "unresolved", "reason": "factual_ship_opponent_missing"}

    captured_entry = site_rows.get(captured_ship_id)
    if not isinstance(captured_entry, Mapping):
        return {
            "status": "unresolved",
            "reason": "captured_ship_not_independently_predicted_at_site",
        }

    relations = context.get("relations")
    controls = context.get("controls")
    factual = context.get("factual")
    before_turn = int(context["before_turn"])
    if not isinstance(relations, Mapping) or not isinstance(controls, Mapping):
        return {"status": "unresolved", "reason": "relation_context_missing"}
    factual_pair_rows = (
        factual.get("pair_rows")
        if isinstance(factual, Mapping)
        else {}
    )
    factual_pair_rows = factual_pair_rows if isinstance(factual_pair_rows, Mapping) else {}

    candidates: list[dict[str, Any]] = []
    for raw_ship_id, entry in sorted(site_rows.items(), key=lambda item: int(item[0])):
        ship_id = int(raw_ship_id)
        if ship_id == captured_ship_id or not isinstance(entry, Mapping):
            continue
        owner_id = int(entry["owner_id"])
        if owner_id == new_owner_id:
            continue
        raw = entry.get("raw")
        if not isinstance(raw, Mapping):
            continue

        request = _requests_combat(raw, new_owner_id)
        pair = _pair(captured_ship_id, ship_id)
        signature = _relation_signature(
            relations.get(before_turn, {}),
            owner_id,
            new_owner_id,
        )
        excluded = frozenset(factual_pair_rows.get(pair, set()))
        strict_permission = _independent_permission(
            request=request,
            owner_id=owner_id,
            opponent_owner_id=new_owner_id,
            signature=signature,
            controls=controls,
            excluded_rows=excluded,
        )
        priority = _priority(raw, ship_id)
        candidates.append(
            {
                "ship_id": ship_id,
                "owner_id": owner_id,
                "requests_new_owner": request,
                "strict_permission": strict_permission,
                "priority": list(priority) if priority is not None else None,
                "is_factual_next_opponent": ship_id == factual_opponent_id,
            }
        )

    requesters = [
        row for row in candidates
        if row["requests_new_owner"] is True and row["priority"] is not None
    ]
    strict_requesters = [
        row for row in candidates
        if row["strict_permission"] is True and row["priority"] is not None
    ]
    requesters.sort(key=lambda row: tuple(row["priority"]))
    strict_requesters.sort(key=lambda row: tuple(row["priority"]))

    requester_rank = next(
        (idx + 1 for idx, row in enumerate(requesters) if row["ship_id"] == factual_opponent_id),
        None,
    )
    strict_rank = next(
        (idx + 1 for idx, row in enumerate(strict_requesters) if row["ship_id"] == factual_opponent_id),
        None,
    )
    factual_row = next(
        (row for row in candidates if row["ship_id"] == factual_opponent_id),
        None,
    )

    return {
        "status": "resolved",
        "captured_ship_id": captured_ship_id,
        "new_owner_id": new_owner_id,
        "factual_opponent_ship_id": factual_opponent_id,
        "predicted_site_ship_count": len(site_rows),
        "foreign_candidate_count": len(candidates),
        "requester_count": len(requesters),
        "strict_requester_count": len(strict_requesters),
        "factual_opponent_predicted_at_site": factual_row is not None,
        "factual_opponent_requests_new_owner": (
            factual_row.get("requests_new_owner")
            if isinstance(factual_row, Mapping)
            else None
        ),
        "factual_opponent_strict_permission": (
            factual_row.get("strict_permission")
            if isinstance(factual_row, Mapping)
            else None
        ),
        "factual_opponent_requester_rank": requester_rank,
        "factual_opponent_strict_rank": strict_rank,
        "requester_order": [int(row["ship_id"]) for row in requesters],
        "strict_requester_order": [int(row["ship_id"]) for row in strict_requesters],
        "candidates": candidates,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    capture_report = capture_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=10000,
            output=None,
        )
    )
    targets = _capture_targets(capture_report)
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    seen_targets: set[tuple[int, int, int, int]] = set()

    def observer(context: Mapping[str, Any]) -> None:
        key = (
            int(context["game_id"]),
            int(context["battle_turn"]),
            int(context["x"]),
            int(context["y"]),
        )
        capture = targets.get(key)
        if capture is None:
            return
        seen_targets.add(key)
        result = _analyze_site(context, capture)
        status = str(result.get("status", "unknown"))
        counts[f"status:{status}"] += 1
        if status == "resolved":
            if result.get("factual_opponent_predicted_at_site") is True:
                counts["factual_opponent_predicted_at_site"] += 1
            if result.get("factual_opponent_requests_new_owner") is True:
                counts["factual_opponent_requests_new_owner"] += 1
            if result.get("factual_opponent_strict_permission") is True:
                counts["factual_opponent_strict_permission_true"] += 1
            elif result.get("factual_opponent_strict_permission") is None:
                counts["factual_opponent_strict_permission_unknown"] += 1
            else:
                counts["factual_opponent_strict_permission_false"] += 1
            rank = result.get("factual_opponent_requester_rank")
            counts[f"requester_rank:{rank if rank is not None else 'none'}"] += 1
            strict_rank = result.get("factual_opponent_strict_rank")
            counts[f"strict_rank:{strict_rank if strict_rank is not None else 'none'}"] += 1
        if len(examples) < args.example_limit:
            examples.append(
                {
                    "game_id": key[0],
                    "battle_turn": key[1],
                    "x": key[2],
                    "y": key[3],
                    "capture": {
                        "ship_id": capture.get("ship_id"),
                        "captor_ship_id": capture.get("captor_ship_id"),
                        "captor_owner_id": capture.get("captor_owner_id"),
                        "current_opponent_ship_id": capture.get("current_opponent_ship_id"),
                        "from_vcr_id": capture.get("from_vcr_id"),
                        "to_vcr_id": capture.get("to_vcr_id"),
                    },
                    "result": result,
                }
            )

    baseline = baseline_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=0,
            output=None,
            site_observer=observer,
        )
    )

    missing = sorted(set(targets) - seen_targets)
    counts["ship_capture_targets"] = len(targets)
    counts["target_sites_observed_by_position_reconstructor"] = len(seen_targets)
    counts["target_sites_missing"] = len(missing)

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": capture_report.get("summary", {}).get("feature_scope"),
            "counts": dict(sorted(counts.items())),
            "baseline_initial_standard": baseline.get("summary"),
            "missing_target_sites": [list(row) for row in missing],
        },
        "examples": examples,
        "evidence_boundary": (
            "Descriptive post-capture ship-candidate inventory only. Capture rows "
            "come from the production capture differential. Site membership is "
            "reconstructed independently by the existing owner-current T-1 "
            "position pipeline. For each foreign predicted ship, its T-1 "
            "Kill!/Primary-Enemy request is reevaluated against the prize ship's "
            "new owner, and strict diplomacy permission removes factual rows for "
            "the exact candidate pair so the held-out next engagement cannot "
            "prove its own permission. Factual VCR N+1 contributes only the "
            "opponent ship id comparator after candidates are built. This v1 "
            "does not yet apply active-membership history before the capture, "
            "rebuild captured-ship aggression, or promote a next-pair rule."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory independently reconstructed ship candidates after combat capture."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--feature-index", type=Path, default=DEFAULT_FEATURE_INDEX_PATH)
    parser.add_argument("--scope-profile", default="combat-planar-no-horwasp")
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT POST-CAPTURE SHIP CANDIDATE INVENTORY =====")
    print("summary:", report["summary"])
    if report["examples"]:
        print()
        print("EXAMPLES:")
        for row in report["examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: discovery only; active-membership history and full post-capture "
        "pair recomposition remain separate before promotion."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
