from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
from planets_lab.rules.combat.order import (
    EVIL_EMPIRE_RACE_ID,
    GORBIE_HULL_ID,
)

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs, _standard_relation
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _int,
    _owner_raw,
    _ship_side,
)

TARGET_CASE = (621896, 28, 67)
DEFAULT_EXAMPLE_LIMIT = 40
GAME_CONTEXT_FIELDS = (
    "type",
    "gametype",
    "scenarioid",
    "campaignmode",
    "isacademy",
    "isprivate",
)


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _mechanics_game_context(snapshots: Sequence[Any]) -> dict[str, list[Any]]:
    values: dict[str, set[Any]] = {key: set() for key in GAME_CONTEXT_FIELDS}
    for snapshot in snapshots:
        game = snapshot.mechanics_payload.get("game")
        if not isinstance(game, Mapping):
            continue
        for key in GAME_CONTEXT_FIELDS:
            value = game.get(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                if value is not None:
                    values[key].add(value)
    return {
        key: sorted(field_values, key=lambda value: (type(value).__name__, str(value)))
        for key, field_values in values.items()
        if field_values
    }


def _player_activeadvantages(snapshots: Sequence[Any], player_id: int) -> list[Any]:
    values: dict[str, Any] = {}
    for snapshot in snapshots:
        players = snapshot.mechanics_payload.get("players")
        if not isinstance(players, list):
            continue
        for raw in players:
            if not isinstance(raw, Mapping) or _intish(raw.get("id")) != player_id:
                continue
            value = raw.get("activeadvantages")
            if isinstance(value, (str, int, float, bool)):
                values[json.dumps(value, sort_keys=True)] = value
            elif isinstance(value, list):
                normalized = [item for item in value if isinstance(item, (str, int, float, bool))]
                if len(normalized) == len(value):
                    values[json.dumps(normalized, sort_keys=True)] = normalized
    return [values[key] for key in sorted(values)]


def _documented_side_observation(
    *,
    owner_race_id: int | None,
    hull_id: int,
    factual_side: str,
    dual_empire_gorbie: bool,
) -> str:
    if hull_id != GORBIE_HULL_ID or owner_race_id != EVIL_EMPIRE_RACE_ID:
        return "not_applicable"
    if dual_empire_gorbie:
        return "dual_empire_gorbie_ambiguous"
    if factual_side == "left":
        return "empire_gorbie_left_observed"
    if factual_side == "right":
        return "empire_gorbie_right_requires_advantage_context"
    raise ValueError(f"unexpected factual side: {factual_side}")


def _forced_left_override_needed(*, factual_side: str, standard_relation: str | None) -> bool | None:
    """Whether factual LEFT placement requires overriding standard priority.

    For a Gorbie factually on the right, Galactic Power did not produce the
    observed side and therefore cannot be the explanation for that row.
    """

    if standard_relation is None or standard_relation == "unsupported":
        return None
    if factual_side not in {"left", "right"}:
        raise ValueError(f"unexpected factual side: {factual_side}")
    if factual_side != "left":
        return False
    return standard_relation == "left_higher_priority"


def _safe_order(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    fc = raw.get("friendlycode")
    return {
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendlycode": fc if isinstance(fc, str) else None,
        "damage": _intish(raw.get("damage")),
        "neutronium": _intish(raw.get("neutronium")),
    }


def _gorbie_row(
    *,
    game_id: int,
    battle_turn: int,
    vcr_id: int,
    x: int,
    y: int,
    side: str,
    ship_id: int,
    owner_id: int | None,
    owner_race_id: int | None,
    hull_id: int,
    opponent_side: str,
    opponent_ship_id: int,
    opponent_owner_id: int | None,
    opponent_race_id: int | None,
    opponent_hull_id: int,
    raw: Mapping[str, Any] | None,
    opponent_raw: Mapping[str, Any] | None,
    standard_relation: str | None,
    dual_empire_gorbie: bool,
    game_context: Mapping[str, Any],
    activeadvantages: Sequence[Any],
) -> dict[str, Any]:
    empire_owned = owner_race_id == EVIL_EMPIRE_RACE_ID
    return {
        "game_id": game_id,
        "battle_turn": battle_turn,
        "vcr_id": vcr_id,
        "x": x,
        "y": y,
        "target_case": (game_id, battle_turn, vcr_id) == TARGET_CASE and ship_id == 62,
        "ship_id": ship_id,
        "owner_id": owner_id,
        "owner_race_id": owner_race_id,
        "hull_id": hull_id,
        "factual_side": side,
        "empire_owned": empire_owned,
        "dual_empire_gorbie": dual_empire_gorbie,
        "documented_side_observation": _documented_side_observation(
            owner_race_id=owner_race_id,
            hull_id=hull_id,
            factual_side=side,
            dual_empire_gorbie=dual_empire_gorbie,
        ),
        "standard_relation": standard_relation,
        "forced_left_override_needed": (
            _forced_left_override_needed(factual_side=side, standard_relation=standard_relation)
            if empire_owned and not dual_empire_gorbie
            else None
        ),
        "order": _safe_order(raw),
        "opponent": {
            "side": opponent_side,
            "ship_id": opponent_ship_id,
            "owner_id": opponent_owner_id,
            "owner_race_id": opponent_race_id,
            "hull_id": opponent_hull_id,
            "order": _safe_order(opponent_raw),
        },
        "game_context": dict(game_context),
        "owner_activeadvantages_observed": list(activeadvantages),
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
        if archive_game_id == SPECIAL_GAME_ID:
            continue
        archives_considered += 1

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _race_conflicts = _player_races(prepared.snapshots)
        game_context = _mechanics_game_context(prepared.snapshots)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        for (game_id, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            if left is None or right is None:
                continue
            if int(left["hull_id"]) != GORBIE_HULL_ID and int(right["hull_id"]) != GORBIE_HULL_ID:
                continue

            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if x is None or y is None:
                continue

            before_turn = battle_turn - 1
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)

            # VCR owner IDs remain the factual identity fallback. T-1 owner-current
            # rows are used only when they align with that factual side.
            if left_owner != left["owner_id"]:
                left_raw = None
                left_owner = left["owner_id"]
            if right_owner != right["owner_id"]:
                right_raw = None
                right_owner = right["owner_id"]

            left_race = races.get(left_owner) if left_owner is not None else None
            right_race = races.get(right_owner) if right_owner is not None else None
            left_empire_gorbie = int(left["hull_id"]) == GORBIE_HULL_ID and left_race == EVIL_EMPIRE_RACE_ID
            right_empire_gorbie = int(right["hull_id"]) == GORBIE_HULL_ID and right_race == EVIL_EMPIRE_RACE_ID
            dual_empire_gorbie = left_empire_gorbie and right_empire_gorbie

            standard_relation: str | None = None
            if left_raw is not None and right_raw is not None:
                standard_relation = _standard_relation(
                    left_raw=left_raw,
                    right_raw=right_raw,
                    left_ship_id=left_id,
                    right_ship_id=right_id,
                )

            side_specs = (
                (
                    "left",
                    left,
                    left_owner,
                    left_race,
                    left_raw,
                    "right",
                    right,
                    right_owner,
                    right_race,
                    right_raw,
                ),
                (
                    "right",
                    right,
                    right_owner,
                    right_race,
                    right_raw,
                    "left",
                    left,
                    left_owner,
                    left_race,
                    left_raw,
                ),
            )
            for (
                side,
                ship,
                owner_id,
                owner_race_id,
                raw,
                opponent_side,
                opponent,
                opponent_owner_id,
                opponent_race_id,
                opponent_raw,
            ) in side_specs:
                if int(ship["hull_id"]) != GORBIE_HULL_ID:
                    continue
                rows.append(
                    _gorbie_row(
                        game_id=game_id,
                        battle_turn=battle_turn,
                        vcr_id=vcr_id,
                        x=x,
                        y=y,
                        side=side,
                        ship_id=int(ship["ship_id"]),
                        owner_id=owner_id,
                        owner_race_id=owner_race_id,
                        hull_id=int(ship["hull_id"]),
                        opponent_side=opponent_side,
                        opponent_ship_id=int(opponent["ship_id"]),
                        opponent_owner_id=opponent_owner_id,
                        opponent_race_id=opponent_race_id,
                        opponent_hull_id=int(opponent["hull_id"]),
                        raw=raw,
                        opponent_raw=opponent_raw,
                        standard_relation=standard_relation,
                        dual_empire_gorbie=dual_empire_gorbie,
                        game_context=game_context,
                        activeadvantages=(
                            _player_activeadvantages(prepared.snapshots, owner_id)
                            if owner_id is not None
                            else []
                        ),
                    )
                )

    empire_rows = [row for row in rows if row["empire_owned"]]
    nonempire_rows = [row for row in rows if not row["empire_owned"]]
    single_empire_rows = [row for row in empire_rows if not row["dual_empire_gorbie"]]
    target_rows = [row for row in rows if row["target_case"]]

    summary = {
        "archives_considered": archives_considered,
        "payload_conflicts": payload_conflicts,
        "gorbie_appearances": len(rows),
        "empire_gorbie_appearances": len(empire_rows),
        "nonempire_gorbie_appearances": len(nonempire_rows),
        "dual_empire_gorbie_appearances": sum(int(row["dual_empire_gorbie"]) for row in rows),
        "target_case_rows": len(target_rows),
        "empire_gorbie_side": _serialize(Counter(row["factual_side"] for row in single_empire_rows)),
        "empire_gorbie_observation": _serialize(
            Counter(row["documented_side_observation"] for row in empire_rows)
        ),
        "nonempire_gorbie_side": _serialize(Counter(row["factual_side"] for row in nonempire_rows)),
        "empire_gorbie_standard_relation": _serialize(
            Counter(str(row["standard_relation"]) for row in single_empire_rows)
        ),
        "empire_gorbie_forced_left_override_needed": _serialize(
            Counter(str(row["forced_left_override_needed"]) for row in single_empire_rows)
        ),
        "empire_gorbie_games": _serialize(Counter(row["game_id"] for row in empire_rows)),
    }

    examples = empire_rows[: args.example_limit]
    negative_controls = nonempire_rows[: args.example_limit]
    return {
        "schema": "planets-lab.combat-host-galactic-power-audit.v1",
        "read_only": True,
        "summary": summary,
        "target_case": target_rows,
        "empire_gorbie_examples": examples,
        "nonempire_gorbie_examples": negative_controls,
        "evidence_boundary": (
            "Galactic Power is DOCUMENTED by Planets.nu as forcing an Evil Empire-owned Gorbie to the left when the advantage is active. "
            "This audit observes factual Gorbie sides and bounded game/player metadata but does not infer effective advantage enablement when the archive does not expose it. "
            "Campaign remains fail-closed unless enabled-state is known. Game 591478 is excluded from ordinary promotion."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ordinary Gorbie ship-combat sides for documented Galactic Power.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT GALACTIC POWER AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET CASE:")
    for row in report["target_case"]:
        print(row)
    print()
    print("EVIL EMPIRE GORBIE EXAMPLES:")
    for row in report["empire_gorbie_examples"]:
        print(row)
    print()
    print("NON-EMPIRE GORBIE NEGATIVE CONTROLS:")
    for row in report["nonempire_gorbie_examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: documented Galactic Power boundary audit; no Campaign advantage state is invented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
