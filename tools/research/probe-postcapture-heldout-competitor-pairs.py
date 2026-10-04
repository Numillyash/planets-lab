#!/usr/bin/env python3
"""Targeted competitor-pair recomposition for held-out queue residuals.

This diagnoses the four frozen history-aware selector mismatches from the
secondary held-out run. It does not invent or fit a new selector.

For each row, the predicted competing requester is re-evaluated against the
captured prize through the same production pair-composition machinery and the
same captured-Friendly-Code bounds used by the canonical post-capture
pair-recomposition audit.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import importlib
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_MAIN_ROOT = Path("/workspace")
DEFAULT_CORPUS_DB_ROOT = Path("/corpus-db")
DEFAULT_CAPTURE_SIDE = Path(
    "/workspace/artifacts/public-capture-side/heldout-capture-side.json"
)
DEFAULT_OCCURRENCE = Path(
    "/research/artifacts/external-sources/postcapture-occurrence/"
    "heldout-occurrence-round.json"
)
DEFAULT_OUTPUT = Path(
    "/research/artifacts/external-sources/postcapture-occurrence/"
    "heldout-competitor-pair-recomposition.json"
)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("factual_opponent_ship_id", row.get("next_opponent_ship_id")),
    )
    if not all(_is_int(value) for value in values):
        return None
    return tuple(int(value) for value in values)  # type: ignore[return-value]


def _capture_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("next_opponent_ship_id"),
    )
    if not all(_is_int(value) for value in values):
        return None
    return tuple(int(value) for value in values)  # type: ignore[return-value]


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
    pair = importlib.import_module(
        "combat_host_post_capture_pair_recomposition_audit"
    )
    return oprobe, active, pair


def _history_projection(
    *,
    factual_queue: Sequence[Mapping[str, Any]],
    through_vcr_id: int,
    prize_id: int,
    competitor_id: int,
    factual_id: int,
) -> dict[str, Any]:
    pair_counts: Counter[tuple[int, int]] = Counter()
    ship_counts: Counter[int] = Counter()
    rows: list[dict[str, Any]] = []

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
        ship_counts[a] += 1
        ship_counts[b] += 1

        marks: list[str] = []
        if prize_id in (a, b):
            marks.append("prize")
        if competitor_id in (a, b):
            marks.append("competitor")
        if factual_id in (a, b):
            marks.append("factual")
        rows.append(
            {
                "vcr_id": int(vcr_id),
                "pair": [a, b],
                "marks": marks,
            }
        )

    def pair_count(a: int, b: int) -> int:
        return int(pair_counts[tuple(sorted((a, b)))])

    return {
        "pair_occurrences": {
            "prize_competitor": pair_count(prize_id, competitor_id),
            "prize_factual": pair_count(prize_id, factual_id),
            "competitor_factual": pair_count(competitor_id, factual_id),
        },
        "ship_appearances": {
            "prize": int(ship_counts[prize_id]),
            "competitor": int(ship_counts[competitor_id]),
            "factual": int(ship_counts[factual_id]),
        },
        "elapsed_vcrs": rows,
    }


def _candidate_by_id(
    active_result: Mapping[str, Any],
    ship_id: int,
) -> Mapping[str, Any] | None:
    rows = active_result.get("candidates")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
    ):
        return None
    for row in rows:
        if isinstance(row, Mapping) and row.get("ship_id") == ship_id:
            return row
    return None


def _int_positive(value: Any) -> int | None:
    if _is_int(value) and int(value) > 0:
        return int(value)
    return None


def _compose_candidate_pair(
    *,
    pair_module: Any,
    active_module: Any,
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
    active_result: Mapping[str, Any],
    opponent_id: int,
) -> dict[str, Any]:
    game_id = int(context["game_id"])
    before_turn = int(context["before_turn"])
    prize_id = int(capture["ship_id"])

    predictions = context.get("predictions")
    start_stacks = context.get("start_stacks")
    if not isinstance(predictions, Mapping) or not isinstance(start_stacks, Mapping):
        return {"status": "unresolved", "reason": "site_context_incomplete"}

    prize_entry = predictions.get(prize_id)
    opponent_entry = predictions.get(opponent_id)
    if not isinstance(prize_entry, Mapping):
        return {"status": "unresolved", "reason": "prize_prediction_missing"}
    if not isinstance(opponent_entry, Mapping):
        return {"status": "unresolved", "reason": "opponent_prediction_missing"}

    prize_old_raw = prize_entry.get("raw")
    opponent_raw = opponent_entry.get("raw")
    if not isinstance(prize_old_raw, Mapping):
        return {"status": "unresolved", "reason": "prize_orders_missing"}
    if not isinstance(opponent_raw, Mapping):
        return {"status": "unresolved", "reason": "opponent_orders_missing"}

    prize_owner = _int_positive(active_result.get("prize_owner_id_after_capture"))
    prize_hull = _int_positive(prize_entry.get("hull_id"))
    opponent_owner = _int_positive(opponent_entry.get("owner_id"))
    opponent_hull = _int_positive(opponent_entry.get("hull_id"))
    opponent_race = _int_positive(opponent_entry.get("race_id"))

    captor_id = _int_positive(capture.get("captor_ship_id"))
    capture_vcr_id = _int_positive(capture.get("from_vcr_id"))
    if captor_id is None or capture_vcr_id is None:
        return {
            "status": "unresolved",
            "reason": "capture_identity_missing_for_postcapture_race",
        }

    captor_appearance = active_module._appearance_index(
        appearances,
        game_id=game_id,
        battle_turn=int(context["battle_turn"]),
        vcr_id=capture_vcr_id,
        ship_id=captor_id,
    )
    if not isinstance(captor_appearance, Mapping):
        return {
            "status": "unresolved",
            "reason": "captor_appearance_missing_for_postcapture_race",
            "captor_ship_id": captor_id,
            "capture_vcr_id": capture_vcr_id,
        }
    prize_race = _int_positive(captor_appearance.get("race_id"))

    if any(
        value is None
        for value in (
            prize_owner,
            prize_race,
            prize_hull,
            opponent_owner,
            opponent_hull,
        )
    ):
        return {
            "status": "unresolved",
            "reason": "identity_or_hull_unresolved",
            "prize_owner": prize_owner,
            "prize_race_from_captor": prize_race,
            "prize_hull": prize_hull,
            "opponent_owner": opponent_owner,
            "opponent_race": opponent_race,
            "opponent_hull": opponent_hull,
        }

    assert prize_owner is not None
    assert prize_race is not None
    assert prize_hull is not None
    assert opponent_owner is not None
    assert opponent_hull is not None

    candidate = _candidate_by_id(active_result, opponent_id)
    if not isinstance(candidate, Mapping):
        return {"status": "unresolved", "reason": "candidate_missing"}

    opponent_interference = pair_module._interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=opponent_owner,
        raw=opponent_raw,
        start_stacks=start_stacks,
    )
    prize_interference = pair_module._interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=prize_owner,
        raw=prize_old_raw,
        start_stacks=start_stacks,
    )

    prize_hull_can_cloak = prize_entry.get("hull_can_cloak")
    opponent_hull_can_cloak = opponent_entry.get("hull_can_cloak")

    old_fc = prize_old_raw.get("friendlycode")
    fresh_fc = pair_module._nonmatching_symbolic_fc(
        opponent_raw.get("friendlycode")
    )

    def decision_for(prize_fc: Any) -> dict[str, Any]:
        prize_raw = pair_module._neutral_prize_raw(
            prize_old_raw,
            friendly_code=prize_fc,
        )
        prize_side = pair_module._candidate_input(
            game_id=game_id,
            ship_id=prize_id,
            owner_id=prize_owner,
            raw=prize_raw,
            race_id=prize_race,
            hull_id=prize_hull,
            hull_can_cloak=(
                bool(prize_hull_can_cloak)
                if isinstance(prize_hull_can_cloak, bool)
                else None
            ),
            diplomacy_allows_attack=False,
            interference_protected=prize_interference,
        )
        opponent_side = pair_module._candidate_input(
            game_id=game_id,
            ship_id=opponent_id,
            owner_id=opponent_owner,
            raw=opponent_raw,
            race_id=opponent_race,
            hull_id=opponent_hull,
            hull_can_cloak=(
                bool(opponent_hull_can_cloak)
                if isinstance(opponent_hull_can_cloak, bool)
                else None
            ),
            diplomacy_allows_attack=True,
            interference_protected=opponent_interference,
        )
        return pair_module._decision_projection(
            pair_module.decide_ship_combat_pair(
                left=prize_side,
                right=opponent_side,
                same_location=True,
            )
        )

    preserved = decision_for(old_fc)
    fresh = decision_for(fresh_fc)

    eligibility_invariant = (
        preserved.get("engagement_eligible")
        == fresh.get("engagement_eligible")
    )
    phase_invariant = (
        preserved.get("phase") == fresh.get("phase")
        and preserved.get("prestandard_kind") == fresh.get("prestandard_kind")
    )
    definitely_eligible = (
        preserved.get("engagement_eligible") is True
        and fresh.get("engagement_eligible") is True
        and phase_invariant
    )
    definitely_blocked = (
        preserved.get("engagement_eligible") is False
        and fresh.get("engagement_eligible") is False
    )

    return {
        "status": "resolved",
        "postcapture_identity": {
            "prize_owner_id": prize_owner,
            "prize_race_id_from_captor_vcr": prize_race,
            "prize_hull_id_preserved": prize_hull,
            "captor_ship_id": captor_id,
            "capture_vcr_id": capture_vcr_id,
        },
        "candidate": {
            "ship_id": opponent_id,
            "requests_new_owner": candidate.get("requests_new_owner"),
            "strict_permission": candidate.get("strict_permission"),
            "priority": candidate.get("priority"),
            "position_source": candidate.get("position_source"),
        },
        "opponent_orders": {
            key: opponent_raw.get(key)
            for key in (
                "mission",
                "enemy",
                "friendlycode",
                "neutronium",
                "warp",
                "mission1target",
            )
        },
        "prize_old_friendly_code": old_fc,
        "fresh_prize_friendly_code": fresh_fc,
        "preserved_fc_decision": preserved,
        "fresh_fc_decision": fresh,
        "eligibility_invariant": eligibility_invariant,
        "phase_invariant": phase_invariant,
        "definitely_eligible": definitely_eligible,
        "definitely_blocked": definitely_blocked,
        "fc_sensitive_or_unresolved": not (
            definitely_eligible or definitely_blocked
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    oprobe, active_module, pair_module = _load_main_modules(args.main_root)

    occurrence = _load(args.occurrence)
    if occurrence.get("partition") != "heldout":
        raise ValueError("occurrence artifact must be heldout")

    occurrence_cases = occurrence.get("cases")
    if (
        not isinstance(occurrence_cases, Sequence)
        or isinstance(occurrence_cases, (str, bytes))
    ):
        raise ValueError("occurrence cases missing")

    residual_cases = [
        row
        for row in occurrence_cases
        if isinstance(row, Mapping)
        and row.get("status") == "qualified"
        and isinstance(row.get("predictions"), Mapping)
        and row["predictions"].get("pair_occurrence_round")
        != row.get("factual_opponent_ship_id")
    ]
    if len(residual_cases) != 4:
        raise ValueError(
            f"expected four history-aware heldout residuals, got {len(residual_cases)}"
        )

    residual_by_key = {
        key: row
        for row in residual_cases
        if (key := _key(row)) is not None
    }
    if len(residual_by_key) != 4:
        raise ValueError("residual identity collision or malformed row")

    capture_report = oprobe._load_capture_side_report(
        args.capture_side,
        expected_partition="heldout",
    )
    capture_rows = [
        dict(row)
        for row in capture_report["observations"]
        if isinstance(row, Mapping)
        and _capture_key(row) in residual_by_key
    ]
    if len(capture_rows) != 4:
        raise ValueError(
            f"expected four capture-side join rows, got {len(capture_rows)}"
        )

    targets = oprobe._targets_by_site(capture_rows)
    battle_turns_by_game: dict[int, set[int]] = defaultdict(set)
    for game_id, battle_turn, _x, _y in targets:
        battle_turns_by_game[int(game_id)].add(int(battle_turn))

    scan_ids = sorted({int(row["game_id"]) for row in capture_rows})
    connection, database_path = oprobe.connect_current_compact_read_only(
        args.corpus_db_root
    )
    try:
        appearances: list[dict[str, Any]] = []
        for game_id in scan_ids:
            rows, _summary = oprobe._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=game_id,
                battle_turns=battle_turns_by_game.get(game_id, set()),
            )
            appearances.extend(rows)
        appearances_by_key = oprobe._appearance_mapping(appearances)

        results: list[dict[str, Any]] = []
        counts: Counter[str] = Counter()

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
                item for item in factual_queue_raw if isinstance(item, Mapping)
            ]

            for capture_row in targets.get(site_key, ()):
                ckey = _capture_key(capture_row)
                if ckey is None:
                    continue
                occurrence_row = residual_by_key.get(ckey)
                if not isinstance(occurrence_row, Mapping):
                    continue

                capture = oprobe._capture_projection(capture_row)
                active_result = active_module._simulate_capture(
                    context=context,
                    capture=capture,
                    appearances=appearances_by_key,
                )
                if active_result.get("status") != "resolved":
                    raise ValueError(
                        "targeted active replay unresolved: "
                        f"{active_result.get('reason')}"
                    )

                predictions = occurrence_row.get("predictions")
                assert isinstance(predictions, Mapping)
                competitor_id = predictions.get("pair_occurrence_round")
                factual_id = occurrence_row.get("factual_opponent_ship_id")
                prize_id = occurrence_row.get("captured_ship_id")
                capture_vcr = occurrence_row.get("capture_vcr_id")
                if not all(
                    _is_int(v)
                    for v in (
                        competitor_id,
                        factual_id,
                        prize_id,
                        capture_vcr,
                    )
                ):
                    raise ValueError("residual comparison identity malformed")

                competitor_id = int(competitor_id)
                factual_id = int(factual_id)
                prize_id = int(prize_id)
                capture_vcr = int(capture_vcr)

                competitor_pair = _compose_candidate_pair(
                    pair_module=pair_module,
                    active_module=active_module,
                    appearances=appearances_by_key,
                    context=context,
                    capture=capture,
                    active_result=active_result,
                    opponent_id=competitor_id,
                )
                factual_pair = _compose_candidate_pair(
                    pair_module=pair_module,
                    active_module=active_module,
                    appearances=appearances_by_key,
                    context=context,
                    capture=capture,
                    active_result=active_result,
                    opponent_id=factual_id,
                )

                history = _history_projection(
                    factual_queue=factual_queue,
                    through_vcr_id=capture_vcr,
                    prize_id=prize_id,
                    competitor_id=competitor_id,
                    factual_id=factual_id,
                )

                if competitor_pair.get("status") != "resolved":
                    counts["competitor:predecision_unresolved"] += 1
                elif competitor_pair.get("definitely_eligible") is True:
                    counts["competitor:definitely_eligible"] += 1
                elif competitor_pair.get("definitely_blocked") is True:
                    counts["competitor:definitely_blocked"] += 1
                else:
                    counts["competitor:fc_sensitive_or_unresolved"] += 1

                if factual_pair.get("status") != "resolved":
                    counts["factual:predecision_unresolved"] += 1
                elif factual_pair.get("definitely_eligible") is True:
                    counts["factual:definitely_eligible"] += 1
                elif factual_pair.get("definitely_blocked") is True:
                    counts["factual:definitely_blocked"] += 1
                else:
                    counts["factual:fc_sensitive_or_unresolved"] += 1

                results.append(
                    {
                        "game_id": int(occurrence_row["game_id"]),
                        "turn": int(occurrence_row["turn"]),
                        "x": int(occurrence_row["x"]),
                        "y": int(occurrence_row["y"]),
                        "capture_vcr_id": capture_vcr,
                        "next_vcr_id": int(occurrence_row["next_vcr_id"]),
                        "captured_ship_id": prize_id,
                        "predicted_competitor_id": competitor_id,
                        "factual_opponent_ship_id": factual_id,
                        "static_rank": occurrence_row.get(
                            "factual_static_rank"
                        ),
                        "strict_requester_order": occurrence_row.get(
                            "strict_requester_order"
                        ),
                        "history": history,
                        "competitor_pair": competitor_pair,
                        "factual_pair": factual_pair,
                    }
                )

        for game_id in scan_ids:
            print(
                "progress: stage=competitor_pair "
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
            print(
                "progress: stage=competitor_pair "
                f"game_id={game_id} sites={summary['visited_sites']} status=done",
                flush=True,
            )

        if len(results) != 4:
            raise ValueError(f"expected four targeted results, got {len(results)}")
        results.sort(key=lambda row: (row["game_id"], row["turn"], row["capture_vcr_id"]))

        return {
            "schema": "planets-lab.postcapture-heldout-competitor-pairs.v1",
            "partition": "heldout",
            "evidence_status": "SECONDARY_HELDOUT_RESIDUAL_DIAGNOSTIC",
            "database_path": str(database_path),
            "summary": dict(sorted(counts.items())),
            "cases": results,
            "evidence_boundary": (
                "Targeted diagnostic of the four frozen history-aware heldout "
                "selector mismatches. No new selector is fitted. The predicted "
                "competitor and factual opponent are independently recomposed "
                "against the captured prize through production pair mechanics "
                "under preserved-prize-FC and guaranteed-nonmatching fresh-FC "
                "bounds. Heldout LEFT/RIGHT is not used."
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
    parser.add_argument(
        "--capture-side",
        type=Path,
        default=DEFAULT_CAPTURE_SIDE,
    )
    parser.add_argument(
        "--occurrence",
        type=Path,
        default=DEFAULT_OCCURRENCE,
    )
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

        print("===== HELDOUT HISTORY-SELECTOR RESIDUAL PAIR RECOMPOSITION =====")
        print("summary:", report["summary"])
        print()
        for row in report["cases"]:
            comp = row["competitor_pair"]
            fact = row["factual_pair"]
            hist = row["history"]
            print(
                f"{row['game_id']}/T{row['turn']} "
                f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                f"prize={row['captured_ship_id']} "
                f"predicted={row['predicted_competitor_id']} "
                f"factual={row['factual_opponent_ship_id']}"
            )
            print(
                "  strict order: "
                + ", ".join(
                    str(v)
                    for v in (row.get("strict_requester_order") or [])
                )
            )
            print(
                "  history pair prize-predicted / prize-factual: "
                f"{hist['pair_occurrences']['prize_competitor']} / "
                f"{hist['pair_occurrences']['prize_factual']}"
            )
            print(
                "  history appearances predicted / factual: "
                f"{hist['ship_appearances']['competitor']} / "
                f"{hist['ship_appearances']['factual']}"
            )
            print(
                "  predicted pair: "
                f"status={comp.get('status')} "
                f"reason={comp.get('reason')} "
                f"eligible={comp.get('definitely_eligible')} "
                f"blocked={comp.get('definitely_blocked')} "
                f"fc_sensitive={comp.get('fc_sensitive_or_unresolved')}"
            )
            print(
                "    preserved: "
                f"eligible={comp.get('preserved_fc_decision', {}).get('engagement_eligible')} "
                f"phase={comp.get('preserved_fc_decision', {}).get('phase')} "
                f"reasons={comp.get('preserved_fc_decision', {}).get('unresolved_reasons')}"
            )
            print(
                "    fresh:     "
                f"eligible={comp.get('fresh_fc_decision', {}).get('engagement_eligible')} "
                f"phase={comp.get('fresh_fc_decision', {}).get('phase')} "
                f"reasons={comp.get('fresh_fc_decision', {}).get('unresolved_reasons')}"
            )
            print(
                "  factual pair: "
                f"status={fact.get('status')} "
                f"reason={fact.get('reason')} "
                f"eligible={fact.get('definitely_eligible')} "
                f"blocked={fact.get('definitely_blocked')} "
                f"fc_sensitive={fact.get('fc_sensitive_or_unresolved')}"
            )
            print(
                "    preserved: "
                f"eligible={fact.get('preserved_fc_decision', {}).get('engagement_eligible')} "
                f"phase={fact.get('preserved_fc_decision', {}).get('phase')} "
                f"reasons={fact.get('preserved_fc_decision', {}).get('unresolved_reasons')}"
            )
            print(
                "    fresh:     "
                f"eligible={fact.get('fresh_fc_decision', {}).get('engagement_eligible')} "
                f"phase={fact.get('fresh_fc_decision', {}).get('phase')} "
                f"reasons={fact.get('fresh_fc_decision', {}).get('unresolved_reasons')}"
            )
            print("  elapsed local VCRs:")
            for event in hist["elapsed_vcrs"]:
                marks = ",".join(event["marks"]) if event["marks"] else "-"
                print(
                    f"    VCR {event['vcr_id']}: {event['pair']} [{marks}]"
                )
            print()

        print(f"output: {args.output}")
        print("No new selector was fitted.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
