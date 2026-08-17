from __future__ import annotations

import gzip
import json
from collections import defaultdict
from math import hypot
from pathlib import Path

from planets_lab.corpus.archive import read_archive_member, turn_members


GAME_ID = 591478
PERIOD = 2170
TURNS = range(54, 61)
ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
CONTACT = (915, 2331)
PLANET_ID = 307
FOCUS_SHIPS = (329, 1096, 1185)
FOCUS_IDS = set(FOCUS_SHIPS)
OWNER6 = 6
NEAR_RADIUS = 100.0

SHIP_FIELDS = (
    "id", "ownerid", "hullid", "name", "x", "y", "warp", "targetx", "targety",
    "mission", "mission1target", "mission2target", "enemy", "iscloaked", "damage",
    "crew", "mass", "neutronium", "clans", "ammo", "podcargo", "turn", "turnkilled",
    "infoturn", "readystatus", "transfertargetid", "transfertargettype",
)

PLANET_FIELDS = (
    "id", "ownerid", "name", "x", "y", "clans", "nativeclans", "supplies",
    "megacredits", "neutronium", "duranium", "tritanium", "molybdenum", "podcargo",
    "podhullid", "podspeed", "friendlycode", "infoturn", "readystatus", "defense",
    "factories", "mines",
)


def decode_member(raw: bytes) -> dict:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return json.loads(payload.decode("utf-8-sig"))


def axis_delta(a: int, b: int) -> float:
    raw = b - a
    return ((raw + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def xy(raw):
    if raw is None or raw.get("x") is None or raw.get("y") is None:
        return None
    return (raw.get("x"), raw.get("y"))


def compact(raw, fields):
    if raw is None:
        return None
    return {key: raw.get(key) for key in fields if key in raw}


def norm_text(value, limit=1200):
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def vcr_side(raw):
    if not isinstance(raw, dict):
        return None
    return compact(raw, ("id", "objectid", "hullid", "name", "raceid", "side", "damage", "crew", "mass", "fighters"))


archive_data = ARCHIVE_PATH.read_bytes()
members = {(m.player, m.turn): m for m in turn_members(archive_data) if m.turn in TURNS}
cache = {}


def payload(player: int, turn: int):
    key = (player, turn)
    if key in cache:
        return cache[key]
    member = members.get(key)
    if member is None:
        return None
    parsed = decode_member(read_archive_member(archive_data, member.name))
    cache[key] = parsed
    return parsed


def owner_record(turn: int, ship_id: int):
    # Prefer the perspective whose player id matches ownerid in the record.
    fallback = None
    present = []
    for player in range(1, 31):
        data = payload(player, turn)
        if data is None:
            continue
        for raw in data.get("ships", []) or []:
            if not isinstance(raw, dict) or raw.get("id") != ship_id:
                continue
            present.append(player)
            if fallback is None:
                fallback = raw
            if raw.get("ownerid") == player:
                return player, raw, present
    return None, fallback, present


print("===== FOCUS SHIP LIFECYCLE THROUGH T60 =====")
for ship_id in FOCUS_SHIPS:
    print()
    print(f"SHIP {ship_id}")
    for turn in TURNS:
        owner_player, raw, present = owner_record(turn, ship_id)
        print({
            "turn": turn,
            "owner_record_player": owner_player,
            "present_in_perspectives": present,
            "state": compact(raw, SHIP_FIELDS),
            "distance_to_contact": distance(xy(raw), CONTACT) if raw else None,
        })

print()
print("===== PLANET 307 LIFECYCLE =====")
for turn in TURNS:
    rows = []
    for player in range(1, 31):
        data = payload(player, turn)
        if data is None:
            continue
        planet = next((p for p in data.get("planets", []) or [] if isinstance(p, dict) and p.get("id") == PLANET_ID), None)
        if planet is None:
            continue
        rows.append((player, planet))
    authoritative = None
    for player, planet in rows:
        if planet.get("ownerid") == player:
            authoritative = (player, planet)
            break
    if authoritative is None and rows:
        authoritative = rows[0]
    print({
        "turn": turn,
        "owner_record_player": None if authoritative is None else authoritative[0],
        "state": None if authoritative is None else compact(authoritative[1], PLANET_FIELDS),
        "perspectives_present": [player for player, _ in rows],
        "distance_to_contact": None if authoritative is None else distance(xy(authoritative[1]), CONTACT),
    })

print()
print("===== OWNER-6 LOCAL SHIP BIRTH / DEATH EVENTS =====")
owner6_by_turn = {}
for turn in TURNS:
    data = payload(OWNER6, turn)
    rows = {}
    if data is not None:
        for raw in data.get("ships", []) or []:
            if not isinstance(raw, dict) or raw.get("ownerid") != OWNER6:
                continue
            rows[raw.get("id")] = raw
    owner6_by_turn[turn] = rows

for prev_turn, turn in zip(TURNS, list(TURNS)[1:]):
    prev = owner6_by_turn[prev_turn]
    now = owner6_by_turn[turn]
    disappeared = sorted(set(prev) - set(now))
    appeared = sorted(set(now) - set(prev))

    def local_rows(ids, source):
        out = []
        for ship_id in ids:
            raw = source[ship_id]
            d = distance(xy(raw), CONTACT)
            if d is not None and d <= NEAR_RADIUS:
                out.append({"distance": d, **compact(raw, SHIP_FIELDS)})
        return out

    local_disappeared = local_rows(disappeared, prev)
    local_appeared = local_rows(appeared, now)
    if local_disappeared or local_appeared:
        print({
            "turn": (prev_turn, turn),
            "local_disappeared": local_disappeared,
            "local_appeared": local_appeared,
        })

print()
print("===== OWNER-6 LOCAL SHIPS EACH TURN (<=100 LY) =====")
for turn in TURNS:
    rows = []
    for raw in owner6_by_turn[turn].values():
        d = distance(xy(raw), CONTACT)
        if d is not None and d <= NEAR_RADIUS:
            rows.append({"distance": d, **compact(raw, SHIP_FIELDS)})
    rows.sort(key=lambda r: (r["distance"], r.get("id") or 0))
    print(f"TURN {turn} count={len(rows)}")
    for row in rows:
        print(row)

print()
print("===== EXACT TEXT MENTIONS OF FOCUS SHIPS =====")
needles = (
    "id#1096", "id #1096", "id#1185", "id #1185", "id#329", "id #329",
    "ru30 gunboats", "red mite", "nest",
)
seen_messages = set()
for turn in TURNS:
    for player in range(1, 31):
        data = payload(player, turn)
        if data is None:
            continue
        for msg in data.get("messages", []) or []:
            if not isinstance(msg, dict):
                continue
            headline = str(msg.get("headline") or "")
            body = str(msg.get("body") or "")
            hay = (headline + "\n" + body).lower()
            if not any(needle in hay for needle in needles):
                continue
            key = (msg.get("id"), msg.get("ownerid"), msg.get("turn"), headline, body)
            if key in seen_messages:
                continue
            seen_messages.add(key)
            print({
                "perspective_player": player,
                "id": msg.get("id"),
                "ownerid": msg.get("ownerid"),
                "target": msg.get("target"),
                "turn": msg.get("turn"),
                "x": msg.get("x"),
                "y": msg.get("y"),
                "distance_to_contact": distance((msg.get("x"), msg.get("y")), CONTACT)
                    if msg.get("x") is not None and msg.get("y") is not None else None,
                "messagetype": msg.get("messagetype"),
                "headline": norm_text(headline, 500),
                "body": norm_text(body, 1400),
            })

print()
print("===== PLANET-307 LOCAL MESSAGES =====")
seen_messages = set()
for turn in TURNS:
    for player in range(1, 31):
        data = payload(player, turn)
        if data is None:
            continue
        for msg in data.get("messages", []) or []:
            if not isinstance(msg, dict):
                continue
            mx, my = msg.get("x"), msg.get("y")
            d = None if mx is None or my is None else distance((mx, my), CONTACT)
            text = (str(msg.get("headline") or "") + "\n" + str(msg.get("body") or "")).lower()
            relevant = msg.get("target") == PLANET_ID or "id#307" in text or "id #307" in text
            if not relevant:
                continue
            key = (msg.get("id"), msg.get("ownerid"), msg.get("turn"), msg.get("headline"), msg.get("body"))
            if key in seen_messages:
                continue
            seen_messages.add(key)
            print({
                "perspective_player": player,
                "id": msg.get("id"),
                "ownerid": msg.get("ownerid"),
                "target": msg.get("target"),
                "turn": msg.get("turn"),
                "x": mx,
                "y": my,
                "distance_to_contact": d,
                "messagetype": msg.get("messagetype"),
                "headline": norm_text(msg.get("headline"), 500),
                "body": norm_text(msg.get("body"), 1400),
            })

print()
print("===== VCRS TOUCHING FOCUS OBJECTIDS OR LOCAL CONTACT =====")
seen_vcr = set()
for turn in TURNS:
    for player in range(1, 31):
        data = payload(player, turn)
        if data is None:
            continue
        for vcr in data.get("vcrs", []) or []:
            if not isinstance(vcr, dict):
                continue
            left = vcr.get("left") if isinstance(vcr.get("left"), dict) else {}
            right = vcr.get("right") if isinstance(vcr.get("right"), dict) else {}
            object_ids = {left.get("objectid"), right.get("objectid")}
            vx, vy = vcr.get("x"), vcr.get("y")
            d = None if vx is None or vy is None else distance((vx, vy), CONTACT)
            if not (object_ids & FOCUS_IDS) and not (d is not None and d <= 60):
                continue
            key = (vcr.get("id"), vcr.get("turn"), vcr.get("seed"), left.get("objectid"), right.get("objectid"))
            if key in seen_vcr:
                continue
            seen_vcr.add(key)
            print({
                "perspective_player": player,
                "id": vcr.get("id"),
                "turn": vcr.get("turn"),
                "x": vx,
                "y": vy,
                "distance_to_contact": d,
                "battletype": vcr.get("battletype"),
                "seed": vcr.get("seed"),
                "leftownerid": vcr.get("leftownerid"),
                "rightownerid": vcr.get("rightownerid"),
                "left": vcr_side(left),
                "right": vcr_side(right),
            })

print()
print("NOTE: period=2170 is an empirical coordinate-period candidate for game 591478 only.")
print("This diagnostic distinguishes lifecycle/destruction/conversion evidence from visibility and numeric-ID collisions.")
print("It does not assign semantics to numeric missions or assert a Host rule from one rendezvous.")
