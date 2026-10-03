#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

DEFAULT_INPUT = Path(
    "artifacts/external-sources/afsim-r1/discovery-afsim-r1.json"
)


def _bool_label(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _id_side(prize_id: int, opponent_id: int) -> str | None:
    if prize_id == opponent_id:
        return None
    return "left" if prize_id < opponent_id else "right"


def _pair(values: Any) -> tuple[int, int] | None:
    if (
        not isinstance(values, Sequence)
        or isinstance(values, (str, bytes))
        or len(values) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in values)
    ):
        return None
    return (int(values[0]), int(values[1]))


def _classify_pair(
    *,
    predicted: tuple[int, int] | None,
    prize_id: int,
    factual_opponent_id: int,
) -> str:
    if predicted is None:
        return "no_pair"
    predicted_set = set(predicted)
    factual = {prize_id, factual_opponent_id}
    if predicted_set == factual:
        return "exact"
    if prize_id in predicted_set:
        return "prize_with_wrong_opponent"
    if factual_opponent_id in predicted_set:
        return "factual_opponent_without_prize"
    return "unrelated_pair"


def run(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("partition") != "discovery":
        raise ValueError("expected discovery artifact")
    if payload.get("model") != "AFSIM-R1":
        raise ValueError("expected AFSIM-R1 artifact")

    rows = payload.get("observations")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise ValueError("observations missing or malformed")

    counts: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []

    for row in rows:
        prize_id = row.get("captured_ship_id")
        opponent_id = row.get("next_opponent_ship_id")
        factual = row.get("factual")
        variants = row.get("variants")
        if (
            isinstance(prize_id, bool)
            or not isinstance(prize_id, int)
            or isinstance(opponent_id, bool)
            or not isinstance(opponent_id, int)
            or not isinstance(factual, Mapping)
            or not isinstance(variants, Mapping)
        ):
            counts["row:unresolved_shape"] += 1
            continue

        factual_side = factual.get("prize_side")
        if factual_side not in {"left", "right"}:
            counts["row:unresolved_factual_side"] += 1
            continue

        counts["row:resolved"] += 1

        # Identity-anchored AFSim side-only discriminator.
        predicted_id_side = _id_side(int(prize_id), int(opponent_id))
        id_side_exact = (
            predicted_id_side == factual_side
            if predicted_id_side in {"left", "right"}
            else None
        )
        counts[f"id_side:{_bool_label(id_side_exact)}"] += 1
        counts[f"id_side:factual_{factual_side}"] += 1
        if id_side_exact is True:
            counts[f"id_side:exact:factual_{factual_side}"] += 1
        elif id_side_exact is False:
            counts[f"id_side:mismatch:factual_{factual_side}"] += 1

        variant_rows: dict[str, Any] = {}
        for variant_name in ("tminus1", "all_active"):
            raw_variant = variants.get(variant_name)
            if not isinstance(raw_variant, Mapping):
                continue
            predicted_pair = _pair(raw_variant.get("pair"))
            category = _classify_pair(
                predicted=predicted_pair,
                prize_id=int(prize_id),
                factual_opponent_id=int(opponent_id),
            )
            phase = raw_variant.get("phase")
            phase_name = (
                str(phase)
                if phase in {"kill", "primary_enemy"}
                else "none"
            )
            counts[f"{variant_name}:pair_category:{category}"] += 1
            counts[f"{variant_name}:phase:{phase_name}"] += 1
            counts[
                f"{variant_name}:pair_category:{category}:phase:{phase_name}"
            ] += 1

            variant_rows[variant_name] = {
                "pair": list(predicted_pair) if predicted_pair is not None else None,
                "pair_category": category,
                "phase": phase_name,
                "prize_side": raw_variant.get("prize_side"),
                "pair_exact": raw_variant.get("pair_exact"),
                "side_exact": raw_variant.get("side_exact"),
            }

        cases.append(
            {
                "game_id": row.get("game_id"),
                "turn": row.get("turn"),
                "capture_vcr_id": row.get("capture_vcr_id"),
                "next_vcr_id": row.get("next_vcr_id"),
                "captured_ship_id": int(prize_id),
                "next_opponent_ship_id": int(opponent_id),
                "factual_prize_side": factual_side,
                "id_canonical_predicted_side": predicted_id_side,
                "id_canonical_side_exact": id_side_exact,
                "variants": variant_rows,
            }
        )

    return {
        "schema": "planets-lab.external-afsim-r1-discovery-analysis.v1",
        "source_schema": payload.get("schema"),
        "source_model": payload.get("model"),
        "partition": payload.get("partition"),
        "summary": dict(sorted(counts.items())),
        "cases": cases,
        "evidence_boundary": (
            "Discovery-only post-analysis of the already frozen AFSIM-R1 "
            "artifact. The lower-ID LEFT / higher-ID RIGHT comparator is "
            "conditioned on the factual next-pair identity and therefore tests "
            "side assignment only, not queue prediction. Held-out is not read."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze AFSIM-R1 discovery mismatches and test the recovered "
            "lower-ID LEFT side rule independently of queue selection."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("input must be a JSON object")
        report = run(payload)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        counts = report["summary"]
        print("===== AFSIM-R1 DISCOVERY POST-ANALYSIS =====")
        print(f"resolved rows:                   {counts.get('row:resolved', 0)}")
        print(
            "ID-canonical side exact/mismatch: "
            f"{counts.get('id_side:true', 0)} / "
            f"{counts.get('id_side:false', 0)}"
        )
        print(
            "  factual LEFT exact/mismatch:    "
            f"{counts.get('id_side:exact:factual_left', 0)} / "
            f"{counts.get('id_side:mismatch:factual_left', 0)}"
        )
        print(
            "  factual RIGHT exact/mismatch:   "
            f"{counts.get('id_side:exact:factual_right', 0)} / "
            f"{counts.get('id_side:mismatch:factual_right', 0)}"
        )

        for variant in ("tminus1", "all_active"):
            print()
            print(f"{variant} pair categories:")
            for category in (
                "exact",
                "prize_with_wrong_opponent",
                "factual_opponent_without_prize",
                "unrelated_pair",
                "no_pair",
            ):
                print(
                    f"  {category:30s} "
                    f"{counts.get(f'{variant}:pair_category:{category}', 0)}"
                )
            print(
                "  phase kill / PE / none:         "
                f"{counts.get(f'{variant}:phase:kill', 0)} / "
                f"{counts.get(f'{variant}:phase:primary_enemy', 0)} / "
                f"{counts.get(f'{variant}:phase:none', 0)}"
            )

        if args.output is not None:
            print()
            print(f"output: {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
