from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import zipfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for _path in (REPO_ROOT / "src", DIAGNOSTICS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.corpus_db_compact import (
    _load_specs,
    reconstruct_compact_member,
)
from planets_lab.corpus.corpus_db_runtime import (
    CompactMemberRef,
    connect_current_compact_read_only,
    reconstruct_members,
)
from planets_lab.corpus.indexer import load_manifest_jsonl
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.normalizer import _decode_member_json, mechanics_projection
from planets_lab.corpus.public_finished_discover_cli import _manifest_bucket

import combat_host_capture_continuation_audit as capture_module
import combat_ship_chain_audit as chain_module
from combat_host_post_capture_pair_recomposition_audit import (
    _neutral_prize_raw,
    _nonmatching_symbolic_fc,
    _priority_from_raw,
    _side_from_priority_keys,
)


SCHEMA = "planets-lab.combat-public-capture-side-harvest.v1"
DEFAULT_MANIFEST = Path(
    "validation/corpus/manifests/public-validation-selected.jsonl"
)
DEFAULT_INDEX = Path("validation/corpus/index/public-validation-games.jsonl")
DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_OUTPUT = Path(
    "artifacts/public-capture-side/discovery-capture-side.json"
)
DEFAULT_PARTITION_SALT = "planets-lab-public-capture-side-v1"
DEFAULT_HOLDOUT_MODULUS = 4
APPEARANCE_CACHE_SCHEMA = "planets-lab.combat-public-capture-appearance-cache.v1"
DEFAULT_APPEARANCE_CACHE_DIR = Path(
    "validation/corpus/cache/public-capture-side-v1"
)

SETTING_KEYS = (
    "campaignmode",
    "sphere",
    "combatrng",
    "chainedintercept",
    "cloakandintercept",
    "galacticpower",
    "unlimitedfuel",
    "nominefields",
    "nowarpwells",
    "moscowinterceptinterference",
    "sscruiserinterceptinterference",
    "quantumtorpedos",
    "hrossfightertransfer",
)


def _game_id(record: Mapping[str, Any]) -> int:
    value = record.get("game_id")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("record has invalid game_id")
    return int(value)


def _load_indexed_game_ids(path: Path) -> set[int]:
    result: set[int] = set()
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        payload = json.loads(raw)
        if not isinstance(payload, Mapping):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        result.add(_game_id(payload))
    return result


def _partition_for_game(
    game_id: int,
    *,
    salt: str = DEFAULT_PARTITION_SALT,
    holdout_modulus: int = DEFAULT_HOLDOUT_MODULUS,
) -> str:
    if game_id <= 0:
        raise ValueError("game_id must be positive")
    if holdout_modulus < 2:
        raise ValueError("holdout_modulus must be >= 2")
    digest = hashlib.sha256(f"{salt}:{game_id}".encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big")
    return "heldout" if value % holdout_modulus == 0 else "discovery"


def _appearance_cache_descriptor(
    *,
    scan_ids: set[int],
    archive_dir: Path,
) -> dict[str, Any]:
    archives: list[dict[str, Any]] = []
    for game_id in sorted(scan_ids):
        path = archive_dir / f"game-{game_id}.zip"
        if not path.is_file():
            raise ValueError(f"missing archive for appearance cache: {path}")
        archives.append(
            {
                "game_id": game_id,
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema": APPEARANCE_CACHE_SCHEMA,
        "game_ids": sorted(scan_ids),
        "archives": archives,
    }


def _load_appearance_cache(
    *,
    path: Path,
    descriptor: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], Mapping[str, Any]] | None:
    if not path.is_file():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    if payload.get("descriptor") != descriptor:
        return None
    appearances = payload.get("appearances")
    chain_summary = payload.get("chain_summary")
    if (
        not isinstance(appearances, list)
        or not all(isinstance(row, Mapping) for row in appearances)
        or not isinstance(chain_summary, Mapping)
    ):
        return None
    return [dict(row) for row in appearances], dict(chain_summary)


def _write_appearance_cache(
    *,
    path: Path,
    descriptor: Mapping[str, Any],
    appearances: Sequence[Mapping[str, Any]],
    chain_summary: Mapping[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "descriptor": dict(descriptor),
        "appearances": [dict(row) for row in appearances],
        "chain_summary": dict(chain_summary),
    }
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(
            payload,
            handle,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def _collect_appearances_cached(
    *,
    args: argparse.Namespace,
    scan_ids: set[int],
) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    cache_path = args.appearance_cache_dir / f"{args.partition}-appearances.json.gz"
    descriptor = _appearance_cache_descriptor(
        scan_ids=scan_ids,
        archive_dir=args.archive_dir,
    )
    cached = _load_appearance_cache(
        path=cache_path,
        descriptor=descriptor,
    )
    if cached is not None:
        appearances, chain_summary = cached
        print(
            "progress: stage=collect_capture_appearances "
            f"games={len(scan_ids)} status=cache-hit "
            f"appearances={len(appearances)} cache={cache_path}",
            flush=True,
        )
        return appearances, chain_summary

    print(
        "progress: stage=collect_capture_appearances "
        f"games={len(scan_ids)} status=cache-miss cache={cache_path}",
        flush=True,
    )
    appearances, chain_summary = capture_module._collect_appearances(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            example_limit=args.example_limit,
            progress=True,
        ),
        selected_ids=scan_ids,
    )
    _write_appearance_cache(
        path=cache_path,
        descriptor=descriptor,
        appearances=appearances,
        chain_summary=chain_summary,
    )
    print(
        "progress: stage=collect_capture_appearances "
        f"games={len(scan_ids)} appearances={len(appearances)} "
        f"status=cache-written cache={cache_path}",
        flush=True,
    )
    return appearances, chain_summary



def _db_vcr_member_refs(
    connection: Any,
    *,
    scan_ids: set[int],
) -> list[CompactMemberRef]:
    if not scan_ids:
        return []
    ordered = sorted(scan_ids)
    placeholders = ",".join("?" for _ in ordered)
    rows = connection.execute(
        f"""
        SELECT DISTINCT
               sm.member_id,
               sm.game_id,
               sm.source_member_name,
               sm.perspective_player_id,
               sm.archive_turn,
               sm.embedded_turn,
               sm.decoded_payload_sha256,
               sm.member_ordinal
        FROM source_members sm
        JOIN typed_vcrs tv USING (member_id)
        WHERE sm.game_id IN ({placeholders})
        ORDER BY sm.game_id,
                 sm.archive_turn,
                 sm.perspective_player_id,
                 sm.member_ordinal
        """,
        ordered,
    ).fetchall()
    return [
        CompactMemberRef(
            member_id=int(row[0]),
            game_id=int(row[1]),
            source_member_name=str(row[2]),
            perspective_player_id=int(row[3]),
            archive_turn=int(row[4]),
            embedded_turn=int(row[5]),
            decoded_payload_sha256=str(row[6]),
        )
        for row in rows
    ]


def _collect_appearances_db(
    *,
    connection: Any,
    scan_ids: set[int],
    progress: bool,
) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    refs = _db_vcr_member_refs(connection, scan_ids=scan_ids)
    summary: Counter[str] = Counter()
    summary["source_members_with_vcrs"] = len(refs)

    unique_cases: dict[tuple[int, int, int], dict[str, Any]] = {}
    conflict_keys: set[tuple[int, int, int]] = set()

    current_game: int | None = None
    current_members = 0
    current_vcr_observations = 0

    for ref, payload in reconstruct_members(connection, refs):
        if progress and current_game != ref.game_id:
            if current_game is not None:
                print(
                    "progress: stage=collect_capture_appearances_db "
                    f"game_id={current_game} members={current_members} "
                    f"vcr_observations={current_vcr_observations} status=done",
                    flush=True,
                )
            current_game = ref.game_id
            current_members = 0
            current_vcr_observations = 0
            print(
                "progress: stage=collect_capture_appearances_db "
                f"game_id={current_game} status=start",
                flush=True,
            )

        current_members += 1
        game = payload.get("game")
        if not isinstance(game, Mapping):
            continue
        game_id = chain_module._int(game, "id")
        game_turn = chain_module._int(game, "turn")
        if game_id not in scan_ids or game_turn is None:
            continue

        beams = chain_module._objects(payload, "beams")
        torpedoes = chain_module._objects(payload, "torpedos")
        settings = payload.get("settings")
        settings = dict(settings) if isinstance(settings, Mapping) else {}

        for raw_vcr in chain_module._objects(payload, "vcrs"):
            vcr_id = chain_module._int(raw_vcr, "id")
            battle_turn = chain_module._int(raw_vcr, "turn") or game_turn
            if vcr_id is None:
                continue
            current_vcr_observations += 1
            summary["raw_vcr_observations"] += 1
            key = (int(game_id), int(battle_turn), int(vcr_id))
            payload_hash = chain_module._canonical_hash(raw_vcr)
            existing = unique_cases.get(key)
            if existing is None:
                unique_cases[key] = {
                    "payload": dict(raw_vcr),
                    "payload_hash": payload_hash,
                    "beams": beams,
                    "torpedoes": torpedoes,
                    "settings": settings,
                }
            elif existing["payload_hash"] != payload_hash:
                conflict_keys.add(key)

    if progress and current_game is not None:
        print(
            "progress: stage=collect_capture_appearances_db "
            f"game_id={current_game} members={current_members} "
            f"vcr_observations={current_vcr_observations} status=done",
            flush=True,
        )

    summary["unique_vcrs"] = len(unique_cases)
    summary["payload_conflicts"] = len(conflict_keys)

    appearances: list[dict[str, Any]] = []
    for key, case in sorted(unique_cases.items()):
        if key in conflict_keys:
            continue
        game_id, turn, vcr_id = key
        try:
            replay = chain_module.replay_nuhost_from_nu_catalog(
                case["payload"],
                beams=case["beams"],
                torpedoes=case["torpedoes"],
                settings=case["settings"],
            )
        except chain_module.ReplayUnsupported:
            summary["replay_unsupported"] += 1
            continue

        summary["replay_supported"] += 1
        position = chain_module._position(case["payload"])
        for side_name in ("left", "right"):
            raw_side = case["payload"].get(side_name)
            replay_side = replay.get(side_name)
            if (
                not isinstance(raw_side, Mapping)
                or not isinstance(replay_side, Mapping)
            ):
                continue
            appearance = chain_module._appearance(
                game_id=game_id,
                turn=turn,
                vcr_id=vcr_id,
                position=position,
                side_name=side_name,
                raw_side=raw_side,
                replay_side=replay_side,
            )
            if appearance is not None:
                appearances.append(appearance)
                summary["ship_appearances"] += 1

    return appearances, {
        "backend": "corpus-db",
        **dict(sorted(summary.items())),
    }


def _targeted_tminus1_ship_raw_db(
    connection: Any,
    *,
    specs: Mapping[str, Any],
    game_id: int,
    player_id: int,
    archive_turn: int,
    ship_id: int,
    projection_cache: dict[
        tuple[int, int, int],
        Mapping[str, Any] | None,
    ],
) -> Mapping[str, Any] | None:
    cache_key = (game_id, player_id, archive_turn)
    if cache_key not in projection_cache:
        row = connection.execute(
            """
            SELECT member_id, source_member_name
            FROM source_members
            WHERE game_id = ?
              AND perspective_player_id = ?
              AND archive_turn = ?
            ORDER BY member_ordinal
            LIMIT 1
            """,
            [game_id, player_id, archive_turn],
        ).fetchone()
        if row is None:
            projection_cache[cache_key] = None
        else:
            payload = reconstruct_compact_member(
                connection,
                int(row[0]),
                specs=specs,
            )
            projection_cache[cache_key] = mechanics_projection(
                payload,
                member=str(row[1]),
            )

    projection = projection_cache.get(cache_key)
    if not isinstance(projection, Mapping):
        return None
    ships = projection.get("ships")
    if not isinstance(ships, Sequence) or isinstance(ships, (str, bytes)):
        return None
    for raw_ship in ships:
        if not isinstance(raw_ship, Mapping):
            continue
        observed_ship_id = _intish(
            raw_ship.get("id", raw_ship.get("objectid"))
        )
        observed_owner_id = _intish(
            raw_ship.get("ownerid", raw_ship.get("owner_id"))
        )
        if observed_ship_id != ship_id:
            continue
        if observed_owner_id is not None and observed_owner_id != player_id:
            continue
        return raw_ship
    return None


def _enrich_tminus1_order_context_db(
    *,
    rows: list[dict[str, Any]],
    connection: Any,
) -> Counter[str]:
    counts: Counter[str] = Counter()
    specs = _load_specs(connection)
    projection_cache: dict[
        tuple[int, int, int],
        Mapping[str, Any] | None,
    ] = {}

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    ordered_games = sorted(by_game.items())
    for game_position, (game_id, game_rows) in enumerate(
        ordered_games,
        start=1,
    ):
        print(
            "progress: stage=enrich_tminus1_order_context_db "
            f"game={game_position}/{len(ordered_games)} "
            f"game_id={game_id} cases={len(game_rows)} status=start",
            flush=True,
        )
        for row in game_rows:
            battle_turn = int(row["turn"])
            before_turn = battle_turn - 1
            captured_owner = row.get("owner_id_before")
            opponent_owner = row.get("next_opponent_owner_id")
            if (
                isinstance(captured_owner, bool)
                or not isinstance(captured_owner, int)
                or captured_owner <= 0
                or isinstance(opponent_owner, bool)
                or not isinstance(opponent_owner, int)
                or opponent_owner <= 0
            ):
                row["order_context"] = {
                    "status": "unresolved",
                    "reason": "owner_attribution_missing",
                }
                counts["order_context:unresolved"] += 1
                counts["order_context:owner_attribution_missing"] += 1
                continue

            captured_raw = _targeted_tminus1_ship_raw_db(
                connection,
                specs=specs,
                game_id=game_id,
                player_id=captured_owner,
                archive_turn=before_turn,
                ship_id=int(row["captured_ship_id"]),
                projection_cache=projection_cache,
            )
            opponent_raw = _targeted_tminus1_ship_raw_db(
                connection,
                specs=specs,
                game_id=game_id,
                player_id=opponent_owner,
                archive_turn=before_turn,
                ship_id=int(row["next_opponent_ship_id"]),
                projection_cache=projection_cache,
            )
            if not isinstance(captured_raw, Mapping):
                row["order_context"] = {
                    "status": "unresolved",
                    "reason": "captured_ship_tminus1_missing",
                }
                counts["order_context:unresolved"] += 1
                counts["order_context:captured_ship_tminus1_missing"] += 1
                continue
            if not isinstance(opponent_raw, Mapping):
                row["order_context"] = {
                    "status": "unresolved",
                    "reason": "opponent_ship_tminus1_missing",
                }
                counts["order_context:unresolved"] += 1
                counts["order_context:opponent_ship_tminus1_missing"] += 1
                continue

            context = _order_side_controls(
                captured_ship_id=int(row["captured_ship_id"]),
                opponent_ship_id=int(row["next_opponent_ship_id"]),
                captured_raw=captured_raw,
                opponent_raw=opponent_raw,
                prior_pair_occurrences=int(
                    row["prior_same_pair_occurrences"]
                ),
                factual_side=str(row["captured_ship_side_next"]),
            )
            context["status"] = "resolved"
            row["order_context"] = context
            counts["order_context:resolved"] += 1
            for name, exact in context["side_control_exact"].items():
                if exact is True:
                    counts[f"side:{name}:exact"] += 1
                elif exact is False:
                    counts[f"side:{name}:mismatch"] += 1
                else:
                    counts[f"side:{name}:unresolved"] += 1

        print(
            "progress: stage=enrich_tminus1_order_context_db "
            f"game={game_position}/{len(ordered_games)} "
            f"game_id={game_id} status=done",
            flush=True,
        )

    return counts


def _pair_occurrence_index(
    by_vcr: Mapping[tuple[int, int, int], Sequence[Mapping[str, Any]]],
) -> dict[tuple[int, int, tuple[int, int]], list[int]]:
    result: dict[tuple[int, int, tuple[int, int]], list[int]] = defaultdict(list)
    for (game_id, turn, vcr_id), appearances in by_vcr.items():
        ship_ids = sorted(
            {
                int(row["ship_id"])
                for row in appearances
                if isinstance(row.get("ship_id"), int)
                and not isinstance(row.get("ship_id"), bool)
            }
        )
        if len(ship_ids) != 2:
            continue
        result[(game_id, turn, (ship_ids[0], ship_ids[1]))].append(vcr_id)
    for vcr_ids in result.values():
        vcr_ids.sort()
    return result


def _previous_ship_appearance(
    *,
    chain: Sequence[Mapping[str, Any]],
    before_vcr_id: int,
) -> Mapping[str, Any] | None:
    previous = [
        row
        for row in chain
        if isinstance(row.get("vcr_id"), int)
        and not isinstance(row.get("vcr_id"), bool)
        and int(row["vcr_id"]) < before_vcr_id
    ]
    if not previous:
        return None
    return max(previous, key=lambda row: int(row["vcr_id"]))


def _opposite_side(side: Any) -> str | None:
    if side == "left":
        return "right"
    if side == "right":
        return "left"
    return None


def _prior_same_pair_occurrences(
    *,
    occurrence_index: Mapping[
        tuple[int, int, tuple[int, int]],
        Sequence[int],
    ],
    game_id: int,
    turn: int,
    ship_a: int,
    ship_b: int,
    before_vcr_id: int,
) -> tuple[int, list[int]]:
    pair = tuple(sorted((ship_a, ship_b)))
    previous = [
        int(vcr_id)
        for vcr_id in occurrence_index.get((game_id, turn, pair), ())
        if int(vcr_id) < before_vcr_id
    ]
    return len(previous), previous



def _targeted_tminus1_ship_raw(
    archive: zipfile.ZipFile,
    *,
    player_id: int,
    archive_turn: int,
    ship_id: int,
    projection_cache: dict[tuple[int, int], Mapping[str, Any] | None],
) -> Mapping[str, Any] | None:
    cache_key = (player_id, archive_turn)
    if cache_key not in projection_cache:
        member_name = f"player{player_id}-turn{archive_turn}.trn"
        try:
            raw = archive.read(member_name)
        except KeyError:
            projection_cache[cache_key] = None
        else:
            member = TurnMember(
                player=player_id,
                turn=archive_turn,
                name=member_name,
            )
            parsed, _decoded = _decode_member_json(raw, member)
            projection_cache[cache_key] = mechanics_projection(
                parsed,
                member=member_name,
            )

    projection = projection_cache.get(cache_key)
    if not isinstance(projection, Mapping):
        return None
    ships = projection.get("ships")
    if not isinstance(ships, Sequence) or isinstance(ships, (str, bytes)):
        return None
    for raw_ship in ships:
        if not isinstance(raw_ship, Mapping):
            continue
        observed_ship_id = _intish(
            raw_ship.get("id", raw_ship.get("objectid"))
        )
        observed_owner_id = _intish(
            raw_ship.get("ownerid", raw_ship.get("owner_id"))
        )
        if observed_ship_id != ship_id:
            continue
        if observed_owner_id is not None and observed_owner_id != player_id:
            continue
        return raw_ship
    return None


def _order_projection(
    *,
    ship_id: int,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    priority = _priority_from_raw(ship_id, raw)
    return {
        "mission": _intish(raw.get("mission")),
        "mission_target_id": _intish(raw.get("mission1target")),
        "primary_enemy": _intish(raw.get("enemy")),
        "friendlycode": raw.get("friendlycode"),
        "priority": list(priority) if priority is not None else None,
    }


def _order_side_controls(
    *,
    captured_ship_id: int,
    opponent_ship_id: int,
    captured_raw: Mapping[str, Any],
    opponent_raw: Mapping[str, Any],
    prior_pair_occurrences: int,
    factual_side: str,
) -> dict[str, Any]:
    occurrence_index = prior_pair_occurrences + 1
    opponent_key = _priority_from_raw(opponent_ship_id, opponent_raw)
    frozen_prize_key = _priority_from_raw(captured_ship_id, captured_raw)

    old_fc = captured_raw.get("friendlycode")
    opponent_fc = opponent_raw.get("friendlycode")
    fresh_fc = _nonmatching_symbolic_fc(opponent_fc)
    neutral_preserved_raw = _neutral_prize_raw(
        captured_raw,
        friendly_code=old_fc,
    )
    neutral_fresh_raw = _neutral_prize_raw(
        captured_raw,
        friendly_code=fresh_fc,
    )
    neutral_preserved_key = _priority_from_raw(
        captured_ship_id,
        neutral_preserved_raw,
    )
    neutral_fresh_key = _priority_from_raw(
        captured_ship_id,
        neutral_fresh_raw,
    )

    controls = {
        "frozen_tminus1_priority": _side_from_priority_keys(
            prize_ship_id=captured_ship_id,
            opponent_ship_id=opponent_ship_id,
            prize_key=frozen_prize_key,
            opponent_key=opponent_key,
            occurrence_index=occurrence_index,
        ),
        "neutral_orders_preserve_fc": _side_from_priority_keys(
            prize_ship_id=captured_ship_id,
            opponent_ship_id=opponent_ship_id,
            prize_key=neutral_preserved_key,
            opponent_key=opponent_key,
            occurrence_index=occurrence_index,
        ),
        "neutral_orders_fresh_fc": _side_from_priority_keys(
            prize_ship_id=captured_ship_id,
            opponent_ship_id=opponent_ship_id,
            prize_key=neutral_fresh_key,
            opponent_key=opponent_key,
            occurrence_index=occurrence_index,
        ),
    }
    exact = {
        name: value == factual_side if value in {"left", "right"} else None
        for name, value in controls.items()
    }
    return {
        "occurrence_index": occurrence_index,
        "captured_tminus1": _order_projection(
            ship_id=captured_ship_id,
            raw=captured_raw,
        ),
        "opponent_tminus1": _order_projection(
            ship_id=opponent_ship_id,
            raw=opponent_raw,
        ),
        "neutral_preserved_fc_priority": (
            list(neutral_preserved_key)
            if neutral_preserved_key is not None
            else None
        ),
        "neutral_fresh_fc": fresh_fc,
        "neutral_fresh_fc_priority": (
            list(neutral_fresh_key)
            if neutral_fresh_key is not None
            else None
        ),
        "side_controls": controls,
        "side_control_exact": exact,
    }


def _enrich_tminus1_order_context(
    *,
    rows: list[dict[str, Any]],
    archive_dir: Path,
) -> Counter[str]:
    counts: Counter[str] = Counter()
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    ordered_games = sorted(by_game.items())
    for game_position, (game_id, game_rows) in enumerate(
        ordered_games,
        start=1,
    ):
        print(
            "progress: stage=enrich_tminus1_order_context "
            f"game={game_position}/{len(ordered_games)} "
            f"game_id={game_id} cases={len(game_rows)} status=start",
            flush=True,
        )
        archive_path = archive_dir / f"game-{game_id}.zip"
        if not archive_path.is_file():
            for row in game_rows:
                row["order_context"] = {
                    "status": "unresolved",
                    "reason": "archive_missing",
                }
                counts["order_context:unresolved"] += 1
                counts["order_context:archive_missing"] += 1
            continue

        projection_cache: dict[
            tuple[int, int],
            Mapping[str, Any] | None,
        ] = {}
        with zipfile.ZipFile(archive_path) as archive:
            for row in game_rows:
                battle_turn = int(row["turn"])
                before_turn = battle_turn - 1
                captured_owner = row.get("owner_id_before")
                opponent_owner = row.get("next_opponent_owner_id")
                if (
                    isinstance(captured_owner, bool)
                    or not isinstance(captured_owner, int)
                    or captured_owner <= 0
                    or isinstance(opponent_owner, bool)
                    or not isinstance(opponent_owner, int)
                    or opponent_owner <= 0
                ):
                    row["order_context"] = {
                        "status": "unresolved",
                        "reason": "owner_attribution_missing",
                    }
                    counts["order_context:unresolved"] += 1
                    counts["order_context:owner_attribution_missing"] += 1
                    continue

                captured_raw = _targeted_tminus1_ship_raw(
                    archive,
                    player_id=captured_owner,
                    archive_turn=before_turn,
                    ship_id=int(row["captured_ship_id"]),
                    projection_cache=projection_cache,
                )
                opponent_raw = _targeted_tminus1_ship_raw(
                    archive,
                    player_id=opponent_owner,
                    archive_turn=before_turn,
                    ship_id=int(row["next_opponent_ship_id"]),
                    projection_cache=projection_cache,
                )
                if not isinstance(captured_raw, Mapping):
                    row["order_context"] = {
                        "status": "unresolved",
                        "reason": "captured_ship_tminus1_missing",
                    }
                    counts["order_context:unresolved"] += 1
                    counts["order_context:captured_ship_tminus1_missing"] += 1
                    continue
                if not isinstance(opponent_raw, Mapping):
                    row["order_context"] = {
                        "status": "unresolved",
                        "reason": "opponent_ship_tminus1_missing",
                    }
                    counts["order_context:unresolved"] += 1
                    counts["order_context:opponent_ship_tminus1_missing"] += 1
                    continue

                context = _order_side_controls(
                    captured_ship_id=int(row["captured_ship_id"]),
                    opponent_ship_id=int(row["next_opponent_ship_id"]),
                    captured_raw=captured_raw,
                    opponent_raw=opponent_raw,
                    prior_pair_occurrences=int(
                        row["prior_same_pair_occurrences"]
                    ),
                    factual_side=str(row["captured_ship_side_next"]),
                )
                context["status"] = "resolved"
                row["order_context"] = context
                counts["order_context:resolved"] += 1
                for name, exact in context["side_control_exact"].items():
                    if exact is True:
                        counts[f"side:{name}:exact"] += 1
                    elif exact is False:
                        counts[f"side:{name}:mismatch"] += 1
                    else:
                        counts[f"side:{name}:unresolved"] += 1

        print(
            "progress: stage=enrich_tminus1_order_context "
            f"game={game_position}/{len(ordered_games)} "
            f"game_id={game_id} status=done",
            flush=True,
        )

    return counts


def _manifest_context(record: Mapping[str, Any]) -> dict[str, Any]:
    settings = record.get("settings")
    settings = settings if isinstance(settings, Mapping) else {}
    player_slots = record.get("player_slots")
    player_slots = (
        player_slots
        if isinstance(player_slots, Sequence)
        and not isinstance(player_slots, (str, bytes))
        else ()
    )
    active_advantages = sum(
        1
        for player in player_slots
        if isinstance(player, Mapping)
        and isinstance(player.get("activeadvantages"), str)
        and bool(str(player.get("activeadvantages")).strip())
    )
    active_hulls = sum(
        1
        for player in player_slots
        if isinstance(player, Mapping)
        and isinstance(player.get("activehulls"), str)
        and bool(str(player.get("activehulls")).strip())
    )
    return {
        "settings_hash": record.get("settings_hash"),
        "bucket": _manifest_bucket(record),
        "settings": {key: settings.get(key) for key in SETTING_KEYS},
        "players_with_activeadvantages": active_advantages,
        "players_with_activehulls": active_hulls,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    manifests = list(
        load_manifest_jsonl(args.manifest.read_text(encoding="utf-8"))
    )
    manifest_by_game = {_game_id(row): row for row in manifests}
    indexed_ids = _load_indexed_game_ids(args.index)
    indexed_ids &= set(manifest_by_game)

    partitions = {
        game_id: _partition_for_game(
            game_id,
            salt=args.partition_salt,
            holdout_modulus=args.holdout_modulus,
        )
        for game_id in sorted(indexed_ids)
    }
    if args.partition == "all":
        scan_ids = set(indexed_ids)
    else:
        scan_ids = {
            game_id
            for game_id, partition in partitions.items()
            if partition == args.partition
        }

    db_connection = None
    database_path: Path | None = None
    if args.corpus_db_root is not None:
        db_connection, database_path = connect_current_compact_read_only(
            args.corpus_db_root
        )
        appearances, chain_summary = _collect_appearances_db(
            connection=db_connection,
            scan_ids=scan_ids,
            progress=True,
        )
    else:
        appearances, chain_summary = _collect_appearances_cached(
            args=args,
            scan_ids=scan_ids,
        )

    by_vcr: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    by_ship_turn: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in appearances:
        by_vcr[
            (int(row["game_id"]), int(row["turn"]), int(row["vcr_id"]))
        ].append(row)
        by_ship_turn[
            (int(row["game_id"]), int(row["turn"]), int(row["ship_id"]))
        ].append(row)

    for appearance_chain in by_ship_turn.values():
        appearance_chain.sort(key=lambda item: int(item["vcr_id"]))

    occurrence_index = _pair_occurrence_index(by_vcr)
    counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    prior_pair_counts: Counter[str] = Counter()
    by_game: Counter[int] = Counter()
    rows: list[dict[str, Any]] = []

    for chain in by_ship_turn.values():
        for previous, current in zip(chain, chain[1:]):
            if not capture_module._same_location(previous, current):
                continue
            terminal = previous.get("terminal")
            if not isinstance(terminal, Mapping) or terminal.get("captured") is not True:
                continue

            counts["capture_continuations"] += 1
            previous_opponent = capture_module._other_appearance(by_vcr, previous)
            current_opponent = capture_module._other_appearance(by_vcr, current)
            current_opponent_is_planet = capture_module._other_is_planet(
                by_vcr,
                current,
            )
            transition = capture_module._capture_transition(
                previous=previous,
                current=current,
                previous_opponent=previous_opponent,
                current_opponent=current_opponent,
                current_opponent_is_planet=current_opponent_is_planet,
            )
            if transition.get("status") != "capture_continuation":
                counts["unresolved_capture_transition"] += 1
                continue

            if current_opponent_is_planet or not isinstance(current_opponent, Mapping):
                counts["next_combat_planet"] += 1
                continue

            counts["next_combat_ship"] += 1
            game_id = int(transition["game_id"])
            turn = int(transition["turn"])
            captured_ship_id = int(transition["ship_id"])
            opponent_ship_id = int(current_opponent["ship_id"])
            to_vcr_id = int(transition["to_vcr_id"])
            prior_count, prior_vcr_ids = _prior_same_pair_occurrences(
                occurrence_index=occurrence_index,
                game_id=game_id,
                turn=turn,
                ship_a=captured_ship_id,
                ship_b=opponent_ship_id,
                before_vcr_id=to_vcr_id,
            )
            opponent_previous = _previous_ship_appearance(
                chain=by_ship_turn.get((game_id, turn, opponent_ship_id), ()),
                before_vcr_id=to_vcr_id,
            )
            opponent_previous_side = (
                opponent_previous.get("side")
                if isinstance(opponent_previous, Mapping)
                else None
            )
            opponent_previous_vcr_id = (
                int(opponent_previous["vcr_id"])
                if isinstance(opponent_previous, Mapping)
                and isinstance(opponent_previous.get("vcr_id"), int)
                and not isinstance(opponent_previous.get("vcr_id"), bool)
                else None
            )

            captured_side = transition.get("current_side")
            opponent_side = current_opponent.get("side")
            capture_side = previous.get("side")
            side_counts[f"captured:{captured_side}"] += 1
            side_counts[f"opponent:{opponent_side}"] += 1
            prior_pair_counts[str(prior_count)] += 1
            by_game[game_id] += 1

            row = {
                "game_id": game_id,
                "turn": turn,
                "position": transition.get("position"),
                "captured_ship_id": captured_ship_id,
                "captor_ship_id": transition.get("captor_ship_id"),
                "next_opponent_ship_id": opponent_ship_id,
                "next_opponent_owner_id": current_opponent.get("owner_id"),
                "capture_vcr_id": int(transition["from_vcr_id"]),
                "next_vcr_id": to_vcr_id,
                "capture_side": capture_side,
                "captor_side": (
                    previous_opponent.get("side")
                    if isinstance(previous_opponent, Mapping)
                    else None
                ),
                "captured_ship_side_next": captured_side,
                "next_opponent_side": opponent_side,
                "owner_id_before": transition.get("owner_id_before"),
                "captor_owner_id": transition.get("captor_owner_id"),
                "owner_id_after": transition.get("owner_id_after"),
                "race_id_before": transition.get("race_id_before"),
                "captor_race_id": transition.get("captor_race_id"),
                "race_id_after": transition.get("race_id_after"),
                "prior_same_pair_occurrences": prior_count,
                "prior_same_pair_vcr_ids": prior_vcr_ids,
                "next_opponent_previous_vcr_id": opponent_previous_vcr_id,
                "next_opponent_previous_side": opponent_previous_side,
                "next_opponent_side_carry_exact": (
                    opponent_side == opponent_previous_side
                    if opponent_side in {"left", "right"}
                    and opponent_previous_side in {"left", "right"}
                    else None
                ),
                "opponent_side_cursor_prediction": (
                    _opposite_side(opponent_previous_side)
                    if opponent_previous_side in {"left", "right"}
                    else "left"
                ),
                "opponent_side_cursor_exact": (
                    captured_side
                    == (
                        _opposite_side(opponent_previous_side)
                        if opponent_previous_side in {"left", "right"}
                        else "left"
                    )
                    if captured_side in {"left", "right"}
                    else None
                ),
                "simple_opponent_initiator_right_exact": captured_side == "left",
                "sticky_capture_side_exact": (
                    captured_side == capture_side
                    if captured_side in {"left", "right"}
                    and capture_side in {"left", "right"}
                    else None
                ),
                "ruleset": _manifest_context(manifest_by_game[game_id]),
            }
            rows.append(row)

    rows.sort(
        key=lambda row: (
            int(row["game_id"]),
            int(row["turn"]),
            int(row["next_vcr_id"]),
            int(row["captured_ship_id"]),
        )
    )

    print(
        "progress: stage=enrich_tminus1_order_context "
        f"ship_cases={len(rows)} status=start",
        flush=True,
    )
    if db_connection is not None:
        order_counts = _enrich_tminus1_order_context_db(
            rows=rows,
            connection=db_connection,
        )
        db_connection.close()
        db_connection = None
    else:
        order_counts = _enrich_tminus1_order_context(
            rows=rows,
            archive_dir=args.archive_dir,
        )
    print(
        "progress: stage=enrich_tminus1_order_context "
        f"ship_cases={len(rows)} "
        f"resolved={int(order_counts.get('order_context:resolved', 0))} "
        "status=done",
        flush=True,
    )
    counts.update(order_counts)

    partition_counts = Counter(partitions.values())
    report = {
        "schema": SCHEMA,
        "evidence_status": "DISCOVERY_ONLY_NOT_PROMOTED",
        "partition": args.partition,
        "storage_backend": (
            "corpus-db" if database_path is not None else "archive"
        ),
        "database_path": (
            str(database_path) if database_path is not None else None
        ),
        "partition_salt": args.partition_salt,
        "holdout_modulus": args.holdout_modulus,
        "indexed_game_ids": sorted(indexed_ids),
        "partition_counts": dict(sorted(partition_counts.items())),
        "scanned_game_ids": sorted(scan_ids),
        "unscanned_game_ids": sorted(indexed_ids - scan_ids),
        "chain_summary": chain_summary,
        "summary": {
            **dict(sorted(counts.items())),
            "ship_capture_side_counts": dict(sorted(side_counts.items())),
            "prior_same_pair_occurrence_counts": dict(
                sorted(prior_pair_counts.items())
            ),
            "ship_capture_continuations_by_game": {
                str(game_id): count
                for game_id, count in sorted(by_game.items())
            },
            "next_opponent_prior_appearance": sum(
                1 for row in rows
                if row["next_opponent_previous_vcr_id"] is not None
            ),
            "next_opponent_side_carry_exact": sum(
                1 for row in rows
                if row["next_opponent_side_carry_exact"] is True
            ),
            "next_opponent_side_carry_mismatch": sum(
                1 for row in rows
                if row["next_opponent_side_carry_exact"] is False
            ),
            "opponent_side_cursor_exact": sum(
                1 for row in rows
                if row["opponent_side_cursor_exact"] is True
            ),
            "opponent_side_cursor_mismatch": sum(
                1 for row in rows
                if row["opponent_side_cursor_exact"] is False
            ),
            "simple_opponent_initiator_right_exact": sum(
                1
                for row in rows
                if row["simple_opponent_initiator_right_exact"] is True
            ),
            "sticky_capture_side_exact": sum(
                1
                for row in rows
                if row["sticky_capture_side_exact"] is True
            ),
            "order_side_controls": {
                name: {
                    "exact": int(counts[f"side:{name}:exact"]),
                    "mismatch": int(counts[f"side:{name}:mismatch"]),
                    "unresolved": int(counts[f"side:{name}:unresolved"]),
                }
                for name in (
                    "frozen_tminus1_priority",
                    "neutral_orders_preserve_fc",
                    "neutral_orders_fresh_fc",
                )
            },
        },
        "observations": rows,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Harvest ship-to-ship post-capture LEFT/RIGHT observations from the "
            "independent public validation corpus without promoting a rule."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument(
        "--corpus-db-root",
        type=Path,
        default=None,
        help=(
            "Read source members from the shared compact Corpus DB instead of "
            "ZIP archives. The DB is opened read-only."
        ),
    )
    parser.add_argument(
        "--appearance-cache-dir",
        type=Path,
        default=DEFAULT_APPEARANCE_CACHE_DIR,
    )
    parser.add_argument(
        "--partition",
        choices=("discovery", "heldout", "all"),
        default="discovery",
    )
    parser.add_argument("--partition-salt", default=DEFAULT_PARTITION_SALT)
    parser.add_argument("--holdout-modulus", type=int, default=DEFAULT_HOLDOUT_MODULUS)
    parser.add_argument("--example-limit", type=int, default=40)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary = report["summary"]
        print("===== PUBLIC CAPTURE-SIDE HARVEST =====")
        print(f"partition:                    {report['partition']}")
        print(f"storage_backend:              {report['storage_backend']}")
        print(f"indexed_games:                {len(report['indexed_game_ids'])}")
        print(f"scanned_games:                {len(report['scanned_game_ids'])}")
        print(f"unscanned_games:              {len(report['unscanned_game_ids'])}")
        print(
            "capture_continuations:         "
            f"{summary.get('capture_continuations', 0)}"
        )
        print(
            "next_combat_ship:              "
            f"{summary.get('next_combat_ship', 0)}"
        )
        print(
            "next_combat_planet:            "
            f"{summary.get('next_combat_planet', 0)}"
        )
        print(
            "ship_capture_side_counts:      "
            f"{summary.get('ship_capture_side_counts', {})}"
        )
        print(
            "prior_pair_occurrence_counts:  "
            f"{summary.get('prior_same_pair_occurrence_counts', {})}"
        )
        print(
            "opponent_prior_appearance:     "
            f"{summary.get('next_opponent_prior_appearance', 0)}"
        )
        print(
            "opponent_side_carry:           "
            f"{summary.get('next_opponent_side_carry_exact', 0)} exact / "
            f"{summary.get('next_opponent_side_carry_mismatch', 0)} mismatch"
        )
        print(
            "opponent_side_cursor:          "
            f"{summary.get('opponent_side_cursor_exact', 0)} exact / "
            f"{summary.get('opponent_side_cursor_mismatch', 0)} mismatch"
        )
        print(
            "opponent_initiator_right_exact:"
            f" {summary.get('simple_opponent_initiator_right_exact', 0)}"
        )
        print(
            "sticky_capture_side_exact:     "
            f"{summary.get('sticky_capture_side_exact', 0)}"
        )
        print(
            "order_context_resolved:        "
            f"{summary.get('order_context:resolved', 0)}"
        )
        print(
            "order_side_controls:           "
            f"{summary.get('order_side_controls', {})}"
        )
        print(f"output:                       {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
