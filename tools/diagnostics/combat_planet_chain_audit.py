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
    PLANET_CARRYOVER_BASIS,
    ReplayUnsupported,
    apply_planet_carryover,
    rebuild_planet_combatant,
    replay_nuhost_from_nu_catalog,
)


DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
SPECIAL_GAME_ID = 591478
FIELD_MAP = {
    "beam_count": "beamcount",
    "launcher_count": "launchercount",
    "bay_count": "baycount",
    "beam_id": "beamid",
    "torpedo_id": "torpedoid",
    "shield": "shield",
    "damage": "damage",
    "crew": "crew",
    "mass": "mass",
    "fighters": "fighters",
}


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


def _int(record: Mapping[str, Any] | None, key: str) -> int | None:
    if not isinstance(record, Mapping):
        return None
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _bool(record: Mapping[str, Any] | None, key: str) -> bool | None:
    if not isinstance(record, Mapping):
        return None
    value = record.get(key)
    return value if isinstance(value, bool) else None


def _objects(rst: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = rst.get(key)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _position(vcr: Mapping[str, Any]) -> tuple[int, int] | None:
    x = _int(vcr, "x")
    y = _int(vcr, "y")
    if x is None or y is None:
        return None
    return x, y


def _archive_paths(args: argparse.Namespace) -> list[Path]:
    explicit = [Path(value) for value in args.archive]
    paths = explicit or sorted(Path(args.archive_dir).glob("game-*.zip"))
    if not paths:
        raise ValueError("no loadall archives found")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"archive paths do not exist: {missing}")
    return paths


def _same_position(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return a.get("position") is not None and a.get("position") == b.get("position")


def _infer_no_starbase_start(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    """Infer DP only when factual VCR explicitly says no starbase."""

    if _bool(raw, "hasstarbase") is not False:
        return None
    mass = _int(raw, "mass")
    shield = _int(raw, "shield")
    if mass is None or mass < 100 or shield is None:
        return None
    return rebuild_planet_combatant(
        {
            "hull_id": 0,
            "race_id": _int(raw, "raceid"),
            "has_starbase": False,
            "planet_defense": mass - 100,
        },
        shield=shield,
    )


def _projection_check(
    predicted: Mapping[str, Any],
    factual: Mapping[str, Any],
) -> dict[str, Any]:
    comparable: list[str] = []
    mismatches: list[str] = []
    fields: dict[str, dict[str, Any]] = {}

    for predicted_key, factual_key in FIELD_MAP.items():
        expected_raw = predicted.get(predicted_key)
        expected = (
            int(expected_raw)
            if isinstance(expected_raw, int) and not isinstance(expected_raw, bool)
            else None
        )
        actual = _int(factual, factual_key)
        matches = expected == actual if expected is not None and actual is not None else None
        if matches is not None:
            comparable.append(factual_key)
            if not matches:
                mismatches.append(factual_key)
        fields[factual_key] = {
            "predicted": expected,
            "factual": actual,
            "matches": matches,
        }

    expected_base_raw = predicted.get("has_starbase")
    expected_base = expected_base_raw if isinstance(expected_base_raw, bool) else None
    actual_base = _bool(factual, "hasstarbase")
    base_matches = (
        expected_base == actual_base
        if expected_base is not None and actual_base is not None
        else None
    )
    if base_matches is not None:
        comparable.append("hasstarbase")
        if not base_matches:
            mismatches.append("hasstarbase")
    fields["hasstarbase"] = {
        "predicted": expected_base,
        "factual": actual_base,
        "matches": base_matches,
    }

    return {
        "status": (
            "not_comparable"
            if not comparable
            else ("mismatch" if mismatches else "match")
        ),
        "comparable_fields": comparable,
        "mismatches": mismatches,
        "fields": fields,
    }


def _transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
) -> dict[str, Any]:
    terminal = previous.get("terminal")
    next_start = current.get("start")
    if not isinstance(terminal, Mapping) or not isinstance(next_start, Mapping):
        return {"status": "not_comparable", "reason": "missing terminal/start"}

    result: dict[str, Any] = {
        "game_id": previous["game_id"],
        "turn": previous["turn"],
        "planet_id": previous["planet_id"],
        "from_vcr": previous["vcr_id"],
        "to_vcr": current["vcr_id"],
        "gap": int(current["vcr_id"]) - int(previous["vcr_id"]),
        "has_starbase": previous.get("has_starbase"),
    }

    if bool(terminal.get("destroyed") or terminal.get("captured")):
        result["status"] = "reappearance_after_defeat"
        return result

    terminal_shield_raw = terminal.get("shield")
    terminal_shield = (
        int(terminal_shield_raw)
        if isinstance(terminal_shield_raw, int)
        and not isinstance(terminal_shield_raw, bool)
        else None
    )
    next_shield = _int(next_start, "shield")
    shield_match = (
        terminal_shield == next_shield
        if terminal_shield is not None and next_shield is not None
        else None
    )
    result["shield_carry"] = {
        "terminal": terminal_shield,
        "next_start": next_shield,
        "matches": shield_match,
    }

    inferred = _infer_no_starbase_start(previous["start"])
    if inferred is None:
        result["exact_no_starbase"] = {"status": "not_applicable"}
        result["status"] = (
            "mismatch"
            if shield_match is False
            else ("match" if shield_match is True else "not_comparable")
        )
        return result

    start_check = _projection_check(inferred, previous["start"])
    if start_check["status"] != "match":
        result["exact_no_starbase"] = {
            "status": "start_reconstruction_mismatch",
            "start_reconstruction": start_check,
        }
        result["status"] = "mismatch" if shield_match is False else "not_comparable"
        return result

    predicted = apply_planet_carryover(inferred, inferred, terminal)
    next_check = _projection_check(predicted, next_start)
    result["exact_no_starbase"] = {
        "status": next_check["status"],
        "basis": PLANET_CARRYOVER_BASIS,
        "start_planet_defense": inferred.get("planet_defense"),
        "predicted_next_planet_defense": predicted.get("planet_defense"),
        "comparison": next_check,
    }
    if shield_match is False or next_check["status"] == "mismatch":
        result["status"] = "mismatch"
    elif shield_match is True and next_check["status"] == "match":
        result["status"] = "match"
    else:
        result["status"] = "not_comparable"
    return result


def _scope(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: Counter[str] = Counter()
    shield: Counter[str] = Counter()
    exact: Counter[str] = Counter()
    base_kind: Counter[str] = Counter()
    gaps: Counter[int] = Counter()
    mismatches: Counter[str] = Counter()

    for row in rows:
        status = str(row.get("status", "unknown"))
        statuses[status] += 1
        base = row.get("has_starbase")
        base_kind["starbase" if base is True else "no_starbase" if base is False else "unknown"] += 1
        gap = row.get("gap")
        if isinstance(gap, int) and not isinstance(gap, bool):
            gaps[gap] += 1

        shield_row = row.get("shield_carry")
        if isinstance(shield_row, Mapping):
            match = shield_row.get("matches")
            shield["match" if match is True else "mismatch" if match is False else "unknown"] += 1

        exact_row = row.get("exact_no_starbase")
        if isinstance(exact_row, Mapping):
            exact_status = str(exact_row.get("status", "unknown"))
            exact[exact_status] += 1
            comparison = exact_row.get("comparison")
            if isinstance(comparison, Mapping):
                values = comparison.get("mismatches")
                if isinstance(values, list):
                    for value in values:
                        mismatches[str(value)] += 1

    def serialize(counter: Counter[Any]) -> dict[str, int]:
        return {
            str(key): value
            for key, value in sorted(
                counter.items(),
                key=lambda item: (-item[1], str(item[0])),
            )
        }

    return {
        "transitions": len(rows),
        "status": serialize(statuses),
        "base_kind": serialize(base_kind),
        "shield_carry": serialize(shield),
        "exact_no_starbase": serialize(exact),
        "exact_mismatch_fields": serialize(mismatches),
        "vcr_gaps": serialize(gaps),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    archives = _archive_paths(args)
    summary: Counter[str] = Counter()
    summary["archives"] = len(archives)
    unique_cases: dict[tuple[int, int, int], dict[str, Any]] = {}
    payload_conflicts: set[tuple[int, int, int]] = set()
    malformed_members: list[dict[str, str]] = []
    archive_reports: list[dict[str, Any]] = []

    for archive_path in archives:
        archive_started = time.perf_counter()
        data = archive_path.read_bytes()
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        archive_game_ids: set[int] = set()
        archive_observations = 0

        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
            except ValueError as exc:
                summary["malformed_members"] += 1
                if len(malformed_members) < args.detail_limit:
                    malformed_members.append({"member": member.name, "reason": str(exc)})
                continue

            game = rst.get("game")
            game_id = _int(game, "id")
            game_turn = _int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            archive_game_ids.add(game_id)
            beams = _objects(rst, "beams")
            torpedoes = _objects(rst, "torpedos")
            settings_raw = rst.get("settings")
            settings = dict(settings_raw) if isinstance(settings_raw, Mapping) else {}

            for vcr in _objects(rst, "vcrs"):
                vcr_id = _int(vcr, "id")
                battle_turn = _int(vcr, "turn") or game_turn
                if vcr_id is None:
                    continue
                archive_observations += 1
                summary["raw_vcr_observations"] += 1
                key = (game_id, battle_turn, vcr_id)
                payload_hash = _canonical_hash(vcr)
                existing = unique_cases.get(key)
                if existing is None:
                    unique_cases[key] = {
                        "game_id": game_id,
                        "turn": battle_turn,
                        "vcr_id": vcr_id,
                        "payload": vcr,
                        "payload_hash": payload_hash,
                        "beams": beams,
                        "torpedoes": torpedoes,
                        "settings": settings,
                    }
                elif existing["payload_hash"] != payload_hash:
                    payload_conflicts.add(key)

        archive_reports.append(
            {
                "archive": archive_path.name,
                "game_ids": sorted(archive_game_ids),
                "turn_members": len(members),
                "vcr_observations": archive_observations,
                "seconds": round(time.perf_counter() - archive_started, 3),
            }
        )

    summary["unique_vcrs"] = len(unique_cases)
    summary["payload_conflicts"] = len(payload_conflicts)

    appearances: list[dict[str, Any]] = []
    replay_unsupported_reasons: Counter[str] = Counter()

    for key, case in sorted(unique_cases.items()):
        if key in payload_conflicts:
            continue
        try:
            replay = replay_nuhost_from_nu_catalog(
                case["payload"],
                beams=case["beams"],
                torpedoes=case["torpedoes"],
                settings=case["settings"],
            )
        except ReplayUnsupported as exc:
            summary["replay_unsupported"] += 1
            replay_unsupported_reasons[str(exc)] += 1
            continue

        summary["replay_supported"] += 1
        position = _position(case["payload"])
        for side_name in ("left", "right"):
            raw_side = case["payload"].get(side_name)
            terminal = replay.get(side_name)
            if not isinstance(raw_side, Mapping) or not isinstance(terminal, Mapping):
                continue
            hull_id = _int(raw_side, "hullid")
            planet_id = _int(raw_side, "objectid")
            if hull_id is None or hull_id > 0 or planet_id is None:
                continue
            appearances.append(
                {
                    "game_id": case["game_id"],
                    "turn": case["turn"],
                    "vcr_id": case["vcr_id"],
                    "planet_id": planet_id,
                    "position": position,
                    "side": side_name,
                    "has_starbase": _bool(raw_side, "hasstarbase"),
                    "start": dict(raw_side),
                    "terminal": dict(terminal),
                }
            )
            summary["planet_appearances"] += 1

    chains: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for appearance in appearances:
        chains[
            (
                int(appearance["game_id"]),
                int(appearance["turn"]),
                int(appearance["planet_id"]),
            )
        ].append(appearance)

    transitions: list[dict[str, Any]] = []
    for chain in chains.values():
        chain.sort(key=lambda item: int(item["vcr_id"]))
        if len(chain) < 2:
            continue
        summary["candidate_same_turn_planet_chains"] += 1
        for previous, current in zip(chain, chain[1:]):
            if not _same_position(previous, current):
                summary["skipped_location_change"] += 1
                continue
            transition = _transition(previous, current)
            transitions.append(transition)
            summary["same_location_transitions"] += 1
            summary[str(transition.get("status", "unknown"))] += 1

    ordinary = [row for row in transitions if row.get("game_id") != SPECIAL_GAME_ID]
    special = [row for row in transitions if row.get("game_id") == SPECIAL_GAME_ID]
    no_starbase_ordinary = [
        row for row in ordinary if row.get("has_starbase") is False
    ]
    starbase_ordinary = [
        row for row in ordinary if row.get("has_starbase") is True
    ]

    details = [
        row
        for row in transitions
        if row.get("status") not in {"match"}
    ][: args.detail_limit]

    return {
        "schema": "planets-lab.combat-planet-chain-audit.v1",
        "read_only": True,
        "evidence_boundary": (
            "Independent differential: replay terminal planet state from factual VCR N "
            "versus factual start state of the same planet in its next same-turn "
            "same-location VCR. Exact DP reconstruction is attempted only when "
            "hasstarbase is explicitly false and the inferred first engagement "
            "reproduces the factual VCR start."
        ),
        "summary": dict(summary),
        "scopes": {
            "ordinary_all": _scope(ordinary),
            "ordinary_no_starbase": _scope(no_starbase_ordinary),
            "ordinary_starbase": _scope(starbase_ordinary),
            "game_591478": _scope(special),
        },
        "replay_unsupported_reasons": dict(sorted(replay_unsupported_reasons.items())),
        "archives": archive_reports,
        "details": details,
        "malformed_member_samples": malformed_members,
        "seconds": round(time.perf_counter() - started, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only differential audit for repeated planetary VCRs."
    )
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--archive", action="append", default=[])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--detail-limit", type=int, default=100)
    return parser.parse_args()


def _print_scope(name: str, scope: Mapping[str, Any]) -> None:
    print(f"===== {name} =====")
    for key in (
        "transitions",
        "status",
        "base_kind",
        "shield_carry",
        "exact_no_starbase",
        "exact_mismatch_fields",
        "vcr_gaps",
    ):
        print(f"{key}: {scope.get(key)}")


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print("===== PLANET COMBAT CHAIN DIFFERENTIAL AUDIT =====")
    print(f"summary: {report['summary']}")
    print(f"replay_unsupported_reasons: {report['replay_unsupported_reasons']}")
    for name, scope in report["scopes"].items():
        print()
        _print_scope(name, scope)
    print()
    print(f"detail_rows: {len(report['details'])}")
    print(f"seconds: {report['seconds']}")
    if args.output is not None:
        print(f"output: {args.output}")
    print("NOTE: exact no-starbase DP carry is an independent next-VCR differential; starbase hidden persistent state remains fail-closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
