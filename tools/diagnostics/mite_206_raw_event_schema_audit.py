from __future__ import annotations

import gzip
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from planets_lab.corpus.archive import read_archive_members, turn_members


GAME_ID = 591478
ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")

# Case under investigation and matched retained control.
FOCUS = {
    "206_loss": {
        "turns": range(64, 69),
        "players": {6, 12},
        "refs": {3, 119, 206, 452, 1167},
        "ships": {206, 1167},
        "planets": {3, 119, 452},
    },
    "522_control": {
        "turns": range(77, 82),
        "players": {6, 12},
        "refs": {119, 384, 452, 522, 1082},
        "ships": {522, 1082},
        "planets": {119, 384, 452},
    },
}

# We deliberately do not print free-form message/chat text. This diagnostic is
# intended to reveal the raw mechanical event schema without leaking corpus text.
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
    "vcr",
    "battle",
    "combat",
    "event",
    "report",
    "message",
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

ENTITY_SAFE_FIELDS = (
    "id",
    "planetid",
    "ownerid",
    "hullid",
    "x",
    "y",
    "warp",
    "targetx",
    "targety",
    "mission",
    "mission1target",
    "mission2target",
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
    "nativeclans",
    "megacredits",
    "ammo",
    "podcargo",
    "transfertargetid",
    "transfertargettype",
    "infoturn",
    "readystatus",
    "defense",
    "defenseposts",
    "factories",
    "mines",
    "starbaseid",
    "isbase",
)


def decode_member(raw: bytes, name: str) -> dict[str, Any]:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)

    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{name}: expected top-level object")
    return parsed


def is_text_key(key: Any) -> bool:
    text = str(key).lower()
    return any(token in text for token in TEXT_FIELD_TOKENS)


def looks_like_reference_key(key: Any) -> bool:
    text = str(key).lower()
    return any(token in text for token in REFERENCE_KEY_TOKENS)


def looks_like_event_key(key: Any) -> bool:
    text = str(key).lower()
    return any(token in text for token in EVENT_KEY_TOKENS)


def safe_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float))


def sanitize_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    suppressed_text_fields: list[str] = []

    for key, value in raw.items():
        key_text = str(key)

        if is_text_key(key):
            if value not in (None, "", [], {}):
                suppressed_text_fields.append(key_text)
            continue

        if safe_scalar(value):
            result[key_text] = value
            continue

        if isinstance(value, str) and key_text.lower() in SAFE_STRING_KEYS:
            result[key_text] = value
            continue

        if isinstance(value, list):
            result[f"{key_text}__len"] = len(value)
        elif isinstance(value, Mapping):
            result[f"{key_text}__keys"] = sorted(str(k) for k in value.keys())

    if suppressed_text_fields:
        result["suppressed_text_fields"] = sorted(suppressed_text_fields)

    return result


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


def entity_excerpt(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field: raw.get(field)
        for field in ENTITY_SAFE_FIELDS
        if field in raw
    }


def print_top_level_schema(parsed: Mapping[str, Any]) -> None:
    print("  top-level schema:")

    for key in sorted(parsed):
        value = parsed[key]

        if isinstance(value, list):
            info: dict[str, Any] = {
                "type": "list",
                "len": len(value),
            }
            first_mapping = next((item for item in value if isinstance(item, Mapping)), None)
            if first_mapping is not None:
                info["item_keys"] = sorted(str(k) for k in first_mapping.keys())
            print(f"    {key}: {info}")

        elif isinstance(value, Mapping):
            print(
                f"    {key}: "
                f"{{'type': 'dict', 'keys': {sorted(str(k) for k in value.keys())}}}"
            )
        else:
            print(f"    {key}: {type(value).__name__}")


def print_focus_entities(parsed: Mapping[str, Any], focus: Mapping[str, Any]) -> None:
    print("  focus entities:")

    for raw in parsed.get("ships", []) or []:
        if not isinstance(raw, Mapping):
            continue
        ship_id = raw.get("id")
        if ship_id in focus["ships"]:
            print("    ship:", entity_excerpt(raw))

    for raw in parsed.get("planets", []) or []:
        if not isinstance(raw, Mapping):
            continue
        planet_id = raw.get("id")
        if planet_id in focus["planets"]:
            print("    planet:", entity_excerpt(raw))

    for raw in parsed.get("starbases", []) or []:
        if not isinstance(raw, Mapping):
            continue
        planet_id = raw.get("planetid", raw.get("id"))
        if planet_id in focus["planets"]:
            print("    starbase:", entity_excerpt(raw))


def print_candidate_event_records(parsed: Mapping[str, Any], refs: set[int]) -> None:
    print("  candidate event/report records referencing focus IDs:")
    found = 0

    for key, value in parsed.items():
        if not looks_like_event_key(key):
            continue

        if isinstance(value, list):
            for index, item in enumerate(value):
                if not isinstance(item, Mapping):
                    continue
                if not object_references(item, refs):
                    continue

                print(
                    f"    {key}[{index}]",
                    sanitize_mapping(item),
                )
                found += 1

        elif isinstance(value, Mapping):
            if object_references(value, refs):
                print(
                    f"    {key}",
                    sanitize_mapping(value),
                )
                found += 1

    if not found:
        print("    NONE")


def print_all_candidate_list_schemas(parsed: Mapping[str, Any]) -> None:
    print("  event-like list schemas:")
    found = 0

    for key, value in parsed.items():
        if not looks_like_event_key(key):
            continue
        if not isinstance(value, list):
            continue

        mapping_items = [item for item in value if isinstance(item, Mapping)]
        keys = sorted(
            {
                str(item_key)
                for item in mapping_items[:20]
                for item_key in item.keys()
            }
        )

        print(
            f"    {key}: len={len(value)} item_keys={keys}"
        )
        found += 1

    if not found:
        print("    NONE")


def main() -> None:
    archive_data = ARCHIVE_PATH.read_bytes()
    members = turn_members(archive_data)

    selected = []

    for member in members:
        for focus in FOCUS.values():
            if member.player in focus["players"] and member.turn in focus["turns"]:
                selected.append(member)
                break

    raw_by_name = read_archive_members(
        archive_data,
        [member.name for member in selected],
    )

    parsed_by_key: dict[tuple[int, int], dict[str, Any]] = {}

    for member in selected:
        parsed_by_key[(member.player, member.turn)] = decode_member(
            raw_by_name[member.name],
            member.name,
        )

    print("selected_members:", len(selected))

    for label, focus in FOCUS.items():
        print()
        print("#" * 110)
        print(label)
        print("#" * 110)

        for turn in focus["turns"]:
            for player in sorted(focus["players"]):
                parsed = parsed_by_key.get((player, turn))
                if parsed is None:
                    print()
                    print(f"TURN {turn} PLAYER {player}: MISSING")
                    continue

                print()
                print("=" * 100)
                print(f"TURN {turn} PLAYER {player}")
                print("=" * 100)

                print_all_candidate_list_schemas(parsed)
                print_focus_entities(parsed, focus)
                print_candidate_event_records(parsed, set(focus["refs"]))

        # Print one full top-level schema per case, from the central Horwasp perspective.
        center_turn = sorted(focus["turns"])[len(list(focus["turns"])) // 2]
        schema_payload = parsed_by_key.get((6, center_turn))
        if schema_payload is not None:
            print()
            print("=" * 100)
            print(f"TOP-LEVEL SCHEMA SAMPLE: {label} turn={center_turn} player=6")
            print("=" * 100)
            print_top_level_schema(schema_payload)


if __name__ == "__main__":
    main()
