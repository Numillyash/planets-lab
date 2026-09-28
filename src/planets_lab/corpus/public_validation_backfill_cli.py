from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .indexer import CorpusIndexError, load_manifest_jsonl
from .public_finished_discover_cli import (
    _int_value,
    _manifest_bucket,
    _merge_records,
    _tokenize,
    _write_json,
    _write_jsonl,
)


DEFAULT_BASELINE = Path("validation/corpus/manifests/accounts-recent-finished.jsonl")
DEFAULT_CANDIDATES = Path(
    "validation/corpus/manifests/public-validation-candidates.jsonl"
)
DEFAULT_SELECTED = Path(
    "validation/corpus/manifests/public-validation-selected.jsonl"
)
DEFAULT_STATS = Path("validation/corpus/index/public-validation-stats.json")
DEFAULT_SELECTION_REPORT = Path("artifacts/public-validation-corpus/selection-report.json")
DEFAULT_REJECTED = Path(
    "validation/corpus/manifests/public-validation-rejected.json"
)
DEFAULT_COMBINED = Path(
    "validation/corpus/manifests/public-validation-combined.jsonl"
)
DEFAULT_REPORT = Path("artifacts/public-validation-corpus/backfill-report.json")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    return list(load_manifest_jsonl(path.read_text(encoding="utf-8")))


def _game_id(record: Mapping[str, Any]) -> int:
    value = record.get("game_id")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("manifest record has invalid game_id")
    return int(value)


def _selection_target(
    report: Mapping[str, Any],
    current_selected: Sequence[Mapping[str, Any]],
) -> tuple[int, Counter[str]]:
    raw_count = report.get("selected_games")
    target_count = (
        int(raw_count)
        if isinstance(raw_count, int) and not isinstance(raw_count, bool) and raw_count > 0
        else len(current_selected)
    )

    raw_buckets = report.get("selected_by_bucket")
    target_buckets: Counter[str] = Counter()
    if isinstance(raw_buckets, Mapping):
        for key, value in raw_buckets.items():
            if (
                isinstance(key, str)
                and isinstance(value, int)
                and not isinstance(value, bool)
                and value > 0
            ):
                target_buckets[key] = int(value)

    if sum(target_buckets.values()) != target_count:
        target_buckets = Counter(_manifest_bucket(row) for row in current_selected)
        target_count = len(current_selected)

    return target_count, target_buckets


def _rejected_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": "planets-lab.public-validation-rejected.v1",
            "rejected_game_ids": [],
            "history": [],
        }
    payload = _load_json(path)
    ids = payload.get("rejected_game_ids")
    if not isinstance(ids, list):
        raise ValueError(f"{path}: rejected_game_ids must be a list")
    return payload


def _novelty_score(
    record: Mapping[str, Any],
    *,
    seen_tokens: set[str],
    bucket_gap: int,
) -> tuple[float, float, float, float]:
    tokens = _tokenize(record)
    novelty = sum(
        weight
        for token, weight in tokens.items()
        if token not in seen_tokens
    )
    game = record.get("game")
    game = game if isinstance(game, Mapping) else {}
    size_bonus = min(_int_value(game, "turn"), 250) / 20.0
    slot_bonus = min(_int_value(game, "slots"), 30) / 4.0
    # Exact replacement of a missing coverage bucket dominates general novelty.
    bucket_bonus = 1000.0 if bucket_gap > 0 else 0.0
    return (
        bucket_bonus + novelty + size_bonus + slot_bonus,
        novelty,
        size_bonus,
        slot_bonus,
    )


def _select_backfill(
    *,
    candidates: Sequence[Mapping[str, Any]],
    baseline: Sequence[Mapping[str, Any]],
    successful: Sequence[Mapping[str, Any]],
    rejected_ids: set[int],
    target_count: int,
    target_buckets: Counter[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    selected_ids = {_game_id(row) for row in successful}
    remaining = [
        dict(row)
        for row in candidates
        if _game_id(row) not in selected_ids
        and _game_id(row) not in rejected_ids
    ]

    seen_tokens: set[str] = set()
    for row in (*baseline, *successful):
        seen_tokens.update(_tokenize(row))

    current_buckets = Counter(_manifest_bucket(row) for row in successful)
    replacements: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []

    while len(successful) + len(replacements) < target_count and remaining:
        best_index: int | None = None
        best_key: tuple[float, int, int] | None = None
        best_detail: tuple[float, float, float, float] | None = None

        for index, record in enumerate(remaining):
            bucket = _manifest_bucket(record)
            gap = max(target_buckets.get(bucket, 0) - current_buckets[bucket], 0)
            detail = _novelty_score(
                record,
                seen_tokens=seen_tokens,
                bucket_gap=gap,
            )
            game = record.get("game")
            game = game if isinstance(game, Mapping) else {}
            game_id = _game_id(record)
            key = (
                detail[0],
                _int_value(game, "turn"),
                game_id,
            )
            if best_key is None or key > best_key:
                best_index = index
                best_key = key
                best_detail = detail

        assert best_index is not None
        assert best_detail is not None
        record = remaining.pop(best_index)
        game_id = _game_id(record)
        bucket = _manifest_bucket(record)
        gap_before = max(target_buckets.get(bucket, 0) - current_buckets[bucket], 0)
        replacements.append(record)
        current_buckets[bucket] += 1
        seen_tokens.update(_tokenize(record))

        game = record.get("game")
        game = game if isinstance(game, Mapping) else {}
        report_rows.append(
            {
                "game_id": game_id,
                "name": game.get("name"),
                "turn": game.get("turn"),
                "slots": game.get("slots"),
                "gametype": game.get("gametype"),
                "bucket": bucket,
                "target_bucket_gap_before": gap_before,
                "score": best_detail[0],
                "novelty": best_detail[1],
                "turn_bonus": best_detail[2],
                "slot_bonus": best_detail[3],
            }
        )

    return replacements, report_rows, current_buckets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replace failed public validation games with untried loadinfo "
            "candidates while preserving the original ruleset bucket targets."
        )
    )
    parser.add_argument("--baseline-manifest", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--candidates-manifest", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--selected-manifest", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    parser.add_argument(
        "--selection-report",
        type=Path,
        default=DEFAULT_SELECTION_REPORT,
    )
    parser.add_argument("--rejected", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--combined-output", type=Path, default=DEFAULT_COMBINED)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        baseline = _load_manifest(args.baseline_manifest)
        candidates = _load_manifest(args.candidates_manifest)
        selected = _load_manifest(args.selected_manifest)
        stats = _load_json(args.stats)
        selection_report = _load_json(args.selection_report)
        rejected_state = _rejected_state(args.rejected)

        raw_failed = stats.get("failed_game_ids")
        if not isinstance(raw_failed, list):
            raise ValueError(f"{args.stats}: failed_game_ids must be a list")
        failed_ids = {
            int(game_id)
            for game_id in raw_failed
            if isinstance(game_id, int) and not isinstance(game_id, bool) and game_id > 0
        }

        raw_rejected = rejected_state.get("rejected_game_ids", [])
        rejected_ids = {
            int(game_id)
            for game_id in raw_rejected
            if isinstance(game_id, int) and not isinstance(game_id, bool) and game_id > 0
        }
        rejected_ids.update(failed_ids)

        target_count, target_buckets = _selection_target(
            selection_report,
            selected,
        )
        successful = [
            dict(record)
            for record in selected
            if _game_id(record) not in failed_ids
            and _game_id(record) not in rejected_ids - failed_ids
        ]
        successful_ids = {_game_id(row) for row in successful}

        replacements, replacement_rows, final_buckets = _select_backfill(
            candidates=candidates,
            baseline=baseline,
            successful=successful,
            rejected_ids=rejected_ids,
            target_count=target_count,
            target_buckets=target_buckets,
        )

        next_selected = [*successful, *replacements]
        next_selected.sort(key=_game_id)
        combined = _merge_records(baseline, next_selected)

        args.selected_manifest.parent.mkdir(parents=True, exist_ok=True)
        _write_jsonl(args.selected_manifest, next_selected)
        _write_jsonl(args.combined_output, combined)

        history = rejected_state.get("history")
        history = list(history) if isinstance(history, list) else []
        history.append(
            {
                "failed_game_ids": sorted(failed_ids),
                "successful_game_ids": sorted(successful_ids),
                "replacement_game_ids": [_game_id(row) for row in replacements],
            }
        )
        rejected_payload = {
            "schema": "planets-lab.public-validation-rejected.v1",
            "rejected_game_ids": sorted(rejected_ids),
            "history": history,
        }
        _write_json(args.rejected, rejected_payload)

        missing_bucket_counts = {
            bucket: max(count - final_buckets.get(bucket, 0), 0)
            for bucket, count in sorted(target_buckets.items())
            if max(count - final_buckets.get(bucket, 0), 0) > 0
        }
        report = {
            "schema": "planets-lab.public-validation-backfill.v1",
            "target_games": target_count,
            "current_failed_game_ids": sorted(failed_ids),
            "rejected_game_ids": sorted(rejected_ids),
            "successful_games_before_backfill": len(successful),
            "replacement_games": len(replacements),
            "selected_games_after_backfill": len(next_selected),
            "target_by_bucket": dict(sorted(target_buckets.items())),
            "selected_by_bucket_after_backfill": dict(sorted(final_buckets.items())),
            "missing_bucket_counts": missing_bucket_counts,
            "replacements": replacement_rows,
            "selected_manifest": str(args.selected_manifest),
            "combined_manifest": str(args.combined_output),
            "rejected_file": str(args.rejected),
        }
        _write_json(args.report_output, report)

        print("===== PUBLIC VALIDATION CORPUS BACKFILL =====")
        print(f"target_games:                  {target_count}")
        print(f"failed_this_round:             {len(failed_ids)}")
        print(f"rejected_total:                {len(rejected_ids)}")
        print(f"successful_before_backfill:    {len(successful)}")
        print(f"replacements_selected:         {len(replacements)}")
        print(f"selected_after_backfill:       {len(next_selected)}")
        print(f"target_by_bucket:              {dict(sorted(target_buckets.items()))}")
        print(
            "selected_by_bucket_after:      "
            f"{dict(sorted(final_buckets.items()))}"
        )
        print(f"missing_bucket_counts:         {missing_bucket_counts}")
        print(
            "replacement_game_ids:          "
            f"{[_game_id(row) for row in replacements]}"
        )
        print(f"report:                        {args.report_output}")
        return 0 if len(next_selected) == target_count else 1
    except (OSError, ValueError, CorpusIndexError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
