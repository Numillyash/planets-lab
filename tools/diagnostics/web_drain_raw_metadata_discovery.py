from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.normalizer import _decode_member_json


RAW_DIR = Path("validation/corpus/cache/loadall")

# Runtime-verified raw-sufficient -> Crystal-web-insufficient candidates.
CANDIDATES = (
    (360690, 44, 6, 7),
    (360690, 122, 6, 7),
    (360690, 172, 6, 7),
    (511506, 47, 8, 7),
)

MATCH_TOKENS = (
    "creat",
    "start",
    "date",
    "year",
    "host",
    "team",
    "relation",
    "alliance",
    "allied",
    "ally",
    "diplom",
    "passage",
)

SENSITIVE_TOKENS = (
    "email",
    "username",
    "user_name",
    "createdby",
    "savekey",
    "password",
    "apikey",
    "api_key",
    "token",
    "secret",
    "name",
    "description",
    "message",
    "notes",
)


def _interesting_key(key: str) -> bool:
    text = key.lower()
    return any(token in text for token in MATCH_TOKENS)


def _sensitive_key(key: str) -> bool:
    text = key.lower()
    return any(token in text for token in SENSITIVE_TOKENS)


def _safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if len(text) <= 80:
            return text
        return text[:77] + "..."
    return f"<{type(value).__name__}>"


def _walk_interesting(
    value: Any,
    *,
    path: str,
    depth: int = 0,
    max_depth: int = 6,
) -> list[tuple[str, Any]]:
    if depth > max_depth:
        return []
    result: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            child_path = f"{path}.{key}" if path else key
            if _sensitive_key(key):
                continue
            if _interesting_key(key):
                if isinstance(child, Mapping):
                    result.append((child_path, {"type": "dict", "keys": sorted(map(str, child.keys()))[:80]}))
                elif isinstance(child, list):
                    result.append((child_path, {"type": "list", "len": len(child)}))
                else:
                    result.append((child_path, _safe_scalar(child)))
            result.extend(
                _walk_interesting(
                    child,
                    path=child_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value[:64]):
            result.extend(
                _walk_interesting(
                    child,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            )
    return result


def _player_excerpt(raw: Mapping[str, Any], slots: set[int]) -> dict[str, Any] | None:
    player_id = raw.get("id")
    if not isinstance(player_id, int) or isinstance(player_id, bool) or player_id not in slots:
        return None
    result: dict[str, Any] = {"id": player_id}
    for key, value in raw.items():
        text = str(key)
        if _sensitive_key(text):
            continue
        if text.lower() in {"raceid", "teamid", "relationto", "relationfrom", "conflictlevel"} or _interesting_key(text):
            if isinstance(value, (Mapping, list)):
                if isinstance(value, Mapping):
                    result[text] = {"type": "dict", "keys": sorted(map(str, value.keys()))[:80]}
                else:
                    result[text] = {"type": "list", "len": len(value)}
            else:
                result[text] = _safe_scalar(value)
    return result


def _top_shape(parsed: Mapping[str, Any]) -> dict[str, Any]:
    shape: dict[str, Any] = {}
    for key, value in parsed.items():
        if isinstance(value, Mapping):
            shape[str(key)] = {"type": "dict", "keys": sorted(map(str, value.keys()))[:120]}
        elif isinstance(value, list):
            item_keys: list[str] = []
            for item in value[:8]:
                if isinstance(item, Mapping):
                    item_keys = sorted(map(str, item.keys()))[:120]
                    break
            shape[str(key)] = {"type": "list", "len": len(value), "item_keys": item_keys}
        else:
            shape[str(key)] = {"type": type(value).__name__}
    return shape


def _members_for_candidate(
    members: Sequence[Any],
    *,
    archive_turn: int,
    preferred_player: int,
) -> list[Any]:
    exact = [m for m in members if m.turn == archive_turn and m.player == preferred_player]
    if exact:
        return exact
    return [m for m in members if m.turn == archive_turn]


def main() -> int:
    print("===== RAW WEB-DRAIN METADATA / DIPLOMACY DISCOVERY =====")
    print(
        "Privacy guard: values for names, creator identity, email, username, savekey, password, API keys, secrets, messages and notes are never printed."
    )

    candidates_by_game: dict[int, list[tuple[int, int, int]]] = {}
    for game_id, archive_turn, target_slot, web_slot in CANDIDATES:
        candidates_by_game.setdefault(game_id, []).append((archive_turn, target_slot, web_slot))

    for game_id in sorted(candidates_by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            raise SystemExit(f"missing archive: {archive_path}")
        archive_data = archive_path.read_bytes()
        members = turn_members(archive_data)
        print(f"\n===== GAME {game_id} =====")
        print("archive_turn_range=", (min(m.turn for m in members), max(m.turn for m in members)))
        print("archive_player_slots=", sorted({m.player for m in members}))

        for archive_turn, target_slot, web_slot in candidates_by_game[game_id]:
            selected = _members_for_candidate(
                members,
                archive_turn=archive_turn,
                preferred_player=target_slot,
            )
            print(f"\n--- candidate turn={archive_turn} target_slot={target_slot} web_slot={web_slot} ---")
            print("selected_members=", [m.name for m in selected])
            if not selected:
                continue
            raw_by_name = read_archive_members(archive_data, [m.name for m in selected])
            for member in selected:
                parsed, _ = _decode_member_json(raw_by_name[member.name], member)
                print(f"\nmember= {member.name}")
                print("top_level_keys=", sorted(parsed.keys()))
                print("top_level_shape=", _top_shape(parsed))

                game = parsed.get("game")
                if isinstance(game, Mapping):
                    safe_game: dict[str, Any] = {}
                    for key, value in game.items():
                        text = str(key)
                        if _sensitive_key(text):
                            continue
                        if text.lower() in {"id", "turn", "iscustom", "yearstarted", "statusname", "scenarioid"} or _interesting_key(text):
                            safe_game[text] = _safe_scalar(value)
                    print("safe_game_metadata=", safe_game)

                settings = parsed.get("settings")
                if isinstance(settings, Mapping):
                    safe_settings: dict[str, Any] = {}
                    for key, value in settings.items():
                        text = str(key)
                        if _sensitive_key(text):
                            continue
                        if _interesting_key(text):
                            safe_settings[text] = _safe_scalar(value) if not isinstance(value, (Mapping, list)) else {
                                "type": "dict" if isinstance(value, Mapping) else "list",
                                "len": len(value),
                            }
                    print("interesting_settings=", safe_settings)

                raw_players = parsed.get("players")
                if isinstance(raw_players, list):
                    excerpts = []
                    for raw_player in raw_players:
                        if isinstance(raw_player, Mapping):
                            excerpt = _player_excerpt(raw_player, {target_slot, web_slot})
                            if excerpt is not None:
                                excerpts.append(excerpt)
                    print("target_web_player_excerpts=", excerpts)

                interesting = _walk_interesting(parsed, path="")
                seen: set[str] = set()
                unique = []
                for path, value in interesting:
                    if path in seen:
                        continue
                    seen.add(path)
                    unique.append((path, value))
                print("interesting_paths_count=", len(unique))
                for path, value in unique[:240]:
                    print(path, "=", value)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This is schema discovery only. Missing paths mean the raw loadall archive does not expose that field in the selected perspective/turn; "
        "they do not prove neutral diplomacy. Use discovered raw paths to build a narrow deterministic extractor before applying any game-era immunity rule."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
