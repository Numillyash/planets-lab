from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from planets_lab.corpus.feature_index import (
    load_feature_rows,
    profile_selection_summary,
)


CHAIN_TOOL = Path(__file__).with_name("combat_ship_chain_audit.py")
spec = importlib.util.spec_from_file_location("combat_ship_chain_audit", CHAIN_TOOL)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {CHAIN_TOOL}")
chain_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain_audit)

DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_FEATURE_INDEX = Path("validation/corpus/compiled/v1/metadata/game_features.parquet")
DEFAULT_SCOPE_PROFILE = "combat-planar-no-horwasp"
CARRY_FIELDS = ("damage", "crew", "torpedoes", "fighters")


def _counter(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): value
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _gap_bucket(gap: int) -> str:
    if gap <= 1:
        return "1"
    if gap <= 3:
        return "2-3"
    if gap <= 10:
        return "4-10"
    return ">10"


def _scope(
    game_id: int,
    *,
    selected_ids: set[int],
    unknown_ids: set[int],
) -> str:
    if game_id in unknown_ids:
        return "profile_unknown"
    if game_id in selected_ids:
        return "profile_selected"
    return "profile_excluded"


def _problem_signature(comparison: Mapping[str, Any]) -> str:
    status = str(comparison.get("status", "unknown"))
    if status == "reappearance_after_defeat":
        return status
    fields = comparison.get("carry_mismatches")
    carry = tuple(str(item) for item in fields) if isinstance(fields, list) else ()
    shield = comparison.get("shield")
    shield_model = (
        str(shield.get("model"))
        if isinstance(shield, Mapping)
        else "unknown"
    )
    parts = list(carry)
    if shield_model == "mismatch":
        parts.append("shield")
    return "+".join(parts) if parts else status


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _delta_from_carry(comparison: Mapping[str, Any], field: str) -> int | None:
    carry = comparison.get("carry")
    if not isinstance(carry, Mapping):
        return None
    values = carry.get(field)
    if not isinstance(values, Mapping):
        return None
    terminal = _int(values.get("terminal"))
    next_start = _int(values.get("next_start"))
    if terminal is None or next_start is None:
        return None
    return next_start - terminal


def _shield_delta(comparison: Mapping[str, Any]) -> int | None:
    shield = comparison.get("shield")
    if not isinstance(shield, Mapping):
        return None
    terminal = _int(shield.get("terminal"))
    next_start = _int(shield.get("next_start"))
    if terminal is None or next_start is None:
        return None
    return next_start - terminal


def _status_counts_for_games(
    games: Mapping[str, Mapping[str, Any]],
    game_ids: set[int],
) -> Counter[str]:
    result: Counter[str] = Counter()
    for raw_game_id, values in games.items():
        game_id = int(raw_game_id)
        if game_id not in game_ids:
            continue
        for key in ("same_location_transitions", "match", "mismatch", "not_comparable", "reappearance_after_defeat"):
            value = _int(values.get(key))
            if value is not None:
                result[key] += value
    return result


def _scope_selection(args: argparse.Namespace) -> dict[str, Any] | None:
    feature_index = getattr(args, "feature_index", None)
    if feature_index is None:
        return None
    rows = load_feature_rows(Path(feature_index))
    return profile_selection_summary(
        rows,
        profile=getattr(args, "scope_profile", DEFAULT_SCOPE_PROFILE),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_args = argparse.Namespace(
        archive_dir=args.archive_dir,
        archive=list(args.archive),
        output=None,
        detail_limit=1_000_000,
        sample_limit=1_000_000,
        feature_index=None,
        feature_profile="all-indexed",
    )
    base = chain_audit.run(base_args)
    problems = list(base.get("mismatch_details") or [])
    race1 = list(base.get("race1_samples") or [])

    selection = _scope_selection(args)
    games = base.get("games")
    games = games if isinstance(games, Mapping) else {}
    all_game_ids = {int(game_id) for game_id in games}
    if selection is None:
        selected_ids = set(all_game_ids)
        excluded_ids: set[int] = set()
        unknown_ids: set[int] = set()
    else:
        selected_ids = set(selection["included_game_ids"])
        excluded_ids = set(selection["excluded_game_ids"])
        unknown_ids = set(selection["unknown_game_ids"])

    by_scope_status: dict[str, Counter[str]] = defaultdict(Counter)
    by_scope_signature: dict[str, Counter[str]] = defaultdict(Counter)
    by_scope_race: dict[str, Counter[int]] = defaultdict(Counter)
    by_scope_hull: dict[str, Counter[int]] = defaultdict(Counter)
    by_scope_side: dict[str, Counter[str]] = defaultdict(Counter)
    by_scope_gap: dict[str, Counter[str]] = defaultdict(Counter)
    by_scope_field_delta: dict[str, dict[str, Counter[int]]] = defaultdict(
        lambda: {field: Counter() for field in CARRY_FIELDS}
    )
    by_scope_shield_delta: dict[str, Counter[int]] = defaultdict(Counter)
    by_scope_self_class: dict[str, Counter[str]] = defaultdict(Counter)

    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in problems:
        if not isinstance(item, Mapping):
            continue
        game_id = int(item["game_id"])
        scope = _scope(game_id, selected_ids=selected_ids, unknown_ids=unknown_ids)
        comparison = item.get("comparison")
        if not isinstance(comparison, Mapping):
            continue
        status = str(comparison.get("status", "unknown"))
        signature = _problem_signature(comparison)
        by_scope_status[scope][status] += 1
        by_scope_signature[scope][signature] += 1

        race_id = _int(item.get("race_id"))
        hull_id = _int(item.get("hull_id"))
        if race_id is not None:
            by_scope_race[scope][race_id] += 1
        if hull_id is not None:
            by_scope_hull[scope][hull_id] += 1

        from_side = str(item.get("from_side", "?"))
        to_side = str(item.get("to_side", "?"))
        by_scope_side[scope][f"{from_side}->{to_side}"] += 1
        from_vcr = _int(item.get("from_vcr"))
        to_vcr = _int(item.get("to_vcr"))
        if from_vcr is not None and to_vcr is not None:
            by_scope_gap[scope][_gap_bucket(max(0, to_vcr - from_vcr))] += 1

        if race_id == 12:
            self_class = "race12"
        elif hull_id is not None and hull_id >= 1000:
            self_class = "hull_ge_1000"
        else:
            self_class = "ordinary_id_self"
        by_scope_self_class[scope][self_class] += 1

        for field in CARRY_FIELDS:
            delta = _delta_from_carry(comparison, field)
            if delta is not None:
                by_scope_field_delta[scope][field][delta] += 1
        shield_delta = _shield_delta(comparison)
        if shield_delta is not None:
            by_scope_shield_delta[scope][shield_delta] += 1

        if len(examples[scope]) < args.sample_limit:
            examples[scope].append(
                {
                    "game_id": game_id,
                    "turn": item.get("turn"),
                    "ship_id": item.get("ship_id"),
                    "race_id": race_id,
                    "hull_id": hull_id,
                    "from_vcr": from_vcr,
                    "to_vcr": to_vcr,
                    "side": f"{from_side}->{to_side}",
                    "status": status,
                    "signature": signature,
                    "carry_deltas": {
                        field: _delta_from_carry(comparison, field)
                        for field in CARRY_FIELDS
                    },
                    "shield_delta": shield_delta,
                }
            )

    race1_models: Counter[str] = Counter()
    race1_status: Counter[str] = Counter()
    race1_shield_deltas: Counter[int] = Counter()
    race1_terminal_to_next: Counter[str] = Counter()
    for item in race1:
        if not isinstance(item, Mapping):
            continue
        comparison = item.get("comparison")
        if not isinstance(comparison, Mapping):
            continue
        race1_status[str(comparison.get("status", "unknown"))] += 1
        shield = comparison.get("shield")
        if not isinstance(shield, Mapping):
            continue
        race1_models[str(shield.get("model", "unknown"))] += 1
        terminal = _int(shield.get("terminal"))
        next_start = _int(shield.get("next_start"))
        if terminal is not None and next_start is not None:
            race1_shield_deltas[next_start - terminal] += 1
            race1_terminal_to_next[f"{terminal}->{next_start}"] += 1

    selected_status = _status_counts_for_games(games, selected_ids)
    excluded_status = _status_counts_for_games(games, excluded_ids)
    unknown_status = _status_counts_for_games(games, unknown_ids)

    def scope_payload(scope: str, status_counts: Counter[str]) -> dict[str, Any]:
        return {
            "status": dict(status_counts),
            "problem_status": _counter(by_scope_status[scope]),
            "problem_signatures": _counter(by_scope_signature[scope]),
            "problem_races": _counter(by_scope_race[scope]),
            "problem_hulls": _counter(by_scope_hull[scope]),
            "problem_side_transitions": _counter(by_scope_side[scope]),
            "problem_vcr_gap_buckets": _counter(by_scope_gap[scope]),
            "problem_self_classes": _counter(by_scope_self_class[scope]),
            "field_deltas_next_minus_terminal": {
                field: _counter(by_scope_field_delta[scope][field])
                for field in CARRY_FIELDS
            },
            "shield_deltas_next_minus_terminal": _counter(by_scope_shield_delta[scope]),
            "samples": examples[scope],
        }

    return {
        "schema": "planets-lab.combat-ship-chain-cluster-audit.v2",
        "read_only": True,
        "source_chain_schema": base.get("schema"),
        "source_summary": base.get("summary"),
        "scope_selection": selection,
        "scopes": {
            "profile_selected": scope_payload("profile_selected", selected_status),
            "profile_excluded": scope_payload("profile_excluded", excluded_status),
            "profile_unknown": scope_payload("profile_unknown", unknown_status),
        },
        "race1_shield": {
            "transitions": len(race1),
            "status": _counter(race1_status),
            "models": _counter(race1_models),
            "deltas_next_minus_terminal": _counter(race1_shield_deltas),
            "terminal_to_next": _counter(race1_terminal_to_next),
        },
        "notes": [
            "This diagnostic clusters C3 differential failures; it does not change combat mechanics.",
            "Scope classification comes from the feature-index profile; no game id is special-cased.",
            "Field deltas are factual next-VCR start minus deterministic previous-VCR terminal state.",
            "Race-1 shield models are observational candidates only; no Federation rule is promoted here.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cluster C3 ship-chain differential mismatches without changing mechanics."
    )
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--archive", action="append", default=[])
    parser.add_argument(
        "--feature-index",
        type=Path,
        default=DEFAULT_FEATURE_INDEX,
        help="Compiled game feature index used only to classify report scopes.",
    )
    parser.add_argument(
        "--scope-profile",
        default=DEFAULT_SCOPE_PROFILE,
        help="Feature-index profile defining the clean combat scope.",
    )
    parser.add_argument("--sample-limit", type=int, default=12)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")

    print("===== SHIP COMBAT CHAIN MISMATCH CLUSTERS =====")
    print(f"source_summary: {report['source_summary']}")
    for scope_name, scope in report["scopes"].items():
        print(f"\n===== {scope_name} =====")
        for key in (
            "status",
            "problem_status",
            "problem_signatures",
            "problem_races",
            "problem_hulls",
            "problem_side_transitions",
            "problem_vcr_gap_buckets",
            "problem_self_classes",
            "field_deltas_next_minus_terminal",
            "shield_deltas_next_minus_terminal",
        ):
            print(f"{key}: {scope[key]}")
    print("\n===== RACE 1 SHIELD =====")
    for key, value in report["race1_shield"].items():
        print(f"{key}: {value}")
    if args.output is not None:
        print(f"output: {args.output}")
    print("NOTE: clustering only; no combat rule is changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
