from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import (
    FriendlyCodePriorityKind,
    classify_battle_friendly_code,
    orders_request_ship_combat,
    priority_intercept_order_signature,
    priority_intercept_reciprocal_target_signature,
)

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs, _standard_relation
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _int,
    _owner_raw,
    _ship_side,
    _static_specs,
)

TARGET_CASE = (511506, 19, 13, 89, 80)
DEFAULT_EXAMPLE_LIMIT = 30


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _fc_projection(raw: Mapping[str, Any]) -> dict[str, Any]:
    text = raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None
    classified = classify_battle_friendly_code(text)
    return {
        "text": text,
        "kind": classified.kind.value,
        "numeric_value": classified.numeric_value,
        "evidence": classified.evidence,
    }


def _supported_nonmatching_fc(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_fc = classify_battle_friendly_code(a.get("friendlycode"))
    b_fc = classify_battle_friendly_code(b.get("friendlycode"))
    return (
        a_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
        and b_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
        and a.get("friendlycode") != b.get("friendlycode")
    )


def _target_aggression_shape(
    *,
    target_raw: Mapping[str, Any],
    interceptor_owner_id: int,
) -> str:
    kill = _intish(target_raw.get("mission")) == 3
    pe_match = _intish(target_raw.get("enemy")) == interceptor_owner_id
    if kill and pe_match:
        return "kill_and_pe"
    if kill:
        return "kill_only"
    if pe_match:
        return "pe_only"
    return "none"


def _qualifies_reciprocal_only(
    *,
    interceptor_raw: Mapping[str, Any],
    interceptor_owner_id: int,
    interceptor_hull_can_cloak: bool | None,
    target_ship_id: int,
    target_owner_id: int,
    target_raw: Mapping[str, Any],
) -> bool:
    target_requests = orders_request_ship_combat(
        mission=_intish(target_raw.get("mission")),
        primary_enemy=_intish(target_raw.get("enemy")),
        opponent_owner_id=interceptor_owner_id,
    )
    normal_pia = priority_intercept_order_signature(
        mission=_intish(interceptor_raw.get("mission")),
        mission_target_id=_intish(interceptor_raw.get("mission1target")),
        primary_enemy=_intish(interceptor_raw.get("enemy")),
        target_owner_id=target_owner_id,
        hull_can_cloak=interceptor_hull_can_cloak,
    )
    reciprocal = priority_intercept_reciprocal_target_signature(
        interceptor_mission=_intish(interceptor_raw.get("mission")),
        interceptor_target_id=_intish(interceptor_raw.get("mission1target")),
        interceptor_hull_can_cloak=interceptor_hull_can_cloak,
        target_ship_id=target_ship_id,
        target_would_combat_interceptor=target_requests,
    )
    return normal_pia is False and reciprocal is True


def _safe_side(
    *,
    ship_id: int,
    owner_id: int,
    race_id: int | None,
    hull_id: int,
    hull_can_cloak: bool | None,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "hull_can_cloak": hull_can_cloak,
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendly_code": _fc_projection(raw),
        "neutronium": _intish(raw.get("neutronium")),
        "damage": _intish(raw.get("damage")),
        "iscloaked_tminus1": raw.get("iscloaked") if isinstance(raw.get("iscloaked"), bool) else None,
    }


def _site_position(site_vcr_ids: Sequence[int], vcr_id: int) -> dict[str, Any]:
    ordered = sorted(int(value) for value in site_vcr_ids)
    index = ordered.index(vcr_id)
    return {
        "site_ship_vcr_ids": ordered,
        "site_ship_vcr_count": len(ordered),
        "site_ship_vcr_index": index + 1,
        "site_first_ship_vcr": index == 0,
        "site_prior_ship_vcr_count": index,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    payload_conflicts = 0
    archives_considered = 0

    for archive_path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            archive_game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if archive_game_id == SPECIAL_GAME_ID:
            continue
        archives_considered += 1

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _ = _player_races(prepared.snapshots)
        specs = _static_specs(archive_data)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        site_ship_vcrs: dict[tuple[int, int, int], list[int]] = defaultdict(list)
        for (game_id, battle_turn, vcr_id), (_digest, vcr) in seen.items():
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue
            site_ship_vcrs[(game_id, battle_turn, x * 100000 + y)].append(vcr_id)

        for (game_id, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue

            before_turn = battle_turn - 1
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)
            if left_owner != left["owner_id"] or right_owner != right["owner_id"]:
                continue
            if left_raw is None or right_raw is None or left_owner is None or right_owner is None:
                continue
            if left_owner <= 0 or right_owner <= 0 or left_owner == right_owner:
                continue
            if not _supported_nonmatching_fc(left_raw, right_raw):
                continue

            standard_relation = _standard_relation(
                left_raw=left_raw,
                right_raw=right_raw,
                left_ship_id=left_id,
                right_ship_id=right_id,
            )
            if standard_relation == "unsupported":
                continue

            side_specs = (
                ("left", left, left_owner, left_raw, "right", right, right_owner, right_raw),
                ("right", right, right_owner, right_raw, "left", left, left_owner, left_raw),
            )
            for (
                interceptor_side,
                interceptor,
                interceptor_owner,
                interceptor_raw,
                target_side,
                target,
                target_owner,
                target_raw,
            ) in side_specs:
                interceptor_hull = specs.hulls.get(int(interceptor["hull_id"]))
                interceptor_can_cloak = interceptor_hull.can_cloak if interceptor_hull is not None else None
                if not _qualifies_reciprocal_only(
                    interceptor_raw=interceptor_raw,
                    interceptor_owner_id=interceptor_owner,
                    interceptor_hull_can_cloak=interceptor_can_cloak,
                    target_ship_id=int(target["ship_id"]),
                    target_owner_id=target_owner,
                    target_raw=target_raw,
                ):
                    continue

                site = _site_position(
                    site_ship_vcrs[(game_id, battle_turn, x * 100000 + y)],
                    vcr_id,
                )
                target_hull = specs.hulls.get(int(target["hull_id"]))
                target_can_cloak = target_hull.can_cloak if target_hull is not None else None
                row = {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "vcr_id": vcr_id,
                    "x": x,
                    "y": y,
                    "target_case": (
                        game_id,
                        battle_turn,
                        vcr_id,
                        int(interceptor["ship_id"]),
                        int(target["ship_id"]),
                    ) == TARGET_CASE,
                    "interceptor_side": interceptor_side,
                    "target_side": target_side,
                    "standard_relation": standard_relation,
                    "target_aggression_shape": _target_aggression_shape(
                        target_raw=target_raw,
                        interceptor_owner_id=interceptor_owner,
                    ),
                    "interceptor": _safe_side(
                        ship_id=int(interceptor["ship_id"]),
                        owner_id=interceptor_owner,
                        race_id=races.get(interceptor_owner),
                        hull_id=int(interceptor["hull_id"]),
                        hull_can_cloak=interceptor_can_cloak,
                        raw=interceptor_raw,
                    ),
                    "target": _safe_side(
                        ship_id=int(target["ship_id"]),
                        owner_id=target_owner,
                        race_id=races.get(target_owner),
                        hull_id=int(target["hull_id"]),
                        hull_can_cloak=target_can_cloak,
                        raw=target_raw,
                    ),
                    **site,
                }
                rows.append(row)

    target_rows = [row for row in rows if row["target_case"]]
    multi_rows = [row for row in rows if row["site_ship_vcr_count"] > 1]
    summary = {
        "archives_considered": archives_considered,
        "payload_conflicts": payload_conflicts,
        "candidate_rows": len(rows),
        "target_case_rows": len(target_rows),
        "interceptor_side": _serialize(Counter(row["interceptor_side"] for row in rows)),
        "standard_relation": _serialize(Counter(row["standard_relation"] for row in rows)),
        "target_aggression_shape": _serialize(Counter(row["target_aggression_shape"] for row in rows)),
        "site_first_ship_vcr": _serialize(Counter(str(row["site_first_ship_vcr"]) for row in rows)),
        "site_ship_vcr_count": _serialize(Counter(row["site_ship_vcr_count"] for row in rows)),
        "multi_vcr_site_rows": len(multi_rows),
        "multi_vcr_site_first_rows": sum(int(row["site_first_ship_vcr"]) for row in multi_rows),
        "games": _serialize(Counter(row["game_id"] for row in rows)),
    }
    return {
        "schema": "planets-lab.combat-host-priority-intercept-reciprocal-audit.v1",
        "read_only": True,
        "summary": summary,
        "target_case": target_rows,
        "examples": rows[: args.example_limit],
        "evidence_boundary": (
            "DOCUMENTED candidate selector for the reciprocal Priority Intercept ordering branch: a cloak-capable "
            "mission-7 ship targets its factual opponent, does not itself satisfy the normal PIA PE signature, and "
            "the intercepted target has Kill!/PE orders requesting combat with the interceptor. Factual VCR presence "
            "establishes that combat actually occurred; this audit does not infer omitted diplomacy/cloak blockers. "
            "Side and queue-position counts are CORPUS_OBSERVED population evidence only until runtime validation. "
            "Game 591478 is excluded."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit reciprocal target-initiated Priority Intercept ordering in ordinary ship combat."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT RECIPROCAL PRIORITY INTERCEPT AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET CASE:")
    for row in report["target_case"]:
        print(row)
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: reciprocal Priority Intercept population audit; no new universal side rule is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
