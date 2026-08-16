from __future__ import annotations

import gzip
import json
from pathlib import Path

from planets_lab.corpus.archive import read_archive_member, turn_members


GAME_ID = 591478
ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")

FOCUS = {
    "206_loss": {
        "players": (6, 12),
        "turns": range(64, 69),
        "ship_ids": {206, 1167},
        "planet_ids": {3, 119, 452},
        "center": (2334, 2329),
    },
    "522_control": {
        "players": (6, 12),
        "turns": range(77, 82),
        "ship_ids": {522, 1082},
        "planet_ids": {119, 384, 452},
        "center": (2334, 2329),
    },
}

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
)

SETTING_KEYS = (
    "campaignmode",
    "shipscanrange",
    "planetscanrange",
    "horwaspscanrobotmodifier",
    "sensorsweepcombatpodscanrange",
    "sensorsweepnoncombatpodscanrange",
    "cloakandintercept",
    "cloakfail",
    "racehullsonlycloakandintercept",
    "sscruiserinterceptinterference",
    "nowarpwells",
    "sphere",
    "mapshape",
    "mapwidth",
    "mapheight",
)


def decode_member(raw: bytes) -> dict:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return json.loads(payload.decode("utf-8-sig"))


def compact(raw: dict, fields) -> dict:
    return {key: raw.get(key) for key in fields if key in raw}


def norm_text(value, limit: int = 1600):
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[:limit] + "...<truncated>"
    return text


def vcr_side(raw):
    if not isinstance(raw, dict):
        return None
    fields = (
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
    )
    return compact(raw, fields)


archive_data = ARCHIVE_PATH.read_bytes()
members = {(m.player, m.turn): m for m in turn_members(archive_data)}

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


# ---------------------------------------------------------------------------
# Global settings / active Fury capabilities from the authoritative owner turn.
# ---------------------------------------------------------------------------
print("===== SETTINGS / FURY CAPABILITIES =====")

sample = payload(12, 66)
if sample is not None:
    settings = sample.get("settings", {})
    print("settings:")
    for key in SETTING_KEYS:
        print(f"  {key:36s} {settings.get(key)!r}")

    player = sample.get("player", {})
    advantage_map = {
        item.get("id"): item.get("name")
        for item in sample.get("advantages", [])
        if isinstance(item, dict)
    }
    active = player.get("activeadvantages") or []
    print("player12 activeadvantages:")
    for value in active:
        if isinstance(value, dict):
            aid = value.get("id")
        else:
            aid = value
        print(" ", aid, advantage_map.get(aid))

    for hull_id in (1033, 35, 213):
        hull = next(
            (
                h
                for h in sample.get("hulls", [])
                if isinstance(h, dict) and h.get("id") == hull_id
            ),
            None,
        )
        print(f"hull {hull_id}:", None if hull is None else compact(
            hull,
            (
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
            ),
        ))


for label, cfg in FOCUS.items():
    print()
    print("#" * 110)
    print(label)
    print("#" * 110)

    focus_ids = set(cfg["ship_ids"]) | set(cfg["planet_ids"])

    # -----------------------------------------------------------------------
    # Owner-order timeline with all transfer fields.
    # -----------------------------------------------------------------------
    owner_ship = 206 if label == "206_loss" else 522
    owner_player = 12

    print()
    print("===== OWNER SHIP ORDER / TRANSFER TIMELINE =====")
    for turn in cfg["turns"]:
        data = payload(owner_player, turn)
        if data is None:
            continue
        ship = next(
            (
                s
                for s in data.get("ships", [])
                if isinstance(s, dict) and s.get("id") == owner_ship
            ),
            None,
        )
        print(f"turn={turn}:", None if ship is None else compact(ship, SHIP_FIELDS))

    # -----------------------------------------------------------------------
    # All owner-12 ships physically on planet 452 and all ships ordering a
    # transfer to 452. This is the direct ground-combat / foreign-cargo test.
    # -----------------------------------------------------------------------
    print()
    print("===== OWNER 12 SHIPS AT / TRANSFERRING TO PLANET 452 =====")
    for turn in cfg["turns"]:
        data = payload(12, turn)
        if data is None:
            continue

        matches = []
        for ship in data.get("ships", []):
            if not isinstance(ship, dict) or ship.get("ownerid") != 12:
                continue
            at_452 = (ship.get("x"), ship.get("y")) == (2334, 2329)
            transfer_452 = ship.get("transfertargetid") == 452
            if at_452 or transfer_452:
                matches.append((at_452, transfer_452, compact(ship, SHIP_FIELDS)))

        print(f"turn={turn}: count={len(matches)}")
        for at_452, transfer_452, row in matches:
            print("  ", {"at_452": at_452, "transfer_452": transfer_452, **row})

    # -----------------------------------------------------------------------
    # Exact planet state from both relevant perspectives.
    # -----------------------------------------------------------------------
    print()
    print("===== PLANET 452 RAW STATE =====")
    for turn in cfg["turns"]:
        for player in cfg["players"]:
            data = payload(player, turn)
            if data is None:
                continue
            planet = next(
                (
                    p
                    for p in data.get("planets", [])
                    if isinstance(p, dict) and p.get("id") == 452
                ),
                None,
            )
            print(
                f"turn={turn} player={player}:",
                None if planet is None else compact(planet, PLANET_FIELDS),
            )

    # -----------------------------------------------------------------------
    # Focus system-report messages. Restrict to mechanical target IDs and the
    # exact turn window; do not dump arbitrary user messages.
    # -----------------------------------------------------------------------
    print()
    print("===== FOCUS MESSAGE TEXT =====")
    for turn in cfg["turns"]:
        for player in cfg["players"]:
            data = payload(player, turn)
            if data is None:
                continue

            rows = []
            for msg in data.get("messages", []):
                if not isinstance(msg, dict):
                    continue
                if msg.get("turn") != turn:
                    continue
                if msg.get("target") not in focus_ids:
                    continue
                rows.append(msg)

            if not rows:
                continue

            print()
            print(f"TURN {turn} PLAYER {player}")
            for msg in rows:
                print(
                    {
                        "id": msg.get("id"),
                        "ownerid": msg.get("ownerid"),
                        "target": msg.get("target"),
                        "turn": msg.get("turn"),
                        "x": msg.get("x"),
                        "y": msg.get("y"),
                        "messagetype": msg.get("messagetype"),
                        "headline": norm_text(msg.get("headline"), 500),
                        "body": norm_text(msg.get("body"), 1600),
                    }
                )

    # -----------------------------------------------------------------------
    # Conventional combat/VCR at planet 452 or involving focus object IDs.
    # -----------------------------------------------------------------------
    print()
    print("===== FOCUS VCR DETAILS =====")
    for turn in cfg["turns"]:
        for player in cfg["players"]:
            data = payload(player, turn)
            if data is None:
                continue

            rows = []
            for vcr in data.get("vcrs", []):
                if not isinstance(vcr, dict):
                    continue

                left = vcr.get("left") if isinstance(vcr.get("left"), dict) else {}
                right = vcr.get("right") if isinstance(vcr.get("right"), dict) else {}

                nested_ids = {
                    left.get("id"),
                    left.get("objectid"),
                    right.get("id"),
                    right.get("objectid"),
                }

                at_452 = (vcr.get("x"), vcr.get("y")) == (2334, 2329)
                touches_focus = bool(nested_ids & focus_ids)

                if at_452 or touches_focus:
                    rows.append(vcr)

            if not rows:
                continue

            print()
            print(f"TURN {turn} PLAYER {player}")
            for vcr in rows:
                print(
                    {
                        "id": vcr.get("id"),
                        "turn": vcr.get("turn"),
                        "x": vcr.get("x"),
                        "y": vcr.get("y"),
                        "battletype": vcr.get("battletype"),
                        "seed": vcr.get("seed"),
                        "leftownerid": vcr.get("leftownerid"),
                        "rightownerid": vcr.get("rightownerid"),
                        "left": vcr_side(vcr.get("left")),
                        "right": vcr_side(vcr.get("right")),
                    }
                )

    # -----------------------------------------------------------------------
    # Starbase 452 state, if one exists.
    # -----------------------------------------------------------------------
    print()
    print("===== STARBASE AT PLANET 452 =====")
    for turn in cfg["turns"]:
        for player in cfg["players"]:
            data = payload(player, turn)
            if data is None:
                continue
            bases = [
                b
                for b in data.get("starbases", [])
                if isinstance(b, dict) and b.get("planetid") == 452
            ]
            if bases:
                print(f"turn={turn} player={player}:")
                for base in bases:
                    print("  ", base)
