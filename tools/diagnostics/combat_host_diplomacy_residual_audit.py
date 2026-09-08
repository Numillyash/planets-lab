from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish


RAW_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_GAME_ID = 621253
DEFAULT_BATTLE_TURN = 10
DEFAULT_PLAYER_A = 4
DEFAULT_PLAYER_B = 3
RELATION_FIELDS = (
    "id",
    "playerid",
    "playertoid",
    "relationto",
    "relationfrom",
    "conflictlevel",
)


def _decode_turn(raw: bytes, member_name: str) -> dict[str, Any]:
    payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{member_name}: turn payload must be an object")
    return parsed


def _safe_relation(raw: Mapping[str, Any]) -> dict[str, int | None]:
    """Project only mechanical relation fields; never propagate identity/message fields."""
    return {field: _intish(raw.get(field)) for field in RELATION_FIELDS}


def _is_target_pair(row: Mapping[str, Any], player_a: int, player_b: int) -> bool:
    player_id = _intish(row.get("playerid"))
    player_to_id = _intish(row.get("playertoid"))
    return (player_id, player_to_id) in {(player_a, player_b), (player_b, player_a)}


def _unique_relation_values(rows: list[dict[str, Any]], player_a: int, player_b: int) -> dict[str, list[list[int | None]]]:
    result: dict[str, list[list[int | None]]] = {}
    for source, target in ((player_a, player_b), (player_b, player_a)):
        values = {
            (
                _intish(row.get("relationto")),
                _intish(row.get("relationfrom")),
                _intish(row.get("conflictlevel")),
            )
            for row in rows
            if _intish(row.get("playerid")) == source
            and _intish(row.get("playertoid")) == target
        }
        result[f"{source}->{target}"] = [list(value) for value in sorted(values, key=repr)]
    return result


def _mirror_consistent(unique: Mapping[str, list[list[int | None]]], player_a: int, player_b: int) -> bool | None:
    forward = unique.get(f"{player_a}->{player_b}", [])
    reverse = unique.get(f"{player_b}->{player_a}", [])
    if len(forward) != 1 or len(reverse) != 1:
        return None
    a_to, a_from, _a_conflict = forward[0]
    b_to, b_from, _b_conflict = reverse[0]
    return a_to == b_from and a_from == b_to


def run(args: argparse.Namespace) -> dict[str, Any]:
    pre_turn = int(args.battle_turn) - 1
    if pre_turn < 0:
        raise ValueError("battle turn must be positive")

    archive_path = args.archive_dir / f"game-{args.game_id}.zip"
    data = archive_path.read_bytes()
    members = [member for member in turn_members(data) if member.turn == pre_turn]
    raw_members = read_archive_members(data, [member.name for member in members])

    perspectives: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    relationto_values: Counter[str] = Counter()
    relationfrom_values: Counter[str] = Counter()
    conflict_values: Counter[str] = Counter()
    relation_key_shapes: Counter[tuple[str, ...]] = Counter()

    for member in members:
        parsed = _decode_turn(raw_members[member.name], member.name)
        player = parsed.get("player")
        active_player_id = _intish(player.get("id")) if isinstance(player, Mapping) else None
        embedded_game = parsed.get("game")
        embedded_turn = _intish(embedded_game.get("turn")) if isinstance(embedded_game, Mapping) else None
        raw_relations = parsed.get("relations")

        if not isinstance(raw_relations, list):
            perspectives.append(
                {
                    "member": member.name,
                    "member_player": member.player,
                    "active_player_id": active_player_id,
                    "embedded_turn": embedded_turn,
                    "relations_status": "missing_or_non_list",
                    "relations_count": 0,
                    "target_pair_rows": [],
                }
            )
            continue

        safe_rows: list[dict[str, int | None]] = []
        for raw_relation in raw_relations:
            if not isinstance(raw_relation, Mapping):
                continue
            relation_key_shapes[tuple(sorted(str(key) for key in raw_relation.keys()))] += 1
            safe = _safe_relation(raw_relation)
            safe_rows.append(safe)
            relationto_values[str(safe["relationto"])] += 1
            relationfrom_values[str(safe["relationfrom"])] += 1
            conflict_values[str(safe["conflictlevel"])] += 1

        pair = [row for row in safe_rows if _is_target_pair(row, args.player_a, args.player_b)]
        for row in pair:
            target_rows.append(
                {
                    "perspective_player": member.player,
                    **row,
                }
            )

        perspectives.append(
            {
                "member": member.name,
                "member_player": member.player,
                "active_player_id": active_player_id,
                "embedded_turn": embedded_turn,
                "relations_status": "list",
                "relations_count": len(safe_rows),
                "target_pair_rows": pair,
            }
        )

    unique = _unique_relation_values(target_rows, args.player_a, args.player_b)
    return {
        "schema": "planets-lab.combat-host-diplomacy-residual-audit.v1",
        "read_only": True,
        "game_id": int(args.game_id),
        "battle_turn": int(args.battle_turn),
        "pre_combat_archive_turn": pre_turn,
        "players": [int(args.player_a), int(args.player_b)],
        "summary": {
            "turn_members": len(members),
            "perspectives_with_relations": sum(1 for row in perspectives if row["relations_status"] == "list"),
            "target_pair_rows": len(target_rows),
        },
        "value_inventory": {
            "relationto": dict(sorted(relationto_values.items())),
            "relationfrom": dict(sorted(relationfrom_values.items())),
            "conflictlevel": dict(sorted(conflict_values.items())),
        },
        "relation_key_shapes": [
            {"keys": list(keys), "count": count}
            for keys, count in sorted(relation_key_shapes.items(), key=lambda item: (-item[1], item[0]))
        ],
        "perspectives": perspectives,
        "target_pair_rows": target_rows,
        "directed_unique_values": unique,
        "mirror_consistent": _mirror_consistent(unique, args.player_a, args.player_b),
        "evidence_boundary": (
            "Raw turn diplomacy schema/value probe only. It prints only numeric relation fields and does not assign "
            "Safe Passage semantics to relation levels. The battle uses T-1 as the pre-combat orders/diplomacy turn."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect raw pre-combat diplomacy for one ordinary combat residual.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--game-id", type=int, default=DEFAULT_GAME_ID)
    parser.add_argument("--battle-turn", type=int, default=DEFAULT_BATTLE_TURN)
    parser.add_argument("--player-a", type=int, default=DEFAULT_PLAYER_A)
    parser.add_argument("--player-b", type=int, default=DEFAULT_PLAYER_B)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT DIPLOMACY RESIDUAL AUDIT =====")
    print(f"game_id: {report['game_id']}")
    print(f"battle_turn: {report['battle_turn']}")
    print(f"pre_combat_archive_turn: {report['pre_combat_archive_turn']}")
    print(f"players: {report['players']}")
    print(f"summary: {report['summary']}")
    print(f"value_inventory: {report['value_inventory']}")
    print(f"relation_key_shapes: {report['relation_key_shapes']}")
    print(f"directed_unique_values: {report['directed_unique_values']}")
    print(f"mirror_consistent: {report['mirror_consistent']}")
    print("target_pair_rows:")
    for row in report["target_pair_rows"]:
        print(f"  {row}")
    print("perspectives:")
    for row in report["perspectives"]:
        print(
            "  "
            f"member={row['member']} member_player={row['member_player']} active_player={row['active_player_id']} "
            f"embedded_turn={row['embedded_turn']} relations_status={row['relations_status']} "
            f"relations_count={row['relations_count']} target_pair_rows={row['target_pair_rows']}"
        )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: raw relation values only; no numeric diplomacy level is labeled by this tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
