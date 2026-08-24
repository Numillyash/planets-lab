from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot, pi, sqrt
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot, _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
HORWASP_HULL_IDS = frozenset(range(201, 214))


def _floatish(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _first(raw: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return None


def _static_specs(archive_data: bytes) -> NuStaticSpecs:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    member = members[0]
    raw = read_archive_members(archive_data, [member.name])[member.name]
    payload, _ = _decode_member_json(raw, member)
    return NuStaticSpecs.from_catalog(import_static_all(payload))


def _cross_track_and_progress(
    target_vector: tuple[int, int],
    observed_vector: tuple[int, int],
) -> tuple[float | None, float | None]:
    tx, ty = target_vector
    ox, oy = observed_vector
    target_distance = hypot(tx, ty)
    if target_distance <= 1e-9:
        return None, None
    cross_track = abs(tx * oy - ty * ox) / target_distance
    progress = (tx * ox + ty * oy) / target_distance
    return cross_track, progress


def _minefield_radius(raw: Mapping[str, Any]) -> tuple[float | None, str]:
    radius = _floatish(_first(raw, "radius", "minefieldradius", "minefield_radius"))
    if radius is not None and radius >= 0:
        return radius, "radius"

    # In VGA/Planets minefield geometry, one mine is distributed per pi square
    # light-years, so a field with N mine units has radius sqrt(N). Keep the
    # inference explicit in output rather than treating it as a raw field.
    units = _floatish(_first(raw, "units", "mines", "mineunits", "mine_units"))
    if units is not None and units >= 0:
        return sqrt(units), "sqrt_units"
    return None, "missing"


def _parse_minefield(raw: Mapping[str, Any]) -> dict[str, Any]:
    radius, radius_source = _minefield_radius(raw)
    return {
        "id": _intish(_first(raw, "id", "minefieldid", "minefield_id")),
        "owner_id": _intish(_first(raw, "ownerid", "owner_id")),
        "x": _floatish(_first(raw, "x", "centerx", "center_x")),
        "y": _floatish(_first(raw, "y", "centery", "center_y")),
        "radius": radius,
        "radius_source": radius_source,
        "is_web": _boolish(_first(raw, "isweb", "is_web", "web", "webmine", "iswebmine")),
        "keys": tuple(sorted(str(key) for key in raw)),
    }


def _minefields_for_snapshots(
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    archive_turn: int,
    player_id: int | None = None,
) -> tuple[list[dict[str, Any]], Counter[tuple[str, ...]]]:
    parsed: list[dict[str, Any]] = []
    keysets: Counter[tuple[str, ...]] = Counter()
    seen: set[tuple[Any, ...]] = set()

    for snapshot in snapshots:
        if snapshot.archive_turn != archive_turn:
            continue
        if player_id is not None and snapshot.player_id != player_id:
            continue
        raw_fields = snapshot.mechanics_payload.get("minefields", [])
        if not isinstance(raw_fields, list):
            continue
        for raw in raw_fields:
            if not isinstance(raw, Mapping):
                continue
            field = _parse_minefield(raw)
            keysets[field["keys"]] += 1
            identity = (
                field["id"],
                field["owner_id"],
                field["x"],
                field["y"],
                None if field["radius"] is None else round(float(field["radius"]), 6),
                field["is_web"],
            )
            if identity in seen:
                continue
            seen.add(identity)
            parsed.append(field)
    return parsed, keysets


def _field_parseable(field: Mapping[str, Any]) -> bool:
    return (
        field.get("x") is not None
        and field.get("y") is not None
        and field.get("radius") is not None
        and field.get("is_web") is not None
    )


def _enemyish(field: Mapping[str, Any], owner_id: int) -> bool:
    field_owner = field.get("owner_id")
    return isinstance(field_owner, int) and field_owner > 0 and field_owner != owner_id


def _point_in_field(
    point: tuple[int, int],
    field: Mapping[str, Any],
    topology: Any,
    *,
    tolerance: float = 1.0,
) -> bool:
    if not _field_parseable(field):
        return False
    center = (int(round(float(field["x"]))), int(round(float(field["y"]))))
    dx, dy = _vector(center, point, topology)
    return hypot(dx, dy) <= float(field["radius"]) + tolerance


def _segment_intersects_field(
    *,
    origin: tuple[int, int],
    target_vector: tuple[int, int],
    field: Mapping[str, Any],
    topology: Any,
    tolerance: float = 1.0,
) -> bool:
    if not _field_parseable(field):
        return False
    center = (int(round(float(field["x"]))), int(round(float(field["y"]))))
    cx, cy = _vector(origin, center, topology)
    tx, ty = target_vector
    length_sq = tx * tx + ty * ty
    if length_sq <= 1e-9:
        return hypot(cx, cy) <= float(field["radius"]) + tolerance
    t = (cx * tx + cy * ty) / length_sq
    t = min(1.0, max(0.0, t))
    closest_x = t * tx
    closest_y = t * ty
    return hypot(cx - closest_x, cy - closest_y) <= float(field["radius"]) + tolerance


def _owner_post_state(
    *,
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    before_turn: int,
    after_turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None, Mapping[str, Any] | None]:
    owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
    if owner_id is None or before_owner is None:
        return None, None, None
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
    if after_owner_id != owner_id or after_owner is None:
        return owner_id, before_owner.raw, None
    return owner_id, before_owner.raw, after_owner.raw


def _post_reset_signature(after_raw: Mapping[str, Any] | None, observed: tuple[int, int]) -> bool:
    if after_raw is None:
        return False
    warp = _intish(after_raw.get("warp"))
    target_x = _intish(after_raw.get("targetx", after_raw.get("waypointx")))
    target_y = _intish(after_raw.get("targety", after_raw.get("waypointy")))
    return warp == 0 and (target_x, target_y) == observed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit generic short same-line movement residuals for observed normal/web "
            "mine-hit signatures. Private prepared state is read locally; output is "
            "restricted to derived mechanical evidence."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=30)
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
                baseline_category,
                warp,
                is_gravitonic_hull,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                nominal_max_distance
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp BETWEEN 1 AND 9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== MINE-HIT GENERIC RESIDUAL AUDIT =====")
    print("generic_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    schema_keysets: Counter[tuple[str, ...]] = Counter()
    radius_sources = Counter()
    candidate_hulls = Counter()
    candidate_games = Counter()
    web_state_hulls = Counter()
    web_state_games = Counter()
    web_strong_hulls = Counter()
    web_strong_games = Counter()
    normal_strong_hulls = Counter()
    normal_strong_games = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, prepared_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        specs = _static_specs(archive_data)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")

        # Collect schema coverage once per game over all snapshots, without
        # printing minefield ids/owners/coordinates.
        game_field_records = 0
        game_parseable = 0
        game_web = 0
        for snapshot in prepared.snapshots:
            raw_fields = snapshot.mechanics_payload.get("minefields", [])
            if not isinstance(raw_fields, list):
                continue
            for raw in raw_fields:
                if not isinstance(raw, Mapping):
                    continue
                field = _parse_minefield(raw)
                schema_keysets[field["keys"]] += 1
                radius_sources[str(field["radius_source"])] += 1
                game_field_records += 1
                if _field_parseable(field):
                    game_parseable += 1
                if field.get("is_web") is True:
                    game_web += 1

        print(
            f"prepared game={game_id} cache_hit={prepared_hit} rows={len(by_game[game_id])} "
            f"minefield_records={game_field_records} parseable={game_parseable} web={game_web} "
            f"raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )

        field_cache: dict[tuple[int, int | None], list[dict[str, Any]]] = {}

        def fields(turn: int, player_id: int | None) -> list[dict[str, Any]]:
            key = (turn, player_id)
            if key not in field_cache:
                parsed, _ = _minefields_for_snapshots(
                    prepared.snapshots,
                    archive_turn=turn,
                    player_id=player_id,
                )
                field_cache[key] = parsed
            return field_cache[key]

        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                baseline_category,
                warp,
                _is_gravitonic,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                nominal_max_distance,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            origin = (int(x_before), int(y_before))
            observed = (int(x_after), int(y_after))
            target = (int(target_x), int(target_y))

            observed_vector = _vector(origin, observed, topology)
            target_vector = _vector(origin, target, topology)
            observed_distance = hypot(*observed_vector)
            target_distance = hypot(*target_vector)
            nominal = float(nominal_max_distance or 0.0)
            regular_distance = min(target_distance, nominal)
            cross_track, progress = _cross_track_and_progress(target_vector, observed_vector)
            short_same_line = (
                cross_track is not None
                and progress is not None
                and cross_track <= 1.5
                and progress > 0.0
                and observed_distance > 0.0
                and observed_distance + 1.5 < regular_distance
            )
            if not short_same_line:
                continue

            totals["short_same_line_forward"] += 1
            candidate_hulls[hull_id] += 1
            candidate_games[game_id] += 1

            owner_id, before_raw, after_raw = _owner_post_state(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None:
                totals["owner_state_missing"] += 1
                continue
            if after_raw is None:
                totals["post_state_missing"] += 1

            before_damage = _intish(before_raw.get("damage"))
            after_damage = _intish(after_raw.get("damage")) if after_raw is not None else None
            damage_increase = (
                before_damage is not None
                and after_damage is not None
                and after_damage > before_damage
            )
            if damage_increase:
                totals["damage_increase"] += 1

            reset = _post_reset_signature(after_raw, observed)
            if reset:
                totals["post_warp0_waypoint_reset"] += 1
            web_state_signature = damage_increase and reset
            if web_state_signature:
                totals["web_state_signature"] += 1
                web_state_hulls[hull_id] += 1
                web_state_games[game_id] += 1

            owner_fields = fields(before_turn, owner_id) + fields(after_turn, owner_id)
            any_fields = fields(before_turn, None) + fields(after_turn, None)
            owner_enemy_fields = [field for field in owner_fields if _enemyish(field, owner_id)]
            any_enemy_fields = [field for field in any_fields if _enemyish(field, owner_id)]

            owner_parseable = [field for field in owner_enemy_fields if _field_parseable(field)]
            any_parseable = [field for field in any_enemy_fields if _field_parseable(field)]
            if owner_parseable:
                totals["owner_perspective_enemy_field_available"] += 1
            if any_parseable:
                totals["any_perspective_enemy_field_available"] += 1

            owner_web_at_observed = [
                field
                for field in owner_parseable
                if field.get("is_web") is True and _point_in_field(observed, field, topology)
            ]
            any_web_at_observed = [
                field
                for field in any_parseable
                if field.get("is_web") is True and _point_in_field(observed, field, topology)
            ]
            if owner_web_at_observed:
                totals["owner_visible_web_at_observed"] += 1
            if any_web_at_observed:
                totals["any_visible_web_at_observed"] += 1

            web_strong = web_state_signature and bool(any_web_at_observed)
            if web_strong:
                totals["web_strong"] += 1
                web_strong_hulls[hull_id] += 1
                web_strong_games[game_id] += 1

            hull_spec = specs.hulls.get(hull_id)
            hull_tech = hull_spec.tech_level if hull_spec is not None else None
            lost_distance = regular_distance - observed_distance
            inferred_hits = int(round(lost_distance / 10.0)) if lost_distance > 0 else 0
            ten_ly_match = (
                hull_tech is not None
                and hull_tech < 7
                and inferred_hits >= 1
                and abs(lost_distance - inferred_hits * 10.0) <= 1.5
            )
            if ten_ly_match:
                totals["normal_mine_10ly_geometry"] += 1

            if regular_distance > 0.0 and target_distance > 0.0:
                scale = regular_distance / target_distance
                regular_vector = (
                    int(round(target_vector[0] * scale)),
                    int(round(target_vector[1] * scale)),
                )
            else:
                regular_vector = (0, 0)

            any_normal_crossing = [
                field
                for field in any_parseable
                if field.get("is_web") is False
                and _segment_intersects_field(
                    origin=origin,
                    target_vector=regular_vector,
                    field=field,
                    topology=topology,
                )
            ]
            if any_normal_crossing:
                totals["any_visible_normal_field_crossing"] += 1

            normal_strong = damage_increase and ten_ly_match and bool(any_normal_crossing)
            if normal_strong:
                totals["normal_mine_strong"] += 1
                normal_strong_hulls[hull_id] += 1
                normal_strong_games[game_id] += 1

            before_fuel = _intish(before_raw.get("neutronium"))
            after_fuel = _intish(after_raw.get("neutronium")) if after_raw is not None else None
            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "baseline": str(baseline_category),
                "warp": warp,
                "hull_tech": hull_tech,
                "regular_distance": round(regular_distance, 3),
                "observed_distance": round(observed_distance, 3),
                "lost_distance": round(lost_distance, 3),
                "damage_before": before_damage,
                "damage_after": after_damage,
                "fuel_before": before_fuel,
                "fuel_after": after_fuel,
                "post_reset": reset,
                "owner_visible_web": bool(owner_web_at_observed),
                "any_visible_web": bool(any_web_at_observed),
                "normal_10ly_geometry": ten_ly_match,
                "any_visible_normal_crossing": bool(any_normal_crossing),
            }
            if web_strong and len(examples["web_strong"]) < args.examples:
                examples["web_strong"].append(detail)
            elif web_state_signature and len(examples["web_state"]) < args.examples:
                examples["web_state"].append(detail)
            if normal_strong and len(examples["normal_strong"]) < args.examples:
                examples["normal_strong"].append(detail)

    print("\n===== POPULATION =====")
    for key in (
        "short_same_line_forward",
        "owner_state_missing",
        "post_state_missing",
        "damage_increase",
        "post_warp0_waypoint_reset",
        "web_state_signature",
        "owner_perspective_enemy_field_available",
        "any_perspective_enemy_field_available",
        "owner_visible_web_at_observed",
        "any_visible_web_at_observed",
        "web_strong",
        "normal_mine_10ly_geometry",
        "any_visible_normal_field_crossing",
        "normal_mine_strong",
    ):
        print(f"{key}=", totals[key])

    print("\n===== SHORT SAME-LINE BY HULL =====")
    for hull_id, count in candidate_hulls.most_common(40):
        print(hull_id, count)

    print("\n===== SHORT SAME-LINE BY GAME =====")
    for game_id, count in candidate_games.most_common():
        print(game_id, count)

    print("\n===== WEB STATE SIGNATURE BY HULL =====")
    for hull_id, count in web_state_hulls.most_common():
        print(hull_id, count)
    print("web_state_games=", sorted(web_state_games))

    print("\n===== WEB STRONG BY HULL =====")
    for hull_id, count in web_strong_hulls.most_common():
        print(hull_id, count)
    print("web_strong_games=", sorted(web_strong_games))

    print("\n===== NORMAL MINE STRONG BY HULL =====")
    for hull_id, count in normal_strong_hulls.most_common():
        print(hull_id, count)
    print("normal_mine_strong_games=", sorted(normal_strong_games))

    print("\n===== MINEFIELD RADIUS SOURCE =====")
    for key, count in radius_sources.most_common():
        print(key, count)

    print("\n===== MINEFIELD RAW KEYSETS =====")
    for keyset, count in schema_keysets.most_common(12):
        print(count, list(keyset))

    for bucket in ("web_strong", "web_state", "normal_strong"):
        print(f"\n===== {bucket.upper()} EXAMPLES =====")
        for detail in examples[bucket]:
            print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "web_strong requires short same-line movement, a surviving owner-state damage increase, "
        "post-state Warp-0 plus waypoint reset to the observed endpoint, and an enemy web field "
        "containing that endpoint in at least one available perspective. web_state_signature is "
        "mechanically suggestive when field visibility is absent but is not by itself proof of a web hit."
    )
    print(
        "normal_mine_strong additionally requires a hull below tech 7, lost distance near an integer "
        "multiple of 10 ly, damage increase, and an observed enemy normal-mine corridor intersection. "
        "Minefield visibility and between-snapshot lay/decay/push changes remain explicit limitations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
