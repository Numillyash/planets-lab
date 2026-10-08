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

from planets_lab.corpus.feature_scope import DEFAULT_FEATURE_INDEX_PATH, load_feature_scope
from planets_lab.corpus.movement_differential import _intish
from planets_lab.data.nu_loadturn import _ship_ammo
from planets_lab.rules.combat.mutable_queue import (
    ShipCaptureTransfer,
    apply_ship_terminal_batch,
)

import combat_host_capture_continuation_audit as capture_module
import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_capture_ship_candidate_audit as candidate_module
import combat_host_post_capture_special_movement_audit as special_movement_module
import combat_host_post_mutation_next_pair_audit as mutation_audit
from combat_host_candidate_set_audit import (
    _independent_permission,
    _pair,
    _requests_combat,
)
from combat_host_matching_fc_suppression_audit import _relation_signature
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-post-capture-active-membership-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _appearance_index(
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    *,
    game_id: int,
    battle_turn: int,
    vcr_id: int,
    ship_id: int,
) -> Mapping[str, Any] | None:
    return appearances.get(
        mutation_audit._appearance_key(game_id, battle_turn, vcr_id, ship_id)
    )


def _raw_active_ship(entry: Mapping[str, Any], *, ship_id: int) -> dict[str, Any]:
    raw = entry.get("raw")
    raw = raw if isinstance(raw, Mapping) else {}
    owner_id = entry.get("owner_id")
    race_id = entry.get("race_id")
    hull_id = entry.get("hull_id")

    def integer(*keys: str, default: int = 0) -> int:
        for key in keys:
            value = raw.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return int(value)
        return default

    (
        beam_count,
        launcher_count,
        bay_count,
        fighters,
        torpedoes,
        unresolved_ammo,
    ) = _ship_ammo(raw)
    if unresolved_ammo > 0:
        raise ValueError(
            f"ship {ship_id}: ambiguous Nu ammo={unresolved_ammo} "
            f"with launchers={launcher_count} bays={bay_count}"
        )

    return {
        "id": ship_id,
        "owner_id": int(owner_id) if isinstance(owner_id, int) and not isinstance(owner_id, bool) else None,
        "race_id": int(race_id) if isinstance(race_id, int) and not isinstance(race_id, bool) else None,
        "hull_id": int(hull_id) if isinstance(hull_id, int) and not isinstance(hull_id, bool) and hull_id > 0 else 1,
        "shield": integer("shield", default=100),
        "damage": integer("damage"),
        "crew": integer("crew", default=1),
        "physical_beam_count": beam_count,
        "physical_launcher_count": launcher_count,
        "physical_bay_count": bay_count,
        "beam_count": beam_count,
        "launcher_count": launcher_count,
        "bay_count": bay_count,
        "torpedoes": torpedoes,
        "fighters": fighters,
        "federation_crew_bonus": race_id == 1,
        "lizard_crew_bonus": race_id == 2,
    }


def _capture_transfer(
    *,
    pair: tuple[int, int],
    terminals: Mapping[int, Mapping[str, Any]],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    game_id: int,
    battle_turn: int,
    vcr_id: int,
) -> tuple[dict[int, ShipCaptureTransfer] | None, str | None]:
    captured = [
        ship_id
        for ship_id, terminal in terminals.items()
        if terminal.get("captured") is True
    ]
    if not captured:
        return {}, None
    if len(captured) != 1:
        return None, "capture_cardinality_unresolved"

    prize_id = captured[0]
    captor_id = pair[1] if pair[0] == prize_id else pair[0]
    captor = _appearance_index(
        appearances,
        game_id=game_id,
        battle_turn=battle_turn,
        vcr_id=vcr_id,
        ship_id=captor_id,
    )
    if not isinstance(captor, Mapping):
        return None, "captor_appearance_missing"

    owner_id = captor.get("owner_id")
    race_id = captor.get("race_id")
    if (
        isinstance(owner_id, bool)
        or not isinstance(owner_id, int)
        or owner_id <= 0
        or isinstance(race_id, bool)
        or not isinstance(race_id, int)
        or race_id <= 0
    ):
        return None, "captor_identity_unresolved"

    return {
        prize_id: ShipCaptureTransfer(
            new_owner_id=int(owner_id),
            new_race_id=int(race_id),
            new_federation_crew_bonus=int(race_id) == 1,
            new_lizard_crew_bonus=int(race_id) == 2,
        )
    }, None


def _terminal_batch_with_transfer(
    *,
    game_id: int,
    battle_turn: int,
    factual_vcr: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> tuple[
    dict[int, Mapping[str, Any]] | None,
    dict[int, ShipCaptureTransfer] | None,
    str | None,
]:
    vcr_id = factual_vcr.get("vcr_id")
    pair_raw = factual_vcr.get("pair")
    if (
        isinstance(vcr_id, bool)
        or not isinstance(vcr_id, int)
        or not isinstance(pair_raw, tuple)
        or len(pair_raw) != 2
    ):
        return None, None, "factual_vcr_shape_unresolved"

    pair = (int(pair_raw[0]), int(pair_raw[1]))
    terminals: dict[int, Mapping[str, Any]] = {}
    for ship_id in pair:
        appearance = _appearance_index(
            appearances,
            game_id=game_id,
            battle_turn=battle_turn,
            vcr_id=int(vcr_id),
            ship_id=ship_id,
        )
        if not isinstance(appearance, Mapping):
            return None, None, "replay_appearance_missing"
        terminal = appearance.get("terminal")
        if not isinstance(terminal, Mapping):
            return None, None, "replay_terminal_missing"
        terminals[ship_id] = terminal

    transfers, issue = _capture_transfer(
        pair=pair,
        terminals=terminals,
        appearances=appearances,
        game_id=game_id,
        battle_turn=battle_turn,
        vcr_id=int(vcr_id),
    )
    return terminals, transfers, issue


def _first_appearance(
    *,
    game_id: int,
    battle_turn: int,
    ship_id: int,
    factual_queue: Sequence[Mapping[str, Any]],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    return mutation_audit._first_appearance_for_ship(
        game_id=game_id,
        battle_turn=battle_turn,
        ship_id=ship_id,
        factual_queue=factual_queue,
        appearances=appearances,
    )


def _simulate_capture(
    *,
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    game_id = int(context["game_id"])
    battle_turn = int(context["battle_turn"])
    before_turn = int(context["before_turn"])
    from_vcr_id = int(capture["from_vcr_id"])
    prize_id = int(capture["ship_id"])
    factual_opponent_id = capture.get("current_opponent_ship_id")
    if (
        isinstance(factual_opponent_id, bool)
        or not isinstance(factual_opponent_id, int)
        or factual_opponent_id <= 0
    ):
        return {"status": "unresolved", "reason": "factual_opponent_missing"}

    factual_queue = context.get("factual_queue")
    predictions = context.get("predictions")
    site_rows = context.get("site_ship_rows")
    relations = context.get("relations")
    controls = context.get("controls")
    factual = context.get("factual")
    if (
        not isinstance(factual_queue, Sequence)
        or isinstance(factual_queue, (str, bytes))
        or not isinstance(predictions, Mapping)
        or not isinstance(site_rows, Mapping)
        or not isinstance(relations, Mapping)
        or not isinstance(controls, Mapping)
    ):
        return {"status": "unresolved", "reason": "site_context_incomplete"}

    history = [
        row
        for row in factual_queue
        if isinstance(row, Mapping)
        and isinstance(row.get("vcr_id"), int)
        and not isinstance(row.get("vcr_id"), bool)
        and int(row["vcr_id"]) <= from_vcr_id
    ]
    if not history or int(history[-1]["vcr_id"]) != from_vcr_id:
        return {"status": "unresolved", "reason": "capture_vcr_not_in_site_history"}

    initial_ids = {int(ship_id) for ship_id in site_rows}
    history_ids: set[int] = set()
    for row in history:
        pair_raw = row.get("pair")
        if isinstance(pair_raw, tuple) and len(pair_raw) == 2:
            history_ids.update((int(pair_raw[0]), int(pair_raw[1])))
    initial_ids.update(history_ids)

    active_ships: dict[int, dict[str, Any]] = {}
    anchored_history_ids: list[int] = []
    for ship_id in sorted(initial_ids):
        appearance = _first_appearance(
            game_id=game_id,
            battle_turn=battle_turn,
            ship_id=ship_id,
            factual_queue=history,
            appearances=appearances,
        )
        if isinstance(appearance, Mapping):
            active = mutation_audit._active_ship_from_appearance(
                appearance,
                ship_id=ship_id,
            )
            anchored_history_ids.append(ship_id)
        else:
            entry = predictions.get(ship_id)
            if not isinstance(entry, Mapping):
                return {
                    "status": "unresolved",
                    "reason": "initial_ship_state_missing",
                    "ship_id": ship_id,
                }
            active = _raw_active_ship(entry, ship_id=ship_id)
        active_ships[ship_id] = active

    mutation_trace: list[dict[str, Any]] = []
    owner_changed_ids: set[int] = set()
    removed_ids: set[int] = set()

    for row in history:
        vcr_id = int(row["vcr_id"])
        terminals, transfers, issue = _terminal_batch_with_transfer(
            game_id=game_id,
            battle_turn=battle_turn,
            factual_vcr=row,
            appearances=appearances,
        )
        if issue is not None or terminals is None or transfers is None:
            return {
                "status": "unresolved",
                "reason": issue or "terminal_batch_unresolved",
                "from_vcr_id": vcr_id,
                "mutation_trace": mutation_trace,
            }

        missing_active = sorted(set(terminals) - set(active_ships))
        if missing_active:
            return {
                "status": "unresolved",
                "reason": "terminal_participant_not_active",
                "missing_ship_ids": missing_active,
                "from_vcr_id": vcr_id,
                "mutation_trace": mutation_trace,
            }

        mutation = apply_ship_terminal_batch(
            active_ships=active_ships,
            terminals_by_ship_id=terminals,
            capture_transfers_by_ship_id=transfers,
        )
        if mutation.resolved is not True:
            return {
                "status": "unresolved",
                "reason": "production_mutation_unresolved",
                "mutation_reasons": list(mutation.unresolved_reasons),
                "from_vcr_id": vcr_id,
                "mutation_trace": mutation_trace,
            }

        owner_changed_ids.update(mutation.captured_ship_ids)
        removed_ids.update(mutation.removed_ship_ids)
        active_ships = mutation.active_ships
        mutation_trace.append(
            {
                "vcr_id": vcr_id,
                "removed_ship_ids": list(mutation.removed_ship_ids),
                "captured_ship_ids": list(mutation.captured_ship_ids),
                "active_ship_ids": sorted(active_ships),
            }
        )

    prize = active_ships.get(prize_id)
    if not isinstance(prize, Mapping):
        return {
            "status": "unresolved",
            "reason": "prize_not_active_after_capture",
            "mutation_trace": mutation_trace,
        }
    prize_owner = prize.get("owner_id")
    if (
        isinstance(prize_owner, bool)
        or not isinstance(prize_owner, int)
        or prize_owner <= 0
    ):
        return {
            "status": "unresolved",
            "reason": "prize_owner_unresolved_after_capture",
            "mutation_trace": mutation_trace,
        }

    expected_owner = capture.get("captor_owner_id")
    if prize_owner != expected_owner:
        return {
            "status": "mismatch",
            "reason": "prize_owner_not_captor",
            "predicted_owner_id": prize_owner,
            "expected_captor_owner_id": expected_owner,
            "mutation_trace": mutation_trace,
        }

    factual_pair_rows = (
        factual.get("pair_rows")
        if isinstance(factual, Mapping)
        else {}
    )
    factual_pair_rows = factual_pair_rows if isinstance(factual_pair_rows, Mapping) else {}

    candidates: list[dict[str, Any]] = []
    unresolved_foreign: list[dict[str, Any]] = []

    for ship_id in sorted(active_ships):
        if ship_id == prize_id:
            continue
        current = active_ships[ship_id]
        current_owner = current.get("owner_id")
        if (
            isinstance(current_owner, bool)
            or not isinstance(current_owner, int)
            or current_owner <= 0
        ):
            unresolved_foreign.append(
                {"ship_id": ship_id, "reason": "current_owner_unresolved"}
            )
            continue
        if current_owner == prize_owner:
            continue

        entry = predictions.get(ship_id)
        if not isinstance(entry, Mapping):
            unresolved_foreign.append(
                {"ship_id": ship_id, "reason": "tminus1_prediction_missing"}
            )
            continue
        tminus1_owner = entry.get("owner_id")
        raw = entry.get("raw")
        if (
            not isinstance(tminus1_owner, int)
            or isinstance(tminus1_owner, bool)
            or not isinstance(raw, Mapping)
        ):
            unresolved_foreign.append(
                {"ship_id": ship_id, "reason": "tminus1_order_state_missing"}
            )
            continue
        if int(current_owner) != int(tminus1_owner):
            unresolved_foreign.append(
                {
                    "ship_id": ship_id,
                    "reason": "candidate_owner_changed_before_capture",
                    "tminus1_owner_id": int(tminus1_owner),
                    "current_owner_id": int(current_owner),
                }
            )
            continue

        request = _requests_combat(raw, int(prize_owner))
        pair = _pair(prize_id, ship_id)
        signature = _relation_signature(
            relations.get(before_turn, {}),
            int(current_owner),
            int(prize_owner),
        )
        excluded = frozenset(factual_pair_rows.get(pair, set()))
        strict_permission = _independent_permission(
            request=request,
            owner_id=int(current_owner),
            opponent_owner_id=int(prize_owner),
            signature=signature,
            controls=controls,
            excluded_rows=excluded,
        )
        priority = candidate_module._priority(raw, ship_id)
        candidates.append(
            {
                "ship_id": ship_id,
                "owner_id": int(current_owner),
                "requests_new_owner": request,
                "strict_permission": strict_permission,
                "priority": list(priority) if priority is not None else None,
                "position_source": entry.get("source"),
                "is_factual_next_opponent": ship_id == int(factual_opponent_id),
            }
        )

    requesters = [
        row
        for row in candidates
        if row["requests_new_owner"] is True and row["priority"] is not None
    ]
    strict_requesters = [
        row
        for row in candidates
        if row["strict_permission"] is True and row["priority"] is not None
    ]
    requesters.sort(key=lambda row: tuple(row["priority"]))
    strict_requesters.sort(key=lambda row: tuple(row["priority"]))

    requester_rank = next(
        (
            index + 1
            for index, row in enumerate(requesters)
            if row["ship_id"] == factual_opponent_id
        ),
        None,
    )
    strict_rank = next(
        (
            index + 1
            for index, row in enumerate(strict_requesters)
            if row["ship_id"] == factual_opponent_id
        ),
        None,
    )
    factual_candidate = next(
        (
            row
            for row in candidates
            if row["ship_id"] == factual_opponent_id
        ),
        None,
    )

    return {
        "status": "resolved",
        "prize_ship_id": prize_id,
        "prize_owner_id_after_capture": int(prize_owner),
        "factual_opponent_ship_id": int(factual_opponent_id),
        "factual_opponent_active": int(factual_opponent_id) in active_ships,
        "factual_opponent_candidate_resolved": factual_candidate is not None,
        "factual_opponent_requests_new_owner": (
            factual_candidate.get("requests_new_owner")
            if isinstance(factual_candidate, Mapping)
            else None
        ),
        "factual_opponent_strict_permission": (
            factual_candidate.get("strict_permission")
            if isinstance(factual_candidate, Mapping)
            else None
        ),
        "factual_opponent_requester_rank": requester_rank,
        "factual_opponent_strict_rank": strict_rank,
        "active_ship_ids": sorted(active_ships),
        "removed_ship_ids": sorted(removed_ids),
        "owner_changed_ship_ids": sorted(owner_changed_ids),
        "history_anchored_ship_ids": sorted(anchored_history_ids),
        "unresolved_foreign_candidates": unresolved_foreign,
        "requester_order": [int(row["ship_id"]) for row in requesters],
        "strict_requester_order": [int(row["ship_id"]) for row in strict_requesters],
        "candidates": candidates,
        "mutation_trace": mutation_trace,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
    )
    capture_report = capture_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=10000,
            output=None,
        )
    )
    targets = candidate_module._capture_targets(capture_report)

    appearances, chain_summary = mutation_audit._collect_replay_appearances(args)
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    seen_observations: set[tuple[int, int, int, int, int]] = set()

    def prediction_overlay(
        context: Mapping[str, Any],
    ) -> dict[int, dict[str, Any]]:
        key = (
            int(context["game_id"]),
            int(context["battle_turn"]),
        )
        target_turns = {
            (game_id, battle_turn)
            for game_id, battle_turn, _x, _y in targets
        }
        if key not in target_turns:
            return {}
        return special_movement_module.special_position_overlay(context)

    def observer(context: Mapping[str, Any]) -> None:
        site_key = (
            int(context["game_id"]),
            int(context["battle_turn"]),
            int(context["x"]),
            int(context["y"]),
        )
        captures = targets.get(site_key)
        if not captures:
            return

        for capture in captures:
            observation_key = (
                site_key[0],
                site_key[1],
                int(capture["from_vcr_id"]),
                int(capture["to_vcr_id"]),
                int(capture["ship_id"]),
            )
            seen_observations.add(observation_key)
            result = _simulate_capture(
                context=context,
                capture=capture,
                appearances=appearances,
            )
            status = str(result.get("status", "unknown"))
            counts[f"status:{status}"] += 1
            if status == "resolved":
                if result.get("factual_opponent_active") is True:
                    counts["factual_opponent_active"] += 1
                if result.get("factual_opponent_candidate_resolved") is True:
                    counts["factual_opponent_candidate_resolved"] += 1
                if result.get("factual_opponent_requests_new_owner") is True:
                    counts["factual_opponent_requests_new_owner"] += 1
                if result.get("factual_opponent_strict_permission") is True:
                    counts["factual_opponent_strict_permission_true"] += 1
                if result.get("factual_opponent_requester_rank") == 1:
                    counts["requester_rank:1"] += 1
                if result.get("factual_opponent_strict_rank") == 1:
                    counts["strict_rank:1"] += 1
                unresolved = result.get("unresolved_foreign_candidates")
                if isinstance(unresolved, list):
                    counts["unresolved_foreign_candidates"] += len(unresolved)
                removed = result.get("removed_ship_ids")
                if isinstance(removed, list) and removed:
                    counts["observations_with_removed_history"] += 1
                changed = result.get("owner_changed_ship_ids")
                if isinstance(changed, list) and changed:
                    counts["observations_with_capture_history"] += 1

            if len(examples) < args.example_limit:
                examples.append(
                    {
                        "game_id": site_key[0],
                        "battle_turn": site_key[1],
                        "x": site_key[2],
                        "y": site_key[3],
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
            prediction_overlay=prediction_overlay,
        )
    )

    population = sum(len(rows) for rows in targets.values())
    counts["ship_capture_observations"] = population
    counts["observations_seen"] = len(seen_observations)

    acceptance = {
        "population_present": population > 0,
        "all_observations_seen": len(seen_observations) == population,
        "all_mutation_histories_resolved": int(counts["status:resolved"]) == population,
        "all_factual_opponents_active": int(counts["factual_opponent_active"]) == population,
        "all_factual_opponents_candidate_resolved": (
            int(counts["factual_opponent_candidate_resolved"]) == population
        ),
        "all_factual_opponents_request_new_owner": (
            int(counts["factual_opponent_requests_new_owner"]) == population
        ),
        "all_factual_opponents_strictly_permitted": (
            int(counts["factual_opponent_strict_permission_true"]) == population
        ),
        "all_factual_opponents_requester_rank_one": (
            int(counts["requester_rank:1"]) == population
        ),
        "all_factual_opponents_strict_rank_one": (
            int(counts["strict_rank:1"]) == population
        ),
        "no_owner_mutated_foreign_candidate_uncertainty": (
            int(counts["unresolved_foreign_candidates"]) == 0
        ),
    }
    acceptance["post_capture_active_membership_gate_passed"] = all(
        acceptance.values()
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": feature_scope.to_dict(),
            "counts": dict(sorted(counts.items())),
            "chain_audit_summary": chain_summary,
            "baseline_initial_standard": baseline.get("summary"),
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Held-out post-capture active-membership differential for ship-to-ship "
            "capture continuations. The initial site universe is reconstructed from "
            "owner-current T-1 positions plus the already validated special-movement "
            "overlay. Factual VCRs up to and including capture VCR N are treated as "
            "elapsed queue history: deterministic replay supplies terminal state, "
            "and production apply_ship_terminal_batch performs destroy/survivor/"
            "capture mutation atomically. Capture owner/race transfer is derived "
            "from the captor in VCR N; VCR N+1 is never used for mutation. "
            "After mutation, foreign candidates are rebuilt from active membership, "
            "current owner identity, T-1 orders for ships whose owner has not changed, "
            "and independently calibrated diplomacy. Any non-prize candidate whose "
            "owner changed earlier in the queue fails closed because persistence of "
            "its pre-capture orders is not assumed. The factual next opponent id is "
            "used only as the final comparator. This gate does not yet claim complete "
            "post-capture pair recomposition or left/right side prediction."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filter post-capture ship candidates through production mutable "
            "queue history before held-out next-opponent comparison."
        )
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
    print("===== HOST COMBAT POST-CAPTURE ACTIVE MEMBERSHIP AUDIT =====")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
