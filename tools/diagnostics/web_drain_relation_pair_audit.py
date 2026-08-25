from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.normalizer import _decode_member_json


RAW_DIR = Path("validation/corpus/cache/loadall")

# Runtime-verified raw-sufficient -> Crystal-web-insufficient candidates.
# (game_id, archive_turn, target_slot, crystal_web_owner_slot, exact_endpoint)
CANDIDATES = (
    (360690, 44, 6, 7, True),
    (360690, 122, 6, 7, False),
    (360690, 172, 6, 7, False),
    (511506, 47, 8, 7, False),
)

JAN_2021 = datetime(2021, 1, 1)
DEC_2023 = datetime(2023, 12, 9)

# Planets.nu client-facing numeric diplomacy levels used by the historical API.
# Only the >=2 Safe Passage threshold is material to the pre-2021 candidates.
RELATION_LABELS = {
    -1: "blocked",
    0: "none",
    1: "ambassador",
    2: "safe_passage",
    3: "share_intel",
    4: "full_alliance",
}


def _parse_nu_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.startswith("1/1/0001"):
        return None
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _exact_relation(
    relations: Any,
    *,
    target_slot: int,
    web_slot: int,
) -> Mapping[str, Any] | None:
    if not isinstance(relations, list):
        return None
    matches = []
    for raw in relations:
        if not isinstance(raw, Mapping):
            continue
        player_id = _intish(raw.get("playerid"))
        player_to_id = _intish(raw.get("playertoid"))
        if player_id == target_slot and player_to_id == web_slot:
            matches.append(raw)
    if len(matches) != 1:
        return None
    return matches[0]


def _player_team(players: Any, slot: int) -> int | None:
    if not isinstance(players, list):
        return None
    for raw in players:
        if not isinstance(raw, Mapping):
            continue
        if _intish(raw.get("id")) != slot:
            continue
        team_id = _intish(raw.get("teamid"))
        return team_id if team_id is not None and team_id > 0 else None
    return None


def _safe_relation_excerpt(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    result: dict[str, Any] = {}
    for key in ("id", "playerid", "playertoid", "relationto", "relationfrom", "conflictlevel"):
        if key in raw:
            result[key] = raw.get(key)
    relation_to = _intish(raw.get("relationto"))
    relation_from = _intish(raw.get("relationfrom"))
    result["relationto_label"] = RELATION_LABELS.get(relation_to, "unknown")
    result["relationfrom_label"] = RELATION_LABELS.get(relation_from, "unknown")
    return result


def _era_decision(
    *,
    date_created: datetime | None,
    is_custom: bool | None,
    relation_to: int | None,
    relation_from: int | None,
    same_nonzero_team: bool,
) -> tuple[str, bool | None, str]:
    if is_custom is not False:
        return "custom_or_unknown", None, "custom game/settings require explicit Web diplomacy settings"
    if date_created is None:
        return "unknown_date", None, "game creation date is unavailable"

    if date_created < JAN_2021:
        if relation_from is None:
            return "pre_2021_classic", None, "Crystal->target relationfrom is unavailable"
        immune = relation_from >= 2
        return (
            "pre_2021_classic",
            immune,
            "classic Standard: Crystal owner granting Safe Passage or higher prevents Web Drain",
        )

    if date_created < DEC_2023:
        return (
            "2021_to_2023_standard",
            False,
            "Standard games created in this era ignore Safe Passage/Full Alliance for Web fields",
        )

    if same_nonzero_team:
        return (
            "post_2023_standard",
            True,
            "same non-zero team is a direct Full Alliance signal",
        )
    if relation_to is None or relation_from is None:
        return "post_2023_standard", None, "Full Alliance relation state is unavailable"
    immune = relation_to >= 4 and relation_from >= 4
    return (
        "post_2023_standard",
        immune,
        "Standard games created after 2023-12-09 honor mutual Full Alliance",
    )


def main() -> int:
    print("===== WEB-DRAIN EXACT RELATION-PAIR / ERA AUDIT =====")
    print("candidate_count_expected=", len(CANDIDATES))

    found = 0
    exact_case_drain_allowed: bool | None = None

    for game_id, archive_turn, target_slot, web_slot, exact_endpoint in CANDIDATES:
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            raise SystemExit(f"missing archive: {archive_path}")
        archive_data = archive_path.read_bytes()
        members = [
            member
            for member in turn_members(archive_data)
            if member.turn == archive_turn and member.player == target_slot
        ]
        print(
            f"\n===== game={game_id} turn={archive_turn} target={target_slot} "
            f"crystal={web_slot} exact_endpoint={exact_endpoint} ====="
        )
        print("selected_members=", [member.name for member in members])
        if len(members) != 1:
            print("decision= unresolved_member_selection")
            continue

        member = members[0]
        raw_by_name = read_archive_members(archive_data, [member.name])
        parsed, _ = _decode_member_json(raw_by_name[member.name], member)

        game = parsed.get("game")
        settings = parsed.get("settings")
        players = parsed.get("players")
        relation = _exact_relation(
            parsed.get("relations"),
            target_slot=target_slot,
            web_slot=web_slot,
        )

        date_created_raw = game.get("datecreated") if isinstance(game, Mapping) else None
        date_created = _parse_nu_datetime(date_created_raw)
        is_custom_raw = game.get("iscustom") if isinstance(game, Mapping) else None
        is_custom = is_custom_raw if isinstance(is_custom_raw, bool) else None

        target_team = _player_team(players, target_slot)
        web_team = _player_team(players, web_slot)
        same_nonzero_team = (
            target_team is not None
            and web_team is not None
            and target_team == web_team
        )

        relation_to = _intish(relation.get("relationto")) if relation is not None else None
        relation_from = _intish(relation.get("relationfrom")) if relation is not None else None

        era, immune, reason = _era_decision(
            date_created=date_created,
            is_custom=is_custom,
            relation_to=relation_to,
            relation_from=relation_from,
            same_nonzero_team=same_nonzero_team,
        )
        drain_allowed = None if immune is None else not immune

        safe_settings: dict[str, Any] = {}
        if isinstance(settings, Mapping):
            for key in (
                "webdiplomacylevel",
                "webdraindiplomacylevel",
                "crystalwebimmunity",
                "nowebfriendlycodes",
                "nowebsinotherids",
                "maxsafepassage",
            ):
                if key in settings:
                    safe_settings[key] = settings.get(key)

        print("datecreated=", date_created_raw)
        print("iscustom=", is_custom)
        print("target_teamid=", target_team)
        print("crystal_teamid=", web_team)
        print("same_nonzero_team=", same_nonzero_team)
        print("web_settings=", safe_settings)
        print("relation_pair=", _safe_relation_excerpt(relation))
        print("relation_direction_note= relationto is target->Crystal; relationfrom is Crystal->target")
        print("era=", era)
        print("web_diplomacy_immune=", immune)
        print("web_drain_allowed=", drain_allowed)
        print("decision_reason=", reason)

        if relation is not None:
            found += 1
        if exact_endpoint:
            exact_case_drain_allowed = drain_allowed

    print("\n===== SUMMARY =====")
    print("candidate_relation_pairs_found=", found)
    print("exact_case_web_drain_allowed=", exact_case_drain_allowed)
    if exact_case_drain_allowed is True:
        print("exact_case_diplomacy_guard= PASSED")
    elif exact_case_drain_allowed is False:
        print("exact_case_diplomacy_guard= REJECTED_BY_IMMUNITY")
    else:
        print("exact_case_diplomacy_guard= UNRESOLVED")

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This audit resolves only the historical Web diplomacy guard for the four already-identified candidates. "
        "It does not promote Web Drain into production: one exact game/hull remains evidence-only unless independent support appears."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
