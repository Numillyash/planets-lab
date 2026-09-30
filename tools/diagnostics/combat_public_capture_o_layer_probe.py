from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for _path in (REPO_ROOT / "src", DIAGNOSTICS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_capture_active_membership_audit as active_module
import combat_host_post_capture_special_movement_audit as special_movement_module
from combat_host_post_capture_pair_recomposition_audit import (
    _external_c2ng_original_order_prize_continuation,
)
from combat_host_post_mutation_next_pair_audit import _appearance_key
from combat_host_priority_intercept_audit import PREPARED_DIR
from combat_public_capture_side_harvest import (
    DEFAULT_APPEARANCE_CACHE_DIR,
    DEFAULT_ARCHIVE_DIR,
    _collect_appearances_cached,
)


SCHEMA = "planets-lab.combat-public-capture-o-layer-probe.v1"
DEFAULT_DISCOVERY = Path(
    "artifacts/public-capture-side/discovery-capture-side.json"
)
DEFAULT_OUTPUT = Path(
    "artifacts/public-capture-side/discovery-o-layer-probe.json"
)


def _load_discovery(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("discovery artifact must be a JSON object")
    if payload.get("partition") != "discovery":
        raise ValueError("O-layer probe requires partition=discovery")
    observations = payload.get("observations")
    if (
        not isinstance(observations, Sequence)
        or isinstance(observations, (str, bytes))
        or not all(isinstance(row, Mapping) for row in observations)
    ):
        raise ValueError("discovery observations are missing or malformed")
    return payload


def _targets_by_site(
    observations: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], list[Mapping[str, Any]]]:
    result: dict[
        tuple[int, int, int, int],
        list[Mapping[str, Any]],
    ] = defaultdict(list)
    for row in observations:
        game_id = row.get("game_id")
        turn = row.get("turn")
        position = row.get("position")
        if (
            isinstance(game_id, bool)
            or not isinstance(game_id, int)
            or isinstance(turn, bool)
            or not isinstance(turn, int)
            or not isinstance(position, Sequence)
            or isinstance(position, (str, bytes))
            or len(position) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in position
            )
        ):
            raise ValueError("discovery observation has invalid site identity")
        result[(game_id, turn, int(position[0]), int(position[1]))].append(row)
    return result


def _appearance_mapping(
    appearances: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    result: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    for row in appearances:
        values = (
            row.get("game_id"),
            row.get("turn"),
            row.get("vcr_id"),
            row.get("ship_id"),
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in values
        ):
            continue
        game_id, turn, vcr_id, ship_id = (int(value) for value in values)
        result[_appearance_key(game_id, turn, vcr_id, ship_id)] = row
    return result


def _capture_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ship_id": row.get("captured_ship_id"),
        "captor_ship_id": row.get("captor_ship_id"),
        "captor_owner_id": row.get("captor_owner_id"),
        "current_opponent_ship_id": row.get("next_opponent_ship_id"),
        "from_vcr_id": row.get("capture_vcr_id"),
        "to_vcr_id": row.get("next_vcr_id"),
        "current_side": row.get("captured_ship_side_next"),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    discovery = _load_discovery(args.discovery)
    observations = [
        dict(row)
        for row in discovery["observations"]
        if isinstance(row, Mapping)
    ]
    scan_ids_raw = discovery.get("scanned_game_ids")
    if (
        not isinstance(scan_ids_raw, Sequence)
        or isinstance(scan_ids_raw, (str, bytes))
    ):
        raise ValueError("discovery scanned_game_ids missing")
    scan_ids = {
        int(value)
        for value in scan_ids_raw
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if not scan_ids:
        raise ValueError("discovery game population is empty")

    cache_args = argparse.Namespace(
        archive_dir=args.archive_dir,
        appearance_cache_dir=args.appearance_cache_dir,
        partition="discovery",
        example_limit=args.example_limit,
    )
    appearances, chain_summary = _collect_appearances_cached(
        args=cache_args,
        scan_ids=scan_ids,
    )
    appearances_by_key = _appearance_mapping(appearances)

    targets = _targets_by_site(observations)
    target_turns = {
        (game_id, battle_turn)
        for game_id, battle_turn, _x, _y in targets
    }

    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int, int]] = set()

    def site_filter(game_id: int, battle_turn: int, x: int, y: int) -> bool:
        return (game_id, battle_turn, x, y) in targets

    def prediction_overlay(context: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
        key = (int(context["game_id"]), int(context["battle_turn"]))
        if key not in target_turns:
            return {}
        return special_movement_module.special_position_overlay(context)

    def observer(context: Mapping[str, Any]) -> None:
        site_key = (
            int(context["game_id"]),
            int(context["battle_turn"]),
            int(context["x"]),
            int(context["y"]),
        )
        rows = targets.get(site_key, ())
        for row in rows:
            capture = _capture_projection(row)
            from_vcr_id = capture.get("from_vcr_id")
            prize_id = capture.get("ship_id")
            if (
                isinstance(from_vcr_id, bool)
                or not isinstance(from_vcr_id, int)
                or isinstance(prize_id, bool)
                or not isinstance(prize_id, int)
            ):
                counts["status:unresolved"] += 1
                continue
            seen.add(
                (
                    site_key[0],
                    site_key[1],
                    int(from_vcr_id),
                    int(prize_id),
                )
            )

            active_result = active_module._simulate_capture(
                context=context,
                capture=capture,
                appearances=appearances_by_key,
            )
            if active_result.get("status") != "resolved":
                result = {
                    "status": "unresolved",
                    "reason": "active_membership_dependency_unresolved",
                    "active_status": active_result.get("status"),
                    "active_reason": active_result.get("reason"),
                }
            else:
                result = _external_c2ng_original_order_prize_continuation(
                    context=context,
                    capture=capture,
                    active_result=active_result,
                    capture_prize_side=str(row.get("capture_side")),
                )

            status = str(result.get("status", "unknown"))
            counts[f"status:{status}"] += 1
            factual_side = row.get("captured_ship_side_next")
            if factual_side in {"left", "right"}:
                counts[f"factual_side:{factual_side}"] += 1

            if status == "resolved":
                pair_exact = result.get("pair_exact")
                exact = result.get("exact")
                if pair_exact is True:
                    counts["o_pair_reachable"] += 1
                    if factual_side in {"left", "right"}:
                        counts[f"o_pair_reachable:{factual_side}"] += 1
                elif pair_exact is False:
                    counts["o_pair_not_reachable"] += 1
                    if factual_side in {"left", "right"}:
                        counts[f"o_pair_not_reachable:{factual_side}"] += 1
                if exact is True:
                    counts["external_o_exact"] += 1
                elif exact is False:
                    counts["external_o_mismatch"] += 1

            if len(examples) < args.example_limit:
                examples.append(
                    {
                        "game_id": site_key[0],
                        "turn": site_key[1],
                        "x": site_key[2],
                        "y": site_key[3],
                        "capture_vcr_id": row.get("capture_vcr_id"),
                        "next_vcr_id": row.get("next_vcr_id"),
                        "captured_ship_id": row.get("captured_ship_id"),
                        "next_opponent_ship_id": row.get("next_opponent_ship_id"),
                        "capture_side": row.get("capture_side"),
                        "factual_prize_side": factual_side,
                        "result": result,
                    }
                )

    print(
        "progress: stage=o_layer_site_context "
        f"games={len(scan_ids)} sites={len(targets)} status=start",
        flush=True,
    )
    baseline = baseline_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            feature_index=None,
            scope_profile="combat-planar-no-horwasp",
            selected_game_ids=scan_ids,
            site_filter=site_filter,
            progress=True,
            example_limit=0,
            output=None,
            site_observer=observer,
            prediction_overlay=prediction_overlay,
        )
    )
    print(
        "progress: stage=o_layer_site_context "
        f"games={len(scan_ids)} sites={len(targets)} status=done",
        flush=True,
    )

    counts["discovery_ship_rows"] = len(observations)
    counts["observations_seen"] = len(seen)
    counts["adjacent_rows"] = sum(
        1
        for row in observations
        if isinstance(row.get("capture_vcr_id"), int)
        and isinstance(row.get("next_vcr_id"), int)
        and not isinstance(row.get("capture_vcr_id"), bool)
        and not isinstance(row.get("next_vcr_id"), bool)
        and int(row["next_vcr_id"]) == int(row["capture_vcr_id"]) + 1
    )

    return {
        "schema": SCHEMA,
        "evidence_status": "DISCOVERY_ONLY_EXTERNAL_REFERENCE_NOT_PROMOTED",
        "source_discovery": str(args.discovery),
        "scanned_game_ids": sorted(scan_ids),
        "summary": {
            "counts": dict(sorted(counts.items())),
            "chain_audit_summary": dict(chain_summary),
            "baseline_summary": baseline.get("summary"),
        },
        "observations": examples,
        "evidence_boundary": (
            "Discovery-only bounded O-layer comparator. The frozen-order cursor "
            "is transcribed from the separately audited external c2ng/THost path "
            "and is not NuHost authority. Only globally adjacent capture->next "
            "VCR rows are comparable; nonadjacent rows fail closed. Capture VCR N "
            "anchors the existing cursor, independently reconstructed movement/"
            "site state and strict post-capture attackers determine reachability, "
            "and factual N+1 supplies only the final opponent/side comparator. "
            "Held-out games are not included."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test a bounded external original-order cursor against the sealed "
            "public discovery capture population."
        )
    )
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument(
        "--appearance-cache-dir",
        type=Path,
        default=DEFAULT_APPEARANCE_CACHE_DIR,
    )
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=80)
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
        counts = report["summary"]["counts"]
        print("===== PUBLIC CAPTURE O-LAYER DISCOVERY =====")
        print(f"discovery_ship_rows:  {counts.get('discovery_ship_rows', 0)}")
        print(f"adjacent_rows:        {counts.get('adjacent_rows', 0)}")
        print(f"resolved:             {counts.get('status:resolved', 0)}")
        print(f"not_comparable:       {counts.get('status:not_comparable', 0)}")
        print(f"unresolved:           {counts.get('status:unresolved', 0)}")
        print(f"O pair reachable:     {counts.get('o_pair_reachable', 0)}")
        print(
            "  factual LEFT/RIGHT: "
            f"{counts.get('o_pair_reachable:left', 0)} / "
            f"{counts.get('o_pair_reachable:right', 0)}"
        )
        print(f"O pair not reachable: {counts.get('o_pair_not_reachable', 0)}")
        print(
            "  factual LEFT/RIGHT: "
            f"{counts.get('o_pair_not_reachable:left', 0)} / "
            f"{counts.get('o_pair_not_reachable:right', 0)}"
        )
        print(f"external O exact:     {counts.get('external_o_exact', 0)}")
        print(f"external O mismatch:  {counts.get('external_o_mismatch', 0)}")
        print(f"output:               {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
