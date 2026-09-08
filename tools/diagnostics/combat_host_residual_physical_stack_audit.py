from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records

from combat_host_residual_source_context_audit import (
    AuditCase,
    DEFAULT_CASE_TEXTS,
    PREPARED_DIR,
    RAW_DIR,
    _collect_factual_vcrs,
    _parse_case,
    _positive_int,
    _project_ship_record,
)

INTERCEPT_LIKE_MISSIONS = frozenset({7, 20})


def _owner_current_record(records: Sequence[PerspectiveRecord]) -> tuple[str, PerspectiveRecord | None, int, int]:
    current = [record for record in records if record.is_current]
    owner_current = []
    for record in current:
        owner_id = _positive_int(record.raw.get("ownerid", record.raw.get("owner_id")))
        if owner_id == record.player_id:
            owner_current.append(record)
    if len(owner_current) == 1:
        return "owner_current", owner_current[0], len(current), 1
    if not current:
        return "no_current", None, 0, 0
    if not owner_current:
        return "no_owner_current", None, len(current), 0
    return "ambiguous_owner_current", None, len(current), len(owner_current)


def _safe_owner_record(record: PerspectiveRecord) -> dict[str, Any]:
    return {
        "perspective_player_id": record.player_id,
        "archive_turn": record.archive_turn,
        "embedded_turn": record.embedded_turn,
        "infoturn": record.infoturn,
        "freshness": "current" if record.is_current else "stale",
        **_project_ship_record(record.raw),
    }


def _turn_owner_index(
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    turn: int,
) -> tuple[dict[int, PerspectiveRecord], dict[int, dict[str, Any]]]:
    resolved: dict[int, PerspectiveRecord] = {}
    unresolved: dict[int, dict[str, Any]] = {}
    for (archive_turn, ship_id), records in ship_groups.items():
        if archive_turn != turn:
            continue
        status, record, current_count, owner_current_count = _owner_current_record(records)
        if record is not None:
            resolved[int(ship_id)] = record
        elif status != "no_current":
            unresolved[int(ship_id)] = {
                "status": status,
                "perspective_count": len(records),
                "current_count": current_count,
                "owner_current_count": owner_current_count,
            }
    return resolved, unresolved


def _xy(raw: Mapping[str, Any]) -> tuple[int | None, int | None]:
    return _intish(raw.get("x")), _intish(raw.get("y"))


def _waypoint(raw: Mapping[str, Any]) -> tuple[int | None, int | None]:
    return _intish(raw.get("targetx")), _intish(raw.get("targety"))


def _candidate_reasons(
    *,
    ship_id: int,
    raw: Mapping[str, Any],
    tracked_ship_ids: set[int],
    battle_xy: tuple[int, int],
    tracked_tminus1_positions: set[tuple[int, int]],
) -> list[str]:
    reasons: list[str] = []
    position = _xy(raw)
    waypoint = _waypoint(raw)
    mission = _intish(raw.get("mission"))
    mission_target = _positive_int(raw.get("mission1target"))

    if ship_id in tracked_ship_ids:
        reasons.append("tracked_ship")
    if position == battle_xy:
        reasons.append("at_battle_coordinate_pre_move")
    if waypoint == battle_xy:
        reasons.append("waypoint_to_battle_coordinate")
    if mission in INTERCEPT_LIKE_MISSIONS and mission_target in tracked_ship_ids:
        reasons.append("intercepts_tracked_ship")
    if ship_id not in tracked_ship_ids and position in tracked_tminus1_positions:
        reasons.append("shares_tminus1_location_with_tracked_ship")
    return reasons


def _site_coordinates(vcr_rows: Sequence[Mapping[str, Any]], target_vcr_id: int) -> tuple[int, int]:
    for row in vcr_rows:
        if int(row["vcr_id"]) != target_vcr_id:
            continue
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            break
        x = _intish(payload.get("x"))
        y = _intish(payload.get("y"))
        if x is not None and y is not None:
            return x, y
        break
    raise ValueError(f"target VCR {target_vcr_id} is missing usable coordinates")


def _safe_candidate(
    ship_id: int,
    record: PerspectiveRecord,
    *,
    reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "ship_id": ship_id,
        "reasons": list(reasons),
        **_safe_owner_record(record),
    }


def _audit_case(
    case: AuditCase,
    *,
    archive_dir: Path,
    prepared_dir: Path,
) -> dict[str, Any]:
    archive_path = archive_dir / f"game-{case.game_id}.zip"
    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=case.game_id,
        cache_path=prepared_dir / f"game-{case.game_id}.pickle",
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    vcr_rows, payload_conflicts = _collect_factual_vcrs(
        archive_data,
        game_id=case.game_id,
        battle_turn=case.battle_turn,
    )
    battle_xy = _site_coordinates(vcr_rows, case.vcr_id)
    tracked = set(case.ship_ids)

    tminus1_index, tminus1_unresolved = _turn_owner_index(ship_groups, case.battle_turn - 1)
    t_index, t_unresolved = _turn_owner_index(ship_groups, case.battle_turn)

    tracked_tminus1_positions = {
        position
        for ship_id in tracked
        if (record := tminus1_index.get(ship_id)) is not None
        if None not in (position := _xy(record.raw))
    }

    tminus1_candidates: list[dict[str, Any]] = []
    for ship_id, record in sorted(tminus1_index.items()):
        reasons = _candidate_reasons(
            ship_id=ship_id,
            raw=record.raw,
            tracked_ship_ids=tracked,
            battle_xy=battle_xy,
            tracked_tminus1_positions=tracked_tminus1_positions,
        )
        if reasons:
            tminus1_candidates.append(_safe_candidate(ship_id, record, reasons=reasons))

    t_survivors: list[dict[str, Any]] = []
    for ship_id, record in sorted(t_index.items()):
        if _xy(record.raw) != battle_xy:
            continue
        previous = tminus1_index.get(ship_id)
        row = {
            "ship_id": ship_id,
            "tracked": ship_id in tracked,
            "t_owner_current": _safe_owner_record(record),
            "tminus1_owner_current": _safe_owner_record(previous) if previous is not None else None,
        }
        t_survivors.append(row)

    site_vcrs = []
    for row in vcr_rows:
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if (_intish(payload.get("x")), _intish(payload.get("y"))) == battle_xy:
            site_vcrs.append(int(row["vcr_id"]))

    untracked_survivors = [row for row in t_survivors if not row["tracked"]]
    untracked_candidates = [row for row in tminus1_candidates if row["ship_id"] not in tracked]

    return {
        "case": {
            "game_id": case.game_id,
            "battle_turn": case.battle_turn,
            "target_vcr_id": case.vcr_id,
            "tracked_ship_ids": list(case.ship_ids),
            "battle_xy": list(battle_xy),
        },
        "source": {
            "archive_path": str(archive_path),
            "prepared_cache_hit": cache_hit,
        },
        "summary": {
            "payload_conflicts": len(payload_conflicts),
            "site_vcr_ids": site_vcrs,
            "site_vcr_count": len(site_vcrs),
            "t_owner_current_survivors_at_battle_coordinate": len(t_survivors),
            "t_untracked_survivors_at_battle_coordinate": len(untracked_survivors),
            "tminus1_context_candidates": len(tminus1_candidates),
            "tminus1_untracked_context_candidates": len(untracked_candidates),
            "tminus1_unresolved_owner_records": len(tminus1_unresolved),
            "t_unresolved_owner_records": len(t_unresolved),
        },
        "t_survivors_at_battle_coordinate": t_survivors,
        "tminus1_context_candidates": tminus1_candidates,
        "unresolved_owner_record_counts": {
            "T-1": tminus1_unresolved,
            "T": t_unresolved,
        },
        "evidence_boundary": (
            "This diagnostic tests whether a one-VCR site was also a two-ship physical stack. "
            "T rows are post-combat/end-of-turn owner-current survivors, so extra T ships at the battle coordinate "
            "are strong evidence of noncombatant stack members, but absence of extras does not exclude a ship removed "
            "by an earlier non-VCR Host phase. T-1 candidates are context leads only; waypoint/intercept membership "
            "does not prove post-move co-location. No combat rule is inferred."
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    cases = args.case or [_parse_case(text) for text in DEFAULT_CASE_TEXTS]
    reports = [
        _audit_case(case, archive_dir=args.archive_dir, prepared_dir=args.prepared_dir)
        for case in cases
    ]
    return {
        "schema": "planets-lab.combat-host-residual-physical-stack-audit.v1",
        "read_only": True,
        "summary": {
            "cases": len(reports),
            "payload_conflicts": sum(int(row["summary"]["payload_conflicts"]) for row in reports),
            "cases_with_untracked_t_survivor": sum(
                int(row["summary"]["t_untracked_survivors_at_battle_coordinate"] > 0)
                for row in reports
            ),
        },
        "cases": reports,
        "evidence_boundary": (
            "Narrow privacy-safe physical-stack context audit for the two ordinary mission-7 residuals. "
            "Owner-current ship records only; arbitrary raw fields are never emitted."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect physical stack context for the two C5 mission-7 residuals.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument(
        "--case",
        action="append",
        type=_parse_case,
        default=None,
        metavar="GAME:BATTLE_TURN:VCR_ID:SHIP_A:SHIP_B",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT RESIDUAL PHYSICAL STACK AUDIT =====")
    print(f"summary: {report['summary']}")
    for index, case in enumerate(report["cases"], start=1):
        meta = case["case"]
        print()
        print(
            f"CASE {index}: game={meta['game_id']} battle_turn={meta['battle_turn']} "
            f"target_vcr={meta['target_vcr_id']} battle_xy={tuple(meta['battle_xy'])}"
        )
        print(f"  summary: {case['summary']}")
        print("  T survivors at battle coordinate:")
        for row in case["t_survivors_at_battle_coordinate"]:
            print(
                f"    ship={row['ship_id']} tracked={row['tracked']} "
                f"T={row['t_owner_current']['fields']} "
                f"T-1={row['tminus1_owner_current']['fields'] if row['tminus1_owner_current'] else None}"
            )
        print("  T-1 context candidates:")
        for row in case["tminus1_context_candidates"]:
            print(f"    ship={row['ship_id']} reasons={row['reasons']} fields={row['fields']}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        import json

        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: physical-stack context only; no combat rule is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
