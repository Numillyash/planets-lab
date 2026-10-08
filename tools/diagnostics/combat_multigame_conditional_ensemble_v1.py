"""Read-only multigame pilot: conditional Classic ensembles, not Host predictions.

This samples multiple independent games from one SHA-pinned public100 corpus.
The current-VCR oracle supplies side assignment, effective combat modifiers,
weapon fit and precombat mutable state. Seed and combat mass are removed BEFORE
the scenario evaluator is called. The observed VCR seed/mass are read only
AFTER ensemble evaluation, for separately labelled descriptive coverage checks.

No Host-wide RNG continuity or independent per-turn combat payload is claimed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.combat_vcr_runtime import (
    CombatVcrInputConflict, combat_vcr_cases_for_turns,
)
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, first_last_member_refs,
    reconstruct_compact_member,
)
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.combat.classic import ReplayUnsupported, combat_rng_from_settings
from planets_lab.rules.combat.probabilistic import evaluate_conditional_classic


SCHEMA = "planets-lab.multigame-conditional-combat-pilot.v1"
# This special/campaign/Horwasp-heavy game is not ordinary Classic scope.
EXCLUDED_KNOWN_SPECIAL_GAMES = frozenset({591478})


def _int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def select_game_turn_candidates(
    connection: Any, *,
    anchor_game_id: int = 400330,
    anchor_turn: int = 141,
    max_candidate_games: int = 24,
) -> list[tuple[int, int]]:
    """Select diverse games and low/moderate VCR-volume turns, deterministically.

    The vcrs view is part of the v2 compact typed corpus. An unavailable view
    fails closed; never substitute guessed game IDs or downloaded VCRs.
    """
    rows = connection.execute(
        """
        SELECT game_id, embedded_turn, COUNT(*) AS observations
        FROM vcrs
        GROUP BY game_id, embedded_turn
        HAVING COUNT(*) BETWEEN 2 AND 120
        ORDER BY game_id, observations ASC, embedded_turn ASC
        """
    ).fetchall()
    candidates: list[tuple[int, int]] = []
    by_game: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for game_id, turn, count in rows:
        gid, t = int(game_id), int(turn)
        if gid in EXCLUDED_KNOWN_SPECIAL_GAMES or t < 1:
            continue
        by_game[gid].append((t, int(count)))
    for game_rows in by_game.values():
        game_rows.sort(key=lambda row: (row[1], row[0]))
    if anchor_game_id in by_game:
        candidates.append((anchor_game_id, anchor_turn))
    for game_id in sorted(by_game):
        if game_id == anchor_game_id:
            continue
        if len({g for g, _ in candidates}) >= max_candidate_games:
            break
        # Fewer VCR observations per turn = bounded reconstruction.
        turn = by_game[game_id][0][0]
        candidates.append((game_id, turn))
    return candidates


def _independent_hull_specs(connection: Any, game_id: int) -> NuStaticSpecs:
    first, _last = first_last_member_refs(connection, game_id=game_id)
    payload = reconstruct_compact_member(connection, first.member_id)
    specs = NuStaticSpecs.from_catalog(import_static_all(payload))
    if not specs.hulls:
        raise ValueError(f"game {game_id}: static hull catalog missing")
    return specs


def _strip_oracle_rng_and_mass(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Deliberately remove prohibited outcomes BEFORE invoking evaluator."""
    stripped = deepcopy(dict(payload))
    stripped.pop("seed", None)
    for side_name in ("left", "right"):
        side = stripped.get(side_name)
        if isinstance(side, dict):
            side.pop("mass", None)
    return stripped


def _observational_mass_match(
    payload: Mapping[str, Any], ensemble: Mapping[str, Any],
) -> bool | None:
    left, right = payload.get("left"), payload.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return None
    left_actual = _int(left.get("mass"))
    right_actual = _int(right.get("mass"))
    if left_actual is None or right_actual is None:
        return None
    allowed = {s["right_mass"] for s in ensemble["mass_scenarios"]}
    return left_actual == ensemble["left_mass"] and right_actual in allowed


def _sample_one(
    *,
    case: Any,
    specs: NuStaticSpecs,
    seeds: tuple[int, ...],
) -> dict[str, Any]:
    factual = case.payload
    left, right = factual.get("left"), factual.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise ReplayUnsupported("factual VCR side is malformed")
    left_hull_id, right_hull_id = _int(left.get("hullid")), _int(right.get("hullid"))
    if (
        left_hull_id is None or right_hull_id is None
        or left_hull_id <= 0 or right_hull_id <= 0
    ):
        raise ReplayUnsupported("non ship-vs-ship / missing hull IDs")
    if combat_rng_from_settings(case.settings) != 0:
        raise ReplayUnsupported("not a supported Classic combatrng=0 game")
    left_spec = specs.hulls.get(left_hull_id)
    right_spec = specs.hulls.get(right_hull_id)
    if left_spec is None or right_spec is None:
        raise ReplayUnsupported("ship hull absent from independent static catalog")

    # Critically: the evaluator sees NO factual seed or mass.
    hypothetical_input = _strip_oracle_rng_and_mass(factual)
    ensemble = evaluate_conditional_classic(
        hypothetical_input,
        beams=case.beams,
        torpedoes=case.torpedoes,
        settings=case.settings,
        left_hull_mass=left_spec.mass,
        right_hull_mass=right_spec.mass,
        assumed_no_other_mass_modifiers=True,
        seed_values=seeds,
    )
    return {
        "vcr_id": case.vcr_id,
        "battle_turn": case.battle_turn,
        "pair": [ensemble["side_ids"]["left"], ensemble["side_ids"]["right"]],
        "input_provenance": (
            "ORACLE_ASSISTED_CURRENT_VCR_FIELDS_EXCEPT_SEED_AND_MASS"
        ),
        "observed_mass_inside_scenarios": _observational_mass_match(
            factual, ensemble
        ),
        "factual_seed_inside_grid_after_evaluation": (
            _int(factual.get("seed")) in seeds
        ),
        "ensemble": ensemble,
    }


def build_report(
    *,
    connection: Any,
    db_path: str,
    max_games: int = 5,
    cases_per_game: int = 2,
    max_candidate_games: int = 24,
    seeds: tuple[int, ...] = tuple(range(1, 119)),
) -> dict[str, Any]:
    if max_games <= 0 or cases_per_game <= 0 or max_candidate_games < max_games:
        raise ValueError("invalid multigame sample bounds")
    selection = select_game_turn_candidates(
        connection, max_candidate_games=max_candidate_games
    )
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    scan_count = 0
    for game_id, turn in selection:
        if len(selected) >= max_games:
            break
        scan_count += 1
        try:
            specs = _independent_hull_specs(connection, game_id)
            cases = combat_vcr_cases_for_turns(
                connection, game_id=game_id, battle_turns={turn}
            )
        except (ValueError, CombatVcrInputConflict, TypeError) as exc:
            rejected.append({
                "game_id": game_id, "turn": turn,
                "stage": "corpus_or_catalog", "reason": str(exc),
            })
            continue

        sample: list[dict[str, Any]] = []
        attempted = 0
        unsupported: Counter[str] = Counter()
        for (_t, _vcr_id), case in sorted(cases.items()):
            if len(sample) >= cases_per_game:
                break
            attempted += 1
            try:
                row = _sample_one(case=case, specs=specs, seeds=seeds)
                sample.append(row)
            except ReplayUnsupported as exc:
                unsupported[str(exc)] += 1
        if sample:
            selected.append({
                "game_id": game_id, "turn": turn,
                "sampled_case_count": len(sample),
                "attempted_case_count": attempted,
                "unsupported_reasons": dict(sorted(unsupported.items())),
                "cases": sample,
            })
        else:
            rejected.append({
                "game_id": game_id, "turn": turn,
                "stage": "eligible_cases",
                "reason": "no supported Classic ship-vs-ship cases",
                "unsupported_reasons": dict(sorted(unsupported.items())),
            })

    total_cases = sum(row["sampled_case_count"] for row in selected)
    mass_in = sum(
        case["observed_mass_inside_scenarios"] is True
        for game in selected for case in game["cases"]
    )
    mass_out = sum(
        case["observed_mass_inside_scenarios"] is False
        for game in selected for case in game["cases"]
    )
    return {
        "schema": SCHEMA,
        "status": (
            "CONDITIONAL_MULTIGAME_PILOT_COMPLETE"
            if len(selected) >= max_games
            else "PARTIAL_SAMPLE_SCOPE_NOT_MET"
        ),
        "corpus": {
            "database_path": db_path, "source": "public100_compact",
            "game_count_target": max_games,
            "case_target_per_game": cases_per_game,
            "candidate_game_scan_limit": max_candidate_games,
            "known_special_game_exclusions": sorted(EXCLUDED_KNOWN_SPECIAL_GAMES),
        },
        "summary": {
            "games_selected": len(selected),
            "different_game_ids": [game["game_id"] for game in selected],
            "cases_evaluated": total_cases,
            "scenario_replays": sum(
                case["ensemble"]["scenario_count"]
                for game in selected for case in game["cases"]
            ),
            "observed_mass_inside_scenarios": mass_in,
            "observed_mass_outside_scenarios": mass_out,
            "candidate_games_attempted": scan_count,
            "games_rejected": len(rejected),
        },
        "selected_games": selected,
        "rejected_games": rejected,
        "evidence_boundary": (
            "A current-VCR ORACLE supplies the current pair, owner/race, weapon "
            "fit, effective counts, shield, crew, ammo, combat modifiers and "
            "game weapon catalog. The ensemble NEVER receives factual seed "
            "or combat mass; both are scenario parameters. Its assumed 1..118 "
            "uniform seeds and independent 60% carrier bonus are NOT calibrated "
            "Host probabilities. Mass modifiers beyond hull/Fed/carrier are "
            "assumed absent and not independently proven. This is NOT a fully "
            "generative battle simulator or a held-out factual outcome test. "
            "Cross-game diversity is a diagnostic, not universal validation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-db-root", type=Path, required=True)
    parser.add_argument("--corpus-db-generation", required=True)
    parser.add_argument("--max-games", type=int, default=5)
    parser.add_argument("--cases-per-game", type=int, default=2)
    parser.add_argument("--max-candidate-games", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        conn, path = connect_compact_generation_read_only(
            args.corpus_db_generation, args.corpus_db_root
        )
        try:
            report = build_report(
                connection=conn, db_path=str(path),
                max_games=args.max_games, cases_per_game=args.cases_per_game,
                max_candidate_games=args.max_candidate_games,
            )
        finally:
            conn.close()
    except (OSError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("===== MULTIGAME CONDITIONAL CLASSIC PILOT V1 =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    for game in report["selected_games"]:
        print(
            f"game={game['game_id']} turn={game['turn']} "
            f"cases={game['sampled_case_count']} "
            f"skipped={game['unsupported_reasons']}"
        )
        for case in game["cases"]:
            ensemble = case["ensemble"]
            print(
                f"  V{case['vcr_id']} pair={case['pair']} "
                f"scenarios={ensemble['scenario_count']} "
                f"carrier_eligible={ensemble['carrier_eligible']} "
                f"observed_mass_inside_scenarios={case['observed_mass_inside_scenarios']} "
                f"outcome_probabilities={ensemble['outcome_probabilities']}"
            )
    print("output:", args.output)
    return 0 if report["status"] == "CONDITIONAL_MULTIGAME_PILOT_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
