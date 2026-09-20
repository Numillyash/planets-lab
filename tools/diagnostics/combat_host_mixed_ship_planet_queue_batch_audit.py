from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.mixed_queue import (
    PlanetAttackCandidate,
    select_initial_plain_planet_attacker,
)
from planets_lab.rules.combat.order import (
    orders_request_ship_combat,
    standard_battle_priority_key,
)

import combat_host_capture_continuation_audit as capture_module
import combat_host_post_capture_opponent_audit as opponent_module
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _int,
    _owner_raw,
)


SCHEMA = "planets-lab.combat-host-mixed-ship-planet-queue-batch-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 80
PLANET_ATTACK_CODES = frozenset({"nuk", "att"})
HORWASP_RACE_ID = 12


def _counter(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(
            counter.items(),
            key=lambda item: (-item[1], str(item[0])),
        )
    }


def _shape(raw_vcr: Mapping[str, Any]) -> str:
    left = raw_vcr.get("left")
    right = raw_vcr.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return "unknown"
    left_hull = _int(left, "hullid")
    right_hull = _int(right, "hullid")
    if left_hull is None or right_hull is None:
        return "unknown"
    left_planet = left_hull <= 0
    right_planet = right_hull <= 0
    if left_planet and right_planet:
        return "planet_vs_planet"
    if left_planet or right_planet:
        return "ship_vs_planet"
    return "ship_vs_ship"


def _side(
    raw_vcr: Mapping[str, Any],
    side_name: str,
) -> dict[str, Any] | None:
    raw = raw_vcr.get(side_name)
    if not isinstance(raw, Mapping):
        return None
    hull_id = _int(raw, "hullid")
    object_id = _int(raw, "objectid")
    owner_key = "leftownerid" if side_name == "left" else "rightownerid"
    owner_id = _int(raw_vcr, owner_key)
    if hull_id is None or object_id is None or owner_id is None:
        return None
    return {
        "side": side_name,
        "object_id": object_id,
        "owner_id": owner_id,
        "hull_id": hull_id,
        "kind": "planet" if hull_id <= 0 else "ship",
        "raw": raw,
    }


def _planet_pair(
    raw_vcr: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    left = _side(raw_vcr, "left")
    right = _side(raw_vcr, "right")
    if left is None or right is None:
        return None
    if left["kind"] == "ship" and right["kind"] == "planet":
        return left, right
    if right["kind"] == "ship" and left["kind"] == "planet":
        return right, left
    return None


def _ship_ids(raw_vcr: Mapping[str, Any]) -> tuple[int, ...]:
    result: list[int] = []
    for side_name in ("left", "right"):
        side = _side(raw_vcr, side_name)
        if side is not None and side["kind"] == "ship":
            result.append(int(side["object_id"]))
    return tuple(result)


def _priority_projection(
    ship_groups: Mapping[Any, Any],
    *,
    battle_turn: int,
    ship_id: int,
) -> dict[str, Any]:
    owner_id, raw = _owner_raw(ship_groups, battle_turn - 1, ship_id)
    if owner_id is None or not isinstance(raw, Mapping):
        return {
            "resolved": False,
            "reason": "ship_tminus1_unresolved",
            "ship_id": ship_id,
        }
    mission = _intish(raw.get("mission"))
    enemy = _intish(raw.get("enemy"))
    fc = raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None
    key = standard_battle_priority_key(
        ship_id=ship_id,
        mission=mission,
        primary_enemy=enemy,
        friendly_code=fc,
    )
    return {
        "resolved": key is not None,
        "reason": None if key is not None else "priority_unresolved",
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": _intish(raw.get("raceid")),
        "mission": mission,
        "enemy": enemy,
        "friendlycode": fc,
        "priority_key": list(key) if key is not None else None,
    }


def _planet_projection(
    planet_groups: Mapping[Any, Any],
    *,
    battle_turn: int,
    planet_id: int,
) -> dict[str, Any]:
    owner_id, raw = _owner_raw(planet_groups, battle_turn - 1, planet_id)
    if owner_id is None or not isinstance(raw, Mapping):
        return {
            "resolved": False,
            "reason": "planet_tminus1_unresolved",
            "planet_id": planet_id,
        }
    fc = raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None
    normalized = fc.strip().lower() if isinstance(fc, str) else None
    return {
        "resolved": True,
        "planet_id": planet_id,
        "owner_id": owner_id,
        "race_id": _intish(raw.get("raceid")),
        "friendlycode": fc,
        "normalized_friendlycode": normalized,
        "attack_code": normalized in PLANET_ATTACK_CODES,
        "has_starbase": raw.get("hasstarbase") if isinstance(raw.get("hasstarbase"), bool) else None,
        "defense": _intish(raw.get("defense")),
    }


def _load_groups(
    *,
    archive_dir: Path,
    prepared_dir: Path,
    game_id: int,
) -> tuple[Mapping[Any, Any], Mapping[Any, Any]]:
    archive_path = archive_dir / f"game-{game_id}.zip"
    prepared, _ = load_or_build_prepared_game_cache(
        archive_path.read_bytes(),
        game_id=game_id,
        cache_path=prepared_dir / f"game-{game_id}.pickle",
    )
    return (
        group_perspective_records(prepared.snapshots, "ship"),
        group_perspective_records(prepared.snapshots, "planet"),
    )


def _capture_index(
    *,
    archive_dir: Path,
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    report = capture_module.run(
        argparse.Namespace(
            archive_dir=archive_dir,
            example_limit=10000,
            output=None,
        )
    )
    rows = report.get("examples")
    rows = rows if isinstance(rows, list) else []
    result: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or row.get("status") != "capture_continuation":
            continue
        key = (
            int(row["game_id"]),
            int(row["turn"]),
            int(row["to_vcr_id"]),
            int(row["ship_id"]),
        )
        result[key] = row
    return result


def _site_profile(rows: Sequence[Mapping[str, Any]]) -> str:
    token = {
        "ship_vs_ship": "S",
        "ship_vs_planet": "P",
        "planet_vs_planet": "X",
        "unknown": "?",
    }
    return "".join(token.get(str(row["shape"]), "?") for row in rows)


def _same_planet_priority_group(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(rows) < 2:
        return {
            "comparable": False,
            "reason": "single_planet_engagement",
        }
    factual = [int(row["ship"]["object_id"]) for row in rows]
    priorities: list[tuple[tuple[int, int, int], int]] = []
    for row in rows:
        projection = row.get("ship_tminus1")
        if not isinstance(projection, Mapping) or projection.get("resolved") is not True:
            return {
                "comparable": False,
                "reason": "ship_priority_unresolved",
                "factual_ship_order": factual,
            }
        key_raw = projection.get("priority_key")
        if not isinstance(key_raw, list) or len(key_raw) != 3:
            return {
                "comparable": False,
                "reason": "priority_key_shape_unresolved",
                "factual_ship_order": factual,
            }
        key = tuple(int(value) for value in key_raw)
        priorities.append((key, int(row["ship"]["object_id"])))

    expected = [ship_id for _key, ship_id in sorted(priorities)]
    return {
        "comparable": True,
        "factual_ship_order": factual,
        "expected_standard_priority_order": expected,
        "exact": factual == expected,
    }


def _production_planet_order(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(rows) < 2:
        return {"comparable": False, "reason": "single_planet_engagement"}
    if any(row.get("post_capture") is True for row in rows):
        return {
            "comparable": False,
            "reason": "post_capture_generated_order_present",
            "factual_ship_order": [
                int(row["ship"]["object_id"]) for row in rows
            ],
        }

    remaining = list(rows)
    predicted: list[int] = []
    while remaining:
        candidates: list[PlanetAttackCandidate] = []
        by_ship: dict[int, Mapping[str, Any]] = {}
        for row in remaining:
            projection = row.get("ship_tminus1")
            if (
                not isinstance(projection, Mapping)
                or projection.get("resolved") is not True
            ):
                return {
                    "comparable": False,
                    "reason": "ship_priority_unresolved",
                    "factual_ship_order": [
                        int(item["ship"]["object_id"]) for item in rows
                    ],
                }
            ship_id = int(row["ship"]["object_id"])
            by_ship[ship_id] = row
            candidates.append(
                PlanetAttackCandidate(
                    ship_id=ship_id,
                    mission=projection.get("mission"),
                    primary_enemy=projection.get("enemy"),
                    friendly_code=projection.get("friendlycode"),
                    engagement_eligible=True,
                )
            )

        selected = select_initial_plain_planet_attacker(candidates)
        if selected.engagement_available is not True or selected.ship_id is None:
            return {
                "comparable": False,
                "reason": "production_planet_selector_unresolved",
                "unresolved_reasons": list(selected.unresolved_reasons),
                "factual_ship_order": [
                    int(item["ship"]["object_id"]) for item in rows
                ],
            }
        predicted.append(selected.ship_id)
        remaining = [
            row
            for row in remaining
            if int(row["ship"]["object_id"]) != selected.ship_id
        ]

    factual = [int(row["ship"]["object_id"]) for row in rows]
    return {
        "comparable": True,
        "factual_ship_order": factual,
        "predicted_ship_order": predicted,
        "exact": factual == predicted,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    vcrs, payload_conflicts = opponent_module._vcr_index(args.archive_dir)
    capture_index = _capture_index(archive_dir=args.archive_dir)

    sites_map: dict[tuple[int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    unknown_shape_vcrs = 0
    missing_position_vcrs = 0

    for (game_id, battle_turn, vcr_id), raw_vcr in sorted(vcrs.items()):
        x = _int(raw_vcr, "x")
        y = _int(raw_vcr, "y")
        if x is None or y is None:
            missing_position_vcrs += 1
            continue
        shape = _shape(raw_vcr)
        if shape == "unknown":
            unknown_shape_vcrs += 1
        sites_map[(game_id, battle_turn, x, y)].append(
            {
                "game_id": game_id,
                "battle_turn": battle_turn,
                "vcr_id": vcr_id,
                "x": x,
                "y": y,
                "shape": shape,
                "raw_vcr": raw_vcr,
            }
        )

    mixed_keys = [
        key
        for key, rows in sites_map.items()
        if {str(row["shape"]) for row in rows}
        >= {"ship_vs_ship", "ship_vs_planet"}
    ]

    groups_by_game: dict[
        int,
        tuple[Mapping[Any, Any], Mapping[Any, Any]],
    ] = {}
    counts: Counter[str] = Counter()
    profiles: Counter[str] = Counter()
    transition_shapes: Counter[str] = Counter()
    planet_codes: Counter[str] = Counter()
    planet_side_counts: Counter[str] = Counter()
    repeated_planet_priority: Counter[str] = Counter()
    site_examples: list[dict[str, Any]] = []
    priority_examples: list[dict[str, Any]] = []
    initiator_residual_examples: list[dict[str, Any]] = []
    capture_group_examples: list[dict[str, Any]] = []

    counts["mixed_sites"] = len(mixed_keys)

    for key in sorted(mixed_keys):
        game_id, battle_turn, x, y = key
        rows = sorted(sites_map[key], key=lambda item: int(item["vcr_id"]))
        if game_id not in groups_by_game:
            groups_by_game[game_id] = _load_groups(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                game_id=game_id,
            )
        ship_groups, planet_groups = groups_by_game[game_id]

        profile = _site_profile(rows)
        profiles[profile] += 1
        counts["mixed_vcrs"] += len(rows)

        shapes = [str(row["shape"]) for row in rows]
        first_planet_index = next(
            (index for index, shape in enumerate(shapes) if shape == "ship_vs_planet"),
            None,
        )
        phase_violation = bool(
            first_planet_index is not None
            and any(
                shape == "ship_vs_ship"
                for shape in shapes[first_planet_index + 1 :]
            )
        )
        if phase_violation:
            counts["sites_with_planet_to_ship_return"] += 1
        else:
            counts["sites_ship_block_before_planet_block"] += 1

        for previous, current in zip(rows, rows[1:]):
            transition_shapes[
                f"{previous['shape']}->{current['shape']}"
            ] += 1

        prior_ship_ids: set[int] = set()
        planet_rows_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
        detailed_rows: list[dict[str, Any]] = []

        for index, row in enumerate(rows):
            shape = str(row["shape"])
            raw_vcr = row["raw_vcr"]

            if shape == "ship_vs_ship":
                counts["ship_vs_ship_vcrs"] += 1
                prior_ship_ids.update(_ship_ids(raw_vcr))
                detailed_rows.append(
                    {
                        "vcr_id": int(row["vcr_id"]),
                        "shape": shape,
                        "ship_ids": list(_ship_ids(raw_vcr)),
                    }
                )
                continue

            if shape != "ship_vs_planet":
                counts[f"other_shape:{shape}"] += 1
                detailed_rows.append(
                    {
                        "vcr_id": int(row["vcr_id"]),
                        "shape": shape,
                    }
                )
                continue

            counts["ship_vs_planet_vcrs"] += 1
            pair = _planet_pair(raw_vcr)
            if pair is None:
                counts["planet_pair_projection_unresolved"] += 1
                continue
            ship, planet = pair
            ship_id = int(ship["object_id"])
            planet_id = int(planet["object_id"])

            capture_key = (
                game_id,
                battle_turn,
                int(row["vcr_id"]),
                ship_id,
            )
            post_capture = capture_key in capture_index

            planet_side_counts[str(planet["side"])] += 1
            if planet["side"] == "right":
                counts["planet_on_right"] += 1
            else:
                counts["planet_on_left"] += 1

            ship_projection = _priority_projection(
                ship_groups,
                battle_turn=battle_turn,
                ship_id=ship_id,
            )
            planet_projection = _planet_projection(
                planet_groups,
                battle_turn=battle_turn,
                planet_id=planet_id,
            )
            if ship_projection.get("resolved") is True:
                counts["planet_attacker_priority_resolved"] += 1
            else:
                counts["planet_attacker_priority_unresolved"] += 1

            ship_requests_planet = None
            planet_requests_ship = None
            if planet_projection.get("resolved") is True:
                code = planet_projection.get("normalized_friendlycode")
                planet_codes[str(code)] += 1
                planet_requests_ship = (
                    planet_projection.get("attack_code") is True
                )
                if planet_requests_ship:
                    counts["planet_attack_code_rows"] += 1
                else:
                    counts["planet_nonattack_code_rows"] += 1

                if ship_projection.get("resolved") is True:
                    ordinary_ship_request = orders_request_ship_combat(
                        mission=ship_projection.get("mission"),
                        primary_enemy=ship_projection.get("enemy"),
                        opponent_owner_id=int(planet_projection["owner_id"]),
                    )
                    horwasp_ship_request = (
                        ship_projection.get("race_id") == HORWASP_RACE_ID
                        and int(ship["owner_id"]) != int(planet["owner_id"])
                    )
                    ship_requests_planet = bool(
                        ordinary_ship_request or horwasp_ship_request
                    )
                    if horwasp_ship_request and not ordinary_ship_request:
                        counts["planet_initiator:horwasp_ship_kill_equivalent"] += 1

                    horwasp_planet_request = (
                        planet_projection.get("race_id") == HORWASP_RACE_ID
                        and int(ship["owner_id"]) != int(planet["owner_id"])
                    )
                    if horwasp_planet_request and not planet_requests_ship:
                        planet_requests_ship = True
                        counts["planet_initiator:horwasp_planet_nuk_equivalent"] += 1
                    if ship_requests_planet and planet_requests_ship:
                        counts["planet_initiator:both"] += 1
                    elif ship_requests_planet:
                        counts["planet_initiator:ship_only"] += 1
                    elif planet_requests_ship:
                        counts["planet_initiator:planet_only"] += 1
                    else:
                        counts["planet_initiator:neither_basic_order"] += 1
                        if len(initiator_residual_examples) < args.example_limit:
                            initiator_residual_examples.append(
                                {
                                    "game_id": game_id,
                                    "battle_turn": battle_turn,
                                    "x": x,
                                    "y": y,
                                    "vcr_id": int(row["vcr_id"]),
                                    "ship_id": ship_id,
                                    "planet_id": planet_id,
                                    "ship_tminus1_owner_id": ship_projection.get("owner_id"),
                                    "ship_vcr_owner_id": ship.get("owner_id"),
                                    "ship_race_id": ship_projection.get("race_id"),
                                    "planet_owner_id": planet_projection.get("owner_id"),
                                    "planet_race_id": planet_projection.get("race_id"),
                                    "ship_tminus1": ship_projection,
                                    "planet_tminus1": planet_projection,
                                    "post_capture": post_capture,
                                }
                            )

                    ship_fc = ship_projection.get("friendlycode")
                    planet_fc = planet_projection.get("friendlycode")
                    if (
                        isinstance(ship_fc, str)
                        and isinstance(planet_fc, str)
                        and ship_fc == planet_fc
                    ):
                        counts["ship_planet_matching_fc_rows"] += 1
                else:
                    counts["planet_initiator_unresolved:ship_tminus1"] += 1
            else:
                counts["planet_tminus1_unresolved"] += 1
                counts["planet_initiator_unresolved:planet_tminus1"] += 1

            appeared_in_prior_ship_combat = ship_id in prior_ship_ids
            if appeared_in_prior_ship_combat:
                counts["planet_rows_ship_already_fought_ship"] += 1
            else:
                counts["planet_rows_fresh_ship"] += 1

            immediate_previous = rows[index - 1] if index > 0 else None
            immediate_previous_same_ship = bool(
                isinstance(immediate_previous, Mapping)
                and str(immediate_previous.get("shape")) == "ship_vs_ship"
                and ship_id in _ship_ids(immediate_previous["raw_vcr"])
            )
            if immediate_previous_same_ship:
                counts["ship_to_planet_immediate_same_ship"] += 1

            if post_capture:
                counts["planet_rows_post_capture"] += 1
            elif appeared_in_prior_ship_combat:
                counts["planet_rows_post_ship_non_capture"] += 1

            owner_changed_since_tminus1 = (
                ship_projection.get("resolved") is True
                and ship_projection.get("owner_id") != ship.get("owner_id")
            )
            if owner_changed_since_tminus1:
                counts["planet_rows_owner_changed_since_tminus1"] += 1

            projection = {
                "vcr_id": int(row["vcr_id"]),
                "shape": shape,
                "ship": {
                    key: value
                    for key, value in ship.items()
                    if key != "raw"
                },
                "planet": {
                    key: value
                    for key, value in planet.items()
                    if key != "raw"
                },
                "ship_tminus1": ship_projection,
                "planet_tminus1": planet_projection,
                "ship_requests_planet": ship_requests_planet,
                "planet_requests_ship": planet_requests_ship,
                "appeared_in_prior_ship_combat": appeared_in_prior_ship_combat,
                "immediate_previous_same_ship": immediate_previous_same_ship,
                "post_capture": post_capture,
                "owner_changed_since_tminus1": owner_changed_since_tminus1,
            }
            detailed_rows.append(projection)
            planet_rows_by_id[planet_id].append(projection)
            prior_ship_ids.add(ship_id)

        distinct_planets = len(planet_rows_by_id)
        counts[f"distinct_planets_per_mixed_site:{distinct_planets}"] += 1
        if distinct_planets > 1:
            counts["mixed_sites_multiple_planets"] += 1

        for planet_id, planet_rows in sorted(planet_rows_by_id.items()):
            counts["planet_engagement_groups"] += 1
            if len(planet_rows) > 1:
                counts["repeated_planet_groups"] += 1
                counts["repeated_planet_vcrs"] += len(planet_rows)

                has_post_capture = any(
                    row.get("post_capture") is True for row in planet_rows
                )
                if has_post_capture:
                    counts["repeated_planet_groups_with_post_capture"] += 1
                    if len(capture_group_examples) < args.example_limit:
                        capture_group_examples.append(
                            {
                                "game_id": game_id,
                                "battle_turn": battle_turn,
                                "x": x,
                                "y": y,
                                "planet_id": planet_id,
                                "rows": planet_rows,
                            }
                        )
                    seen_post_capture = False
                    capture_after_ordinary = True
                    for item in planet_rows:
                        if item.get("post_capture") is True:
                            seen_post_capture = True
                        elif seen_post_capture:
                            capture_after_ordinary = False
                    if capture_after_ordinary:
                        counts[
                            "post_capture_rows_after_all_ordinary_attackers"
                        ] += 1
                    else:
                        counts[
                            "post_capture_rows_interleaved_before_ordinary_attackers"
                        ] += 1
                else:
                    counts["repeated_planet_groups_without_post_capture"] += 1

                naive = _same_planet_priority_group(planet_rows)
                if naive["comparable"] is True:
                    counts["repeated_planet_priority_comparable"] += 1
                    if naive["exact"] is True:
                        counts["repeated_planet_priority_exact"] += 1
                        repeated_planet_priority["naive_exact"] += 1
                    else:
                        counts["repeated_planet_priority_mismatch"] += 1
                        repeated_planet_priority["naive_mismatch"] += 1

                result = _production_planet_order(planet_rows)
                if result["comparable"] is True:
                    counts["production_planet_order_comparable"] += 1
                    if result["exact"] is True:
                        counts["production_planet_order_exact"] += 1
                        repeated_planet_priority["production_exact"] += 1
                    else:
                        counts["production_planet_order_mismatch"] += 1
                        repeated_planet_priority["production_mismatch"] += 1
                        if len(priority_examples) < args.example_limit:
                            priority_examples.append(
                                {
                                    "game_id": game_id,
                                    "battle_turn": battle_turn,
                                    "x": x,
                                    "y": y,
                                    "planet_id": planet_id,
                                    "result": result,
                                    "rows": planet_rows,
                                }
                            )
                else:
                    counts["production_planet_order_unresolved"] += 1
                    repeated_planet_priority[
                        f"production_unresolved:{result['reason']}"
                    ] += 1
                    if (
                        result["reason"]
                        == "post_capture_generated_order_present"
                        and len(priority_examples) < args.example_limit
                    ):
                        priority_examples.append(
                            {
                                "game_id": game_id,
                                "battle_turn": battle_turn,
                                "x": x,
                                "y": y,
                                "planet_id": planet_id,
                                "result": result,
                                "rows": planet_rows,
                            }
                        )

        if len(site_examples) < args.example_limit:
            site_examples.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "x": x,
                    "y": y,
                    "profile": profile,
                    "phase_order_violation": phase_violation,
                    "rows": detailed_rows,
                }
            )

    mixed_sites = int(counts["mixed_sites"])
    planet_rows = int(counts["ship_vs_planet_vcrs"])
    priority_comparable = int(counts["repeated_planet_priority_comparable"])
    production_comparable = int(counts["production_planet_order_comparable"])
    basic_initiator_resolved = (
        int(counts["planet_initiator:both"])
        + int(counts["planet_initiator:ship_only"])
        + int(counts["planet_initiator:planet_only"])
        + int(counts["planet_initiator:neither_basic_order"])
    )
    hypotheses = {
        "ship_block_always_precedes_planet_block": (
            mixed_sites > 0
            and int(counts["sites_with_planet_to_ship_return"]) == 0
        ),
        "planet_always_on_right": (
            planet_rows > 0
            and int(counts["planet_on_right"]) == planet_rows
            and int(counts["planet_on_left"]) == 0
        ),
        "all_resolved_planet_fights_have_basic_ship_or_planet_initiator": (
            basic_initiator_resolved > 0
            and int(counts["planet_initiator:neither_basic_order"]) == 0
        ),
        "ordinary_repeated_planet_groups_follow_production_priority": (
            production_comparable > 0
            and int(counts["production_planet_order_exact"])
            == production_comparable
            and int(counts["production_planet_order_mismatch"]) == 0
        ),
        "capture_insertion_groups_place_post_capture_after_ordinary_attackers": (
            int(counts["repeated_planet_groups_with_post_capture"]) > 0
            and int(counts["post_capture_rows_interleaved_before_ordinary_attackers"])
            == 0
        ),
        "naive_all_repeated_groups_follow_tminus1_priority": (
            priority_comparable > 0
            and int(counts["repeated_planet_priority_exact"]) == priority_comparable
            and int(counts["repeated_planet_priority_mismatch"]) == 0
        ),
    }
    structural_acceptance = {
        "mixed_population_present": mixed_sites > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "unknown_shape_vcrs_absent": unknown_shape_vcrs == 0,
        "planet_pair_projection_resolved": int(
            counts["planet_pair_projection_unresolved"]
        ) == 0,
        "ship_and_planet_rows_present": (
            int(counts["ship_vs_ship_vcrs"]) > 0
            and planet_rows > 0
        ),
    }

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "payload_conflicts": payload_conflicts,
            "missing_position_vcrs": missing_position_vcrs,
            "unknown_shape_vcrs": unknown_shape_vcrs,
            "counts": dict(sorted(counts.items())),
            "profiles": _counter(profiles),
            "transition_shapes": _counter(transition_shapes),
            "planet_friendly_codes": _counter(planet_codes),
            "planet_side_counts": _counter(planet_side_counts),
            "repeated_planet_priority": _counter(repeated_planet_priority),
            "structural_acceptance": structural_acceptance,
            "hypotheses": hypotheses,
        },
        "priority_mismatch_examples": priority_examples,
        "initiator_residual_examples": initiator_residual_examples,
        "capture_group_examples": capture_group_examples,
        "site_examples": site_examples,
        "evidence_boundary": (
            "Large read-only first-pass mixed ship/planet queue batch. It "
            "inventories factual mixed-site queue profiles, S->P/P->S "
            "transitions, planet side orientation, T-1 NUK/ATT state, whether "
            "planet attackers already fought ships at the site, capture-to-planet "
            "handoffs, repeated attacks on the same planet, and a deliberately "
            "naive and production ordinary-priority ordering for repeated planet "
            "groups, basic ship/planet initiator orders, and capture-aware group "
            "partitioning. Factual queue order is used only as an observation. "
            "No mixed-order production rule is promoted by this pass; false "
            "hypotheses are expected to expose the next focused gate."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a broad first-pass population audit over ordinary combat sites "
            "that contain both ship-vs-ship and ship-vs-planet/base VCRs."
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
    print("===== HOST COMBAT MIXED SHIP/PLANET QUEUE BATCH =====")
    print("summary:", report["summary"])
    if report["priority_mismatch_examples"]:
        print()
        print("PRIORITY MISMATCH EXAMPLES:")
        for row in report["priority_mismatch_examples"]:
            print(row)
    if report["initiator_residual_examples"]:
        print()
        print("INITIATOR RESIDUAL EXAMPLES:")
        for row in report["initiator_residual_examples"]:
            print(row)
    if report["capture_group_examples"]:
        print()
        print("CAPTURE GROUP EXAMPLES:")
        for row in report["capture_group_examples"]:
            print(row)
    if report["site_examples"]:
        print()
        print("SITE EXAMPLES:")
        for row in report["site_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: batch discovery gate only; hypotheses are reported independently "
        "and may be false without making the structural audit invalid."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
