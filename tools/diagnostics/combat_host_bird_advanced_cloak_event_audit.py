from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.archive import read_archive_members, turn_members

from combat_host_priority_intercept_audit import RAW_DIR, SPECIAL_GAME_ID


SCHEMA = "planets-lab.combat-host-bird-advanced-cloak-event-audit.v1"
DEFAULT_TEXT_LIMIT = 1600
DEFAULT_RECORD_LIMIT = 200

FOCUS_CASES: tuple[dict[str, Any], ...] = (
    {
        "label": "advanced_factual_680435_t31",
        "game_id": 680435,
        "before_turn": 30,
        "battle_turn": 31,
        "target_owner_id": 3,
        "target_ship_ids": (68,),
        "attacker_ship_ids": (26,),
        "site": (1984, 2266),
        "expected_blocked": False,
    },
    {
        "label": "advanced_skipped_620694_t119",
        "game_id": 620694,
        "before_turn": 118,
        "battle_turn": 119,
        "target_owner_id": 3,
        "target_ship_ids": (26, 69),
        "attacker_ship_ids": (74,),
        "site": (1590, 1837),
        "expected_blocked": True,
    },
)

MECHANICAL_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mine", ("mine hit", "minefield", "mine field", "hit a mine", "mine")),
    ("web", ("web mine", "webmine", "web field", "web")),
    ("cloak", ("decloak", "de-cloak", "uncloak", "cloak")),
    ("loki", ("loki",)),
    ("glory", ("glory", "pop", "trg")),
    ("damage", ("damaged", "damage",)),
    ("fuel", ("out of fuel", "fuel", "neutronium")),
    ("ion", ("ion pulse", "ion storm", "ion")),
    ("warp_well", ("warp well", "warpwell")),
    ("combat", ("combat", "battle", "attacked", "attack")),
)

EVENT_KEY_TOKENS = (
    "event",
    "report",
    "message",
    "history",
    "activity",
    "notification",
    "combat",
    "battle",
    "fight",
    "attack",
)

TEXT_KEYS = {
    "body",
    "text",
    "message",
    "subject",
    "headline",
    "title",
    "description",
    "note",
    "comment",
}

REFERENCE_KEYS = {
    "target",
    "targetid",
    "target_id",
    "shipid",
    "ship_id",
    "objectid",
    "object_id",
    "attackerid",
    "attacker_id",
    "defenderid",
    "defender_id",
    "planetid",
    "planet_id",
    "combatid",
    "combat_id",
    "battleid",
    "battle_id",
}

SAFE_STRING_KEYS = {
    "type",
    "kind",
    "status",
    "result",
    "eventtype",
    "messagetype",
    "targettype",
    "objecttype",
}

SETTINGS_KEYS = (
    "campaignmode",
    "cloakfail",
    "cloakandintercept",
    "racehullsonlycloakandintercept",
    "nowarpwells",
    "sphere",
    "mapshape",
    "mapwidth",
    "mapheight",
)

SHIP_FIELDS = (
    "id",
    "ownerid",
    "hullid",
    "name",
    "x",
    "y",
    "warp",
    "targetx",
    "targety",
    "mission",
    "enemy",
    "friendlycode",
    "iscloaked",
    "damage",
    "neutronium",
    "mass",
    "infoturn",
    "turn",
    "turnkilled",
)

MINEFIELD_FIELDS = (
    "id",
    "ownerid",
    "x",
    "y",
    "radius",
    "units",
    "mines",
    "isweb",
    "infoturn",
    "turn",
    "friendlycode",
)


def _decode_member(raw: bytes, name: str) -> dict[str, Any]:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{name}: expected top-level JSON object")
    return parsed


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _norm_text(value: Any, limit: int = DEFAULT_TEXT_LIMIT) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def _mechanical_keywords(value: Any) -> list[str]:
    text = " ".join(str(value or "").lower().split())
    found: list[str] = []
    for label, needles in MECHANICAL_TERMS:
        if any(needle in text for needle in needles):
            found.append(label)
    return found


def _mapping_references_ids(raw: Mapping[str, Any], focus_ids: set[int]) -> bool:
    for key, value in raw.items():
        key_text = str(key).lower()
        if key_text not in REFERENCE_KEYS:
            continue
        if isinstance(value, bool):
            continue
        candidate = _intish(value)
        if candidate is not None and candidate in focus_ids:
            return True
    return False


def _site_match(raw: Mapping[str, Any], site: tuple[int, int]) -> bool:
    x = _intish(raw.get("x"))
    y = _intish(raw.get("y"))
    return x == site[0] and y == site[1]


def _focus_name_hit(text: str, names: set[str]) -> bool:
    lowered = text.lower()
    return any(name and name.lower() in lowered for name in names)


def _focus_ship_id_text_hit(text: str, ship_ids: set[int]) -> bool:
    lowered = text.lower()
    for ship_id in ship_ids:
        patterns = (
            rf"\bship\s*#?\s*{ship_id}\b",
            rf"\bship\s+id\s*#?\s*{ship_id}\b",
            rf"\bshipid\s*[:=#]?\s*{ship_id}\b",
        )
        if any(re.search(pattern, lowered) for pattern in patterns):
            return True
    return False


def _message_matches_focus(
    raw: Mapping[str, Any],
    *,
    focus_ids: set[int],
    focus_ship_ids: set[int],
    focus_names: set[str],
    site: tuple[int, int],
) -> bool:
    if _mapping_references_ids(raw, focus_ids):
        return True

    text = " ".join(
        str(raw.get(key) or "")
        for key in ("headline", "subject", "body", "text", "message", "description")
    )
    keywords = _mechanical_keywords(text)
    if not keywords:
        return False
    if _site_match(raw, site):
        return True
    if _focus_name_hit(text, focus_names):
        return True
    return _focus_ship_id_text_hit(text, focus_ship_ids)


def _message_projection(raw: Mapping[str, Any]) -> dict[str, Any]:
    headline = _norm_text(raw.get("headline"), 500)
    body = _norm_text(raw.get("body", raw.get("text", raw.get("message"))))
    combined = f"{headline or ''} {body or ''}"
    return {
        "id": raw.get("id"),
        "ownerid": raw.get("ownerid"),
        "target": raw.get("target"),
        "targettype": raw.get("targettype"),
        "turn": raw.get("turn"),
        "x": raw.get("x"),
        "y": raw.get("y"),
        "messagetype": raw.get("messagetype"),
        "headline": headline,
        "body": body,
        "mechanical_keywords": _mechanical_keywords(combined),
    }


def _sanitize_event_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    suppressed_text: list[str] = []
    for key, value in raw.items():
        key_text = str(key)
        lowered = key_text.lower()
        if lowered in TEXT_KEYS:
            if value not in (None, "", [], {}):
                suppressed_text.append(key_text)
            continue
        if value is None or isinstance(value, (bool, int, float)):
            result[key_text] = value
        elif isinstance(value, str) and lowered in SAFE_STRING_KEYS:
            result[key_text] = value
        elif isinstance(value, list):
            result[f"{key_text}__len"] = len(value)
        elif isinstance(value, Mapping):
            result[f"{key_text}__keys"] = sorted(str(child) for child in value)
    if suppressed_text:
        result["suppressed_text_fields"] = sorted(suppressed_text)
    return result


def _active_advantage_projection(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    advantage_names: dict[int, str | None] = {}
    for raw in payload.get("advantages", []) or []:
        if not isinstance(raw, Mapping):
            continue
        advantage_id = _intish(raw.get("id"))
        if advantage_id is None:
            continue
        name = raw.get("name")
        advantage_names[advantage_id] = str(name) if name is not None else None

    player = payload.get("player")
    player = player if isinstance(player, Mapping) else {}
    active = player.get("activeadvantages") or []
    result: list[dict[str, Any]] = []
    for item in active:
        if isinstance(item, Mapping):
            advantage_id = _intish(item.get("id"))
            embedded_name = item.get("name")
        else:
            advantage_id = _intish(item)
            embedded_name = None
        if advantage_id is None:
            continue
        name = advantage_names.get(advantage_id)
        if name is None and embedded_name is not None:
            name = str(embedded_name)
        result.append({"id": advantage_id, "name": name})
    result.sort(key=lambda row: int(row["id"]))
    return result


def _relevant_advantages(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    tokens = ("mine", "cloak", "loki", "glory", "spy", "immune", "hidden", "intercept")
    result: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("name") or "").lower()
        if any(token in name for token in tokens):
            result.append(dict(row))
    return result


def _compact(raw: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    return {field: raw.get(field) for field in fields if field in raw}


def _vcr_side(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    return _compact(
        raw,
        (
            "id",
            "objectid",
            "hullid",
            "name",
            "raceid",
            "side",
            "damage",
            "crew",
            "mass",
            "fighters",
            "hasstarbase",
        ),
    )


def _vcr_matches_focus(
    raw: Mapping[str, Any],
    *,
    focus_ids: set[int],
    site: tuple[int, int],
) -> bool:
    if _site_match(raw, site):
        return True
    for side_key in ("left", "right"):
        side = raw.get(side_key)
        if not isinstance(side, Mapping):
            continue
        for key in ("id", "objectid", "shipid"):
            value = _intish(side.get(key))
            if value is not None and value in focus_ids:
                return True
    return False


def _vcr_projection(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "turn": raw.get("turn"),
        "x": raw.get("x"),
        "y": raw.get("y"),
        "battletype": raw.get("battletype"),
        "seed": raw.get("seed"),
        "leftownerid": raw.get("leftownerid"),
        "rightownerid": raw.get("rightownerid"),
        "left": _vcr_side(raw.get("left")),
        "right": _vcr_side(raw.get("right")),
    }


def _member_window(case: Mapping[str, Any]) -> set[int]:
    before_turn = int(case["before_turn"])
    battle_turn = int(case["battle_turn"])
    return {before_turn, battle_turn, battle_turn + 1}


def _ship_names(
    payloads: Mapping[tuple[int, int], Mapping[str, Any]],
    ship_ids: set[int],
) -> set[str]:
    result: set[str] = set()
    for payload in payloads.values():
        for ship in payload.get("ships", []) or []:
            if not isinstance(ship, Mapping):
                continue
            ship_id = _intish(ship.get("id"))
            if ship_id not in ship_ids:
                continue
            name = ship.get("name")
            if isinstance(name, str) and name.strip():
                result.add(name.strip())
    return result


def _case_report(case: Mapping[str, Any], archive_dir: Path) -> dict[str, Any]:
    game_id = int(case["game_id"])
    archive_path = archive_dir / f"game-{game_id}.zip"
    if not archive_path.exists():
        return {
            "label": case["label"],
            "game_id": game_id,
            "archive_found": False,
        }

    archive_data = archive_path.read_bytes()
    wanted_turns = _member_window(case)
    members = [member for member in turn_members(archive_data) if member.turn in wanted_turns]
    raw_by_name = read_archive_members(archive_data, [member.name for member in members])
    payloads: dict[tuple[int, int], dict[str, Any]] = {}
    for member in members:
        payloads[(member.player, member.turn)] = _decode_member(
            raw_by_name[member.name],
            member.name,
        )

    target_owner_id = int(case["target_owner_id"])
    target_ship_ids = {int(value) for value in case["target_ship_ids"]}
    attacker_ship_ids = {int(value) for value in case["attacker_ship_ids"]}
    focus_ship_ids = target_ship_ids | attacker_ship_ids
    focus_ids = set(focus_ship_ids)
    site = (int(case["site"][0]), int(case["site"][1]))
    focus_names = _ship_names(payloads, focus_ship_ids)

    target_owner_rows: list[dict[str, Any]] = []
    active_advantage_name_counts: Counter[str] = Counter()
    for turn in sorted(wanted_turns):
        payload = payloads.get((target_owner_id, turn))
        if payload is None:
            target_owner_rows.append({"turn": turn, "member_found": False})
            continue
        active = _active_advantage_projection(payload)
        for row in active:
            active_advantage_name_counts[str(row.get("name") or f"id:{row['id']}")] += 1
        settings = payload.get("settings")
        settings = settings if isinstance(settings, Mapping) else {}
        player = payload.get("player")
        player = player if isinstance(player, Mapping) else {}
        minefields = [
            _compact(raw, MINEFIELD_FIELDS)
            for raw in payload.get("minefields", []) or []
            if isinstance(raw, Mapping)
        ]
        target_owner_rows.append(
            {
                "turn": turn,
                "member_found": True,
                "player_id": player.get("id", target_owner_id),
                "settings": {key: settings.get(key) for key in SETTINGS_KEYS if key in settings},
                "active_advantages": active,
                "relevant_active_advantages": _relevant_advantages(active),
                "visible_minefield_count": len(minefields),
                "visible_minefields": minefields[:DEFAULT_RECORD_LIMIT],
            }
        )

    ship_timeline: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    event_records: list[dict[str, Any]] = []
    vcrs: list[dict[str, Any]] = []
    message_keysets: Counter[tuple[str, ...]] = Counter()
    event_keysets: Counter[tuple[str, ...]] = Counter()

    for (player_id, turn), payload in sorted(payloads.items()):
        for ship in payload.get("ships", []) or []:
            if not isinstance(ship, Mapping):
                continue
            ship_id = _intish(ship.get("id"))
            if ship_id not in focus_ship_ids:
                continue
            ship_timeline.append(
                {
                    "perspective_player_id": player_id,
                    "archive_turn": turn,
                    **_compact(ship, SHIP_FIELDS),
                }
            )

        for raw in payload.get("messages", []) or []:
            if not isinstance(raw, Mapping):
                continue
            message_keysets[tuple(sorted(str(key) for key in raw))] += 1
            if not _message_matches_focus(
                raw,
                focus_ids=focus_ids,
                focus_ship_ids=focus_ship_ids,
                focus_names=focus_names,
                site=site,
            ):
                continue
            messages.append(
                {
                    "perspective_player_id": player_id,
                    "archive_turn": turn,
                    **_message_projection(raw),
                }
            )

        for key, value in payload.items():
            key_lower = str(key).lower()
            if key_lower in {"messages", "vcrs"}:
                continue
            if not any(token in key_lower for token in EVENT_KEY_TOKENS):
                continue
            if not isinstance(value, list):
                continue
            for index, raw in enumerate(value):
                if not isinstance(raw, Mapping):
                    continue
                event_keysets[tuple(sorted(str(child) for child in raw))] += 1
                if not (
                    _mapping_references_ids(raw, focus_ids)
                    or _site_match(raw, site)
                ):
                    continue
                event_records.append(
                    {
                        "perspective_player_id": player_id,
                        "archive_turn": turn,
                        "collection": str(key),
                        "index": index,
                        "record": _sanitize_event_mapping(raw),
                    }
                )

        for raw in payload.get("vcrs", []) or []:
            if not isinstance(raw, Mapping):
                continue
            if not _vcr_matches_focus(raw, focus_ids=focus_ids, site=site):
                continue
            vcrs.append(
                {
                    "perspective_player_id": player_id,
                    "archive_turn": turn,
                    **_vcr_projection(raw),
                }
            )

    messages.sort(
        key=lambda row: (
            int(row["archive_turn"]),
            int(row["perspective_player_id"]),
            _intish(row.get("id")) or -1,
        )
    )
    vcrs.sort(
        key=lambda row: (
            int(row["archive_turn"]),
            int(row["perspective_player_id"]),
            _intish(row.get("id")) or -1,
        )
    )

    keyword_counts: Counter[str] = Counter()
    for row in messages:
        for keyword in row.get("mechanical_keywords", []):
            keyword_counts[str(keyword)] += 1

    return {
        "label": case["label"],
        "game_id": game_id,
        "archive_found": True,
        "before_turn": int(case["before_turn"]),
        "battle_turn": int(case["battle_turn"]),
        "expected_blocked": bool(case["expected_blocked"]),
        "target_owner_id": target_owner_id,
        "target_ship_ids": sorted(target_ship_ids),
        "attacker_ship_ids": sorted(attacker_ship_ids),
        "site": list(site),
        "selected_turns": sorted(wanted_turns),
        "selected_member_count": len(members),
        "focus_ship_names": sorted(focus_names),
        "target_owner_context": target_owner_rows,
        "active_advantage_name_counts": dict(sorted(active_advantage_name_counts.items())),
        "focus_ship_timeline": ship_timeline[:DEFAULT_RECORD_LIMIT],
        "focus_messages": messages[:DEFAULT_RECORD_LIMIT],
        "focus_message_keyword_counts": dict(sorted(keyword_counts.items())),
        "focus_event_records": event_records[:DEFAULT_RECORD_LIMIT],
        "focus_vcrs": vcrs[:DEFAULT_RECORD_LIMIT],
        "message_keysets": [
            {"keys": list(keys), "count": count}
            for keys, count in message_keysets.most_common(20)
        ],
        "event_keysets": [
            {"keys": list(keys), "count": count}
            for keys, count in event_keysets.most_common(20)
        ],
        "evidence_boundary": (
            "Raw Host message/event inventory for exact Advanced-Cloak focus IDs and battle-site coordinates only. "
            "Positive mechanical reports can support an attribution hypothesis. Absence of a report is not proof that "
            "the event did not occur because archive perspective/message completeness is not assumed. Active advantages "
            "are descriptive game/race context only. No message or T state is fed into canonical combat selection."
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    cases = [_case_report(case, args.archive_dir) for case in FOCUS_CASES]
    totals: Counter[str] = Counter()
    for case in cases:
        totals["cases"] += 1
        if case.get("archive_found") is True:
            totals["archives_found"] += 1
        totals["focus_messages"] += len(case.get("focus_messages", []))
        totals["focus_event_records"] += len(case.get("focus_event_records", []))
        totals["focus_vcrs"] += len(case.get("focus_vcrs", []))
        for keyword, count in (case.get("focus_message_keyword_counts") or {}).items():
            totals[f"message_keyword:{keyword}"] += int(count)

    return {
        "schema": SCHEMA,
        "read_only": True,
        "special_game_591478_excluded": True,
        "summary": dict(sorted(totals.items())),
        "cases": cases,
        "evidence_boundary": (
            "Focused raw-report attribution gate for the unresolved Bird Advanced-Cloak STANDARD-control contrast. "
            "The audit deliberately requires exact focus IDs, exact battle coordinates, or focus ship names/IDs paired "
            "with mechanical keywords before exposing message text. Absence remains non-evidence."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect raw Host reports/events and active advantages for the unresolved Bird Advanced Cloak rows."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT BIRD ADVANCED CLOAK EVENT AUDIT =====")
    print(f"summary: {report['summary']}")
    for case in report["cases"]:
        print()
        print("CASE:", case["label"])
        print(
            {
                "game_id": case.get("game_id"),
                "archive_found": case.get("archive_found"),
                "before_turn": case.get("before_turn"),
                "battle_turn": case.get("battle_turn"),
                "expected_blocked": case.get("expected_blocked"),
                "target_ship_ids": case.get("target_ship_ids"),
                "attacker_ship_ids": case.get("attacker_ship_ids"),
                "site": case.get("site"),
                "focus_ship_names": case.get("focus_ship_names"),
                "focus_message_keyword_counts": case.get("focus_message_keyword_counts"),
                "active_advantage_name_counts": case.get("active_advantage_name_counts"),
            }
        )
        print("TARGET OWNER CONTEXT:")
        for row in case.get("target_owner_context", []):
            print(row)
        print("FOCUS MESSAGES:")
        for row in case.get("focus_messages", []):
            print(row)
        print("FOCUS EVENT RECORDS:")
        for row in case.get("focus_event_records", []):
            print(row)
        print("FOCUS VCRS:")
        for row in case.get("focus_vcrs", []):
            print(row)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: positive raw mechanical reports are attribution evidence; report absence is not proof of no event.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
