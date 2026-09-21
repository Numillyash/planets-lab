from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import combat_host_post_capture_opponent_audit as opponent_module
from planets_lab.rules.combat.planet_ownership import (
    PlanetClanDropOrder,
    directed_planet_clan_drop,
    ordered_planet_clan_drops,
)
from combat_host_mixed_ship_planet_queue_batch_audit import (
    _load_groups,
    _planet_pair,
    _shape,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _intish,
    _owner_raw,
)


SCHEMA = "planets-lab.combat-host-planet-precombat-owner-source-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 100

ORDER_FIELD_TOKENS = (
    "clan",
    "drop",
    "transfer",
    "target",
    "mission",
    "enemy",
    "friendly",
    "warp",
)


def _interesting_ship_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in raw.items():
        lowered = str(key).lower()
        if key in {"id", "ownerid", "raceid", "hullid", "x", "y", "clans"} or any(
            token in lowered for token in ORDER_FIELD_TOKENS
        ):
            if isinstance(value, (str, int, float, bool)) or value is None:
                result[str(key)] = value
    return dict(sorted(result.items()))


def _same_position(
    raw: Mapping[str, Any],
    *,
    x: int,
    y: int,
) -> bool:
    return _intish(raw.get("x")) == x and _intish(raw.get("y")) == y


def _ship_rows_at_turn(
    ship_groups: Mapping[Any, Sequence[Any]],
    *,
    turn: int,
) -> list[tuple[int, int, Mapping[str, Any]]]:
    result: list[tuple[int, int, Mapping[str, Any]]] = []
    ship_ids = sorted(
        {
            int(entity_id)
            for (archive_turn, entity_id) in ship_groups
            if int(archive_turn) == turn
        }
    )
    for ship_id in ship_ids:
        owner_id, raw = _owner_raw(ship_groups, turn, ship_id)
        if owner_id is None or not isinstance(raw, Mapping):
            continue
        result.append((ship_id, int(owner_id), raw))
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    vcrs, payload_conflicts = opponent_module._vcr_index(args.archive_dir)
    contexts: dict[
        int,
        tuple[Mapping[Any, Any], Mapping[Any, Any], Mapping[int, int]],
    ] = {}
    changed: dict[tuple[int, int, int], dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    field_presence: Counter[str] = Counter()

    for (game_id, battle_turn, vcr_id), raw_vcr in sorted(vcrs.items()):
        if game_id == SPECIAL_GAME_ID or _shape(raw_vcr) != "ship_vs_planet":
            continue
        pair = _planet_pair(raw_vcr)
        if pair is None:
            counts["pair_projection_unresolved"] += 1
            continue
        ship, planet = pair
        planet_id = int(planet["object_id"])
        vcr_owner = int(planet["owner_id"])

        if game_id not in contexts:
            contexts[game_id] = _load_groups(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                game_id=game_id,
            )
        ship_groups, planet_groups, race_owner_map = contexts[game_id]

        tminus1_owner, planet_raw = _owner_raw(
            planet_groups,
            battle_turn - 1,
            planet_id,
        )
        if (
            tminus1_owner is None
            or not isinstance(planet_raw, Mapping)
            or int(tminus1_owner) == vcr_owner
        ):
            continue

        key = (game_id, battle_turn, planet_id)
        row = changed.setdefault(
            key,
            {
                "game_id": game_id,
                "battle_turn": battle_turn,
                "planet_id": planet_id,
                "tminus1_owner_id": int(tminus1_owner),
                "vcr_defender_owner_id": vcr_owner,
                "vcr_planet_race_id": planet.get("race_id"),
                "race_mapped_owner_id": (
                    race_owner_map.get(int(planet["race_id"]))
                    if isinstance(planet.get("race_id"), int)
                    else None
                ),
                "planet_tminus1_x": _intish(planet_raw.get("x")),
                "planet_tminus1_y": _intish(planet_raw.get("y")),
                "planet_tminus1_clans": _intish(planet_raw.get("clans")),
                "attacking_ship_owner_ids": set(),
                "vcr_ids": [],
            },
        )
        row["attacking_ship_owner_ids"].add(int(ship["owner_id"]))
        row["vcr_ids"].append(int(vcr_id))

    for key in sorted(changed):
        row = changed[key]
        game_id = int(row["game_id"])
        battle_turn = int(row["battle_turn"])
        defender_owner = int(row["vcr_defender_owner_id"])
        tminus1_owner = int(row["tminus1_owner_id"])
        x = row["planet_tminus1_x"]
        y = row["planet_tminus1_y"]

        counts["changed_planet_turn_timelines"] += 1
        if tminus1_owner == 0:
            counts["source_class:tminus1_neutral"] += 1
        elif tminus1_owner in row["attacking_ship_owner_ids"]:
            counts["source_class:tminus1_attacker_owned"] += 1
        else:
            counts["source_class:tminus1_third_party_owned"] += 1

        if not isinstance(x, int) or not isinstance(y, int):
            counts["planet_tminus1_position_unresolved"] += 1
            colocated: list[dict[str, Any]] = []
        else:
            colocated = []
            ship_groups = contexts[game_id][0]
            for ship_id, owner_id, raw in _ship_rows_at_turn(
                ship_groups,
                turn=battle_turn - 1,
            ):
                if not _same_position(raw, x=x, y=y):
                    continue
                clans = _intish(raw.get("clans"))
                drop_order = directed_planet_clan_drop(
                    ship_id=ship_id,
                    owner_id=owner_id,
                    transfer_clans=_intish(raw.get("transferclans")),
                    transfer_target_id=_intish(raw.get("transfertargetid")),
                    transfer_target_type=_intish(raw.get("transfertargettype")),
                )
                candidate = {
                    "ship_id": ship_id,
                    "owner_id": owner_id,
                    "race_id": _intish(raw.get("raceid")),
                    "hull_id": _intish(raw.get("hullid")),
                    "clans": clans,
                    "directed_planet_drop": (
                        {
                            "ship_id": drop_order.ship_id,
                            "owner_id": drop_order.owner_id,
                            "planet_id": drop_order.planet_id,
                            "clans": drop_order.clans,
                        }
                        if drop_order is not None and drop_order.planet_id == planet_id
                        else None
                    ),
                    "fields": _interesting_ship_fields(raw),
                }
                colocated.append(candidate)
                for field in candidate["fields"]:
                    field_presence[field] += 1

        defender_ships = [
            candidate
            for candidate in colocated
            if candidate["owner_id"] == defender_owner
        ]
        defender_positive_clans = [
            candidate
            for candidate in defender_ships
            if isinstance(candidate["clans"], int) and candidate["clans"] > 0
        ]
        foreign_positive_clans = [
            candidate
            for candidate in colocated
            if candidate["owner_id"] != tminus1_owner
            and isinstance(candidate["clans"], int)
            and candidate["clans"] > 0
        ]

        if defender_ships:
            counts["changed_with_defender_ship_colocated"] += 1
        else:
            counts["changed_without_defender_ship_colocated"] += 1
        if defender_positive_clans:
            counts["changed_with_defender_ship_positive_clans"] += 1
        else:
            counts["changed_without_defender_ship_positive_clans"] += 1
        if foreign_positive_clans:
            counts["changed_with_foreign_positive_clan_ship"] += 1
        else:
            counts["changed_without_foreign_positive_clan_ship"] += 1

        if len(defender_positive_clans) == 1:
            counts["defender_positive_clan_candidate_count:1"] += 1
        elif len(defender_positive_clans) > 1:
            counts["defender_positive_clan_candidate_count:multi"] += 1
        else:
            counts["defender_positive_clan_candidate_count:0"] += 1

        if defender_directed_drops:
            counts["changed_with_defender_directed_clan_drop"] += 1
            counts["defender_directed_drop_clans_total"] += sum(
                int(candidate["directed_planet_drop"]["clans"])
                for candidate in defender_directed_drops
            )
        else:
            counts["changed_without_defender_directed_clan_drop"] += 1

        if len(defender_directed_drops) == 1:
            counts["defender_directed_drop_candidate_count:1"] += 1
        elif len(defender_directed_drops) > 1:
            counts["defender_directed_drop_candidate_count:multi"] += 1
        else:
            counts["defender_directed_drop_candidate_count:0"] += 1

        if ordered_drops:
            counts["changed_with_any_directed_clan_drop"] += 1
            counts[f"ordered_drop_stream_length:{len(ordered_drops)}"] += 1
            if ordered_drops[0].owner_id == defender_owner:
                counts["ordered_drop:first_owner_is_defender"] += 1
            if ordered_drops[-1].owner_id == defender_owner:
                counts["ordered_drop:last_owner_is_defender"] += 1
            if any(order.owner_id == defender_owner for order in ordered_drops):
                counts["ordered_drop:defender_present"] += 1
        else:
            counts["changed_without_any_directed_clan_drop"] += 1

        predicted_source_ship_id = (
            min(candidate["ship_id"] for candidate in defender_positive_clans)
            if defender_positive_clans
            else None
        )
        row_out = {
            **{
                name: value
                for name, value in row.items()
                if name not in {"attacking_ship_owner_ids", "vcr_ids"}
            },
            "attacking_ship_owner_ids": sorted(row["attacking_ship_owner_ids"]),
            "vcr_ids": sorted(row["vcr_ids"]),
            "colocated_ship_count": len(colocated),
            "defender_ship_count": len(defender_ships),
            "defender_positive_clan_ship_count": len(defender_positive_clans),
            "foreign_positive_clan_ship_count": len(foreign_positive_clans),
            "defender_directed_drop_count": len(defender_directed_drops),
            "predicted_lowest_id_defender_clan_ship": predicted_source_ship_id,
            "ordered_directed_drop_stream": [
                {
                    "ship_id": order.ship_id,
                    "owner_id": order.owner_id,
                    "planet_id": order.planet_id,
                    "clans": order.clans,
                }
                for order in ordered_drops
            ],
            "defender_positive_clan_ships": defender_positive_clans,
            "all_colocated_ships": colocated,
        }
        if len(examples) < args.example_limit:
            examples.append(row_out)

    acceptance = {
        "changed_population_present": counts["changed_planet_turn_timelines"] > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "pair_projection_resolved": counts["pair_projection_unresolved"] == 0,
        "tminus1_positions_resolved": counts["planet_tminus1_position_unresolved"] == 0,
        "all_changed_have_defender_directed_clan_drop": (
            counts["changed_without_defender_directed_clan_drop"] == 0
        ),
    }
    acceptance["precombat_owner_source_inventory_gate_passed"] = all(
        acceptance.values()
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "special_game_591478_excluded": True,
            "payload_conflicts": payload_conflicts,
            "counts": dict(sorted(counts.items())),
            "ship_field_presence_on_colocated_candidates": dict(
                sorted(field_presence.items())
            ),
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "This is a source-candidate and directed-order differential, not yet "
            "a ground-combat casualty simulator. It checks T-1 co-location, "
            "onboard clan cargo, and explicit transferclans orders targeting the "
            "factual planet. Official Host ordering places "
            "cargo drop / Imperial Assault / ground combat before later combat, "
            "but exact drop orders, kill ratios, Imperial Assault conditions, "
            "Horwasp exceptions and sequential multi-ship cargo-drop effects "
            "must be reconstructed independently before production promotion."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory T-1 ship/cargo candidates for factual pre-combat planet "
            "ownership changes."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PLANET PRECOMBAT OWNER SOURCE =====")
    print("summary:", report["summary"])
    if report["examples"]:
        print()
        print("OWNER-CHANGE SOURCE EXAMPLES:")
        for row in report["examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: source-candidate inventory only; no ground-combat ownership "
        "transition is promoted until exact cargo-drop semantics are reproduced."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
