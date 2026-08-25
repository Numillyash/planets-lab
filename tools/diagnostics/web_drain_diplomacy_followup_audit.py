from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_damage_context import _race_map
from planets_lab.corpus.movement_mine_context import _point_in_field, build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
CRYSTAL_RACE_ID = 7

# Runtime-verified raw-sufficient -> Crystal-web-insufficient candidates from
# web_drain_crystal_owner_followup_audit.py. Keep this follow-up deliberately
# narrow: it inspects diplomacy / game-era provenance only and does not alter
# the movement classifier.
CANDIDATES = (
    (360690, 44, 489),
    (360690, 122, 237),
    (360690, 172, 51),
    (511506, 47, 375),
)


def _candidate_rows() -> dict[tuple[int, int, int], dict[str, Any]]:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        rows: dict[tuple[int, int, int], dict[str, Any]] = {}
        for game_id, before_turn, ship_id in CANDIDATES:
            result = con.execute(
                f"""
                SELECT
                    game_id,
                    before_archive_turn,
                    after_archive_turn,
                    ship_id,
                    hull_id,
                    x_before,
                    y_before,
                    x_after,
                    y_after
                FROM {RESIDUAL_VIEW}
                WHERE game_id = ?
                  AND before_archive_turn = ?
                  AND ship_id = ?
                """,
                [game_id, before_turn, ship_id],
            ).fetchone()
            if result is None:
                continue
            names = (
                "game_id",
                "before_archive_turn",
                "after_archive_turn",
                "ship_id",
                "hull_id",
                "x_before",
                "y_before",
                "x_after",
                "y_after",
            )
            rows[(game_id, before_turn, ship_id)] = dict(zip(names, result))
        return rows
    finally:
        con.close()


def _mapping_list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    raw = payload.get(key, [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _collect_payload_records(
    snapshots: tuple[Any, ...],
    *,
    archive_turn: int,
    key: str,
) -> list[Mapping[str, Any]]:
    seen: set[tuple[tuple[str, str], ...]] = set()
    result: list[Mapping[str, Any]] = []
    for snapshot in snapshots:
        if snapshot.archive_turn != archive_turn:
            continue
        payload = snapshot.mechanics_payload
        if not isinstance(payload, Mapping):
            continue
        for raw in _mapping_list(payload, key):
            identity = tuple(sorted((str(k), repr(v)) for k, v in raw.items()))
            if identity in seen:
                continue
            seen.add(identity)
            result.append(raw)
    return result


def _collect_top_level_mappings(
    snapshots: tuple[Any, ...],
    *,
    archive_turn: int,
    key: str,
) -> list[Mapping[str, Any]]:
    seen: set[tuple[tuple[str, str], ...]] = set()
    result: list[Mapping[str, Any]] = []
    for snapshot in snapshots:
        if snapshot.archive_turn != archive_turn:
            continue
        payload = snapshot.mechanics_payload
        if not isinstance(payload, Mapping):
            continue
        raw = payload.get(key)
        if not isinstance(raw, Mapping):
            continue
        identity = tuple(sorted((str(k), repr(v)) for k, v in raw.items()))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(raw)
    return result


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _player_map(players: list[Mapping[str, Any]]) -> dict[int, dict[str, int | None]]:
    result: dict[int, dict[str, int | None]] = {}
    for raw in players:
        player_id = _intish(raw.get("id"))
        if player_id is None or player_id <= 0:
            continue
        result[player_id] = {
            "raceid": _intish(raw.get("raceid")),
            "teamid": _intish(raw.get("teamid")),
        }
    return result


def _relation_projection(raw: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "playerid",
        "playertoid",
        "relationto",
        "relationfrom",
        "conflictlevel",
        "color",
    )
    return {key: raw.get(key) for key in keys if key in raw}


def _game_metadata(
    snapshots: tuple[Any, ...],
    *,
    archive_turn: int,
) -> dict[str, Any]:
    selected = (
        "hoststart",
        "hostcompleted",
        "created",
        "datecreated",
        "yearfrom",
        "gametype",
        "type",
        "isprivate",
        "levelid",
        "teamsize",
        "maxallies",
        "maxshareintel",
        "maxsafepassage",
        "name",
    )
    result: dict[str, Any] = {}
    for key in ("settings", "game"):
        for raw in _collect_top_level_mappings(
            snapshots,
            archive_turn=archive_turn,
            key=key,
        ):
            for field in selected:
                if field in raw and field not in result:
                    result[field] = raw.get(field)
    return result


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing compiled corpus database: {DATABASE}")

    rows = _candidate_rows()
    print("===== WEB-DRAIN DIPLOMACY / GAME-ERA FOLLOW-UP =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("candidate_count_expected=", len(CANDIDATES))
    print("candidate_count_found=", len(rows))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows.values():
        by_game[int(row["game_id"])].append(row)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        prepared_path = PREPARED_DIR / f"game-{game_id}.pickle"
        archive_data = archive_path.read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_path,
        )
        snapshots = tuple(prepared.snapshots)
        races = _race_map(snapshots)
        ship_groups = group_perspective_records(snapshots, "ship")
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=snapshots,
        )
        print(f"\n===== GAME {game_id} prepared_cache_hit={hit} =====")

        for row in sorted(
            by_game[game_id],
            key=lambda item: (int(item["before_archive_turn"]), int(item["ship_id"])),
        ):
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            if owner_id is None or owner is None:
                print({
                    "turn": before_turn,
                    "ship": ship_id,
                    "error": "target owner unavailable",
                })
                continue

            origin = (int(row["x_before"]), int(row["y_before"]))
            crystal_web_owners = sorted({
                int(field.owner_id)
                for field in mine_context.fields(after_turn)
                if field.is_web
                and field.owner_id is not None
                and field.owner_id > 0
                and field.owner_id != owner_id
                and races.get(int(field.owner_id)) == CRYSTAL_RACE_ID
                and _point_in_field(origin, field, mine_context.topology)
            })

            players = _collect_payload_records(
                snapshots,
                archive_turn=before_turn,
                key="players",
            )
            player_map = _player_map(players)
            relations = _collect_payload_records(
                snapshots,
                archive_turn=before_turn,
                key="relations",
            )

            relevant_relations: list[dict[str, Any]] = []
            web_owner_set = set(crystal_web_owners)
            for raw in relations:
                player_id = _intish(raw.get("playerid"))
                player_to_id = _intish(raw.get("playertoid"))
                pair = {player_id, player_to_id}
                if owner_id in pair and pair.intersection(web_owner_set):
                    relevant_relations.append(_relation_projection(raw))

            target_player = player_map.get(owner_id, {})
            web_player_info = {
                web_owner: player_map.get(web_owner, {})
                for web_owner in crystal_web_owners
            }
            target_team = target_player.get("teamid")
            same_nonzero_team = any(
                target_team is not None
                and target_team > 0
                and info.get("teamid") == target_team
                for info in web_player_info.values()
            )

            print({
                "turn": before_turn,
                "ship": ship_id,
                "hull": int(row["hull_id"]) if row["hull_id"] is not None else None,
                "target_owner_slot": owner_id,
                "target_race": races.get(owner_id),
                "crystal_web_owner_slots": crystal_web_owners,
                "target_player": target_player,
                "web_players": web_player_info,
                "same_nonzero_team": same_nonzero_team,
                "game_metadata": _game_metadata(snapshots, archive_turn=before_turn),
                "relation_records": relevant_relations,
                "relation_records_found": len(relevant_relations),
            })

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Do not infer numeric diplomacy levels here. The audit exposes raw relationto/"
        "relationfrom plus team/game-era metadata so the next step can apply the documented "
        "web-diplomacy rule for the actual game creation era. Same non-zero team is a direct "
        "Full Alliance signal; non-team relation codes must be interpreted only after the "
        "runtime payload is inspected."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
