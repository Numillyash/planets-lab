from __future__ import annotations

import gzip
import json
from collections import defaultdict
from collections.abc import Mapping
from math import hypot
from pathlib import Path
from typing import Any

from planets_lab.corpus.archive import read_archive_members, turn_members


GAME_ID = 591478
PERIOD = 2170
ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
TURNS = range(54, 58)
FOCUS_IDS = {329, 1185, 1096, 311}
CONTACT = (915, 2331)

TRANSFER_FIELDS = (
    "transferammo",
    "transferclans",
    "transferduranium",
    "transfermegacredits",
    "transfermolybdenum",
    "transferneutronium",
    "transfersupplies",
    "transfertritanium",
    "transfertargetid",
    "transfertargettype",
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
    "mission1target",
    "mission2target",
    "enemy",
    "iscloaked",
    "damage",
    "crew",
    "mass",
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "supplies",
    "clans",
    "megacredits",
    "ammo",
    "podcargo",
    "friendlycode",
    "turn",
    "turnkilled",
    "infoturn",
    "readystatus",
) + TRANSFER_FIELDS

PLANET_FIELDS = (
    "id",
    "ownerid",
    "name",
    "x",
    "y",
    "clans",
    "nativeclans",
    "supplies",
    "megacredits",
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "podcargo",
    "podhullid",
    "podspeed",
    "friendlycode",
    "infoturn",
    "readystatus",
    "defense",
    "factories",
    "mines",
    "starbaseid",
    "isbase",
)

HULL_FIELDS = (
    "id",
    "name",
    "mass",
    "cargo",
    "crew",
    "fueltank",
    "cancloak",
    "special",
    "advantage",
    "parentid",
    "beams",
    "launchers",
    "fighterbays",
)

TEXT_FIELD_TOKENS = (
    "body",
    "text",
    "message",
    "subject",
    "title",
    "description",
    "note",
    "comment",
    "username",
    "email",
    "savekey",
    "password",
)

REFERENCE_KEY_TOKENS = (
    "id",
    "ship",
    "planet",
    "target",
    "attacker",
    "defender",
    "enemy",
    "owner",
    "object",
    "vcr",
    "combat",
    "battle",
)

EVENT_KEY_TOKENS = (
    "battle",
    "combat",
    "event",
    "report",
    "history",
    "activity",
    "notification",
    "fight",
    "attack",
)

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


def decode_member(raw: bytes) -> dict[str, Any]:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError("expected top-level object")
    return parsed


def compact(raw: Mapping[str, Any], fields) -> dict[str, Any]:
    return {key: raw.get(key) for key in fields if key in raw}


def norm_text(value: Any, limit: int = 1200):
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def axis_delta(a: float, b: float, period: float = PERIOD) -> float:
    raw = b - a
    return ((raw + period / 2) % period) - period / 2


def distance(a, b):
    if a is None or b is None or None in a or None in b:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def xy(raw: Mapping[str, Any] | None):
    if not isinstance(raw, Mapping):
        return None
    x = raw.get("x")
    y = raw.get("y")
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        return None
    if not isinstance(y, (int, float)) or isinstance(y, bool):
        return None
    return (x, y)


def is_text_key(key: Any) -> bool:
    text = str(key).lower()
    return any(token in text for token in TEXT_FIELD_TOKENS)


def looks_like_reference_key(key: Any) -> bool:
    text = str(key).lower()
    return any(token in text for token in REFERENCE_KEY_TOKENS)


def looks_like_event_key(key: Any) -> bool:
    text = str(key).lower()
    return any(token in text for token in EVENT_KEY_TOKENS)


def object_references(raw: Mapping[str, Any], refs: set[int]) -> bool:
    for key, value in raw.items():
        if not looks_like_reference_key(key):
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value in refs:
            return True
        if isinstance(value, float) and value.is_integer() and int(value) in refs:
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, int) and not isinstance(item, bool) and item in refs:
                    return True
    return False


def sanitize_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    suppressed = []
    for key, value in raw.items():
        key_text = str(key)
        if is_text_key(key):
            if value not in (None, "", [], {}):
                suppressed.append(key_text)
            continue
        if value is None or isinstance(value, (bool, int, float)):
            result[key_text] = value
            continue
        if isinstance(value, str) and key_text.lower() in SAFE_STRING_KEYS:
            result[key_text] = value
            continue
        if isinstance(value, list):
            result[f"{key_text}__len"] = len(value)
        elif isinstance(value, Mapping):
            result[f"{key_text}__keys"] = sorted(str(k) for k in value.keys())
    if suppressed:
        result["suppressed_text_fields"] = sorted(suppressed)
    return result


def vcr_side(raw):
    if not isinstance(raw, Mapping):
        return None
    return compact(
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


archive_data = ARCHIVE_PATH.read_bytes()
all_members = [m for m in turn_members(archive_data) if m.turn in TURNS]
raw_by_name = read_archive_members(archive_data, [m.name for m in all_members])

payloads: dict[tuple[int, int], dict[str, Any]] = {}
for member in all_members:
    payloads[(member.player, member.turn)] = decode_member(raw_by_name[member.name])

players_by_turn = defaultdict(list)
for player, turn in payloads:
    players_by_turn[turn].append(player)
for turn in players_by_turn:
    players_by_turn[turn].sort()


def all_ship_records(turn: int, ship_id: int):
    rows = []
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for ship in data.get("ships", []) or []:
            if isinstance(ship, Mapping) and ship.get("id") == ship_id:
                rows.append((player, ship))
    return rows


def owner_ship(turn: int, ship_id: int):
    rows = all_ship_records(turn, ship_id)
    if not rows:
        return None, None
    for player, ship in rows:
        if ship.get("ownerid") == player:
            return player, ship
    return rows[0]


def owner_ships_for_turn(turn: int):
    candidates: dict[int, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for ship in data.get("ships", []) or []:
            if not isinstance(ship, Mapping):
                continue
            sid = ship.get("id")
            if isinstance(sid, int) and not isinstance(sid, bool):
                candidates[sid].append((player, ship))
    out = []
    for sid, rows in candidates.items():
        chosen = next(((p, s) for p, s in rows if s.get("ownerid") == p), rows[0])
        out.append(chosen)
    return out


def owner_planets_for_turn(turn: int):
    candidates: dict[int, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for planet in data.get("planets", []) or []:
            if not isinstance(planet, Mapping):
                continue
            pid = planet.get("id")
            if isinstance(pid, int) and not isinstance(pid, bool):
                candidates[pid].append((player, planet))
    out = []
    for pid, rows in candidates.items():
        chosen = next(((p, s) for p, s in rows if s.get("ownerid") == p), rows[0])
        out.append(chosen)
    return out


print("===== ARCHIVE WINDOW =====")
print("game:", GAME_ID)
print("turns:", list(TURNS))
print("period_candidate:", PERIOD)
for turn in TURNS:
    print({"turn": turn, "players_with_member": players_by_turn.get(turn, [])})

print()
print("===== FOCUS HULL METADATA =====")
sample = next(iter(payloads.values()), None)
if sample is not None:
    focus_hulls = set()
    for turn in TURNS:
        for sid in FOCUS_IDS:
            _player, ship = owner_ship(turn, sid)
            if ship is not None and isinstance(ship.get("hullid"), int):
                focus_hulls.add(ship.get("hullid"))
    for hull in sample.get("hulls", []) or []:
        if isinstance(hull, Mapping) and hull.get("id") in focus_hulls:
            print(compact(hull, HULL_FIELDS))

print()
print("===== FOCUS OWNER-AUTHORITATIVE SHIP TIMELINES =====")
for sid in sorted(FOCUS_IDS):
    print()
    print("SHIP", sid)
    for turn in TURNS:
        player, ship = owner_ship(turn, sid)
        print(
            {
                "turn": turn,
                "owner_record_player": player,
                "state": None if ship is None else compact(ship, SHIP_FIELDS),
                "perspectives_present": [p for p, _s in all_ship_records(turn, sid)],
            }
        )

print()
print("===== RENDEZVOUS GEOMETRY =====")
for turn in TURNS:
    focus = {}
    for sid in sorted(FOCUS_IDS):
        _p, ship = owner_ship(turn, sid)
        focus[sid] = None if ship is None else {
            "xy": xy(ship),
            "distance_to_contact": distance(xy(ship), CONTACT),
            "targetxy": (ship.get("targetx"), ship.get("targety")),
            "targetxy_distance_to_contact": distance(
                (ship.get("targetx"), ship.get("targety")), CONTACT
            ),
            "mission": ship.get("mission"),
            "m1": ship.get("mission1target"),
            "owner": ship.get("ownerid"),
        }
    print({"turn": turn, "focus": focus})

print()
print("===== ALL OWNER-AUTHORITATIVE SHIPS NEAR CONTACT =====")
for turn in TURNS:
    rows = []
    for player, ship in owner_ships_for_turn(turn):
        d = distance(xy(ship), CONTACT)
        if d is not None and d <= 50:
            rows.append((d, player, ship))
    rows.sort(key=lambda item: (item[0], item[2].get("id", -1)))
    print()
    print(f"TURN {turn} count={len(rows)}")
    for d, player, ship in rows:
        print({
            "distance": d,
            "owner_record_player": player,
            **compact(ship, SHIP_FIELDS),
        })

print()
print("===== NEAREST OWNER-AUTHORITATIVE PLANETS TO CONTACT =====")
for turn in TURNS:
    rows = []
    for player, planet in owner_planets_for_turn(turn):
        d = distance(xy(planet), CONTACT)
        if d is not None:
            rows.append((d, player, planet))
    rows.sort(key=lambda item: (item[0], item[2].get("id", -1)))
    print()
    print(f"TURN {turn}")
    for d, player, planet in rows[:5]:
        print({
            "distance": d,
            "owner_record_player": player,
            **compact(planet, PLANET_FIELDS),
        })

print()
print("===== FOCUS SYSTEM/MESSAGE RECORDS =====")
seen_messages = set()
for turn in TURNS:
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for msg in data.get("messages", []) or []:
            if not isinstance(msg, Mapping):
                continue
            target = msg.get("target")
            msg_xy = xy(msg)
            touches_id = target in FOCUS_IDS
            touches_point = distance(msg_xy, CONTACT)
            touches_point = touches_point is not None and touches_point <= 10
            if not (touches_id or touches_point):
                continue
            key = (
                msg.get("id"), msg.get("turn"), msg.get("ownerid"),
                target, msg.get("messagetype"), msg.get("headline"), msg.get("body")
            )
            if key in seen_messages:
                continue
            seen_messages.add(key)
            print({
                "perspective_player": player,
                "id": msg.get("id"),
                "ownerid": msg.get("ownerid"),
                "target": target,
                "turn": msg.get("turn"),
                "x": msg.get("x"),
                "y": msg.get("y"),
                "distance_to_contact": distance(msg_xy, CONTACT),
                "messagetype": msg.get("messagetype"),
                "headline": norm_text(msg.get("headline"), 500),
                "body": norm_text(msg.get("body"), 1600),
            })
if not seen_messages:
    print("NONE")

print()
print("===== FOCUS VCR / COMBAT RECORDS =====")
seen_vcrs = set()
for turn in TURNS:
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for vcr in data.get("vcrs", []) or []:
            if not isinstance(vcr, Mapping):
                continue
            left = vcr.get("left") if isinstance(vcr.get("left"), Mapping) else {}
            right = vcr.get("right") if isinstance(vcr.get("right"), Mapping) else {}
            nested_ids = {
                left.get("id"), left.get("objectid"),
                right.get("id"), right.get("objectid"),
            }
            d = distance(xy(vcr), CONTACT)
            touches_point = d is not None and d <= 10
            touches_id = bool(nested_ids & FOCUS_IDS)
            if not (touches_point or touches_id):
                continue
            key = (vcr.get("id"), vcr.get("turn"), vcr.get("seed"))
            if key in seen_vcrs:
                continue
            seen_vcrs.add(key)
            print({
                "perspective_player": player,
                "id": vcr.get("id"),
                "turn": vcr.get("turn"),
                "x": vcr.get("x"),
                "y": vcr.get("y"),
                "distance_to_contact": d,
                "battletype": vcr.get("battletype"),
                "seed": vcr.get("seed"),
                "leftownerid": vcr.get("leftownerid"),
                "rightownerid": vcr.get("rightownerid"),
                "left": vcr_side(left),
                "right": vcr_side(right),
            })
if not seen_vcrs:
    print("NONE")

print()
print("===== OTHER EVENT-LIKE RECORDS REFERENCING FOCUS IDS =====")
seen_events = set()
for turn in TURNS:
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for top_key, value in data.items():
            if top_key in {"messages", "vcrs"} or not looks_like_event_key(top_key):
                continue
            items = value if isinstance(value, list) else [value]
            for index, item in enumerate(items):
                if not isinstance(item, Mapping) or not object_references(item, FOCUS_IDS):
                    continue
                safe = sanitize_mapping(item)
                fingerprint = (turn, top_key, json.dumps(safe, sort_keys=True, default=str))
                if fingerprint in seen_events:
                    continue
                seen_events.add(fingerprint)
                print({
                    "perspective_player": player,
                    "turn": turn,
                    "top_key": top_key,
                    "index": index,
                    "record": safe,
                })
if not seen_events:
    print("NONE")

print()
print("===== RAW TOP-LEVEL EVENT-LIKE LIST SCHEMAS =====")
for turn in (55, 56):
    printed = set()
    for player in players_by_turn.get(turn, []):
        data = payloads[(player, turn)]
        for key, value in data.items():
            if not isinstance(value, list):
                continue
            if key not in {"messages", "vcrs"} and not looks_like_event_key(key):
                continue
            mapping_items = [item for item in value if isinstance(item, Mapping)]
            item_keys = sorted({str(k) for item in mapping_items[:20] for k in item.keys()})
            signature = (key, tuple(item_keys), len(value))
            if signature in printed:
                continue
            printed.add(signature)
            print({
                "turn": turn,
                "sample_player": player,
                "key": key,
                "len": len(value),
                "item_keys": item_keys,
            })

print()
print("NOTE: period=2170 is an empirical coordinate-period candidate for game 591478 only.")
print("This diagnostic inspects raw event context around the unique 329/1185 rendezvous.")
print("It does not assign semantics to numeric mission codes or infer causality from contact alone.")
