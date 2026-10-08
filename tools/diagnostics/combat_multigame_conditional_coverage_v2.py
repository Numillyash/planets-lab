"""Coverage-oriented multigame conditional Classic combat pilot v2.

Retries a bounded set of different battle turns for each distinct game,
rather than rejecting entire games after a planet-only or unsupported turn.
All simulations remain oracle-assisted except factual VCR seed/mass, which
the pre-existing v1 evaluator strips before the ensemble is called.

Candidates and failures are retained in the output for auditability. No
independent Host-side selection, combat setup, seed policy or calibrated
outcome probability is claimed.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for path in (ROOT / "src", DIAGNOSTICS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.combat_vcr_runtime import (
    CombatVcrInputConflict,
    combat_vcr_cases_for_turns,
)
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.rules.combat.classic import ReplayUnsupported

from combat_multigame_conditional_ensemble_v1 import (
    EXCLUDED_KNOWN_SPECIAL_GAMES,
    _independent_hull_specs,
    _sample_one,
)

SCHEMA = "planets-lab.multigame-conditional-combat-pilot.v2"


@dataclass(frozen=True)
class TurnCandidate:
    game_id: int
    turn: int
    perspective_vcr_rows: int
    selection: str = "ranked_observation_count"


def _spread_ids(ordered_ids: list[int], slots: int) -> list[int]:
    """Evenly sample a stable sorted list without repeating the same game."""
    if slots <= 0:
        return []
    if len(ordered_ids) <= slots:
        return ordered_ids
    return [
        ordered_ids[min(len(ordered_ids) - 1, (2 * i + 1) * len(ordered_ids) // (2 * slots))]
        for i in range(slots)
    ]


def choose_game_turns(
    connection: Any,
    *,
    max_candidate_games: int,
    turns_per_game: int,
    anchor_game_id: int = 400330,
    anchor_turn: int = 141,
) -> list[tuple[int, list[TurnCandidate]]]:
    """Rank turns per game, then stratify games across public100 IDs.

    The vcrs table rows are *perspective observations*, not unique battles.
    Hence their count is only a coarse ordering heuristic, and eligibility
    is decided later by the compact VCR adapter. Never report this count
    as a number of unique battles.
    """
    if max_candidate_games <= 0 or turns_per_game <= 0:
        raise ValueError("invalid selection bounds")
    rows = connection.execute(
        """
        SELECT game_id, embedded_turn, COUNT(*) AS perspective_vcr_rows
        FROM vcrs
        GROUP BY game_id, embedded_turn
        HAVING COUNT(*) BETWEEN 2 AND 400
        ORDER BY game_id ASC, perspective_vcr_rows DESC, embedded_turn ASC
        """
    ).fetchall()
    by_game: dict[int, list[TurnCandidate]] = defaultdict(list)
    for game_id, turn, observations in rows:
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (game_id, turn, observations)):
            raise ValueError("malformed vcrs corpus game/turn/count")
        if game_id in EXCLUDED_KNOWN_SPECIAL_GAMES or turn < 1:
            continue
        by_game[game_id].append(TurnCandidate(game_id, turn, observations))
    for game_id in by_game:
        by_game[game_id].sort(key=lambda v: (-v.perspective_vcr_rows, v.turn))

    selected_ids: list[int] = []
    if anchor_game_id in by_game:
        selected_ids.append(anchor_game_id)
    remaining_ids = sorted(g for g in by_game if g != anchor_game_id)
    selected_ids.extend(_spread_ids(remaining_ids, max_candidate_games - len(selected_ids)))
    result: list[tuple[int, list[TurnCandidate]]] = []
    for game_id in selected_ids:
        choices = list(by_game[game_id])
        if game_id == anchor_game_id:
            anchor = next((r for r in choices if r.turn == anchor_turn), None)
            if anchor is not None:
                choices.remove(anchor)
                choices.insert(0, TurnCandidate(
                    game_id, anchor_turn, anchor.perspective_vcr_rows,
                    "previously_verified_anchor",
                ))
        result.append((game_id, choices[:turns_per_game]))
    return result


def build_coverage_report(
    *,
    connection: Any,
    db_path: str,
    max_games: int = 10,
    cases_per_game: int = 2,
    max_candidate_games: int = 35,
    turns_per_game: int = 4,
    seeds: tuple[int, ...] = tuple(range(1, 119)),
) -> dict[str, Any]:
    if any(isinstance(v, bool) or v <= 0 for v in (
        max_games, cases_per_game, max_candidate_games, turns_per_game
    )) or max_candidate_games < max_games:
        raise ValueError("invalid multigame bounds")

    candidates = choose_game_turns(
        connection, max_candidate_games=max_candidate_games,
        turns_per_game=turns_per_game,
    )
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    total_attempted_vcrs = 0
    total_attempted_turns = 0
    for game_id, turns in candidates:
        if len(selected) >= max_games:
            break
        try:
            specs = _independent_hull_specs(connection, game_id)
        except (ValueError, TypeError, OSError) as exc:
            rejected.append({
                "game_id": game_id, "reason": "static_catalog_unavailable",
                "error": str(exc), "attempted_turns": [],
            })
            continue

        evaluated: list[dict[str, Any]] = []
        attempted_turns: list[dict[str, Any]] = []
        rejection_counts: Counter[str] = Counter()
        for candidate in turns:
            if len(evaluated) >= cases_per_game:
                break
            total_attempted_turns += 1
            turn_record: dict[str, Any] = {
                "battle_turn": candidate.turn,
                "perspective_vcr_rows": candidate.perspective_vcr_rows,
                "selection": candidate.selection,
                "vcrs_seen": 0,
                "vcrs_attempted": 0,
                "vcrs_evaluated": 0,
                "unsupported": {},
            }
            attempted_turns.append(turn_record)
            try:
                cases = combat_vcr_cases_for_turns(
                    connection, game_id=game_id,
                    battle_turns={candidate.turn},
                )
            except (CombatVcrInputConflict, TypeError, ValueError, OSError) as exc:
                turn_record["failure"] = "compact_vcr_input_unavailable"
                turn_record["error"] = str(exc)
                rejection_counts["compact_vcr_input_unavailable"] += 1
                continue

            turn_record["vcrs_seen"] = len(cases)
            reasons: Counter[str] = Counter()
            for (_turn, _id), case in sorted(cases.items()):
                if len(evaluated) >= cases_per_game:
                    break
                total_attempted_vcrs += 1
                turn_record["vcrs_attempted"] += 1
                try:
                    outcome = _sample_one(case=case, specs=specs, seeds=seeds)
                except ReplayUnsupported as exc:
                    reasons[str(exc)] += 1
                    rejection_counts[str(exc)] += 1
                    continue
                evaluated.append(outcome)
                turn_record["vcrs_evaluated"] += 1
            turn_record["unsupported"] = dict(sorted(reasons.items()))

        record = {
            "game_id": game_id,
            "sampled_case_count": len(evaluated),
            "turns_examined": len(attempted_turns),
            "attempted_turns": attempted_turns,
            "unsupported_reasons": dict(sorted(rejection_counts.items())),
        }
        if evaluated:
            record["cases"] = evaluated
            selected.append(record)
        else:
            record["reason"] = "no_supported_ship_vs_ship_classic_case_in_bounded_turns"
            rejected.append(record)

    num_cases = sum(s["sampled_case_count"] for s in selected)
    expected_cases = max_games * cases_per_game
    mass_inside = sum(
        case["observed_mass_inside_scenarios"] is True
        for game in selected for case in game["cases"]
    )
    mass_outside = sum(
        case["observed_mass_inside_scenarios"] is False
        for game in selected for case in game["cases"]
    )
    mass_unknown = num_cases - mass_inside - mass_outside
    summary = {
        "games_selected": len(selected),
        "different_game_ids": [s["game_id"] for s in selected],
        "cases_evaluated": num_cases,
        "target_cases": expected_cases,
        "full_case_quota_games": sum(
            s["sampled_case_count"] == cases_per_game for s in selected
        ),
        "partial_case_quota_games": sum(
            s["sampled_case_count"] < cases_per_game for s in selected
        ),
        "scenario_replays": sum(
            case["ensemble"]["scenario_count"]
            for game in selected for case in game["cases"]
        ),
        "observed_mass_inside_scenarios": mass_inside,
        "observed_mass_outside_scenarios": mass_outside,
        "observed_mass_unknown": mass_unknown,
        "candidate_games_attempted": len(selected) + len(rejected),
        "turns_attempted": total_attempted_turns,
        "vcrs_attempted": total_attempted_vcrs,
        "games_rejected": len(rejected),
    }
    complete = (
        len(selected) == max_games
        and num_cases == expected_cases
    )
    return {
        "schema": SCHEMA,
        "status": (
            "CONDITIONAL_MULTIGAME_COVERAGE_TARGET_MET"
            if complete else "PARTIAL_GAME_OR_CASE_COVERAGE"
        ),
        "database_path": db_path,
        "selection_policy": {
            "source": "v2compact-public100",
            "game_id_sampling": "deterministic_even_spread_plus_verified_anchor",
            "turn_ranking": "descending_perspective_vcr_observations",
            "unique_vcr_count_in_selection": "UNKNOWN_UNTIL_CASE_LOAD",
            "max_games": max_games,
            "cases_per_game": cases_per_game,
            "max_candidate_games": max_candidate_games,
            "turns_per_game": turns_per_game,
            "known_special_game_exclusions": sorted(EXCLUDED_KNOWN_SPECIAL_GAMES),
        },
        "summary": summary,
        "selected_games": selected,
        "rejected_games": rejected,
        "evidence_boundary": (
            "Both sides and effective precombat combat fields come from a "
            "factual CURRENT VCR oracle; only observed seed and combat mass "
            "are excluded before conditional ensemble evaluation. Uniform "
            "start seeds and the independent 60% anti-carrier Bernoulli branch "
            "are scenario assumptions, not empirically calibrated Host RNG. "
            "This expansion measures supported cases and mass candidate-set "
            "coverage across independently identified games; it does not "
            "independently generate entire combat inputs or validate scenario "
            "probabilities against held-out terminal results. Special games, "
            "extended combat RNG, unknown effective fields fail closed."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--corpus-db-generation", required=True)
    p.add_argument("--max-games", type=int, default=10)
    p.add_argument("--cases-per-game", type=int, default=2)
    p.add_argument("--max-candidate-games", type=int, default=35)
    p.add_argument("--turns-per-game", type=int, default=4)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        conn, db_path = connect_compact_generation_read_only(
            args.corpus_db_generation, args.corpus_db_root,
        )
        try:
            report = build_coverage_report(
                connection=conn, db_path=str(db_path),
                max_games=args.max_games,
                cases_per_game=args.cases_per_game,
                max_candidate_games=args.max_candidate_games,
                turns_per_game=args.turns_per_game,
            )
        finally:
            conn.close()
    except (TypeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("===== MULTIGAME CONDITIONAL COMBAT COVERAGE V2 =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    for game in report["selected_games"]:
        ids = [f"T{c['battle_turn']}:V{c['vcr_id']}" for c in game["cases"]]
        print(
            f"game={game['game_id']} cases={game['sampled_case_count']} "
            f"turns_examined={game['turns_examined']} selected={ids} "
            f"unsupported={game['unsupported_reasons']}"
        )
    for game in report["rejected_games"]:
        print(
            f"rejected game={game['game_id']} "
            f"reason={game['reason']} "
            f"turns={game['attempted_turns']}"
        )
    print("output:", args.output)
    # Incomplete coverage is a valid scientific result, not a runtime exception:
    # no fake results are introduced to force a successful "target met" report.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
