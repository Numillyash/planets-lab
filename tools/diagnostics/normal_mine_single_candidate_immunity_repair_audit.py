from __future__ import annotations

from math import hypot, sqrt
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import (
    _segment_intersects_field,
    build_mine_evidence_context,
    nearest_damage_quantum,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"

GAME_ID = 511506
BEFORE_TURN = 23
SHIP_ID = 160
EXPECTED_HULL = 17
EXPECTED_OWNER = 3

RELATION_LABELS = {
    -1: "blocked",
    0: "none",
    1: "ambassador",
    2: "safe_passage",
    3: "share_intel",
    4: "full_alliance",
}


def _load_row() -> dict[str, Any]:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "after_archive_turn",
            "ship_id",
            "hull_id",
            "warp",
            "is_gravitonic_hull",
            "x_before",
            "y_before",
            "x_after",
            "y_after",
            "target_x",
            "target_y",
            "observed_distance",
            "nominal_max_distance",
        ]
        rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM {RESIDUAL_VIEW}
            WHERE game_id = ? AND before_archive_turn = ? AND ship_id = ?
            """,
            [GAME_ID, BEFORE_TURN, SHIP_ID],
        ).fetchall()
    finally:
        con.close()
    if len(rows) != 1:
        raise SystemExit(f"expected exactly one candidate row, found {len(rows)}")
    return dict(zip(names, rows[0]))


def _sample(row: Mapping[str, Any]) -> MovementSample:
    return MovementSample(
        turn=int(row["before_archive_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        gravitonic=row["is_gravitonic_hull"] is True,
        game_id=int(row["game_id"]),
        hull_id=int(row["hull_id"]) if row["hull_id"] is not None else None,
    )


def _planned_vector(sample: MovementSample, nominal_distance: float) -> tuple[tuple[float, float], float, float]:
    dx = float(sample.target_x - sample.x)
    dy = float(sample.target_y - sample.y)
    target_distance = hypot(dx, dy)
    if target_distance <= 1e-9:
        return (0.0, 0.0), 0.0, 0.0
    planned_distance = min(target_distance, max(0.0, nominal_distance))
    scale = planned_distance / target_distance
    return (dx * scale, dy * scale), planned_distance, target_distance


def _exact_relation(relations: Any, *, target_slot: int, field_owner: int) -> Mapping[str, Any] | None:
    if not isinstance(relations, list):
        return None
    matches = []
    for raw in relations:
        if not isinstance(raw, Mapping):
            continue
        if _intish(raw.get("playerid")) == target_slot and _intish(raw.get("playertoid")) == field_owner:
            matches.append(raw)
    return matches[0] if len(matches) == 1 else None


def _player_excerpt(players: Any, slot: int) -> dict[str, Any] | None:
    if not isinstance(players, list):
        return None
    for raw in players:
        if not isinstance(raw, Mapping) or _intish(raw.get("id")) != slot:
            continue
        return {
            "raceid": _intish(raw.get("raceid")),
            "teamid": _intish(raw.get("teamid")),
        }
    return None


def _relation_excerpt(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    relation_to = _intish(raw.get("relationto"))
    relation_from = _intish(raw.get("relationfrom"))
    return {
        "playerid": _intish(raw.get("playerid")),
        "playertoid": _intish(raw.get("playertoid")),
        "relationto": relation_to,
        "relationfrom": relation_from,
        "relationto_label": RELATION_LABELS.get(relation_to, "unknown"),
        "relationfrom_label": RELATION_LABELS.get(relation_from, "unknown"),
        "conflictlevel": _intish(raw.get("conflictlevel")),
    }


def _field_code_candidates(raw: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in raw.items():
        lowered = str(key).lower().replace("_", "")
        if lowered in {"friendlycode", "fcode", "fc"} or "friendlycode" in lowered:
            if isinstance(value, str):
                result[str(key)] = value
    return result


def _field_raw_excerpts(prepared: Any, *, archive_turn: int, field_id: int | None, owner_id: int | None) -> list[dict[str, Any]]:
    excerpts: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for snapshot in prepared.snapshots:
        if snapshot.archive_turn != archive_turn:
            continue
        raw_fields = snapshot.mechanics_payload.get("minefields", [])
        if not isinstance(raw_fields, list):
            continue
        for raw in raw_fields:
            if not isinstance(raw, Mapping):
                continue
            if _intish(raw.get("id")) != field_id or _intish(raw.get("ownerid")) != owner_id:
                continue
            codes = _field_code_candidates(raw)
            identity = (
                snapshot.player_id,
                _intish(raw.get("id")),
                _intish(raw.get("ownerid")),
                raw.get("x"), raw.get("y"), raw.get("radius"),
                tuple(sorted(codes.items())),
            )
            if identity in seen:
                continue
            seen.add(identity)
            excerpts.append({
                "perspective_player": snapshot.player_id,
                "id": _intish(raw.get("id")),
                "ownerid": _intish(raw.get("ownerid")),
                "x": raw.get("x"),
                "y": raw.get("y"),
                "radius": raw.get("radius"),
                "isweb": raw.get("isweb"),
                "friendly_code_fields": codes,
            })
    return excerpts


def _route_interval(*, origin: tuple[int, int], vector: tuple[float, float], field: Any, topology: Any) -> tuple[float, float, float] | None:
    length = hypot(*vector)
    if length <= 1e-9:
        return None
    center = (int(round(field.x)), int(round(field.y)))
    cx, cy = _vector(origin, center, topology)
    ux, uy = vector[0] / length, vector[1] / length
    along = cx * ux + cy * uy
    perp_sq = max(0.0, cx * cx + cy * cy - along * along)
    radius = float(field.radius) + 1.0
    if perp_sq > radius * radius:
        return None
    half = sqrt(max(0.0, radius * radius - perp_sq))
    entry = max(0.0, along - half)
    exit_ = min(length, along + half)
    if exit_ < entry:
        return None
    return entry, exit_, max(0.0, exit_ - entry)


def _repair_prediction(*, before_damage: int, before_supplies: int, quantum: int, hits: int) -> dict[str, int]:
    raw_damage = before_damage + quantum * hits
    repair_percent = min(raw_damage, before_supplies // 5)
    supplies_used = repair_percent * 5
    return {
        "hits": hits,
        "raw_damage_before_repair": raw_damage,
        "repair_percent_from_before_supplies": repair_percent,
        "supplies_used": supplies_used,
        "predicted_damage_after_supply_repair": raw_damage - repair_percent,
        "predicted_supplies_after_supply_repair": before_supplies - supplies_used,
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    row = _load_row()
    archive_path = RAW_DIR / f"game-{GAME_ID}.zip"
    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=GAME_ID,
        cache_path=PREPARED_DIR / f"game-{GAME_ID}.pickle",
    )
    context = build_mine_evidence_context(
        game_id=GAME_ID,
        archive_data=archive_data,
        snapshots=prepared.snapshots,
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")

    before_turn = int(row["before_archive_turn"])
    after_turn = int(row["after_archive_turn"])
    owner_id, owner = _owner_record(ship_groups.get((before_turn, SHIP_ID), ()))
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, SHIP_ID), ()))
    if owner_id != EXPECTED_OWNER or owner is None:
        raise SystemExit(f"owner guard failed: expected {EXPECTED_OWNER}, got {owner_id}")
    if after_owner_id != owner_id or after_owner is None:
        raise SystemExit("after-owner identity unavailable")

    hull_id = int(row["hull_id"]) if row["hull_id"] is not None else None
    if hull_id != EXPECTED_HULL:
        raise SystemExit(f"hull guard failed: expected {EXPECTED_HULL}, got {hull_id}")
    hull = context.specs.hulls.get(hull_id)
    if hull is None:
        raise SystemExit("missing hull spec")

    sample = _sample(row)
    raw_topology = extract_map_topology(archive_data)
    topology = effective_sphere_topology(game_id=GAME_ID, topology=raw_topology)
    effective_sample = sample
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        effective_sample = sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )

    regular_vector, planned_distance, target_distance = _planned_vector(
        effective_sample,
        float(row["nominal_max_distance"] or 0.0),
    )
    origin = (effective_sample.x, effective_sample.y)
    observed_distance = hypot(
        effective_sample.next_x - effective_sample.x,
        effective_sample.next_y - effective_sample.y,
    )

    enemy_normal_fields = [
        field for field in context.fields(after_turn)
        if not field.is_web
        and field.owner_id is not None
        and field.owner_id > 0
        and field.owner_id != owner_id
    ]
    intersected = [
        field for field in enemy_normal_fields
        if _segment_intersects_field(
            origin=origin,
            vector=regular_vector,
            field_record=field,
            topology=topology,
        )
    ]

    members = [
        member for member in turn_members(archive_data)
        if member.turn == before_turn and member.player == owner_id
    ]
    if len(members) != 1:
        raise SystemExit(f"expected one raw owner member, found {[m.name for m in members]}")
    raw_member = members[0]
    raw_bytes = read_archive_members(archive_data, [raw_member.name])[raw_member.name]
    parsed, _ = _decode_member_json(raw_bytes, raw_member)
    relations = parsed.get("relations")
    players = parsed.get("players")

    before_raw = owner.raw
    after_raw = after_owner.raw
    ship_fc = before_raw.get("friendlycode") if isinstance(before_raw.get("friendlycode"), str) else None
    before_damage = _intish(before_raw.get("damage"))
    before_supplies = _intish(before_raw.get("supplies"))
    after_damage = _intish(after_raw.get("damage"))
    after_supplies = _intish(after_raw.get("supplies"))
    quantum = nearest_damage_quantum(hull.mass, web=False)

    print("===== NORMAL-MINE SINGLE CANDIDATE IMMUNITY / REPAIR AUDIT =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("game=", GAME_ID)
    print("turn=", before_turn)
    print("ship=", SHIP_ID)
    print("prepared_cache_hit=", cache_hit)
    print("owner_id=", owner_id)
    print("owner_player=", _player_excerpt(players, owner_id))
    print("hull_id=", hull_id)
    print("hull_tech=", hull.tech_level)
    print("hull_mass=", hull.mass)
    print("slowdown_tech_eligible=", hull.tech_level < 7)
    print("warp=", sample.warp)
    print("planned_distance=", round(planned_distance, 3))
    print("target_distance=", round(target_distance, 3))
    print("observed_distance=", round(observed_distance, 3))
    print("distance_deficit=", round(planned_distance - observed_distance, 3))
    print("normal_mine_damage_quantum=", quantum)
    print("ship_friendlycode=", ship_fc)
    print("ship_fc_is_universal_mfx_shape=", isinstance(ship_fc, str) and len(ship_fc) == 3 and ship_fc[:2].lower() == "mf")
    print("intersected_normal_field_count=", len(intersected))

    print("\n===== INTERSECTED FIELD ELIGIBILITY =====")
    hostile_count = 0
    immune_count = 0
    unresolved_count = 0
    for field in intersected:
        owner_slot = int(field.owner_id) if field.owner_id is not None else None
        relation = _exact_relation(relations, target_slot=owner_id, field_owner=owner_slot) if owner_slot is not None else None
        relation_from = _intish(relation.get("relationfrom")) if relation is not None else None
        owner_grants_safe_passage = relation_from is not None and relation_from >= 2
        target_player = _player_excerpt(players, owner_id)
        field_player = _player_excerpt(players, owner_slot) if owner_slot is not None else None
        same_nonzero_team = bool(
            target_player is not None and field_player is not None
            and target_player.get("teamid") is not None and target_player.get("teamid") > 0
            and target_player.get("teamid") == field_player.get("teamid")
        )

        excerpts = _field_raw_excerpts(
            prepared,
            archive_turn=after_turn,
            field_id=field.field_id,
            owner_id=field.owner_id,
        )
        field_codes = sorted({
            code
            for excerpt in excerpts
            for code in excerpt.get("friendly_code_fields", {}).values()
            if isinstance(code, str)
        })
        exact_field_fc_match = ship_fc is not None and ship_fc in field_codes
        universal_mfx_possible_from_ship_code = isinstance(ship_fc, str) and len(ship_fc) == 3 and ship_fc[:2].lower() == "mf"

        if owner_grants_safe_passage or same_nonzero_team or exact_field_fc_match:
            verdict = "IMMUNE"
            immune_count += 1
        elif field_codes or not universal_mfx_possible_from_ship_code:
            # A non-MFx ship code cannot use universal MFx. If no SP/team and an
            # explicit field code is either known non-matching or absent, the only
            # remaining uncertainty is whether the API omitted the specific field FC.
            if field_codes:
                verdict = "HOSTILE"
                hostile_count += 1
            else:
                verdict = "UNRESOLVED_FIELD_FC_NOT_EXPOSED"
                unresolved_count += 1
        else:
            verdict = "UNRESOLVED"
            unresolved_count += 1

        interval = _route_interval(
            origin=origin,
            vector=regular_vector,
            field=field,
            topology=topology,
        )
        print({
            "field_id": field.field_id,
            "field_owner": owner_slot,
            "field_owner_player": field_player,
            "relation": _relation_excerpt(relation),
            "owner_grants_safe_passage": owner_grants_safe_passage,
            "same_nonzero_team": same_nonzero_team,
            "field_friendly_codes": field_codes,
            "exact_ship_field_fc_match": exact_field_fc_match,
            "route_interval_ly": tuple(round(v, 3) for v in interval) if interval else None,
            "raw_field_excerpts": excerpts,
            "verdict": verdict,
        })

    print("\n===== REPAIR TRACE =====")
    print("before_damage=", before_damage)
    print("before_supplies=", before_supplies)
    print("after_damage_observed=", after_damage)
    print("after_supplies_observational=", after_supplies)
    if quantum is not None and before_damage is not None and before_supplies is not None:
        one = _repair_prediction(
            before_damage=before_damage,
            before_supplies=before_supplies,
            quantum=quantum,
            hits=1,
        )
        two = _repair_prediction(
            before_damage=before_damage,
            before_supplies=before_supplies,
            quantum=quantum,
            hits=2,
        )
        print("one_hit_supply_repair_prediction=", one)
        print("two_hit_supply_repair_prediction=", two)
        print("one_hit_damage_matches_observed=", after_damage == one["predicted_damage_after_supply_repair"])
        print("one_hit_supplies_match_observed=", after_supplies == one["predicted_supplies_after_supply_repair"])
        print("two_hit_damage_matches_observed=", after_damage == two["predicted_damage_after_supply_repair"])
        print("two_hit_supplies_match_observed=", after_supplies == two["predicted_supplies_after_supply_repair"])

    print("\n===== SUMMARY =====")
    print("intersected_normal_fields=", len(intersected))
    print("explicitly_hostile_fields=", hostile_count)
    print("explicitly_immune_fields=", immune_count)
    print("unresolved_fields=", unresolved_count)
    print("one_hit_repair_trace_candidate=", bool(
        quantum is not None and before_damage is not None and before_supplies is not None
        and after_damage == _repair_prediction(before_damage=before_damage, before_supplies=before_supplies, quantum=quantum, hits=1)["predicted_damage_after_supply_repair"]
    ))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This audit resolves deterministic eligibility for the sole tech<7 10*N candidate. "
        "Safe Passage is directional from minefield owner to target; matching minefield FC also grants passage. "
        "The ship code here is checked for universal MFx shape, but absence of an exposed field FC remains fail-closed. "
        "Repair predictions use only submitted before-turn supplies and the corpus-observed normal-mine damage quantum. "
        "after.supplies is observational/editable and therefore corroborating rather than causal evidence. "
        "No mine-hit RNG or production label is inferred here."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
