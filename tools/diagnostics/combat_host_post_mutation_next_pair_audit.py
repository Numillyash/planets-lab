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

from planets_lab.corpus.feature_scope import (
    DEFAULT_FEATURE_INDEX_PATH,
    load_feature_scope,
)
from planets_lab.rules.combat.host_queue import (
    StandardQueueState,
    record_standard_queue_step,
    select_after_ship_mutation,
    select_next_plain_standard,
)
from planets_lab.rules.combat.mutable_queue import apply_ship_terminal_batch
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import ShipCombatSideInput

import combat_host_initial_standard_target_audit as baseline_module
import combat_ship_chain_audit as chain_module
from combat_host_initial_standard_canonical_selector_audit import (
    _decision_from_projection,
    _side_from_projection,
)
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-post-mutation-next-pair-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _pair(a: int, b: int) -> tuple[int, int]:
    return tuple(sorted((int(a), int(b))))


def _pair_inputs(
    rows: Sequence[Mapping[str, Any]],
    *,
    profile: str,
) -> list[InitialStandardPairInput]:
    result: list[InitialStandardPairInput] = []
    for row in rows:
        left = row.get("left")
        right = row.get("right")
        decision = row.get(profile)
        if (
            not isinstance(left, Mapping)
            or not isinstance(right, Mapping)
            or not isinstance(decision, Mapping)
        ):
            raise ValueError("candidate projection incomplete")
        result.append(
            InitialStandardPairInput(
                left=_side_from_projection(left),
                right=_side_from_projection(right),
                decision=_decision_from_projection(decision),
            )
        )
    return result


def _candidate_ship_ids(
    pair_inputs: Sequence[InitialStandardPairInput],
) -> set[int]:
    result: set[int] = set()
    for item in pair_inputs:
        result.add(item.left.ship_id)
        result.add(item.right.ship_id)
    return result


def _appearance_key(
    game_id: int,
    turn: int,
    vcr_id: int,
    ship_id: int,
) -> tuple[int, int, int, int]:
    return int(game_id), int(turn), int(vcr_id), int(ship_id)


def _active_ship_from_appearance(
    appearance: Mapping[str, Any] | None,
    *,
    ship_id: int,
) -> dict[str, Any]:
    start = appearance.get("start") if isinstance(appearance, Mapping) else None
    start = start if isinstance(start, Mapping) else {}
    hull_id = appearance.get("hull_id") if isinstance(appearance, Mapping) else None
    race_id = appearance.get("race_id") if isinstance(appearance, Mapping) else None
    if isinstance(hull_id, bool) or not isinstance(hull_id, int) or hull_id <= 0:
        hull_id = 1

    def integer(primary: str, fallback: str | None = None, default: int = 0) -> int:
        value = start.get(primary)
        if (
            (isinstance(value, bool) or not isinstance(value, int))
            and fallback is not None
        ):
            value = start.get(fallback)
        return (
            int(value)
            if isinstance(value, int) and not isinstance(value, bool)
            else default
        )

    owner_id = appearance.get("owner_id") if isinstance(appearance, Mapping) else None
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        owner_id = None

    return {
        "id": ship_id,
        "hull_id": hull_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "federation_crew_bonus": race_id == 1,
        "lizard_crew_bonus": race_id == 2,
        "shield": integer("shield", default=100),
        "damage": integer("damage"),
        "crew": integer("crew", default=1),
        "physical_beam_count": integer("beamcount", "beam_count"),
        "physical_launcher_count": integer("launchercount", "launcher_count"),
        "physical_bay_count": integer("baycount", "bay_count"),
        "beam_count": integer("beamcount", "beam_count"),
        "launcher_count": integer("launchercount", "launcher_count"),
        "bay_count": integer("baycount", "bay_count"),
        "torpedoes": integer("torpedos", "torpedoes"),
        "fighters": integer("fighters"),
    }


def _first_appearance_for_ship(
    *,
    game_id: int,
    battle_turn: int,
    ship_id: int,
    factual_queue: Sequence[Mapping[str, Any]],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        if isinstance(vcr_id, bool) or not isinstance(vcr_id, int):
            continue
        found = appearances.get(
            _appearance_key(game_id, battle_turn, vcr_id, ship_id)
        )
        if found is not None:
            return found
    return None


def _terminal_batch(
    *,
    game_id: int,
    battle_turn: int,
    factual_vcr: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> tuple[dict[int, Mapping[str, Any]] | None, str | None]:
    vcr_id = factual_vcr.get("vcr_id")
    pair_raw = factual_vcr.get("pair")
    if (
        isinstance(vcr_id, bool)
        or not isinstance(vcr_id, int)
        or not isinstance(pair_raw, tuple)
        or len(pair_raw) != 2
    ):
        return None, "factual_vcr_shape_unresolved"

    terminals: dict[int, Mapping[str, Any]] = {}
    for ship_id in pair_raw:
        appearance = appearances.get(
            _appearance_key(game_id, battle_turn, vcr_id, int(ship_id))
        )
        if not isinstance(appearance, Mapping):
            return None, "replay_appearance_missing"
        terminal = appearance.get("terminal")
        if not isinstance(terminal, Mapping):
            return None, "replay_terminal_missing"
        if terminal.get("captured") is True:
            return None, "capture_predecessor"
        terminals[int(ship_id)] = terminal
    return terminals, None


def _matches_factual(
    step: Any,
    factual: Mapping[str, Any],
) -> bool:
    pair_raw = factual.get("pair")
    if not isinstance(pair_raw, tuple) or len(pair_raw) != 2:
        return False
    return bool(
        step.engagement_available is True
        and step.pair == _pair(pair_raw[0], pair_raw[1])
        and step.left_ship_id == int(factual["left_ship_id"])
        and step.right_ship_id == int(factual["right_ship_id"])
    )


def _simulate_site(
    *,
    game_id: int,
    battle_turn: int,
    rows: Sequence[Mapping[str, Any]],
    profile: str,
    factual_queue: Sequence[Mapping[str, Any]],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if len(factual_queue) < 2:
        return {"status": "not_informative", "reason": "single_vcr_site"}

    try:
        pair_inputs = _pair_inputs(rows, profile=profile)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "unresolved",
            "reason": f"pair_adapter:{type(exc).__name__}:{exc}",
        }

    active_ids = _candidate_ship_ids(pair_inputs)
    if not active_ids:
        return {"status": "unresolved", "reason": "no_candidate_ships"}

    active_ships: dict[int, dict[str, Any]] = {}
    for ship_id in active_ids:
        appearance = _first_appearance_for_ship(
            game_id=game_id,
            battle_turn=battle_turn,
            ship_id=ship_id,
            factual_queue=factual_queue,
            appearances=appearances,
        )
        active_ships[ship_id] = _active_ship_from_appearance(
            appearance,
            ship_id=ship_id,
        )

    state = StandardQueueState()
    first = select_next_plain_standard(
        pair_inputs=pair_inputs,
        active_ship_ids=active_ships.keys(),
        state=state,
    )
    if not _matches_factual(first, factual_queue[0]):
        return {
            "status": "initial_mismatch",
            "predicted_pair": list(first.pair) if first.pair is not None else None,
            "predicted_left_ship_id": first.left_ship_id,
            "predicted_right_ship_id": first.right_ship_id,
            "factual_first": dict(factual_queue[0]),
            "unresolved_reasons": list(first.unresolved_reasons),
        }

    state = record_standard_queue_step(state, first)
    transitions: list[dict[str, Any]] = []

    for index in range(len(factual_queue) - 1):
        current = factual_queue[index]
        factual_next = factual_queue[index + 1]
        terminals, terminal_issue = _terminal_batch(
            game_id=game_id,
            battle_turn=battle_turn,
            factual_vcr=current,
            appearances=appearances,
        )
        if terminal_issue is not None or terminals is None:
            return {
                "status": "excluded",
                "reason": terminal_issue or "terminal_unresolved",
                "resolved_transitions": transitions,
            }

        mutation = apply_ship_terminal_batch(
            active_ships=active_ships,
            terminals_by_ship_id=terminals,
        )
        if mutation.resolved is not True:
            return {
                "status": "unresolved",
                "reason": "production_mutation_unresolved",
                "mutation_reasons": list(mutation.unresolved_reasons),
                "resolved_transitions": transitions,
            }

        predicted_next = select_after_ship_mutation(
            mutation=mutation,
            pair_inputs=pair_inputs,
            state=state,
        )
        exact = _matches_factual(predicted_next, factual_next)
        transition = {
            "from_vcr_id": int(current["vcr_id"]),
            "to_vcr_id": int(factual_next["vcr_id"]),
            "factual_pair": list(factual_next["pair"]),
            "factual_left_ship_id": int(factual_next["left_ship_id"]),
            "factual_right_ship_id": int(factual_next["right_ship_id"]),
            "predicted_pair": (
                list(predicted_next.pair)
                if predicted_next.pair is not None
                else None
            ),
            "predicted_occurrence_index": predicted_next.occurrence_index,
            "predicted_left_ship_id": predicted_next.left_ship_id,
            "predicted_right_ship_id": predicted_next.right_ship_id,
            "inactive_pair_count": predicted_next.inactive_pair_count,
            "exhausted_pair_count": predicted_next.exhausted_pair_count,
            "exact": exact,
            "unresolved_reasons": list(predicted_next.unresolved_reasons),
        }
        transitions.append(transition)

        if not exact:
            return {
                "status": (
                    "next_pair_mismatch"
                    if predicted_next.engagement_available is True
                    else "next_pair_unresolved"
                ),
                "reason": "held_out_next_vcr_not_exact",
                "resolved_transitions": transitions,
            }

        state = record_standard_queue_step(state, predicted_next)
        active_ships = mutation.active_ships

    return {
        "status": "exact",
        "transition_count": len(transitions),
        "transitions": transitions,
    }


def _collect_replay_appearances(
    args: argparse.Namespace,
) -> tuple[
    dict[tuple[int, int, int, int], dict[str, Any]],
    Mapping[str, Any],
]:
    appearances: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
    )
    selected_ids = set(feature_scope.selected_ids)
    original_appearance = chain_module._appearance

    def wrapped_appearance(*wrapped_args: Any, **wrapped_kwargs: Any):
        result = original_appearance(*wrapped_args, **wrapped_kwargs)
        if (
            isinstance(result, dict)
            and result.get("game_id") in selected_ids
        ):
            key = _appearance_key(
                int(result["game_id"]),
                int(result["turn"]),
                int(result["vcr_id"]),
                int(result["ship_id"]),
            )
            appearances[key] = result
        return result

    ordinary_archives = []
    for path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(path.stem.split("-")[-1])
        except ValueError:
            continue
        if game_id in selected_ids:
            ordinary_archives.append(str(path))

    chain_module._appearance = wrapped_appearance
    try:
        report = chain_module.run(
            argparse.Namespace(
                archive=ordinary_archives,
                archive_dir=args.archive_dir,
                detail_limit=args.example_limit,
                sample_limit=min(args.example_limit, 20),
            )
        )
    finally:
        chain_module._appearance = original_appearance
    return appearances, report.get("summary", {})


class _TrackingQueueDict(dict):
    def __init__(
        self,
        *args: Any,
        game_id: int,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._game_id = game_id
        self._context = context

    def get(self, key: Any, default: Any = None) -> Any:
        value = super().get(key, default)
        self._context["game_id"] = self._game_id
        self._context["site_key"] = key
        self._context["factual_queue"] = value
        return value


def run(args: argparse.Namespace) -> dict[str, Any]:
    appearances, chain_summary = _collect_replay_appearances(args)
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    context: dict[str, Any] = {}

    original_queue_builder = baseline_module._factual_queue_by_site
    original_profile_analysis = baseline_module._profile_site_analysis

    def wrapped_queue_builder(*wrapped_args: Any, **wrapped_kwargs: Any):
        result = original_queue_builder(*wrapped_args, **wrapped_kwargs)
        game_id = wrapped_kwargs.get("game_id")
        if game_id is None and wrapped_args:
            game_id = wrapped_args[0]
        return _TrackingQueueDict(
            result,
            game_id=int(game_id),
            context=context,
        )

    def wrapped_profile_analysis(
        *wrapped_args: Any,
        **wrapped_kwargs: Any,
    ) -> dict[str, Any]:
        analysis = original_profile_analysis(*wrapped_args, **wrapped_kwargs)
        rows = wrapped_kwargs.get("rows")
        profile = wrapped_kwargs.get("profile")
        if rows is None and wrapped_args:
            rows = wrapped_args[0]
        if profile is None and len(wrapped_args) > 1:
            profile = wrapped_args[1]
        profile = str(profile)
        rows = rows if isinstance(rows, Sequence) else ()

        if analysis.get("exact_comparable") is not True:
            return analysis

        factual_queue = context.get("factual_queue")
        site_key = context.get("site_key")
        game_id = context.get("game_id")
        if (
            not isinstance(factual_queue, Sequence)
            or isinstance(factual_queue, (str, bytes))
            or len(factual_queue) < 2
            or not isinstance(site_key, tuple)
            or len(site_key) != 3
            or not isinstance(game_id, int)
        ):
            return analysis

        counts[f"{profile}:multi_vcr_exact_set_sites"] += 1
        result = _simulate_site(
            game_id=game_id,
            battle_turn=int(site_key[0]),
            rows=rows,
            profile=profile,
            factual_queue=factual_queue,
            appearances=appearances,
        )
        status = str(result.get("status", "unknown"))
        counts[f"{profile}:site_status:{status}"] += 1

        resolved_transitions = result.get("transitions")
        if not isinstance(resolved_transitions, list):
            resolved_transitions = result.get("resolved_transitions")
        if isinstance(resolved_transitions, list):
            for transition in resolved_transitions:
                if not isinstance(transition, Mapping):
                    continue
                counts[f"{profile}:transitions_compared"] += 1
                if transition.get("exact") is True:
                    counts[f"{profile}:next_vcr_exact"] += 1
                else:
                    counts[f"{profile}:next_vcr_mismatch"] += 1
                if int(transition.get("inactive_pair_count") or 0) > 0:
                    counts[f"{profile}:transitions_with_inactive_filter"] += 1
                if int(transition.get("exhausted_pair_count") or 0) > 0:
                    counts[f"{profile}:transitions_with_exhausted_filter"] += 1
                if int(transition.get("predicted_occurrence_index") or 0) == 2:
                    counts[f"{profile}:second_occurrence_predictions"] += 1

        if status == "excluded":
            reason = str(result.get("reason", "unknown"))
            counts[f"{profile}:excluded:{reason}"] += 1

        if status not in {"exact", "excluded"} and len(examples) < args.example_limit:
            examples.append(
                {
                    "game_id": game_id,
                    "battle_turn": int(site_key[0]),
                    "x": int(site_key[1]),
                    "y": int(site_key[2]),
                    "profile": profile,
                    "factual_queue": list(factual_queue),
                    "result": result,
                }
            )
        return analysis

    baseline_module._factual_queue_by_site = wrapped_queue_builder
    baseline_module._profile_site_analysis = wrapped_profile_analysis
    try:
        baseline = baseline_module.run(
            argparse.Namespace(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                example_limit=args.example_limit,
                feature_index=args.feature_index,
                scope_profile=args.scope_profile,
                output=None,
            )
        )
    finally:
        baseline_module._factual_queue_by_site = original_queue_builder
        baseline_module._profile_site_analysis = original_profile_analysis

    def profile_acceptance(profile: str) -> dict[str, bool]:
        sites = int(counts[f"{profile}:multi_vcr_exact_set_sites"])
        compared = int(counts[f"{profile}:transitions_compared"])
        exact = int(counts[f"{profile}:next_vcr_exact"])
        mismatch = int(counts[f"{profile}:next_vcr_mismatch"])
        unresolved_sites = sum(
            value
            for key, value in counts.items()
            if key.startswith(f"{profile}:site_status:")
            and not key.endswith(":exact")
            and not key.endswith(":excluded")
        )
        return {
            "multi_vcr_exact_set_population_present": sites > 0,
            "next_vcr_transition_population_present": compared > 0,
            "all_compared_next_vcr_exact": compared > 0 and exact == compared and mismatch == 0,
            "no_nonexcluded_unresolved_sites": unresolved_sites == 0,
        }

    strict_acceptance = profile_acceptance("strict")
    conditional_acceptance = profile_acceptance("conditional")
    acceptance = {
        "strict": strict_acceptance,
        "conditional": conditional_acceptance,
        "all_profiles_pass": (
            all(strict_acceptance.values())
            and all(conditional_acceptance.values())
        ),
    }

    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
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
        "mismatch_examples": examples,
        "evidence_boundary": (
            "Bounded post-combat next-pair differential. Candidate rows are "
            "independently reconstructed from owner-current T-1 by the existing "
            "initial STANDARD target audit; only its exact-set comparable sites "
            "with at least two factual ship VCRs enter this gate. Deterministic "
            "Classic replay of factual VCR N supplies only terminal state for "
            "membership mutation. Factual VCR N+1 is held out until comparison. "
            "The selector receives the independently reconstructed T-1 pair "
            "decision rows filtered by production active membership and pair "
            "occurrence history; it never receives the factual next pair. "
            "Capture predecessors are excluded/fail-closed. The clean population "
            "is selected through shared FeatureScope; excluded, UNKNOWN and unindexed "
            "games do not enter the proof. Planet combat, unresolved/pre-standard "
            "candidate sets and non-exact-set "
            "sites remain outside this proof. Pair decisions themselves are the "
            "same bounded T-1 projections used by the already DIFF_VERIFIED "
            "initial selector; this gate does not yet claim dynamic pair-decision "
            "recomputation after combat."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare production post-mutation STANDARD queue selection with "
            "held-out factual next VCRs."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument(
        "--feature-index",
        type=Path,
        default=DEFAULT_FEATURE_INDEX_PATH,
        help="Compiled feature index used to select the attributable combat corpus.",
    )
    parser.add_argument(
        "--scope-profile",
        default="combat-planar-no-horwasp",
        help="FeatureScope profile defining the clean combat population.",
    )
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT POST-MUTATION NEXT-PAIR AUDIT =====")
    print("summary:", report["summary"])
    if report["mismatch_examples"]:
        print()
        print("MISMATCH EXAMPLES:")
        for row in report["mismatch_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: factual VCR N+1 is held out until comparison; capture and "
        "dynamic post-combat pair recomposition remain outside this bounded gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
