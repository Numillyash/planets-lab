from __future__ import annotations

import argparse
import json
from collections import Counter
from math import isqrt
from pathlib import Path
from typing import Any, Mapping

import combat_planet_chain_audit as planet_audit
import combat_ship_chain_audit as ship_audit
from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.rules.combat import planet_native_beam_tech


DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
SPECIAL_GAME_ID = 591478


def _old_intel_federation_shield(shield: int, damage: int) -> int:
    """Current planets-intel candidate: recover 25% of missing shields."""

    shield = max(0, min(100, int(shield)))
    damage = max(0, int(damage))
    loss = 100 - shield
    recovered = (loss + 2) // 4
    return min(max(0, 100 - damage), shield + recovered)


def _old_intel_planet_beam_tech(defense: int) -> int:
    """Current planets-intel candidate: truncating sqrt(DP / 2)."""

    dp = max(0, int(defense))
    if dp <= 0:
        return 0
    return max(1, min(10, isqrt(dp // 2)))


def _federation_recheck(archive_dir: Path) -> dict[str, Any]:
    args = argparse.Namespace(
        archive_dir=archive_dir,
        archive=[],
        output=None,
        detail_limit=100_000,
        sample_limit=100_000,
    )
    report = ship_audit.run(args)

    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for transition in report.get("race1_samples", []):
        if not isinstance(transition, Mapping):
            continue
        comparison = transition.get("comparison")
        if not isinstance(comparison, Mapping):
            continue
        shield_row = comparison.get("shield")
        carry = comparison.get("carry")
        if not isinstance(shield_row, Mapping) or not isinstance(carry, Mapping):
            continue
        damage_row = carry.get("damage")
        if not isinstance(damage_row, Mapping):
            continue

        terminal = shield_row.get("terminal")
        actual = shield_row.get("next_start")
        corrected = shield_row.get("federation_candidate")
        damage = damage_row.get("terminal")
        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (terminal, actual, corrected, damage)
        ):
            counts["not_comparable"] += 1
            continue

        old = _old_intel_federation_shield(terminal, damage)
        counts["comparable"] += 1
        counts["corrected_exact" if corrected == actual else "corrected_mismatch"] += 1
        counts["old_intel_exact" if old == actual else "old_intel_mismatch"] += 1

        if corrected != terminal and corrected == actual:
            counts["observed_recovery_rows"] += 1
        if corrected == actual and old != actual:
            counts["corrected_only_discriminator"] += 1
            if len(examples) < 20:
                examples.append(
                    {
                        "game_id": transition.get("game_id"),
                        "turn": transition.get("turn"),
                        "ship_id": transition.get("ship_id"),
                        "from_vcr": transition.get("from_vcr"),
                        "to_vcr": transition.get("to_vcr"),
                        "terminal_shield": terminal,
                        "terminal_damage": damage,
                        "factual_next_shield": actual,
                        "old_intel_prediction": old,
                        "corrected_prediction": corrected,
                    }
                )
        if old == actual and corrected != actual:
            counts["old_only_discriminator"] += 1

    return {
        "ship_audit_summary": report.get("summary", {}),
        "ship_audit_shield_models": report.get("shield_models", {}),
        "counts": dict(counts),
        "corrected_only_examples": examples,
    }


def _unique_vcrs(archive_dir: Path) -> tuple[dict[tuple[int, int, int], dict[str, Any]], set[tuple[int, int, int]]]:
    unique: dict[tuple[int, int, int], dict[str, Any]] = {}
    conflicts: set[tuple[int, int, int]] = set()

    for archive_path in sorted(archive_dir.glob("game-*.zip")):
        data = archive_path.read_bytes()
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        for member in members:
            rst = planet_audit._decode_turn(raw_members[member.name], member.name)
            game = rst.get("game")
            game_id = planet_audit._int(game, "id")
            game_turn = planet_audit._int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            for vcr in planet_audit._objects(rst, "vcrs"):
                vcr_id = planet_audit._int(vcr, "id")
                battle_turn = planet_audit._int(vcr, "turn") or game_turn
                if vcr_id is None:
                    continue
                key = (game_id, battle_turn, vcr_id)
                payload_hash = planet_audit._canonical_hash(vcr)
                current = unique.get(key)
                if current is None:
                    unique[key] = {
                        "payload": dict(vcr),
                        "payload_hash": payload_hash,
                    }
                elif current["payload_hash"] != payload_hash:
                    conflicts.add(key)
    return unique, conflicts


def _planet_beam_recheck(archive_dir: Path) -> dict[str, Any]:
    unique, conflicts = _unique_vcrs(archive_dir)
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    counts["unique_vcrs"] = len(unique)
    counts["payload_conflicts"] = len(conflicts)

    for (game_id, turn, vcr_id), case in sorted(unique.items()):
        if (game_id, turn, vcr_id) in conflicts or game_id == SPECIAL_GAME_ID:
            continue
        payload = case["payload"]
        for side_name in ("left", "right"):
            side = payload.get(side_name)
            if not isinstance(side, Mapping):
                continue
            hull_id = planet_audit._int(side, "hullid")
            has_starbase = planet_audit._bool(side, "hasstarbase")
            beam_count = planet_audit._int(side, "beamcount")
            factual_beam_id = planet_audit._int(side, "beamid")
            mass = planet_audit._int(side, "mass")
            planet_id = planet_audit._int(side, "objectid")
            if (
                hull_id is None
                or hull_id > 0
                or has_starbase is not False
                or beam_count is None
                or beam_count <= 0
                or factual_beam_id is None
                or mass is None
                or mass < 100
            ):
                continue

            defense = mass - 100
            old = _old_intel_planet_beam_tech(defense)
            corrected = planet_native_beam_tech(defense)
            counts["comparable"] += 1
            counts["corrected_exact" if corrected == factual_beam_id else "corrected_mismatch"] += 1
            counts["old_intel_exact" if old == factual_beam_id else "old_intel_mismatch"] += 1

            if corrected == factual_beam_id and old != factual_beam_id:
                counts["corrected_only_discriminator"] += 1
                if len(examples) < 20:
                    examples.append(
                        {
                            "game_id": game_id,
                            "turn": turn,
                            "vcr_id": vcr_id,
                            "side": side_name,
                            "planet_id": planet_id,
                            "defense_posts": defense,
                            "factual_beam_id": factual_beam_id,
                            "old_intel_prediction": old,
                            "corrected_prediction": corrected,
                        }
                    )
            if old == factual_beam_id and corrected != factual_beam_id:
                counts["old_only_discriminator"] += 1

    return {
        "counts": dict(counts),
        "corrected_only_examples": examples,
    }


def run(archive_dir: Path) -> dict[str, Any]:
    archives = sorted(archive_dir.glob("game-*.zip"))
    if not archives:
        raise ValueError(f"no cached loadall archives under {archive_dir}")

    federation = _federation_recheck(archive_dir)
    planet_beam = _planet_beam_recheck(archive_dir)

    fed_counts = federation["counts"]
    beam_counts = planet_beam["counts"]

    assertions = {
        "federation_corrected_has_no_mismatch": fed_counts.get("corrected_mismatch", 0) == 0,
        "federation_old_intel_is_discriminated": fed_counts.get("corrected_only_discriminator", 0) > 0,
        "federation_no_old_only_counterexample": fed_counts.get("old_only_discriminator", 0) == 0,
        "planet_beam_corrected_has_no_mismatch": beam_counts.get("corrected_mismatch", 0) == 0,
        "planet_beam_old_intel_is_discriminated": beam_counts.get("corrected_only_discriminator", 0) > 0,
        "planet_beam_no_old_only_counterexample": beam_counts.get("old_only_discriminator", 0) == 0,
    }

    return {
        "archive_dir": str(archive_dir),
        "archives": len(archives),
        "scope": "ordinary cached loadall corpus; game 591478 excluded from planet-beam promotion",
        "federation_shield_recovery": federation,
        "planet_native_beam_tech": planet_beam,
        "assertions": assertions,
        "all_assertions_pass": all(assertions.values()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recheck two planets-intel combat formulas against the immutable cached "
            "historical loadall corpus: Federation between-fight shield recovery and "
            "native no-starbase planet beam tech."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args.archive_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0 if report["all_assertions_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
