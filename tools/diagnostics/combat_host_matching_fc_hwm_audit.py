from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.eligibility import MATCHING_SHIP_FC_COMBAT_EXCEPTIONS
from planets_lab.rules.combat.order import BIRD_RACE_ID

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _int,
    _owner_raw,
    _ship_side,
)

DEFAULT_EXAMPLE_LIMIT = 40


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _matching_fc_kind(left_fc: Any, right_fc: Any) -> str:
    if not isinstance(left_fc, str) or not isinstance(right_fc, str):
        return "missing_or_non_string"
    if left_fc != right_fc:
        return "not_matching"
    if left_fc.casefold() in MATCHING_SHIP_FC_COMBAT_EXCEPTIONS:
        return "documented_ship_exception"
    return "ordinary_exact_match"


def _site_position(site_vcr_ids: Sequence[int], vcr_id: int) -> dict[str, Any]:
    ordered = sorted(int(value) for value in site_vcr_ids)
    index = ordered.index(vcr_id)
    return {
        "site_ship_vcr_ids": ordered,
        "site_ship_vcr_count": len(ordered),
        "site_ship_vcr_index": index + 1,
        "site_first_ship_vcr": index == 0,
        "site_prior_ship_vcr_count": index,
    }


def _hwm_observation(
    *,
    matching_fc_kind: str,
    left_race_id: int | None,
    right_race_id: int | None,
    left_start_shield: int | None,
    right_start_shield: int | None,
    site_first_ship_vcr: bool,
) -> str:
    if matching_fc_kind == "documented_ship_exception":
        return "documented_ship_fc_exception"
    if matching_fc_kind != "ordinary_exact_match":
        return "not_applicable"

    left_bird = left_race_id == BIRD_RACE_ID
    right_bird = right_race_id == BIRD_RACE_ID
    if left_bird and right_bird:
        return "both_bird_ambiguous"
    if not left_bird and not right_bird:
        return "nonbird_nonexception_matching_vcr"

    opponent_shield = right_start_shield if left_bird else left_start_shield
    if opponent_shield is None:
        return "bird_enemy_shield_unknown"
    if opponent_shield == 0 and site_first_ship_vcr:
        return "bird_enemy_unshielded_first_site"
    if opponent_shield == 0:
        return "bird_enemy_unshielded_after_prior_site_vcr"
    return "bird_enemy_shielded"


def _safe_side(
    *,
    ship_id: int,
    owner_id: int,
    race_id: int | None,
    hull_id: int,
    raw: Mapping[str, Any],
    start_shield: int | None,
) -> dict[str, Any]:
    fc = raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendly_code": fc,
        "neutronium": _intish(raw.get("neutronium")),
        "damage": _intish(raw.get("damage")),
        "start_shield": start_shield,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    payload_conflicts = 0
    archives_considered = 0

    for archive_path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            archive_game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        archives_considered += 1
        special_game = archive_game_id == SPECIAL_GAME_ID

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _ = _player_races(prepared.snapshots)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        site_ship_vcrs: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
        for (game_id, battle_turn, vcr_id), (_digest, vcr) in seen.items():
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue
            site_ship_vcrs[(game_id, battle_turn, x, y)].append(vcr_id)

        for (game_id, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue

            before_turn = battle_turn - 1
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)
            if left_raw is None or right_raw is None or left_owner is None or right_owner is None:
                continue
            if left_owner != left["owner_id"] or right_owner != right["owner_id"]:
                continue

            left_fc = left_raw.get("friendlycode")
            right_fc = right_raw.get("friendlycode")
            kind = _matching_fc_kind(left_fc, right_fc)
            if kind not in {"documented_ship_exception", "ordinary_exact_match"}:
                continue

            left_vcr = vcr.get("left")
            right_vcr = vcr.get("right")
            if not isinstance(left_vcr, Mapping) or not isinstance(right_vcr, Mapping):
                continue
            left_shield = _int(left_vcr, "shield")
            right_shield = _int(right_vcr, "shield")

            site = _site_position(site_ship_vcrs[(game_id, battle_turn, x, y)], vcr_id)
            left_race = races.get(left_owner)
            right_race = races.get(right_owner)
            observation = _hwm_observation(
                matching_fc_kind=kind,
                left_race_id=left_race,
                right_race_id=right_race,
                left_start_shield=left_shield,
                right_start_shield=right_shield,
                site_first_ship_vcr=bool(site["site_first_ship_vcr"]),
            )

            rows.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "vcr_id": vcr_id,
                    "x": x,
                    "y": y,
                    "special_game_591478": special_game,
                    "matching_fc_kind": kind,
                    "matching_friendly_code": left_fc if isinstance(left_fc, str) else None,
                    "hwm_observation": observation,
                    "left": _safe_side(
                        ship_id=left_id,
                        owner_id=left_owner,
                        race_id=left_race,
                        hull_id=int(left["hull_id"]),
                        raw=left_raw,
                        start_shield=left_shield,
                    ),
                    "right": _safe_side(
                        ship_id=right_id,
                        owner_id=right_owner,
                        race_id=right_race,
                        hull_id=int(right["hull_id"]),
                        raw=right_raw,
                        start_shield=right_shield,
                    ),
                    **site,
                }
            )

    ordinary = [row for row in rows if not row["special_game_591478"]]
    special = [row for row in rows if row["special_game_591478"]]

    def scope_summary(scope_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "rows": len(scope_rows),
            "matching_fc_kind": _serialize(Counter(row["matching_fc_kind"] for row in scope_rows)),
            "hwm_observation": _serialize(Counter(row["hwm_observation"] for row in scope_rows)),
            "matching_friendly_code": _serialize(Counter(row["matching_friendly_code"] for row in scope_rows)),
            "site_first_ship_vcr": _serialize(Counter(str(row["site_first_ship_vcr"]) for row in scope_rows)),
            "games": _serialize(Counter(row["game_id"] for row in scope_rows)),
        }

    hwm_candidates = [
        row
        for row in rows
        if row["matching_fc_kind"] == "ordinary_exact_match"
        and row["hwm_observation"].startswith("bird_enemy_")
    ]
    return {
        "schema": "planets-lab.combat-host-matching-fc-hwm-audit.v1",
        "read_only": True,
        "summary": {
            "archives_considered": archives_considered,
            "payload_conflicts": payload_conflicts,
            "matching_fc_vcr_rows": len(rows),
            "ordinary": scope_summary(ordinary),
            "special_591478": scope_summary(special),
            "hwm_candidate_rows": len(hwm_candidates),
            "hwm_unshielded_first_site_rows": sum(
                int(row["hwm_observation"] == "bird_enemy_unshielded_first_site")
                for row in hwm_candidates
            ),
        },
        "hwm_candidates": hwm_candidates[: args.example_limit],
        "examples": rows[: args.example_limit],
        "evidence_boundary": (
            "Factual ship-vs-ship VCR audit for exact matching Friendly Codes. MKT/NTP/LFM are documented ship-combat "
            "exceptions. Non-special Bird matching-FC VCRs are only HWM candidates; the strongest factual HWM signature "
            "is an opponent starting at shield=0 in the first ship VCR at that site. No effective Campaign advantage "
            "state is invented. Game 591478 is reported separately and never tunes ordinary mechanics."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit factual matching-FC ship combat and Harmonic Weapon Modulation signatures."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT MATCHING FC / HWM AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("HWM CANDIDATES:")
    for row in report["hwm_candidates"]:
        print(row)
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: positive factual matching-FC audit; absence of VCR is not used as suppression evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
