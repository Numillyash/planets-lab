"""Read-only factual VCR seed and deterministic Classic replay continuity audit.

Uses all same-turn observed VCR inputs. It never synthesizes combat seeds,
postulates Host-wide RNG draws, or modifies SiteCombatState.
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
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.rules.combat.classic import RANDOM_SIZE, ReplayUnsupported
from planets_lab.rules.combat.nu import replay_nuhost_from_nu_catalog

SCHEMA = "planets-lab.classic-seed-continuity-audit.v1"


def _int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def build_report(*, cases: Mapping[tuple[int, int], Any], turn: int,
                 game_id: int, db_path: str,
                 replay=replay_nuhost_from_nu_catalog) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for (battle_turn, vcr_id), case in sorted(cases.items()):
        if battle_turn != turn:
            continue
        payload = case.payload
        seed = _int(payload.get("seed"))
        if seed is None or not 0 <= seed <= RANDOM_SIZE:
            raise ValueError(f"VCR {vcr_id}: invalid seed")
        x, y = _int(payload.get("x")), _int(payload.get("y"))
        row = {
            "vcr_id": vcr_id, "factual_seed": seed,
            "site": [x, y] if x is not None and y is not None else None,
            "replayed_final_seed": None, "replay_cycles": None,
            "replay_status": "unresolved", "replay_error": None,
        }
        try:
            outcome = replay(
                payload, beams=case.beams,
                torpedoes=case.torpedoes, settings=case.settings,
            )
            final = _int(outcome.get("final_seed"))
            if final is None or not 0 <= final <= RANDOM_SIZE:
                raise ValueError("invalid Classic final_seed")
            row["replayed_final_seed"] = final
            row["replay_cycles"] = _int(outcome.get("cycles"))
            row["replay_status"] = "supported"
            counts["replay_supported"] += 1
        except (ReplayUnsupported, ValueError) as exc:
            row["replay_error"] = str(exc)
            counts["replay_unresolved"] += 1
        rows.append(row)
    if not rows:
        raise ValueError("target has no VCR cases")

    transitions: list[dict[str, Any]] = []
    for previous, current in zip(rows, rows[1:]):
        final = previous["replayed_final_seed"]
        delta = (
            (current["factual_seed"] - final) % RANDOM_SIZE
            if final is not None else None
        )
        adjacent = current["vcr_id"] == previous["vcr_id"] + 1
        same_site = (previous["site"] is not None and
                     previous["site"] == current["site"])
        row = {
            "from_vcr_id": previous["vcr_id"],
            "to_vcr_id": current["vcr_id"],
            "globally_adjacent": adjacent,
            "same_site_observed": same_site,
            "prior_replay_final_seed": final,
            "next_observed_start_seed": current["factual_seed"],
            "wrapped_delta_mod_119": delta,
            "naive_same_seed": delta == 0 if delta is not None else None,
            "naive_plus_one": delta == 1 if delta is not None else None,
        }
        transitions.append(row)
        counts["transitions"] += 1
        if adjacent and delta is not None:
            counts["adjacent_comparable"] += 1
            counts[
                "adjacent_same" if delta == 0 else
                "adjacent_plus_one" if delta == 1 else
                "adjacent_neither"
            ] += 1
    counts["observed_vcrs"] = len(rows)
    return {
        "schema": SCHEMA, "status": "OBSERVATIONAL_NOT_PROMOTED",
        "game_id": game_id, "battle_turn": turn, "database_path": db_path,
        "classic_rng_size": RANDOM_SIZE,
        "summary": dict(sorted(counts.items())),
        "vcrs": rows, "transitions": transitions,
        "evidence_boundary": (
            "All seeds and VCR inputs are factual observations. Replay "
            "final_seed describes only the within-VCR Classic simulation. "
            "The actual Host's global seed initialization, intermediate RNG "
            "draws and right-side +360 bonus decision are not reconstructed. "
            "This diagnostic does not predict N+1 or feed any observation "
            "back to the executor; matching a naive hypothesis is not proof "
            "of global RNG continuity."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--corpus-db-generation", required=True)
    p.add_argument("--game-id", type=int, default=400330)
    p.add_argument("--battle-turn", type=int, default=141)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        conn, path = connect_compact_generation_read_only(
            args.corpus_db_generation, args.corpus_db_root
        )
        try:
            cases = combat_vcr_cases_for_turns(
                conn, game_id=args.game_id, battle_turns={args.battle_turn}
            )
        finally:
            conn.close()
        report = build_report(
            cases=cases, turn=args.battle_turn,
            game_id=args.game_id, db_path=str(path),
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("===== CLASSIC SEED CONTINUITY AUDIT V1 =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    for row in report["transitions"]:
        print(
            f"V{row['from_vcr_id']}->V{row['to_vcr_id']} "
            f"replay_final={row['prior_replay_final_seed']} "
            f"next_start={row['next_observed_start_seed']} "
            f"delta={row['wrapped_delta_mod_119']} "
            f"same={row['naive_same_seed']} "
            f"plus_one={row['naive_plus_one']}"
        )
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
