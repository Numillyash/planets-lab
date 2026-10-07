from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for path in (REPO_ROOT / "src", DIAGNOSTICS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only

import combat_host_post_capture_active_membership_audit as active_module
import combat_host_post_mutation_next_pair_audit as mutation_module
import combat_site_state_differential_v1 as site_module


SCHEMA = "planets-lab.site-precombat-dynamic-probe.v1"

INTERESTING_EXACT = {
    "id",
    "ownerid",
    "hullid",
    "raceid",
    "friendlycode",
    "mission",
    "mission1target",
    "enemy",
    "x",
    "y",
    "targetx",
    "targety",
    "warp",
    "mass",
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "supplies",
    "megacredits",
    "transfertargetid",
}
INTERESTING_PARTS = ("torp", "fighter", "transfer", "ammo")


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _interesting_raw(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(raw):
        folded = str(key).casefold().replace("_", "").replace("-", "")
        if (
            folded in INTERESTING_EXACT
            or any(part in folded for part in INTERESTING_PARTS)
        ):
            value = raw[key]
            if isinstance(value, (str, int, float, bool)) or value is None:
                result[str(key)] = value
    return result


def _vcr_side_for_ship(
    payload: Mapping[str, Any],
    ship_id: int,
) -> tuple[str, Mapping[str, Any]] | None:
    for side_name in ("left", "right"):
        raw = payload.get(side_name)
        if not isinstance(raw, Mapping):
            continue
        if _int(raw.get("objectid")) == ship_id:
            return side_name, raw
    return None


def _appearance_rows_for_ship(
    *,
    game_id: int,
    battle_turn: int,
    ship_id: int,
    factual_queue: Sequence[Mapping[str, Any]],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    before_vcr_id: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in factual_queue:
        vcr_id = _int(row.get("vcr_id"))
        if vcr_id is None or vcr_id >= before_vcr_id:
            continue
        appearance = appearances.get(
            mutation_module._appearance_key(
                game_id,
                battle_turn,
                vcr_id,
                ship_id,
            )
        )
        if not isinstance(appearance, Mapping):
            continue
        start = appearance.get("start")
        terminal = appearance.get("terminal")
        rows.append(
            {
                "vcr_id": vcr_id,
                "side": appearance.get("side"),
                "start_torpedoes": (
                    _int(start.get("torpedos"))
                    if isinstance(start, Mapping)
                    else None
                ),
                "terminal_torpedoes": (
                    _int(terminal.get("torpedoes"))
                    if isinstance(terminal, Mapping)
                    else None
                ),
                "captured": (
                    terminal.get("captured")
                    if isinstance(terminal, Mapping)
                    else None
                ),
                "destroyed": (
                    terminal.get("destroyed")
                    if isinstance(terminal, Mapping)
                    else None
                ),
            }
        )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    connection, database_path = connect_compact_generation_read_only(
        args.corpus_db_generation,
        args.corpus_db_root,
    )
    try:
        context, appearance_rows, appearance_summary, visit_summary = (
            site_module._target_context(
                connection=connection,
                game_id=args.game_id,
                battle_turn=args.battle_turn,
                x=args.x,
                y=args.y,
            )
        )
        cases = combat_vcr_cases_for_turns(
            connection,
            game_id=args.game_id,
            battle_turns={args.battle_turn},
        )
    finally:
        connection.close()

    case = cases.get((args.battle_turn, args.vcr_id))
    if case is None:
        raise ValueError("target VCR replay case missing")

    appearances = site_module._appearance_map(appearance_rows)
    factual_queue = context.get("factual_queue")
    predictions = context.get("predictions")
    site_rows = context.get("site_ship_rows")
    if (
        not isinstance(factual_queue, Sequence)
        or isinstance(factual_queue, (str, bytes))
        or not isinstance(predictions, Mapping)
        or not isinstance(site_rows, Mapping)
    ):
        raise ValueError("site context incomplete")

    initial_state = site_module._initial_state_before_window(
        context=context,
        appearances=appearances,
        start_vcr_id=args.vcr_id,
    )

    participant_ids: list[int] = []
    for side_name in ("left", "right"):
        side = case.payload.get(side_name)
        if not isinstance(side, Mapping):
            continue
        ship_id = _int(side.get("objectid"))
        if ship_id is not None and ship_id > 0:
            participant_ids.append(ship_id)

    rows: list[dict[str, Any]] = []
    for ship_id in participant_ids:
        prediction = predictions.get(ship_id)
        prediction = prediction if isinstance(prediction, Mapping) else {}
        raw = prediction.get("raw")
        raw = raw if isinstance(raw, Mapping) else {}

        history_appearances = _appearance_rows_for_ship(
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            ship_id=ship_id,
            factual_queue=factual_queue,
            appearances=appearances,
            before_vcr_id=args.vcr_id,
        )
        initial_source = (
            "prewindow_vcr_appearance"
            if history_appearances
            else "tminus1_prediction"
        )

        carried = initial_state.active_ships.get(ship_id)
        carried = carried if isinstance(carried, Mapping) else {}

        vcr_side_pair = _vcr_side_for_ship(case.payload, ship_id)
        if vcr_side_pair is None:
            raise ValueError(f"ship {ship_id}: missing from target VCR")
        side_name, vcr_side = vcr_side_pair

        inbound: list[dict[str, Any]] = []
        for source_ship_id, source_prediction in predictions.items():
            if not isinstance(source_prediction, Mapping):
                continue
            source_raw = source_prediction.get("raw")
            if not isinstance(source_raw, Mapping):
                continue
            if _int(source_raw.get("transfertargetid")) != ship_id:
                continue
            inbound.append(
                {
                    "source_ship_id": int(source_ship_id),
                    "owner_id": source_prediction.get("owner_id"),
                    "at_target_site": int(source_ship_id) in site_rows,
                    "prediction_source": source_prediction.get("source"),
                    "raw": _interesting_raw(source_raw),
                }
            )

        rows.append(
            {
                "ship_id": ship_id,
                "vcr_side": side_name,
                "initial_source": initial_source,
                "prewindow_appearances": history_appearances,
                "tminus1_prediction_source": prediction.get("source"),
                "tminus1_at_target_site": ship_id in site_rows,
                "tminus1_raw": _interesting_raw(raw),
                "carried_before_vcr": {
                    key: carried.get(key)
                    for key in (
                        "owner_id",
                        "race_id",
                        "hull_id",
                        "shield",
                        "damage",
                        "crew",
                        "torpedoes",
                        "fighters",
                        "beam_count",
                        "launcher_count",
                        "bay_count",
                    )
                },
                "current_vcr_start": {
                    key: vcr_side.get(key)
                    for key in (
                        "hullid",
                        "raceid",
                        "shield",
                        "damage",
                        "crew",
                        "torpedos",
                        "fighters",
                        "beamcount",
                        "launchercount",
                        "baycount",
                    )
                },
                "torpedo_delta": (
                    _int(vcr_side.get("torpedos"))
                    - int(carried.get("torpedoes", 0))
                    if _int(vcr_side.get("torpedos")) is not None
                    and isinstance(carried.get("torpedoes"), int)
                    and not isinstance(carried.get("torpedoes"), bool)
                    else None
                ),
                "friendly_code_mkt": (
                    isinstance(raw.get("friendlycode"), str)
                    and raw.get("friendlycode").strip().casefold() == "mkt"
                ),
                "inbound_transfer_candidates": inbound,
            }
        )

    return {
        "schema": SCHEMA,
        "database_path": str(database_path),
        "target": {
            "game_id": args.game_id,
            "battle_turn": args.battle_turn,
            "x": args.x,
            "y": args.y,
            "vcr_id": args.vcr_id,
        },
        "rows": rows,
        "appearance_summary": appearance_summary,
        "visit_summary": visit_summary,
        "evidence_boundary": (
            "Read-only provenance probe. T-1 raw ship/order state and pre-window "
            "VCR appearances are compared with the factual current-VCR start "
            "vector. No rule is promoted and no carried state is modified."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-db-root", type=Path, default=None)
    parser.add_argument("--corpus-db-generation", type=Path, required=True)
    parser.add_argument("--game-id", type=int, default=400330)
    parser.add_argument("--battle-turn", type=int, default=141)
    parser.add_argument("--x", type=int, default=1674)
    parser.add_argument("--y", type=int, default=2363)
    parser.add_argument("--vcr-id", type=int, default=592)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== SITE PRECOMBAT DYNAMIC PROBE V1 =====")
    for row in report["rows"]:
        print(
            f"ship={row['ship_id']} side={row['vcr_side']} "
            f"source={row['initial_source']} "
            f"carried_torps={row['carried_before_vcr']['torpedoes']} "
            f"vcr_torps={row['current_vcr_start']['torpedos']} "
            f"delta={row['torpedo_delta']} "
            f"fc_mkt={row['friendly_code_mkt']}"
        )
        print(f"  tminus1_source: {row['tminus1_prediction_source']}")
        print(f"  tminus1_raw: {row['tminus1_raw']}")
        print(f"  prewindow_appearances: {row['prewindow_appearances']}")
        print(
            "  inbound_transfer_candidates: "
            f"{row['inbound_transfer_candidates']}"
        )
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
