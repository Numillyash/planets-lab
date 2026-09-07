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
    combat_rng_from_settings,
    replay_nuhost_from_nu_catalog,
)


DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")


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


def _object_list(rst: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = rst.get(key)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _safe_side(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"present": False}
    hull_id = _int(raw, "hullid")
    return {
        "present": True,
        "object_id": _int(raw, "objectid"),
        "hull_id": hull_id,
        "race_id": _int(raw, "raceid"),
        "kind": "planet" if hull_id is not None and hull_id <= 0 else "ship",
        "beam_count": _int(raw, "beamcount"),
        "launcher_count": _int(raw, "launchercount"),
        "bay_count": _int(raw, "baycount"),
        "damage": _int(raw, "damage"),
        "shield": _int(raw, "shield"),
    }


def _safe_case(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "seed": _int(payload, "seed"),
        "battle_type": _int(payload, "battletype"),
        "left": _safe_side(payload.get("left")),
        "right": _safe_side(payload.get("right")),
    }


def _replay_signature(replay: Mapping[str, Any]) -> dict[str, Any]:
    def side(name: str) -> dict[str, Any]:
        raw = replay.get(name)
        if not isinstance(raw, Mapping):
            return {}
        return {
            key: raw.get(key)
            for key in (
                "shield",
                "damage",
                "crew",
                "torpedoes",
                "fighters",
                "destroyed",
                "captured",
                "survived",
            )
        }

    return {
        "cycles": replay.get("cycles"),
        "final_seed": replay.get("final_seed"),
        "result": replay.get("result"),
        "left": side("left"),
        "right": side("right"),
    }


def _load_settings_manifest(path: Path | None) -> dict[int, dict[str, Any]]:
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("settings manifest must be a JSON object keyed by game id")

    result: dict[int, dict[str, Any]] = {}
    for raw_game_id, raw_settings in raw.items():
        try:
            game_id = int(raw_game_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid settings manifest game id: {raw_game_id!r}") from exc

        if isinstance(raw_settings, bool):
            raise ValueError(f"game {game_id}: settings entry cannot be boolean")
        if isinstance(raw_settings, int):
            settings: dict[str, Any] = {"combatrng": raw_settings}
        elif isinstance(raw_settings, Mapping):
            settings = dict(raw_settings)
        else:
            raise ValueError(
                f"game {game_id}: settings entry must be integer or object"
            )
        result[game_id] = settings
    return result


def _resolve_settings(
    *,
    game_id: int,
    raw_settings: Mapping[str, Any] | None,
    manifest: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str, str | None]:
    factual = dict(raw_settings) if isinstance(raw_settings, Mapping) else {}
    factual_rng = combat_rng_from_settings(factual)
    manifest_settings = dict(manifest.get(game_id, {}))
    manifest_rng = combat_rng_from_settings(manifest_settings)

    if factual_rng is not None and manifest_rng is not None and factual_rng != manifest_rng:
        return None, "conflict", (
            f"raw combatrng={factual_rng} conflicts with manifest combatrng={manifest_rng}"
        )
    if factual_rng is not None:
        return factual, "raw_rst", None
    if manifest_rng is not None:
        return manifest_settings, "manifest", None
    return None, "missing", "combatrng unavailable"


def _archive_paths(args: argparse.Namespace) -> list[Path]:
    explicit = [Path(value) for value in args.archive]
    if explicit:
        paths = explicit
    else:
        paths = sorted(Path(args.archive_dir).glob("game-*.zip"))
    if not paths:
        raise ValueError("no loadall archives found")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"archive paths do not exist: {missing}")
    return paths


def _shape(payload: Mapping[str, Any]) -> str:
    left = _safe_side(payload.get("left"))
    right = _safe_side(payload.get("right"))
    return f"{left.get('kind', 'missing')}_vs_{right.get('kind', 'missing')}"


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    settings_manifest = _load_settings_manifest(args.settings_manifest)
    archives = _archive_paths(args)

    observations: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    archive_reports: list[dict[str, Any]] = []
    malformed_members: list[dict[str, Any]] = []
    settings_sources: Counter[str] = Counter()

    for archive_path in archives:
        archive_started = time.perf_counter()
        data = archive_path.read_bytes()
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        archive_game_ids: set[int] = set()
        archive_vcr_observations = 0

        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
                game = rst.get("game")
                game_id = _int(game, "id")
                embedded_turn = _int(game, "turn")
                if game_id is None or embedded_turn is None:
                    raise ValueError(f"{member.name}: game id/turn unavailable")
                archive_game_ids.add(game_id)

                beams = _object_list(rst, "beams")
                torpedoes = _object_list(rst, "torpedos")
                raw_settings = rst.get("settings")
                settings, settings_source, settings_error = _resolve_settings(
                    game_id=game_id,
                    raw_settings=raw_settings if isinstance(raw_settings, Mapping) else None,
                    manifest=settings_manifest,
                )
                settings_sources[settings_source] += 1

                for vcr in _object_list(rst, "vcrs"):
                    vcr_id = _int(vcr, "id")
                    if vcr_id is None:
                        continue
                    battle_turn = _int(vcr, "turn")
                    if battle_turn is None:
                        battle_turn = embedded_turn
                    key = (game_id, battle_turn, vcr_id)
                    observations[key].append(
                        {
                            "member": member.name,
                            "archive_turn": member.turn,
                            "player": member.player,
                            "payload": vcr,
                            "payload_hash": _canonical_hash(vcr),
                            "beams": beams,
                            "torpedoes": torpedoes,
                            "settings": settings,
                            "settings_source": settings_source,
                            "settings_error": settings_error,
                        }
                    )
                    archive_vcr_observations += 1
            except (ValueError, TypeError) as exc:
                if len(malformed_members) < args.detail_limit:
                    malformed_members.append(
                        {"archive": archive_path.name, "member": member.name, "reason": str(exc)}
                    )

        archive_reports.append(
            {
                "archive": archive_path.name,
                "game_ids": sorted(archive_game_ids),
                "turn_members": len(members),
                "vcr_observations": archive_vcr_observations,
                "seconds": round(time.perf_counter() - archive_started, 3),
            }
        )

    summary: Counter[str] = Counter()
    summary["archives"] = len(archives)
    summary["unique_vcrs"] = len(observations)
    summary["raw_vcr_observations"] = sum(len(rows) for rows in observations.values())
    unsupported_reasons: Counter[str] = Counter()
    shapes: Counter[str] = Counter()
    by_game: dict[str, Counter[str]] = defaultdict(Counter)
    details: list[dict[str, Any]] = []

    for key in sorted(observations):
        game_id, battle_turn, vcr_id = key
        rows = observations[key]
        game = by_game[str(game_id)]
        game["unique_vcrs"] += 1
        game["raw_observations"] += len(rows)

        payload_hashes = sorted({row["payload_hash"] for row in rows})
        representative = rows[0]["payload"]
        shapes[_shape(representative)] += 1

        case: dict[str, Any] = {
            "game_id": game_id,
            "turn": battle_turn,
            "vcr_id": vcr_id,
            "observations": len(rows),
            "payload_variants": len(payload_hashes),
            "profile": _safe_case(representative),
        }

        if len(payload_hashes) != 1:
            summary["payload_conflicts"] += 1
            game["payload_conflicts"] += 1
            case["status"] = "payload_conflict"
            if len(details) < args.detail_limit:
                details.append(case)
            continue

        successful: dict[str, dict[str, Any]] = {}
        reasons: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        for row in rows:
            source_counts[row["settings_source"]] += 1
            if row["settings"] is None:
                reason = row["settings_error"] or "combat settings unavailable"
                reasons[reason] += 1
                continue
            try:
                replay = replay_nuhost_from_nu_catalog(
                    row["payload"],
                    beams=row["beams"],
                    torpedoes=row["torpedoes"],
                    settings=row["settings"],
                )
            except ReplayUnsupported as exc:
                reasons[str(exc)] += 1
                continue
            signature = _replay_signature(replay)
            successful[_canonical_hash(signature)] = signature

        case["settings_sources"] = dict(sorted(source_counts.items()))
        if len(successful) > 1:
            summary["replay_result_conflicts"] += 1
            game["replay_result_conflicts"] += 1
            case["status"] = "replay_result_conflict"
            case["result_variants"] = len(successful)
            if len(details) < args.detail_limit:
                details.append(case)
            continue

        if successful:
            summary["replay_supported"] += 1
            game["replay_supported"] += 1
            case["status"] = "supported"
            case["replay"] = next(iter(successful.values()))
            if reasons:
                summary["partially_supported"] += 1
                game["partially_supported"] += 1
                case["observation_failures"] = dict(sorted(reasons.items()))
            if args.include_supported and len(details) < args.detail_limit:
                details.append(case)
            continue

        summary["replay_unsupported"] += 1
        game["replay_unsupported"] += 1
        case["status"] = "unsupported"
        case["reasons"] = dict(sorted(reasons.items())) or {"unknown": len(rows)}
        for reason, count in reasons.items():
            unsupported_reasons[reason] += count
        if len(details) < args.detail_limit:
            details.append(case)

    summary["replay_accounted"] = (
        summary["replay_supported"]
        + summary["replay_unsupported"]
        + summary["payload_conflicts"]
        + summary["replay_result_conflicts"]
    )
    summary["malformed_members"] = len(malformed_members)

    elapsed = time.perf_counter() - started
    return {
        "schema": "planets-lab.combat-classic-corpus-parity-audit.v1",
        "read_only": True,
        "evidence_boundary": (
            "Replay support and deterministic agreement across duplicate factual VCR payloads; "
            "not proof of factual terminal-state correctness unless an independent post-combat "
            "observation is supplied."
        ),
        "summary": dict(summary),
        "settings_sources_per_turn_member": dict(sorted(settings_sources.items())),
        "unsupported_reasons": dict(sorted(unsupported_reasons.items())),
        "battle_shapes": dict(sorted(shapes.items())),
        "games": {key: dict(value) for key, value in sorted(by_game.items(), key=lambda item: int(item[0]))},
        "archives": archive_reports,
        "malformed_member_samples": malformed_members,
        "details": details,
        "seconds": round(elapsed, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Classic combat replay coverage audit over cached loadall archives."
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=DEFAULT_ARCHIVE_DIR,
        help="Directory containing game-<id>.zip loadall archives.",
    )
    parser.add_argument(
        "--archive",
        action="append",
        default=[],
        help="Explicit archive path; repeat to override --archive-dir discovery.",
    )
    parser.add_argument(
        "--settings-manifest",
        type=Path,
        default=None,
        help=(
            "Optional JSON object keyed by game id. Each value may be a settings object "
            "or an integer combatrng. Raw RST combatrng wins unless it conflicts."
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--detail-limit", type=int, default=100)
    parser.add_argument("--include-supported", action="store_true")
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
    print("===== CLASSIC COMBAT CORPUS PARITY AUDIT =====")
    for key in (
        "archives",
        "raw_vcr_observations",
        "unique_vcrs",
        "replay_supported",
        "replay_unsupported",
        "payload_conflicts",
        "replay_result_conflicts",
        "partially_supported",
        "replay_accounted",
        "malformed_members",
    ):
        print(f"{key}: {summary.get(key, 0)}")
    print(f"settings_sources_per_turn_member: {report['settings_sources_per_turn_member']}")
    print(f"unsupported_reasons: {report['unsupported_reasons']}")
    print(f"battle_shapes: {report['battle_shapes']}")
    print("games:")
    for game_id, values in report["games"].items():
        print(f"  {game_id}: {values}")
    print("archives:")
    for archive in report["archives"]:
        print(f"  {archive}")
    print(f"seconds: {report['seconds']}")
    if args.output is not None:
        print(f"output: {args.output}")
    print("NOTE: supported replay is deterministic derived evidence, not factual terminal-state proof.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
