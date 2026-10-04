#!/usr/bin/env python3
"""Secondary held-out differential for frozen post-capture history candidates.

The candidate definitions were frozen on discovery before this tool existed.
This public held-out partition was previously opened elsewhere for capture-side
LEFT/RIGHT work, so this is a secondary discriminator rather than pristine
independent validation.

The factual N+1 opponent identity is comparator-only.  LEFT/RIGHT is ignored.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

from postcapture_occurrence_candidates import (
    Candidate,
    select_attacker_appearance_count,
    select_fresh_attacker_boolean,
    select_pair_occurrence_round,
    select_static_cap2,
    select_static_priority,
)


SCHEMA = "planets-lab.postcapture-occurrence-round-heldout.v1"
DEFAULT_MAIN_ROOT = Path("/workspace")
DEFAULT_CORPUS_DB_ROOT = Path("/corpus-db")
DEFAULT_HELDOUT = Path(
    "/workspace/artifacts/public-capture-side/heldout-capture-side.json"
)
DEFAULT_OUTPUT = Path(
    "/research/artifacts/external-sources/postcapture-occurrence/"
    "heldout-occurrence-round.json"
)


Selector = Callable[[Sequence[Candidate]], Candidate | None]


SELECTORS: tuple[tuple[str, Selector], ...] = (
    ("static_priority", select_static_priority),
    ("static_cap2", select_static_cap2),
    ("pair_occurrence_round", select_pair_occurrence_round),
    ("fresh_attacker_boolean", select_fresh_attacker_boolean),
    ("attacker_appearance_count", select_attacker_appearance_count),
)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load_main_modules(main_root: Path):
    diagnostics = main_root / "tools" / "diagnostics"
    source = main_root / "src"
    if not diagnostics.is_dir() or not source.is_dir():
        raise ValueError(f"canonical main checkout incomplete: {main_root}")
    sys.path.insert(0, str(diagnostics))
    sys.path.insert(0, str(source))
    oprobe = importlib.import_module("combat_public_capture_o_layer_probe")
    active = importlib.import_module(
        "combat_host_post_capture_active_membership_audit"
    )
    return oprobe, active


def _history_counts(
    *,
    factual_queue: Sequence[Mapping[str, Any]],
    through_vcr_id: int,
) -> tuple[Counter[tuple[int, int]], Counter[int]]:
    pair_counts: Counter[tuple[int, int]] = Counter()
    appearances: Counter[int] = Counter()
    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        pair = row.get("pair")
        if not _is_int(vcr_id) or int(vcr_id) > through_vcr_id:
            continue
        if (
            not isinstance(pair, Sequence)
            or isinstance(pair, (str, bytes))
            or len(pair) != 2
            or not all(_is_int(value) for value in pair)
        ):
            continue
        a, b = int(pair[0]), int(pair[1])
        pair_counts[tuple(sorted((a, b)))] += 1
        appearances[a] += 1
        appearances[b] += 1
    return pair_counts, appearances


def _priority(value: Any) -> tuple[int, int, int] | None:
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == 3
        and all(_is_int(item) for item in value)
    ):
        return tuple(int(item) for item in value)
    return None


def _qualified(active_result: Mapping[str, Any]) -> bool:
    return (
        active_result.get("status") == "resolved"
        and all(
            active_result.get(name) is True
            for name in (
                "factual_opponent_active",
                "factual_opponent_candidate_resolved",
                "factual_opponent_requests_new_owner",
                "factual_opponent_strict_permission",
            )
        )
        and _is_int(active_result.get("factual_opponent_strict_rank"))
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    oprobe, active_module = _load_main_modules(args.main_root)
    report = oprobe._load_capture_side_report(
        args.heldout,
        expected_partition="heldout",
    )
    observations = [
        dict(row)
        for row in report["observations"]
        if isinstance(row, Mapping)
    ]

    scan_ids_raw = report.get("scanned_game_ids")
    if (
        not isinstance(scan_ids_raw, Sequence)
        or isinstance(scan_ids_raw, (str, bytes))
    ):
        raise ValueError("heldout scanned_game_ids missing")
    scan_ids = {int(value) for value in scan_ids_raw if _is_int(value)}
    if not scan_ids:
        raise ValueError("heldout game population empty")

    targets = oprobe._targets_by_site(observations)
    battle_turns_by_game: dict[int, set[int]] = defaultdict(set)
    for game_id, battle_turn, _x, _y in targets:
        battle_turns_by_game[int(game_id)].add(int(battle_turn))

    connection, database_path = oprobe.connect_current_compact_read_only(
        args.corpus_db_root
    )
    try:
        appearances: list[dict[str, Any]] = []
        appearance_summary: Counter[str] = Counter()
        for game_id in sorted(scan_ids):
            rows, summary = oprobe._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=game_id,
                battle_turns=battle_turns_by_game.get(game_id, set()),
            )
            appearances.extend(rows)
            for key, value in summary.items():
                if _is_int(value):
                    appearance_summary[str(key)] += int(value)
        appearances_by_key = oprobe._appearance_mapping(appearances)

        counts: Counter[str] = Counter()
        cases: list[dict[str, Any]] = []

        def observer(context: Mapping[str, Any]) -> None:
            site_key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            factual_queue_raw = context.get("factual_queue")
            if (
                not isinstance(factual_queue_raw, Sequence)
                or isinstance(factual_queue_raw, (str, bytes))
            ):
                return
            factual_queue = [
                item
                for item in factual_queue_raw
                if isinstance(item, Mapping)
            ]

            for row in targets.get(site_key, ()):
                capture_vcr = row.get("capture_vcr_id")
                next_vcr = row.get("next_vcr_id")
                prize_id = row.get("captured_ship_id")
                factual_id = row.get("next_opponent_ship_id")
                if not all(
                    _is_int(value)
                    for value in (capture_vcr, next_vcr, prize_id, factual_id)
                ):
                    counts["status:shape_unresolved"] += 1
                    continue

                capture_vcr = int(capture_vcr)
                next_vcr = int(next_vcr)
                prize_id = int(prize_id)
                factual_id = int(factual_id)

                if next_vcr != capture_vcr + 1:
                    counts["status:not_comparable_nonadjacent"] += 1
                    continue
                counts["adjacent_rows"] += 1

                capture = oprobe._capture_projection(row)
                active_result = active_module._simulate_capture(
                    context=context,
                    capture=capture,
                    appearances=appearances_by_key,
                )

                if not _qualified(active_result):
                    counts["status:dependency_not_qualified"] += 1
                    cases.append(
                        {
                            "game_id": site_key[0],
                            "turn": site_key[1],
                            "x": site_key[2],
                            "y": site_key[3],
                            "capture_vcr_id": capture_vcr,
                            "next_vcr_id": next_vcr,
                            "captured_ship_id": prize_id,
                            "factual_opponent_ship_id": factual_id,
                            "status": "dependency_not_qualified",
                            "active_status": active_result.get("status"),
                            "active_reason": active_result.get("reason"),
                            "factual_strict_rank": active_result.get(
                                "factual_opponent_strict_rank"
                            ),
                        }
                    )
                    continue

                counts["status:qualified"] += 1
                pair_counts, ship_appearances = _history_counts(
                    factual_queue=factual_queue,
                    through_vcr_id=capture_vcr,
                )

                raw_candidates = active_result.get("candidates")
                if (
                    not isinstance(raw_candidates, Sequence)
                    or isinstance(raw_candidates, (str, bytes))
                ):
                    counts["status:candidates_missing"] += 1
                    continue

                model_candidates: list[Candidate] = []
                candidate_details: list[dict[str, Any]] = []
                for candidate in raw_candidates:
                    if not isinstance(candidate, Mapping):
                        continue
                    if candidate.get("strict_permission") is not True:
                        continue
                    ship_id = candidate.get("ship_id")
                    priority = _priority(candidate.get("priority"))
                    if not _is_int(ship_id) or priority is None:
                        continue
                    ship_id = int(ship_id)
                    pair_key = tuple(sorted((prize_id, ship_id)))
                    model = Candidate(
                        ship_id=ship_id,
                        priority=priority,
                        pair_occurrences=int(pair_counts[pair_key]),
                        attacker_appearances=int(ship_appearances[ship_id]),
                    )
                    model_candidates.append(model)
                    candidate_details.append(
                        {
                            "ship_id": ship_id,
                            "priority": list(priority),
                            "pair_occurrences": model.pair_occurrences,
                            "attacker_appearances": model.attacker_appearances,
                            "is_factual": ship_id == factual_id,
                        }
                    )

                if not model_candidates:
                    counts["status:no_strict_candidates"] += 1
                    continue

                predictions: dict[str, int | None] = {}
                for name, selector in SELECTORS:
                    selected = selector(model_candidates)
                    predicted_id = (
                        selected.ship_id if selected is not None else None
                    )
                    predictions[name] = predicted_id
                    exact = predicted_id == factual_id
                    counts[f"{name}:exact"] += int(exact)
                    counts[f"{name}:mismatch"] += int(not exact)

                pair_pred = predictions["pair_occurrence_round"]
                fresh_pred = predictions["fresh_attacker_boolean"]
                count_pred = predictions["attacker_appearance_count"]
                pair_vs_bool = pair_pred != fresh_pred
                pair_vs_count = pair_pred != count_pred
                if pair_vs_bool:
                    counts["pair_vs_fresh_boolean:divergent"] += 1
                else:
                    counts["pair_vs_fresh_boolean:same"] += 1
                if pair_vs_count:
                    counts["pair_vs_appearance_count:divergent"] += 1
                else:
                    counts["pair_vs_appearance_count:same"] += 1

                if (
                    pair_vs_bool
                    or pair_vs_count
                ):
                    counts["informative_divergence_rows"] += 1

                mismatch_selectors = [
                    name
                    for name, predicted in predictions.items()
                    if predicted != factual_id
                ]

                cases.append(
                    {
                        "game_id": site_key[0],
                        "turn": site_key[1],
                        "x": site_key[2],
                        "y": site_key[3],
                        "capture_vcr_id": capture_vcr,
                        "next_vcr_id": next_vcr,
                        "captured_ship_id": prize_id,
                        "factual_opponent_ship_id": factual_id,
                        "status": "qualified",
                        "factual_static_rank": active_result.get(
                            "factual_opponent_strict_rank"
                        ),
                        "strict_requester_order": active_result.get(
                            "strict_requester_order"
                        ),
                        "candidates": sorted(
                            candidate_details,
                            key=lambda item: tuple(item["priority"]),
                        ),
                        "predictions": predictions,
                        "mismatch_selectors": mismatch_selectors,
                        "pair_vs_fresh_boolean_divergent": pair_vs_bool,
                        "pair_vs_appearance_count_divergent": pair_vs_count,
                    }
                )

        targeted_summaries: list[dict[str, Any]] = []
        for game_id in sorted(scan_ids):
            print(
                "progress: stage=occurrence_heldout "
                f"game_id={game_id} status=start",
                flush=True,
            )
            summary = oprobe._visit_targeted_site_contexts(
                connection=connection,
                game_id=game_id,
                targets=targets,
                appearances=appearances,
                observer=observer,
            )
            targeted_summaries.append({"game_id": game_id, **summary})
            print(
                "progress: stage=occurrence_heldout "
                f"game_id={game_id} sites={summary['visited_sites']} status=done",
                flush=True,
            )

        return {
            "schema": SCHEMA,
            "partition": "heldout",
            "evidence_status": "SECONDARY_HELDOUT_DISCRIMINATOR",
            "database_path": str(database_path),
            "source_capture_side_report": str(args.heldout),
            "summary": {
                "counts": dict(sorted(counts.items())),
                "appearance_summary": dict(sorted(appearance_summary.items())),
                "targeted_site_context": targeted_summaries,
            },
            "cases": cases,
            "candidate_freeze": (
                "Candidate definitions are exactly those frozen after discovery "
                "and before queue-specific held-out evaluation."
            ),
            "evidence_boundary": (
                "Secondary held-out pair/opponent discriminator. This public "
                "partition was previously opened elsewhere for capture-side "
                "LEFT/RIGHT research, so it is not pristine independent "
                "validation. The present history-aware pair selector was derived "
                "only from discovery. Factual N+1 opponent identity is used only "
                "for qualification/comparison; factual LEFT/RIGHT is ignored."
            ),
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, default=DEFAULT_MAIN_ROOT)
    parser.add_argument(
        "--corpus-db-root",
        type=Path,
        default=DEFAULT_CORPUS_DB_ROOT,
    )
    parser.add_argument("--heldout", type=Path, default=DEFAULT_HELDOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        c = report["summary"]["counts"]

        print("===== POST-CAPTURE OCCURRENCE CANDIDATES / HELDOUT =====")
        print(f"adjacent rows:             {c.get('adjacent_rows', 0)}")
        print(f"qualified rows:            {c.get('status:qualified', 0)}")
        print(
            "dependency not qualified:   "
            f"{c.get('status:dependency_not_qualified', 0)}"
        )
        print()
        for name, _selector in SELECTORS:
            print(
                f"{name:27s} "
                f"{c.get(name + ':exact', 0)} / "
                f"{c.get(name + ':mismatch', 0)}"
            )
        print()
        print(
            "pair vs fresh-bool divergent: "
            f"{c.get('pair_vs_fresh_boolean:divergent', 0)}"
        )
        print(
            "pair vs appearance-count divergent: "
            f"{c.get('pair_vs_appearance_count:divergent', 0)}"
        )
        print(
            "informative divergence rows: "
            f"{c.get('informative_divergence_rows', 0)}"
        )

        divergent = [
            row
            for row in report["cases"]
            if row.get("status") == "qualified"
            and (
                row.get("pair_vs_fresh_boolean_divergent") is True
                or row.get("pair_vs_appearance_count_divergent") is True
            )
        ]
        if divergent:
            print()
            print("DIVERGENCE ROWS:")
            for row in divergent:
                print(
                    f"  {row['game_id']}/T{row['turn']} "
                    f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                    f"prize={row['captured_ship_id']} "
                    f"factual={row['factual_opponent_ship_id']} "
                    f"predictions={row['predictions']}"
                )
                print(f"    candidates={row['candidates']}")

        mismatches = [
            row
            for row in report["cases"]
            if row.get("status") == "qualified"
            and row.get("mismatch_selectors")
        ]
        if mismatches:
            print()
            print("MISMATCH ROWS:")
            for row in mismatches:
                print(
                    f"  {row['game_id']}/T{row['turn']} "
                    f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                    f"prize={row['captured_ship_id']} "
                    f"factual={row['factual_opponent_ship_id']} "
                    f"mismatch={row['mismatch_selectors']} "
                    f"predictions={row['predictions']}"
                )

        print()
        print(f"output:                    {args.output}")
        print("LEFT/RIGHT was ignored.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
