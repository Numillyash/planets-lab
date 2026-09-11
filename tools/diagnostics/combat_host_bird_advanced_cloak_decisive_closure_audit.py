from __future__ import annotations

import argparse
import gzip
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from planets_lab.corpus.archive import read_archive_members, turn_members


SCHEMA = "planets-lab.combat-host-bird-advanced-cloak-decisive-closure-audit.v1"
RAW_DIR = Path("validation/corpus/cache/loadall")

FOCUS_ROWS = (
    {
        "label": "factual_mine_decloak",
        "game_id": 680435,
        "before_turn": 30,
        "battle_turn": 31,
        "owner_id": 3,
        "target_ship_id": 68,
        "attacker_ship_id": 26,
        "expected_blocked": False,
        "site": (1984, 2266),
    },
    {
        "label": "blocked_advanced_cloak_26",
        "game_id": 620694,
        "before_turn": 118,
        "battle_turn": 119,
        "owner_id": 3,
        "target_ship_id": 26,
        "attacker_ship_id": 74,
        "expected_blocked": True,
        "site": (1590, 1837),
    },
    {
        "label": "blocked_advanced_cloak_69",
        "game_id": 620694,
        "before_turn": 118,
        "battle_turn": 119,
        "owner_id": 3,
        "target_ship_id": 69,
        "attacker_ship_id": 74,
        "expected_blocked": True,
        "site": (1590, 1837),
    },
)

MINE_HIT_RE = re.compile(
    r"\bID#(?P<ship_id>\d+)\s+has\s+struck\s+a\s+mine!.*?"
    r"Damage\s+is\s+at:\s*(?P<damage>\d+)",
    re.IGNORECASE | re.DOTALL,
)


def _decode(raw: bytes, name: str) -> dict[str, Any]:
    payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{name}: expected top-level object")
    return parsed


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _ship(payload: Mapping[str, Any], ship_id: int) -> Mapping[str, Any] | None:
    for raw in payload.get("ships", []) or []:
        if isinstance(raw, Mapping) and _intish(raw.get("id")) == ship_id:
            return raw
    return None


def _mine_hit_from_message(raw: Mapping[str, Any], ship_id: int) -> dict[str, Any] | None:
    headline = str(raw.get("headline") or "")
    body = str(raw.get("body") or raw.get("text") or raw.get("message") or "")
    match = MINE_HIT_RE.search(f"{headline}\n{body}")
    if match is None or int(match.group("ship_id")) != ship_id:
        return None
    return {
        "message_id": raw.get("id"),
        "turn": raw.get("turn"),
        "x": raw.get("x"),
        "y": raw.get("y"),
        "damage": int(match.group("damage")),
        "messagetype": raw.get("messagetype"),
    }


def _target_vcr_side(
    payload: Mapping[str, Any],
    *,
    target_ship_id: int,
    site: tuple[int, int],
) -> dict[str, Any] | None:
    for vcr in payload.get("vcrs", []) or []:
        if not isinstance(vcr, Mapping):
            continue
        if (_intish(vcr.get("x")), _intish(vcr.get("y"))) != site:
            continue
        for side_name in ("left", "right"):
            side = vcr.get(side_name)
            if not isinstance(side, Mapping):
                continue
            object_id = _intish(side.get("objectid", side.get("shipid")))
            if object_id != target_ship_id:
                continue
            return {
                "vcr_id": vcr.get("id"),
                "side": side_name,
                "objectid": object_id,
                "hullid": _intish(side.get("hullid")),
                "raceid": _intish(side.get("raceid")),
                "damage": _intish(side.get("damage")),
                "crew": _intish(side.get("crew")),
            }
    return None


def _stable_same_ship(
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    *,
    owner_id: int,
) -> bool:
    if before is None or after is None:
        return False
    return (
        _intish(before.get("ownerid")) == owner_id
        and _intish(after.get("ownerid")) == owner_id
        and _intish(before.get("hullid")) is not None
        and _intish(before.get("hullid")) == _intish(after.get("hullid"))
    )


def _load_game_payloads(
    archive_dir: Path,
    *,
    game_id: int,
    owner_id: int,
    turns: set[int],
) -> dict[int, dict[str, Any]]:
    archive_path = archive_dir / f"game-{game_id}.zip"
    archive_data = archive_path.read_bytes()
    selected = [
        member
        for member in turn_members(archive_data)
        if member.player == owner_id and member.turn in turns
    ]
    raw_by_name = read_archive_members(archive_data, [member.name for member in selected])
    return {
        member.turn: _decode(raw_by_name[member.name], member.name)
        for member in selected
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    payload_cache: dict[tuple[int, int], dict[int, dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []

    summary = {
        "focus_rows": len(FOCUS_ROWS),
        "factual_rows": 0,
        "blocked_rows": 0,
        "explicit_target_mine_hit_rows": 0,
        "mine_hit_vcr_damage_match_rows": 0,
        "blocked_stable_t_cloak_true_rows": 0,
    }

    for focus in FOCUS_ROWS:
        game_id = int(focus["game_id"])
        owner_id = int(focus["owner_id"])
        before_turn = int(focus["before_turn"])
        battle_turn = int(focus["battle_turn"])
        target_ship_id = int(focus["target_ship_id"])
        site = tuple(int(value) for value in focus["site"])
        key = (game_id, owner_id)
        if key not in payload_cache:
            payload_cache[key] = _load_game_payloads(
                args.archive_dir,
                game_id=game_id,
                owner_id=owner_id,
                turns={before_turn, battle_turn},
            )
        payloads = payload_cache[key]
        before_payload = payloads.get(before_turn, {})
        battle_payload = payloads.get(battle_turn, {})
        before_ship = _ship(before_payload, target_ship_id)
        after_ship = _ship(battle_payload, target_ship_id)

        mine_hits = []
        for message in battle_payload.get("messages", []) or []:
            if not isinstance(message, Mapping):
                continue
            hit = _mine_hit_from_message(message, target_ship_id)
            if hit is not None:
                mine_hits.append(hit)

        vcr_side = _target_vcr_side(
            battle_payload,
            target_ship_id=target_ship_id,
            site=site,
        )
        stable_t = _stable_same_ship(before_ship, after_ship, owner_id=owner_id)
        t_cloak = _boolish(after_ship.get("iscloaked")) if stable_t and after_ship else None
        t_damage = _intish(after_ship.get("damage")) if stable_t and after_ship else None

        expected_blocked = bool(focus["expected_blocked"])
        if expected_blocked:
            summary["blocked_rows"] += 1
            closure_match = stable_t and t_cloak is True and t_damage == 0
            if closure_match:
                summary["blocked_stable_t_cloak_true_rows"] += 1
            closure_reason = (
                "stable_same_ship_t_cloak_true_damage0_attribution"
                if closure_match
                else "blocked_attribution_not_closed"
            )
        else:
            summary["factual_rows"] += 1
            explicit_hit = len(mine_hits) > 0
            if explicit_hit:
                summary["explicit_target_mine_hit_rows"] += 1
            hit_damage = mine_hits[0]["damage"] if len(mine_hits) == 1 else None
            vcr_damage = vcr_side.get("damage") if vcr_side is not None else None
            damage_match = (
                explicit_hit
                and len(mine_hits) == 1
                and isinstance(hit_damage, int)
                and hit_damage > 0
                and vcr_side is not None
                and vcr_damage == hit_damage
            )
            if damage_match:
                summary["mine_hit_vcr_damage_match_rows"] += 1
            closure_match = bool(damage_match)
            closure_reason = (
                "explicit_mine_hit_matches_positive_vcr_damage"
                if closure_match
                else "factual_mine_decloak_not_closed"
            )

        rows.append(
            {
                **focus,
                "site": list(site),
                "before": None
                if before_ship is None
                else {
                    "ownerid": _intish(before_ship.get("ownerid")),
                    "hullid": _intish(before_ship.get("hullid")),
                    "mission": _intish(before_ship.get("mission")),
                    "damage": _intish(before_ship.get("damage")),
                    "fuel": _intish(before_ship.get("neutronium")),
                    "iscloaked": _boolish(before_ship.get("iscloaked")),
                },
                "explicit_target_mine_hits": mine_hits,
                "factual_vcr_target_side": vcr_side,
                "t_stable_same_ship": stable_t,
                "t_damage_attribution_only": t_damage,
                "t_iscloaked_attribution_only": t_cloak,
                "closure_match": closure_match,
                "closure_reason": closure_reason,
            }
        )

    acceptance = {
        "factual_mine_decloak_closed": summary["mine_hit_vcr_damage_match_rows"] == 1,
        "blocked_advanced_controls_closed": summary["blocked_stable_t_cloak_true_rows"] == 2,
    }
    acceptance["all_decisive_advanced_rows_explained"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": summary,
        "acceptance": acceptance,
        "rows": rows,
        "evidence_boundary": (
            "This audit closes the three previously decisive-unresolved Advanced Cloak corpus rows using positive "
            "identity-safe attribution. The mine-hit message and VCR are factual Host outputs, while stable T cloak "
            "is attribution-only. These observations do not make Host messages or T state valid production inputs."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run(args)
    print("===== BIRD ADVANCED CLOAK DECISIVE CLOSURE =====")
    print("summary:", result["summary"])
    print("acceptance:", result["acceptance"])
    for row in result["rows"]:
        print(row)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print("wrote:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
