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

from planets_lab.rules.combat.queue import (
    InitialStandardPairInput,
    InitialStandardSelection,
    select_initial_plain_standard,
)
from planets_lab.rules.combat.selection import (
    ShipCombatPairDecision,
    ShipCombatPairPhase,
    ShipCombatPrestandardKind,
    ShipCombatSideInput,
)

import combat_host_initial_standard_target_audit as baseline_module
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-initial-standard-canonical-selector-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _side_from_projection(raw: Mapping[str, Any]) -> ShipCombatSideInput:
    return ShipCombatSideInput(
        ship_id=int(raw["ship_id"]),
        owner_id=int(raw["owner_id"]),
        mission=(int(raw["mission"]) if raw.get("mission") is not None else None),
        primary_enemy=(int(raw["enemy"]) if raw.get("enemy") is not None else None),
        friendly_code=raw.get("friendlycode"),
    )


def _decision_from_projection(raw: Mapping[str, Any]) -> ShipCombatPairDecision:
    phase_raw = raw.get("phase")
    kind_raw = raw.get("prestandard_kind")
    phase = ShipCombatPairPhase(str(phase_raw)) if phase_raw is not None else None
    kind = ShipCombatPrestandardKind(str(kind_raw)) if kind_raw is not None else None
    return ShipCombatPairDecision(
        engagement_eligible=raw.get("engagement_eligible"),
        matching_fc_blocks=raw.get("matching_fc_blocks"),
        left_hwm_applies=raw.get("left_hwm_applies"),
        right_hwm_applies=raw.get("right_hwm_applies"),
        phase=phase,
        prestandard_kind=kind,
        phase_attacker_ship_id=(
            int(raw["phase_attacker_ship_id"])
            if raw.get("phase_attacker_ship_id") is not None
            else None
        ),
        left_ship_id=(int(raw["left_ship_id"]) if raw.get("left_ship_id") is not None else None),
        right_ship_id=(
            int(raw["right_ship_id"]) if raw.get("right_ship_id") is not None else None
        ),
        unresolved_reasons=tuple(str(value) for value in raw.get("unresolved_reasons", ())),
    )


def canonical_selection_from_projected_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    profile: str,
) -> tuple[InitialStandardSelection | None, str | None]:
    """Adapt baseline diagnostic rows into the production selector input shape.

    The adapter does not recompute pair mechanics.  It converts the already
    independently composed pair decisions and static side order fields into the
    production stack-selector API, which lets the corpus compare the proven
    legacy diagnostic ordering against the new canonical primitive without
    duplicating the expensive archive reconstruction pipeline.
    """

    pair_inputs: list[InitialStandardPairInput] = []
    try:
        for row in rows:
            left_raw = row.get("left")
            right_raw = row.get("right")
            decision_raw = row.get(profile)
            if not isinstance(left_raw, Mapping):
                return None, "left_projection_missing"
            if not isinstance(right_raw, Mapping):
                return None, "right_projection_missing"
            if not isinstance(decision_raw, Mapping):
                return None, "decision_projection_missing"
            pair_inputs.append(
                InitialStandardPairInput(
                    left=_side_from_projection(left_raw),
                    right=_side_from_projection(right_raw),
                    decision=_decision_from_projection(decision_raw),
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"adapter_error:{type(exc).__name__}:{exc}"

    return select_initial_plain_standard(pair_inputs), None


def _selection_projection(selection: InitialStandardSelection | None) -> dict[str, Any] | None:
    if selection is None:
        return None
    return {
        "engagement_available": selection.engagement_available,
        "eligible_pair_count": selection.eligible_pair_count,
        "pair": list(selection.pair) if selection.pair is not None else None,
        "active_ship_id": selection.active_ship_id,
        "target_ship_id": selection.target_ship_id,
        "left_ship_id": selection.left_ship_id,
        "right_ship_id": selection.right_ship_id,
        "active_priority": (
            list(selection.active_priority) if selection.active_priority is not None else None
        ),
        "target_priority": (
            list(selection.target_priority) if selection.target_priority is not None else None
        ),
        "unresolved_reasons": list(selection.unresolved_reasons),
    }


def _matches_legacy(
    selection: InitialStandardSelection,
    legacy: Mapping[str, Any],
) -> bool:
    pair_raw = legacy.get("pair")
    if not isinstance(pair_raw, Sequence) or isinstance(pair_raw, (str, bytes)) or len(pair_raw) != 2:
        return False
    pair = tuple(sorted((int(pair_raw[0]), int(pair_raw[1]))))
    return bool(
        selection.engagement_available is True
        and selection.pair == pair
        and selection.active_ship_id == int(legacy["active_ship_id"])
        and selection.target_ship_id == int(legacy["target_ship_id"])
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    original_profile_site_analysis = baseline_module._profile_site_analysis

    def wrapped_profile_site_analysis(*wrapped_args: Any, **wrapped_kwargs: Any) -> dict[str, Any]:
        analysis = original_profile_site_analysis(*wrapped_args, **wrapped_kwargs)
        rows = wrapped_kwargs.get("rows")
        profile = wrapped_kwargs.get("profile")
        if rows is None and wrapped_args:
            rows = wrapped_args[0]
        if profile is None and len(wrapped_args) > 1:
            profile = wrapped_args[1]
        profile = str(profile)
        rows = rows if isinstance(rows, Sequence) else ()

        selection, adapter_error = canonical_selection_from_projected_rows(
            rows,
            profile=profile,
        )

        if analysis.get("broad_comparable") is True:
            counts[f"{profile}:legacy_broad_sites"] += 1
            legacy = analysis.get("predicted_first")
            if adapter_error is not None:
                counts[f"{profile}:adapter_error_on_broad"] += 1
            elif selection is None or selection.engagement_available is not True:
                counts[f"{profile}:canonical_unresolved_on_broad"] += 1
            elif isinstance(legacy, Mapping) and _matches_legacy(selection, legacy):
                counts[f"{profile}:canonical_broad_exact"] += 1
            else:
                counts[f"{profile}:canonical_broad_mismatch"] += 1
                if len(examples) < args.example_limit:
                    examples.append(
                        {
                            "profile": profile,
                            "scope": "broad",
                            "legacy": legacy,
                            "canonical": _selection_projection(selection),
                            "adapter_error": adapter_error,
                        }
                    )

        if analysis.get("exact_comparable") is True:
            counts[f"{profile}:legacy_exact_sites"] += 1
            legacy = analysis.get("predicted_first")
            if (
                adapter_error is None
                and selection is not None
                and isinstance(legacy, Mapping)
                and _matches_legacy(selection, legacy)
            ):
                counts[f"{profile}:canonical_exact_set_exact"] += 1
            else:
                counts[f"{profile}:canonical_exact_set_mismatch"] += 1

        return analysis

    baseline_module._profile_site_analysis = wrapped_profile_site_analysis
    try:
        baseline = baseline_module.run(
            argparse.Namespace(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                example_limit=args.example_limit,
                output=None,
            )
        )
    finally:
        baseline_module._profile_site_analysis = original_profile_site_analysis

    baseline_summary = baseline.get("summary")
    baseline_summary = baseline_summary if isinstance(baseline_summary, Mapping) else {}

    def profile_acceptance(profile: str) -> dict[str, bool]:
        broad_sites = int(counts[f"{profile}:legacy_broad_sites"])
        exact_sites = int(counts[f"{profile}:legacy_exact_sites"])
        return {
            "broad_population_present": broad_sites > 0,
            "no_adapter_error_on_broad": int(counts[f"{profile}:adapter_error_on_broad"]) == 0,
            "no_canonical_unresolved_on_broad": int(
                counts[f"{profile}:canonical_unresolved_on_broad"]
            ) == 0,
            "canonical_broad_matches_legacy": (
                int(counts[f"{profile}:canonical_broad_exact"]) == broad_sites
                and int(counts[f"{profile}:canonical_broad_mismatch"]) == 0
            ),
            "exact_set_population_present": exact_sites > 0,
            "canonical_exact_set_matches_legacy": (
                int(counts[f"{profile}:canonical_exact_set_exact"]) == exact_sites
                and int(counts[f"{profile}:canonical_exact_set_mismatch"]) == 0
            ),
        }

    strict_acceptance = profile_acceptance("strict")
    conditional_acceptance = profile_acceptance("conditional")
    acceptance = {
        "strict": strict_acceptance,
        "conditional": conditional_acceptance,
        "all_profiles_match": all(strict_acceptance.values()) and all(conditional_acceptance.values()),
    }

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "counts": dict(sorted(counts.items())),
            "baseline_initial_standard": baseline_summary,
            "baseline_mismatch_examples": len(baseline.get("mismatch_examples", ())),
            "acceptance": acceptance,
        },
        "mismatch_examples": examples,
        "evidence_boundary": (
            "Read-only differential between the established initial plain-STANDARD diagnostic selector and the new production "
            "select_initial_plain_standard primitive. The expensive archive reconstruction and pair decisions remain those of "
            "the independent baseline audit; this adapter only converts its projected pair rows into the canonical stack API. "
            "Comparison is asserted only on baseline broad/exact comparable sites, where engagement and plain STANDARD order "
            "are already fully resolved. This gate proves selector-equivalence only. It does not reconstruct new cloak state, "
            "does not use Host T/postcombat state as production input, and does not yet claim mutable survivor/second-pass logic."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare the canonical initial plain-STANDARD selector against the established corpus diagnostic."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT INITIAL STANDARD CANONICAL SELECTOR =====")
    print("summary:", report["summary"])
    if report["mismatch_examples"]:
        print()
        print("CANONICAL MISMATCH EXAMPLES:")
        for row in report["mismatch_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("output:", args.output)
    print("NOTE: selector equivalence gate only; no new effective-state inference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
