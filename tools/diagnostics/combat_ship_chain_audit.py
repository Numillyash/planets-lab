from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.rules.combat import (
    ReplayUnsupported,
    federation_recover_shields,
    replay_nuhost_from_nu_catalog,
)


DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
CARRY_FIELDS = (
    ("damage", "damage"),
    ("crew", "crew"),
    ("torpedoes", "torpedos"),
    ("fighters", "fighters"),
)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _decode_turn(raw: bytes, member_name: str) -> dict[str, Any]:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        try:
            payload = gzip.decompress(payload)
        except OSError as exc:
            raise ValueError(f"{member_name}: invalid gzip payload") from exc
    try:
        parsed = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{member_name}: turn payload is not UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{member_name}: turn payload must be an object")
    return parsed


def _int(raw: Mapping[str, Any] | None, key: str) -> int | None:
    if not isinstance(raw, Mapping):
        return None
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _objects(rst: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = rst.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _position(vcr: Mapping[str, Any]) -> tuple[int, int] | None:
    x = _int(vcr, "x")
    y = _int(vcr, "y")
    if x is None or y is None:
        return None
    return x, y


def _federation_candidate_shield(
    *,
    terminal_shield: int | None,
    terminal_damage: int | None,
) -> int | None:
    if terminal_shield is None or terminal_damage is None:
        return None
    recovered, _amount = federation_recover_shields(
        {
            "shield": terminal_shield,
            "damage": terminal_damage,
            "federation_crew_bonus": True,
        }
    )
    value = recovered.get("shield")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _transition_comparison(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
) -> dict[str, Any]:
    terminal = previous.get("terminal")
    start = current.get("start")
    if not isinstance(terminal, Mapping) or not isinstance(start, Mapping):
        return {"status": "not_comparable", "reason": "missing terminal/start"}

    if bool(terminal.get("destroyed") or terminal.get("captured")):
        return {
            "status": "reappearance_after_defeat",
            "reason": "ship appears in a later VCR after replay marked it defeated",
        }

    carry: dict[str, Any] = {}
    carry_mismatches: list[str] = []
    carry_comparable = 0
    for terminal_key, start_key in CARRY_FIELDS:
        expected = terminal.get(terminal_key)
        actual = _int(start, start_key)
        comparable = isinstance(expected, int) and not isinstance(expected, bool) and actual is not None
        matches: bool | None
        if comparable:
            carry_comparable += 1
            matches = int(expected) == actual
            if not matches:
                carry_mismatches.append(terminal_key)
        else:
            matches = None
        carry[terminal_key] = {
            "terminal": int(expected) if isinstance(expected, int) and not isinstance(expected, bool) else None,
            "next_start": actual,
            "matches": matches,
        }

    terminal_shield_raw = terminal.get("shield")
    terminal_damage_raw = terminal.get("damage")
    terminal_shield = (
        int(terminal_shield_raw)
        if isinstance(terminal_shield_raw, int) and not isinstance(terminal_shield_raw, bool)
        else None
    )
    terminal_damage = (
        int(terminal_damage_raw)
        if isinstance(terminal_damage_raw, int) and not isinstance(terminal_damage_raw, bool)
        else None
    )
    actual_shield = _int(start, "shield")
    race_id = previous.get("race_id")
    race_id = race_id if isinstance(race_id, int) and not isinstance(race_id, bool) else None

    exact_carry_matches = (
        terminal_shield == actual_shield
        if terminal_shield is not None and actual_shield is not None
        else None
    )
    federation_candidate = (
        _federation_candidate_shield(
            terminal_shield=terminal_shield,
            terminal_damage=terminal_damage,
        )
        if race_id == 1
        else None
    )
    federation_candidate_matches = (
        federation_candidate == actual_shield
        if federation_candidate is not None and actual_shield is not None
        else None
    )

    if exact_carry_matches is True and federation_candidate_matches is True:
        shield_model = "both"
        shield_matches = True
    elif exact_carry_matches is True:
        shield_model = "exact_carry"
        shield_matches = True
    elif federation_candidate_matches is True:
        shield_model = "federation_candidate"
        shield_matches = True
    elif exact_carry_matches is False or federation_candidate_matches is False:
        shield_model = "mismatch"
        shield_matches = False
    else:
        shield_model = "unknown"
        shield_matches = None

    status = "match"
    if carry_mismatches or shield_matches is False:
        status = "mismatch"
    elif carry_comparable == 0 and shield_matches is None:
        status = "not_comparable"

    return {
        "status": status,
        "carry": carry,
        "carry_comparable_fields": carry_comparable,
        "carry_mismatches": carry_mismatches,
        "shield": {
            "terminal": terminal_shield,
            "next_start": actual_shield,
            "exact_carry_matches": exact_carry_matches,
            "federation_candidate": federation_candidate,
            "federation_candidate_matches": federation_candidate_matches,
            "model": shield_model,
            "race1_candidate": race_id == 1,
        },
    }


def _appearance(
    *,
    game_id: int,
    turn: int,
    vcr_id: int,
    position: tuple[int, int] | None,
    side_name: str,
    raw_side: Mapping[str, Any],
    replay_side: Mapping[str, Any],
) -> dict[str, Any] | None:
    hull_id = _int(raw_side, "hullid")
    ship_id = _int(raw_side, "objectid")
    if hull_id is None or hull_id <= 0 or ship_id is None:
        return None
    return {
        "game_id": game_id,
        "turn": turn,
        "vcr_id": vcr_id,
        "position": list(position) if position is not None else None,
        "side": side_name,
        "ship_id": ship_id,
        "hull_id": hull_id,
        "race_id": _int(raw_side, "raceid"),
        "start": dict(raw_side),
        "terminal": dict(replay_side),
    }


def _same_location(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    left = previous.get("position")
    right = current.get("position")
    return (
        isinstance(left, list)
        and isinstance(right, list)
        and len(left) == 2
        and len(right) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) for value in left + right)
        and left == right
    )


def _archive_paths(args: argparse.Namespace) -> list[Path]:
    if args.archive:
        return [Path(value) for value in args.archive]
    return sorted(args.archive_dir.glob("game-*.zip"))


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    archives = _archive_paths(args)
    if not archives:
        raise ValueError("no loadall archives found")

    summary: Counter[str] = Counter()
    summary["archives"] = len(archives)
    unique_cases: dict[tuple[int, int, int], dict[str, Any]] = {}
    payload_conflict_keys: set[tuple[int, int, int]] = set()
    malformed_members: list[dict[str, Any]] = []
    archive_reports: list[dict[str, Any]] = []

    for archive_path in archives:
        archive_started = time.perf_counter()
        data = archive_path.read_bytes()
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        archive_game_ids: set[int] = set()
        archive_vcr_observations = 0

        for member in members:
            raw = raw_members[member.name]
            try:
                payload = _decode_turn(raw, member.name)
            except ValueError as exc:
                summary["malformed_members"] += 1
                if len(malformed_members) < args.detail_limit:
                    malformed_members.append({"member": member.name, "reason": str(exc)})
                continue
            rst = payload.get("rst")
            if not isinstance(rst, Mapping):
                continue
            game = rst.get("game")
            if not isinstance(game, Mapping):
                continue
            game_id = _int(game, "id")
            game_turn = _int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            archive_game_ids.add(game_id)
            beams = _objects(rst, "beams")
            torpedoes = _objects(rst, "torpedos")
            settings = rst.get("settings")
            settings = dict(settings) if isinstance(settings, Mapping) else {}

            for raw_vcr in _objects(rst, "vcrs"):
                vcr_id = _int(raw_vcr, "id")
                battle_turn = _int(raw_vcr, "turn") or game_turn
                if vcr_id is None:
                    continue
                archive_vcr_observations += 1
                summary["raw_vcr_observations"] += 1
                key = (game_id, battle_turn, vcr_id)
                payload_hash = _canonical_hash(raw_vcr)
                existing = unique_cases.get(key)
                if existing is None:
                    unique_cases[key] = {
                        "game_id": game_id,
                        "turn": battle_turn,
                        "vcr_id": vcr_id,
                        "payload": dict(raw_vcr),
                        "payload_hash": payload_hash,
                        "beams": beams,
                        "torpedoes": torpedoes,
                        "settings": settings,
                        "observations": 1,
                    }
                else:
                    existing["observations"] += 1
                    if existing["payload_hash"] != payload_hash:
                        payload_conflict_keys.add(key)

        archive_reports.append(
            {
                "archive": archive_path.name,
                "game_ids": sorted(archive_game_ids),
                "turn_members": len(members),
                "vcr_observations": archive_vcr_observations,
                "seconds": round(time.perf_counter() - archive_started, 3),
            }
        )

    summary["unique_vcrs"] = len(unique_cases)
    summary["payload_conflicts"] = len(payload_conflict_keys)

    appearances: list[dict[str, Any]] = []
    replay_unsupported_reasons: Counter[str] = Counter()
    by_game: dict[str, Counter[str]] = defaultdict(Counter)

    for key, case in sorted(unique_cases.items()):
        game_id, turn, vcr_id = key
        game = by_game[str(game_id)]
        game["unique_vcrs"] += 1
        if key in payload_conflict_keys:
            game["payload_conflicts"] += 1
            continue
        try:
            replay = replay_nuhost_from_nu_catalog(
                case["payload"],
                beams=case["beams"],
                torpedoes=case["torpedoes"],
                settings=case["settings"],
            )
        except ReplayUnsupported as exc:
            reason = str(exc)
            summary["replay_unsupported"] += 1
            game["replay_unsupported"] += 1
            replay_unsupported_reasons[reason] += 1
            continue

        summary["replay_supported"] += 1
        game["replay_supported"] += 1
        position = _position(case["payload"])
        for side_name in ("left", "right"):
            raw_side = case["payload"].get(side_name)
            replay_side = replay.get(side_name)
            if not isinstance(raw_side, Mapping) or not isinstance(replay_side, Mapping):
                continue
            appearance = _appearance(
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
                game["ship_appearances"] += 1

    by_ship_turn: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for appearance in appearances:
        by_ship_turn[(appearance["game_id"], appearance["turn"], appearance["ship_id"])].append(appearance)

    transitions: list[dict[str, Any]] = []
    chain_lengths: Counter[int] = Counter()
    for (game_id, turn, ship_id), chain in sorted(by_ship_turn.items()):
        chain.sort(key=lambda item: item["vcr_id"])
        if len(chain) < 2:
            continue
        summary["candidate_ship_turn_chains"] += 1
        by_game[str(game_id)]["candidate_ship_turn_chains"] += 1
        chain_lengths[len(chain)] += 1
        for previous, current in zip(chain, chain[1:]):
            if not _same_location(previous, current):
                summary["skipped_location_change"] += 1
                by_game[str(game_id)]["skipped_location_change"] += 1
                continue
            comparison = _transition_comparison(previous, current)
            transition = {
                "game_id": game_id,
                "turn": turn,
                "ship_id": ship_id,
                "race_id": previous.get("race_id"),
                "hull_id": previous.get("hull_id"),
                "position": previous.get("position"),
                "from_vcr": previous["vcr_id"],
                "from_side": previous["side"],
                "to_vcr": current["vcr_id"],
                "to_side": current["side"],
                "comparison": comparison,
            }
            transitions.append(transition)
            summary["same_location_transitions"] += 1
            by_game[str(game_id)]["same_location_transitions"] += 1

    field_counts: dict[str, Counter[str]] = {
        key: Counter() for key, _start_key in CARRY_FIELDS
    }
    shield_models: Counter[str] = Counter()
    mismatch_details: list[dict[str, Any]] = []
    match_samples: list[dict[str, Any]] = []
    race1_samples: list[dict[str, Any]] = []

    for transition in transitions:
        comparison = transition["comparison"]
        status = str(comparison.get("status", "unknown"))
        summary[status] += 1
        by_game[str(transition["game_id"])][status] += 1

        carry = comparison.get("carry")
        if isinstance(carry, Mapping):
            for field, values in carry.items():
                if field not in field_counts or not isinstance(values, Mapping):
                    continue
                matches = values.get("matches")
                if matches is True:
                    field_counts[field]["match"] += 1
                elif matches is False:
                    field_counts[field]["mismatch"] += 1
                else:
                    field_counts[field]["unknown"] += 1

        shield = comparison.get("shield")
        if isinstance(shield, Mapping):
            model = str(shield.get("model", "unknown"))
            shield_models[model] += 1
            if bool(shield.get("race1_candidate")):
                summary["race1_transitions"] += 1
                if len(race1_samples) < args.sample_limit:
                    race1_samples.append(transition)
            else:
                summary["non_race1_transitions"] += 1

        if status in {"mismatch", "reappearance_after_defeat"}:
            if len(mismatch_details) < args.detail_limit:
                mismatch_details.append(transition)
        elif status == "match" and len(match_samples) < args.sample_limit:
            match_samples.append(transition)

    elapsed = time.perf_counter() - started
    return {
        "schema": "planets-lab.combat-ship-chain-audit.v1",
        "read_only": True,
        "evidence_boundary": (
            "Independent differential comparison: deterministic terminal state from one factual VCR "
            "versus factual start state of the same ship in its next same-turn same-location VCR."
        ),
        "summary": dict(summary),
        "carry_fields": {key: dict(value) for key, value in field_counts.items()},
        "shield_models": dict(sorted(shield_models.items())),
        "chain_lengths": {str(key): value for key, value in sorted(chain_lengths.items())},
        "replay_unsupported_reasons": dict(sorted(replay_unsupported_reasons.items())),
        "games": {key: dict(value) for key, value in sorted(by_game.items(), key=lambda item: int(item[0]))},
        "archives": archive_reports,
        "mismatch_details": mismatch_details,
        "match_samples": match_samples,
        "race1_samples": race1_samples,
        "malformed_member_samples": malformed_members,
        "seconds": round(elapsed, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only differential audit for same-turn same-location ship combat chains "
            "over cached loadall archives."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--archive", action="append", default=[])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--detail-limit", type=int, default=100)
    parser.add_argument("--sample-limit", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")

    summary = report["summary"]
    print("===== SHIP COMBAT CHAIN DIFFERENTIAL AUDIT =====")
    for key in (
        "archives",
        "raw_vcr_observations",
        "unique_vcrs",
        "payload_conflicts",
        "replay_supported",
        "replay_unsupported",
        "ship_appearances",
        "candidate_ship_turn_chains",
        "same_location_transitions",
        "skipped_location_change",
        "match",
        "mismatch",
        "not_comparable",
        "reappearance_after_defeat",
        "race1_transitions",
        "non_race1_transitions",
        "malformed_members",
    ):
        print(f"{key}: {summary.get(key, 0)}")
    print(f"carry_fields: {report['carry_fields']}")
    print(f"shield_models: {report['shield_models']}")
    print(f"chain_lengths: {report['chain_lengths']}")
    print(f"replay_unsupported_reasons: {report['replay_unsupported_reasons']}")
    print("games:")
    for game_id, values in report["games"].items():
        print(f"  {game_id}: {values}")
    print(f"mismatch_details: {len(report['mismatch_details'])}")
    for item in report["mismatch_details"]:
        print(f"  {item}")
    print(f"race1_samples: {len(report['race1_samples'])}")
    for item in report["race1_samples"]:
        print(f"  {item}")
    print(f"seconds: {report['seconds']}")
    if args.output is not None:
        print(f"output: {args.output}")
    print("NOTE: this is independent next-VCR differential evidence, not replay self-consistency.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
