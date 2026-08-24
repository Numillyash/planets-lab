from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import (
    extract_map_topology,
    sphere_adjusted_sample,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from mine_hit_hostorder_differential_audit import _owner_states


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
HORWASP_HULL_IDS = frozenset(range(201, 214))
LIZARD_RACE_ID = 2


def _race_map(snapshots: Sequence[Any]) -> dict[int, int]:
    observed: dict[int, set[int]] = defaultdict(set)
    for snapshot in snapshots:
        payload = snapshot.mechanics_payload
        candidates: list[Any] = []
        player = payload.get("player") if isinstance(payload, Mapping) else None
        players = payload.get("players", []) if isinstance(payload, Mapping) else []
        if isinstance(player, Mapping):
            candidates.append(player)
        if isinstance(players, list):
            candidates.extend(item for item in players if isinstance(item, Mapping))
        for raw in candidates:
            player_id = _intish(raw.get("id"))
            race_id = _intish(raw.get("raceid"))
            if player_id is not None and player_id > 0 and race_id is not None and race_id > 0:
                observed[player_id].add(race_id)
    return {
        player_id: next(iter(races))
        for player_id, races in observed.items()
        if len(races) == 1
    }


def _max_warp_from_damage(damage: int | None, race_id: int | None) -> int | None:
    if damage is None or damage < 0 or race_id is None:
        return None
    if race_id == LIZARD_RACE_ID:
        if damage > 150:
            return None
        return max(0, min(9, 15 - damage // 10))
    if damage >= 100:
        return None
    return max(0, min(9, 10 - damage // 10))


def _ratio_bucket(distance: float, nominal: float) -> str:
    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (
        ("~0.5x", 0.5),
        ("~1.0x", 1.0),
        ("~1.5x", 1.5),
        ("~2.0x", 2.0),
        ("~3.0x", 3.0),
    ):
        if abs(ratio - target) <= 0.08:
            return label
    if ratio < 0.5:
        return "<0.5x"
    if ratio < 1.0:
        return "0.5-1.0x"
    if ratio < 1.5:
        return "1.0-1.5x"
    if ratio < 2.0:
        return "1.5-2.0x"
    if ratio < 3.0:
        return "2.0-3.0x"
    return ">3.0x"


def _direction_bucket(
    *,
    x: int,
    y: int,
    next_x: int,
    next_y: int,
    target_x: int,
    target_y: int,
) -> str:
    odx, ody = next_x - x, next_y - y
    tdx, tdy = target_x - x, target_y - y
    observed_norm = hypot(odx, ody)
    target_norm = hypot(tdx, tdy)
    if observed_norm <= 1e-9:
        return "observed_stationary"
    if target_norm <= 1e-9:
        return "target_is_origin"
    cosine = (odx * tdx + ody * tdy) / (observed_norm * target_norm)
    if cosine >= 0.98:
        return "same_line_forward"
    if cosine >= 0.75:
        return "mostly_forward"
    if cosine <= -0.98:
        return "same_line_reverse"
    if cosine <= -0.75:
        return "mostly_reverse"
    if -0.25 <= cosine <= 0.25:
        return "roughly_perpendicular"
    return "oblique"


def _target_relation(
    *,
    x: int,
    y: int,
    next_x: int,
    next_y: int,
    target_x: int,
    target_y: int,
) -> str:
    origin = (x, y)
    observed = (next_x, next_y)
    target = (target_x, target_y)
    if observed == origin and target == origin:
        return "observed=origin,target=origin"
    if observed == origin:
        return "observed=origin"
    if target == origin:
        return "target=origin"
    if observed == target:
        return "observed=target"
    return "observed=other"


def _adjusted_sample(
    *,
    game_id: int,
    topology: Any,
    turn: int,
    ship_id: int,
    hull_id: int,
    warp: int,
    gravitonic: bool,
    x: int,
    y: int,
    next_x: int,
    next_y: int,
    target_x: int,
    target_y: int,
) -> MovementSample:
    sample = MovementSample(
        turn=turn,
        ship_id=ship_id,
        x=x,
        y=y,
        target_x=target_x,
        target_y=target_y,
        warp=warp,
        next_x=next_x,
        next_y=next_y,
        hull_id=hull_id,
        gravitonic=gravitonic,
        game_id=game_id,
    )
    effective = effective_sphere_topology(game_id=game_id, topology=topology)
    if (
        effective.sphere is True
        and effective.mapwidth is not None
        and effective.mapheight is not None
    ):
        return sphere_adjusted_sample(
            sample,
            width=int(effective.mapwidth),
            height=int(effective.mapheight),
        )
    return sample


def _prediction(
    *,
    game_id: int,
    topology: Any,
    turn: int,
    ship_id: int,
    hull_id: int,
    requested_warp: int,
    damage: int,
    race_id: int,
    gravitonic: bool,
    x: int,
    y: int,
    next_x: int,
    next_y: int,
    target_x: int,
    target_y: int,
) -> tuple[int, bool, float] | None:
    damage_limit = _max_warp_from_damage(damage, race_id)
    if damage_limit is None:
        return None
    effective_warp = min(requested_warp, damage_limit)
    sample = _adjusted_sample(
        game_id=game_id,
        topology=topology,
        turn=turn,
        ship_id=ship_id,
        hull_id=hull_id,
        warp=effective_warp,
        gravitonic=gravitonic,
        x=x,
        y=y,
        next_x=next_x,
        next_y=next_y,
        target_x=target_x,
        target_y=target_y,
    )
    predicted = host_major_minor_destination(sample)
    exact = predicted == sample.observed_destination
    predicted_distance = hypot(predicted[0] - sample.x, predicted[1] - sample.y)
    return effective_warp, exact, predicted_distance


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the current generic final movement residual for documented damage-limited "
            "maximum-warp signatures. It compares Host-major/minor destinations using raw "
            "pre-movement damage and a conservative current-supplies repair bracket."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                hull_id,
                warp,
                coalesce(is_gravitonic_hull, false),
                baseline_category,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                coalesce(observed_distance, 0.0),
                coalesce(nominal_max_distance, 0.0)
            FROM movement_post_mine_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp BETWEEN 1 AND 9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== DAMAGE-LIMITED WARP RESIDUAL AUDIT =====")
    print("residual_view= movement_post_mine_strong_residual")
    print("generic_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    exact_hulls = Counter()
    exact_games = Counter()
    exact_races = Counter()
    exact_effective_warps = Counter()
    exact_signatures = Counter()
    target_hulls = Counter()
    target_games = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        topology = extract_map_topology(archive_data)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races = _race_map(prepared.snapshots)
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            (
                _gid,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                requested_warp,
                gravitonic,
                baseline_category,
                x,
                y,
                next_x,
                next_y,
                target_x,
                target_y,
                observed_distance,
                nominal_max_distance,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            requested_warp = int(requested_warp)
            gravitonic = bool(gravitonic)
            x, y = int(x), int(y)
            next_x, next_y = int(next_x), int(next_y)
            target_x, target_y = int(target_x), int(target_y)
            observed_distance = float(observed_distance)
            nominal_max_distance = float(nominal_max_distance)

            ratio = _ratio_bucket(observed_distance, nominal_max_distance)
            relation = _target_relation(
                x=x,
                y=y,
                next_x=next_x,
                next_y=next_y,
                target_x=target_x,
                target_y=target_y,
            )
            direction = _direction_bucket(
                x=x,
                y=y,
                next_x=next_x,
                next_y=next_y,
                target_x=target_x,
                target_y=target_y,
            )
            target_short = (
                requested_warp >= 7
                and ratio == "<0.5x"
                and relation == "observed=other"
                and direction == "same_line_forward"
            )
            if target_short:
                totals["target_short_forward_rows"] += 1
                target_hulls[hull_id] += 1
                target_games[game_id] += 1

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None:
                totals["owner_state_missing"] += 1
                continue
            if not same_identity:
                totals["identity_break_after"] += 1
                continue
            totals["same_identity_after"] += 1

            race_id = races.get(owner_id)
            damage_before = _intish(before_raw.get("damage"))
            supplies_before = _intish(before_raw.get("supplies"))
            if damage_before is None or race_id is None:
                totals["damage_or_race_missing"] += 1
                continue
            totals["formula_ready"] += 1
            if damage_before > 0:
                totals["damaged_before"] += 1
            else:
                totals["undamaged_before"] += 1

            raw_prediction = _prediction(
                game_id=game_id,
                topology=topology,
                turn=before_turn,
                ship_id=ship_id,
                hull_id=hull_id,
                requested_warp=requested_warp,
                damage=damage_before,
                race_id=race_id,
                gravitonic=gravitonic,
                x=x,
                y=y,
                next_x=next_x,
                next_y=next_y,
                target_x=target_x,
                target_y=target_y,
            )
            if raw_prediction is None:
                totals["raw_prediction_unavailable"] += 1
                continue
            raw_effective_warp, raw_exact, raw_predicted_distance = raw_prediction
            damage_limited = raw_effective_warp < requested_warp
            if damage_limited:
                totals["raw_damage_limited"] += 1
                if target_short:
                    totals["target_short_raw_damage_limited"] += 1
            else:
                totals["raw_not_damage_limited"] += 1

            if raw_exact:
                totals["raw_endpoint_exact"] += 1
                if damage_limited:
                    totals["raw_damage_limited_endpoint_exact"] += 1
                else:
                    totals["raw_not_damage_limited_endpoint_exact_control"] += 1
                if damage_before == 0:
                    totals["undamaged_endpoint_exact_control"] += 1
                if target_short:
                    totals["target_short_raw_endpoint_exact"] += 1
                exact_hulls[hull_id] += 1
                exact_games[game_id] += 1
                exact_races[race_id] += 1
                exact_effective_warps[raw_effective_warp] += 1
                exact_signatures[(requested_warp, raw_effective_warp, ratio, relation, direction)] += 1

            max_current_supply_repair = max(0, (supplies_before or 0) // 5)
            min_damage = max(0, damage_before - max_current_supply_repair)
            bracket_matches: list[tuple[int, int, float]] = []
            for effective_damage in range(min_damage, damage_before + 1):
                prediction = _prediction(
                    game_id=game_id,
                    topology=topology,
                    turn=before_turn,
                    ship_id=ship_id,
                    hull_id=hull_id,
                    requested_warp=requested_warp,
                    damage=effective_damage,
                    race_id=race_id,
                    gravitonic=gravitonic,
                    x=x,
                    y=y,
                    next_x=next_x,
                    next_y=next_y,
                    target_x=target_x,
                    target_y=target_y,
                )
                if prediction is None:
                    continue
                effective_warp, exact, predicted_distance = prediction
                if exact and effective_warp < requested_warp:
                    bracket_matches.append((effective_damage, effective_warp, predicted_distance))

            bracket_exact = bool(bracket_matches)
            if bracket_exact:
                totals["current_supply_bracket_endpoint_exact"] += 1
                if target_short:
                    totals["target_short_current_supply_bracket_exact"] += 1
            any_exact = raw_exact and damage_limited or bracket_exact
            if any_exact:
                totals["damage_limit_any_exact"] += 1
                if target_short:
                    totals["target_short_damage_limit_any_exact"] += 1

            low_supply = supplies_before is not None and supplies_before < 5
            if raw_exact and damage_limited and low_supply:
                totals["raw_exact_low_supply"] += 1
                if target_short:
                    totals["target_short_raw_exact_low_supply"] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "race_id": race_id,
                "lizard": race_id == LIZARD_RACE_ID,
                "baseline": str(baseline_category),
                "ratio_bucket": ratio,
                "target_relation": relation,
                "direction": direction,
                "gravitonic": gravitonic,
                "requested_warp": requested_warp,
                "damage_before": damage_before,
                "supplies_before": supplies_before,
                "raw_effective_warp": raw_effective_warp,
                "observed_distance": round(observed_distance, 3),
                "raw_predicted_distance": round(raw_predicted_distance, 3),
                "raw_exact": raw_exact,
                "repair_damage_matches": [item[0] for item in bracket_matches],
                "repair_warp_matches": sorted({item[1] for item in bracket_matches}),
            }
            bucket = None
            if target_short and raw_exact and damage_limited:
                bucket = "target_raw_exact"
            elif target_short and bracket_exact:
                bucket = "target_repair_bracket"
            elif target_short:
                bucket = "target_unexplained"
            elif raw_exact and damage_limited:
                bucket = "other_raw_exact"
            if bucket is not None and len(examples[bucket]) < args.examples:
                examples[bucket].append(detail)

    print("\n===== POPULATION =====")
    for key in (
        "target_short_forward_rows",
        "same_identity_after",
        "identity_break_after",
        "owner_state_missing",
        "damage_or_race_missing",
        "formula_ready",
        "damaged_before",
        "undamaged_before",
        "raw_damage_limited",
        "raw_not_damage_limited",
    ):
        print(f"{key}=", totals[key])

    print("\n===== DAMAGE-LIMIT DIFFERENTIAL =====")
    for key in (
        "raw_endpoint_exact",
        "raw_damage_limited_endpoint_exact",
        "current_supply_bracket_endpoint_exact",
        "damage_limit_any_exact",
        "raw_exact_low_supply",
        "raw_not_damage_limited_endpoint_exact_control",
        "undamaged_endpoint_exact_control",
    ):
        print(f"{key}=", totals[key])

    print("\n===== TARGET 121 SHORT-FORWARD FAMILY =====")
    for key in (
        "target_short_forward_rows",
        "target_short_raw_damage_limited",
        "target_short_raw_endpoint_exact",
        "target_short_current_supply_bracket_exact",
        "target_short_damage_limit_any_exact",
        "target_short_raw_exact_low_supply",
    ):
        print(f"{key}=", totals[key])

    print("\n===== TARGET SHORT-FORWARD HULLS =====")
    for hull_id, count in target_hulls.most_common(40):
        print(hull_id, count)

    print("\n===== TARGET SHORT-FORWARD GAMES =====")
    for game_id, count in target_games.most_common():
        print(game_id, count)

    print("\n===== RAW EXACT BY HULL =====")
    for hull_id, count in exact_hulls.most_common(40):
        print(hull_id, count)

    print("\n===== RAW EXACT BY GAME =====")
    for game_id, count in exact_games.most_common():
        print(game_id, count)

    print("\n===== RAW EXACT BY RACE =====")
    for race_id, count in exact_races.most_common():
        print(race_id, count)

    print("\n===== RAW EXACT EFFECTIVE WARP =====")
    for warp, count in sorted(exact_effective_warps.items()):
        print(warp, count)

    print("\n===== RAW EXACT SIGNATURES =====")
    for signature, count in exact_signatures.most_common(40):
        print(signature, count)

    for bucket, title in (
        ("target_raw_exact", "TARGET SHORT-FORWARD RAW-DAMAGE EXACT EXAMPLES"),
        ("target_repair_bracket", "TARGET SHORT-FORWARD SUPPLY-BRACKET EXAMPLES"),
        ("target_unexplained", "TARGET SHORT-FORWARD STILL-UNEXPLAINED EXAMPLES"),
        ("other_raw_exact", "OTHER RESIDUAL RAW-DAMAGE EXACT EXAMPLES"),
    ):
        print(f"\n===== {title} =====")
        for detail in examples[bucket]:
            print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Damage-limited warp is promoted only from exact Host-major/minor destination matches "
        "with requested warp above the documented damage limit. The current-supplies bracket "
        "is evidence only because transfers, starbase repair and other pre-movement Host-order "
        "effects can change damage/supplies before Most Ships Move. Undamaged and not-limited "
        "exact matches are negative controls; investigate them before any production change."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
