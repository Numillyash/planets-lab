from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import (
    FriendlyCodePriorityKind,
    INTERCEPT_MISSION_ID,
    classify_battle_friendly_code,
)

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _canonical_hash,
    _decode_turn,
    _int,
    _objects,
    _owner_raw,
    _pia_side_classification,
    _ship_side,
    _standard_relation,
    _static_specs,
)


def _selected_order_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "mission2target": _intish(raw.get("mission2target")),
        "enemy": _intish(raw.get("enemy")),
        "friendlycode": raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None,
        "iscloaked": raw.get("iscloaked") if isinstance(raw.get("iscloaked"), (bool, int)) else None,
        "neutronium": _intish(raw.get("neutronium")),
        "damage": _intish(raw.get("damage")),
    }


def _side_detail(
    *,
    raw: Mapping[str, Any],
    ship_id: int,
    owner_id: int | None,
    race_id: int | None,
    hull_id: int,
    opponent_ship_id: int,
    target_owner_id: int | None,
    pia_class: str,
    specs: Any,
) -> dict[str, Any]:
    hull = specs.hulls.get(hull_id)
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "hull_name": hull.name if hull is not None else None,
        "hull_special": hull.special if hull is not None else None,
        "hull_can_cloak": hull.can_cloak if hull is not None else None,
        "opponent_ship_id": opponent_ship_id,
        "target_owner_id": target_owner_id,
        "pia_class": pia_class,
        **_selected_order_fields(raw),
    }


def _is_supported_nonmatching_fc(left_raw: Mapping[str, Any], right_raw: Mapping[str, Any]) -> bool:
    left_fc = classify_battle_friendly_code(left_raw.get("friendlycode"))
    right_fc = classify_battle_friendly_code(right_raw.get("friendlycode"))
    return (
        left_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
        and right_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
        and left_raw.get("friendlycode") != right_raw.get("friendlycode")
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    archives = sorted(args.archive_dir.glob("game-*.zip"))
    payload_conflicts = 0

    for archive_path in archives:
        try:
            archive_game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        data = archive_path.read_bytes()
        specs = _static_specs(data)
        prepared, _ = load_or_build_prepared_game_cache(
            data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _race_conflicts = _player_races(prepared.snapshots)

        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        seen: dict[tuple[int, int, int], tuple[str, dict[str, Any]]] = {}
        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            game = rst.get("game")
            game_id = _int(game, "id")
            game_turn = _int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            for vcr in _objects(rst, "vcrs"):
                vcr_id = _int(vcr, "id")
                battle_turn = _int(vcr, "turn") or game_turn
                x = _int(vcr, "x")
                y = _int(vcr, "y")
                if vcr_id is None or x is None or y is None:
                    continue
                key = (game_id, battle_turn, vcr_id)
                digest = _canonical_hash(vcr)
                existing = seen.get(key)
                if existing is None:
                    seen[key] = (digest, vcr)
                elif existing[0] != digest:
                    payload_conflicts += 1

        sites: dict[tuple[int, int, int, int], list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        for (game_id, turn, vcr_id), (_digest, vcr) in seen.items():
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            if x is None or y is None or left is None or right is None:
                continue
            sites[(game_id, turn, x, y)].append((vcr_id, vcr))

        for (game_id, turn, x, y), queue in sorted(sites.items()):
            if len(queue) != 1:
                continue
            vcr_id, vcr = queue[0]
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            assert left is not None and right is not None
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            before_turn = turn - 1
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)
            if left_raw is None or right_raw is None:
                continue
            left_hull = _intish(left_raw.get("hullid", left_raw.get("hull_id")))
            right_hull = _intish(right_raw.get("hullid", right_raw.get("hull_id")))
            if left_hull is None or right_hull is None:
                continue
            if (
                left_owner != left["owner_id"]
                or right_owner != right["owner_id"]
                or left_hull != left["hull_id"]
                or right_hull != right["hull_id"]
            ):
                continue

            if (
                _intish(left_raw.get("mission")) != INTERCEPT_MISSION_ID
                and _intish(right_raw.get("mission")) != INTERCEPT_MISSION_ID
            ):
                continue

            left_target_id = _intish(left_raw.get("mission1target"))
            right_target_id = _intish(right_raw.get("mission1target"))
            left_target_owner = None
            right_target_owner = None
            if left_target_id is not None and left_target_id > 0:
                left_target_owner, _ = _owner_raw(ship_groups, before_turn, left_target_id)
            if right_target_id is not None and right_target_id > 0:
                right_target_owner, _ = _owner_raw(ship_groups, before_turn, right_target_id)

            left_spec = specs.hulls.get(left_hull)
            right_spec = specs.hulls.get(right_hull)
            left_pia = _pia_side_classification(
                raw=left_raw,
                opponent_ship_id=right_id,
                target_owner_id=left_target_owner,
                hull_can_cloak=left_spec.can_cloak if left_spec is not None else None,
            )
            right_pia = _pia_side_classification(
                raw=right_raw,
                opponent_ship_id=left_id,
                target_owner_id=right_target_owner,
                hull_can_cloak=right_spec.can_cloak if right_spec is not None else None,
            )
            if "targets_factual_opponent" in {left_pia, right_pia}:
                continue
            if "signature_unknown" in {left_pia, right_pia}:
                continue
            if not _is_supported_nonmatching_fc(left_raw, right_raw):
                continue
            relation = _standard_relation(
                left_raw=left_raw,
                right_raw=right_raw,
                left_ship_id=left_id,
                right_ship_id=right_id,
            )
            if relation != "left_higher_priority":
                continue

            rows.append(
                {
                    "game_id": game_id,
                    "turn": turn,
                    "vcr_id": vcr_id,
                    "x": x,
                    "y": y,
                    "standard_relation": relation,
                    "left": _side_detail(
                        raw=left_raw,
                        ship_id=left_id,
                        owner_id=left_owner,
                        race_id=races.get(left_owner) if left_owner is not None else None,
                        hull_id=left_hull,
                        opponent_ship_id=right_id,
                        target_owner_id=left_target_owner,
                        pia_class=left_pia,
                        specs=specs,
                    ),
                    "right": _side_detail(
                        raw=right_raw,
                        ship_id=right_id,
                        owner_id=right_owner,
                        race_id=races.get(right_owner) if right_owner is not None else None,
                        hull_id=right_hull,
                        opponent_ship_id=left_id,
                        target_owner_id=right_target_owner,
                        pia_class=right_pia,
                        specs=specs,
                    ),
                }
            )

    ordinary = [row for row in rows if row["game_id"] != SPECIAL_GAME_ID]
    special = [row for row in rows if row["game_id"] == SPECIAL_GAME_ID]
    return {
        "schema": "planets-lab.combat-host-priority-intercept-non-pia-residual-audit.v1",
        "read_only": True,
        "summary": {
            "archives": len(archives),
            "payload_conflicts": payload_conflicts,
            "ordinary_residuals": len(ordinary),
            "game_591478_residuals": len(special),
            "all_residuals": len(rows),
        },
        "ordinary": ordinary,
        "game_591478": special[: args.special_limit],
        "evidence_boundary": (
            "This is a residual-enrichment audit only. It selects isolated ship battles where mission 7 is present, "
            "neither side has a qualified Priority Intercept signature against the factual opponent, FC parsing is "
            "supported/nonmatching, and the canonical standard key predicts the factual left side has higher priority. "
            "It does not infer a new mechanic from the residuals."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich non-PIA mission-7 isolated standard-side residuals.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--special-limit", type=int, default=20)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST PRIORITY INTERCEPT NON-PIA RESIDUAL AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("===== ordinary =====")
    for index, row in enumerate(report["ordinary"], start=1):
        print(f"CASE {index}: game={row['game_id']} turn={row['turn']} vcr={row['vcr_id']} pos=({row['x']},{row['y']})")
        print(f"  left: {row['left']}")
        print(f"  right: {row['right']}")
    print()
    print("===== game_591478 sample =====")
    for index, row in enumerate(report["game_591478"], start=1):
        print(f"CASE {index}: game={row['game_id']} turn={row['turn']} vcr={row['vcr_id']}")
        print(f"  left: {row['left']}")
        print(f"  right: {row['right']}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: residual enrichment only; no new combat rule is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
