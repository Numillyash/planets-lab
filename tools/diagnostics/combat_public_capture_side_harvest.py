from __future__ import annotations

import argparse
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
from planets_lab.corpus.indexer import load_manifest_jsonl
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.normalizer import _decode_member_json, mechanics_projection
from planets_lab.corpus.public_finished_discover_cli import _manifest_bucket

import combat_host_capture_continuation_audit as capture_module
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

    print(
        "progress: stage=collect_capture_appearances "
        f"games={len(scan_ids)} status=start",
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
    print(
        "progress: stage=collect_capture_appearances "
        f"games={len(scan_ids)} appearances={len(appearances)} status=done",
        flush=True,
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

    occurrence_index = _pair_occurrence_index(by_vcr)
    counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    prior_pair_counts: Counter[str] = Counter()
    by_game: Counter[int] = Counter()
    rows: list[dict[str, Any]] = []

    for chain in by_ship_turn.values():
        chain.sort(key=lambda item: int(item["vcr_id"]))
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
