from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from math import hypot
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import (
    _damage_hit_candidates,
    _point_in_field,
    _segment_intersects_field,
    build_mine_evidence_context,
    classify_strong_mine_hit_transition,
    nearest_damage_quantum,
    scaled_floor_normal_mine_endpoint,
)
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS, _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.validation.movement_geometry import MovementSample

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR


EXPECTED_GAME = 360690
EXPECTED_CASES = 3


def _counter(text: str, key: str) -> int:
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"missing counter {key!r}")
    return int(matches[-1])


def _cases(path: Path) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    if _counter(text, "same_line_input") != EXPECTED_CASES:
        raise ValueError("unexpected same-line input")
    if _counter(text, "cases") != EXPECTED_CASES:
        raise ValueError("unexpected same-line case count")
    if _counter(text, "neither_model") != EXPECTED_CASES:
        raise ValueError("same-line proportional-fuel checkpoint no longer matches")
    try:
        block = text.split("===== CASES =====", 1)[1].split("===== INTERPRETATION =====", 1)[0]
    except IndexError as exc:
        raise ValueError("same-line reconciliation log has no CASES block") from exc
    result: list[dict[str, Any]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        item = ast.literal_eval(line)
        if isinstance(item, dict):
            result.append(item)
    if len(result) != EXPECTED_CASES:
        raise ValueError(f"parsed cases={len(result)} expected={EXPECTED_CASES}")
    if {int(item["game"]) for item in result} != {EXPECTED_GAME}:
        raise ValueError("same-line population moved to an unexpected game")
    return tuple(sorted(result, key=lambda item: int(item["turn"])))


def _owner_raw(ship_groups: Any, turn: int, ship_id: int) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _field_detail(field: Any) -> dict[str, Any]:
    return {
        "id": field.field_id,
        "owner": field.owner_id,
        "x": field.x,
        "y": field.y,
        "radius": field.radius,
        "is_web": field.is_web,
    }


def _hostile_fields(context: Any, turn: int, owner_id: int) -> tuple[Any, ...]:
    return tuple(
        field
        for field in context.fields(turn)
        if field.owner_id is not None and field.owner_id > 0 and field.owner_id != owner_id
    )


def _crossings(context: Any, fields: tuple[Any, ...], origin: tuple[int, int], waypoint: tuple[int, int]) -> tuple[Any, ...]:
    vector = _vector(origin, waypoint, context.topology)
    return tuple(
        field
        for field in fields
        if _segment_intersects_field(
            origin=origin,
            vector=vector,
            field_record=field,
            topology=context.topology,
        )
    )


def _damage_summary(raw_before: Mapping[str, Any], raw_after: Mapping[str, Any], hull_mass: int) -> dict[str, Any]:
    normal_quantum = nearest_damage_quantum(hull_mass, web=False)
    web_quantum = nearest_damage_quantum(hull_mass, web=True)
    return {
        "damage_before": _intish(raw_before.get("damage")),
        "damage_after": _intish(raw_after.get("damage")),
        "supplies_before": _intish(raw_before.get("supplies")),
        "supplies_after": _intish(raw_after.get("supplies")),
        "normal_quantum": normal_quantum,
        "web_quantum": web_quantum,
        "normal_hit_candidates": _damage_hit_candidates(
            before_raw=raw_before,
            after_raw=raw_after,
            quantum=normal_quantum,
        ),
        "web_hit_candidates": _damage_hit_candidates(
            before_raw=raw_before,
            after_raw=raw_after,
            quantum=web_quantum,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the three post-reconciliation same-line finite-fuel Tow rows for "
            "visible mine/web stop context, exact damage/supply hit traces and hull-special "
            "metadata. This is context cleanup only; hidden minefields remain possible and "
            "research-only scaled-floor matches outside the production scope are not promoted."
        )
    )
    parser.add_argument("--same-line-log", type=Path, required=True)
    args = parser.parse_args()

    cases = _cases(args.same_line_log)
    archive_path = RAW_DIR / f"game-{EXPECTED_GAME}.zip"
    cache_path = PREPARED_DIR / f"game-{EXPECTED_GAME}.pickle"
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    if not cache_path.is_file():
        raise FileNotFoundError(f"{cache_path}; bounded follow-up does not rebuild caches")

    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=EXPECTED_GAME,
        cache_path=cache_path,
    )
    context = build_mine_evidence_context(
        game_id=EXPECTED_GAME,
        archive_data=archive_data,
        snapshots=prepared.snapshots,
    )
    specs = context.specs
    ship_groups = context.ship_groups

    totals: Counter[str] = Counter(cases=len(cases))
    print("===== FINITE-FUEL TOW SAME-LINE STOP-CONTEXT AUDIT =====")
    print("same_line_log=", args.same_line_log)
    print("same_line_input=", len(cases))
    print("game=", EXPECTED_GAME, "cache_hit=", cache_hit, "sphere=", context.topology.sphere)

    for case in cases:
        turn = int(case["turn"])
        after_turn = turn + 1
        tower_id = int(case["tower_ship"])
        target_id = int(case["target_ship"])
        origin = tuple(int(v) for v in case["origin"])
        waypoint = tuple(int(v) for v in case["waypoint"])
        observed = tuple(int(v) for v in case["observed"])
        warp = int(case["warp"])

        tower_owner, tower_before = _owner_raw(ship_groups, turn, tower_id)
        tower_after_owner, tower_after = _owner_raw(ship_groups, after_turn, tower_id)
        target_owner, target_before = _owner_raw(ship_groups, turn, target_id)
        target_after_owner, target_after = _owner_raw(ship_groups, after_turn, target_id)
        if None in (tower_owner, tower_after_owner, target_owner, target_after_owner):
            raise ValueError(f"T{turn}: owner identity missing")
        if tower_before is None or tower_after is None or target_before is None or target_after is None:
            raise ValueError(f"T{turn}: owner-visible state missing")
        if tower_owner != tower_after_owner or target_owner != target_after_owner:
            raise ValueError(f"T{turn}: owner identity changed")

        tower_hull_id = _intish(tower_before.get("hullid", tower_before.get("hull_id")))
        target_hull_id = _intish(target_before.get("hullid", target_before.get("hull_id")))
        if tower_hull_id is None or target_hull_id is None:
            raise ValueError(f"T{turn}: hull id missing")
        tower_hull = specs.hulls.get(tower_hull_id)
        target_hull = specs.hulls.get(target_hull_id)
        if tower_hull is None or target_hull is None:
            raise ValueError(f"T{turn}: hull spec missing")

        tower_damage = _damage_summary(tower_before, tower_after, tower_hull.mass)
        target_damage = _damage_summary(target_before, target_after, target_hull.mass)
        if tower_damage["normal_hit_candidates"]:
            totals["tower_normal_damage_candidate_rows"] += 1
        if tower_damage["web_hit_candidates"]:
            totals["tower_web_damage_candidate_rows"] += 1
        if target_damage["normal_hit_candidates"] or target_damage["web_hit_candidates"]:
            totals["target_damage_candidate_rows"] += 1

        before_fields = _hostile_fields(context, turn, int(tower_owner))
        after_fields = _hostile_fields(context, after_turn, int(tower_owner))
        before_cross = _crossings(context, before_fields, origin, waypoint)
        after_cross = _crossings(context, after_fields, origin, waypoint)
        visible_cross = before_cross + tuple(field for field in after_cross if _field_detail(field) not in [_field_detail(x) for x in before_cross])
        normal_cross = tuple(field for field in visible_cross if not field.is_web)
        web_cross = tuple(field for field in visible_cross if field.is_web)
        web_at_observed = tuple(
            field for field in visible_cross
            if field.is_web and _point_in_field(observed, field, context.topology)
        )
        if normal_cross:
            totals["visible_normal_crossing_rows"] += 1
        if web_cross:
            totals["visible_web_crossing_rows"] += 1
        if web_at_observed:
            totals["observed_inside_visible_web_rows"] += 1

        sample = MovementSample(
            turn=turn,
            ship_id=tower_id,
            x=origin[0],
            y=origin[1],
            target_x=waypoint[0],
            target_y=waypoint[1],
            warp=warp,
            next_x=observed[0],
            next_y=observed[1],
            hull_id=tower_hull_id,
            gravitonic=tower_hull_id in GRAVITONIC_HULL_IDS,
            game_id=EXPECTED_GAME,
        )
        strong = classify_strong_mine_hit_transition(
            context=context,
            before_turn=turn,
            after_turn=after_turn,
            ship_id=tower_id,
            owner_id=int(tower_owner),
            before_raw=tower_before,
            sample=sample,
        )
        if strong is not None:
            totals["strong_mine_classifier_rows"] += 1

        route_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
        observed_distance = hypot(observed[0] - origin[0], observed[1] - origin[1])
        nominal_distance = float(warp * warp * (2 if tower_hull_id in GRAVITONIC_HULL_IDS else 1))
        scaled_floor_matches: list[dict[str, Any]] = []
        if context.topology.sphere is False and normal_cross:
            for damage_hits in tower_damage["normal_hit_candidates"]:
                for slowdown_hits in range(1, damage_hits + 1):
                    endpoint, penalty = scaled_floor_normal_mine_endpoint(
                        origin=origin,
                        target=waypoint,
                        nominal_distance=nominal_distance,
                        regular_distance=route_distance,
                        slowdown_hits=slowdown_hits,
                    )
                    if endpoint == observed:
                        scaled_floor_matches.append({
                            "damage_hits": damage_hits,
                            "slowdown_hits": slowdown_hits,
                            "penalty_clicks": penalty,
                        })
        if scaled_floor_matches:
            totals["research_scaled_floor_exact_rows"] += 1

        damage_backed_cross = bool(
            (normal_cross and tower_damage["normal_hit_candidates"])
            or (web_cross and tower_damage["web_hit_candidates"])
        )
        if strong is not None:
            lead = "strong_mine_classifier"
        elif damage_backed_cross:
            lead = "damage_backed_visible_mine_context"
        elif scaled_floor_matches:
            lead = "research_scaled_floor_relation_only"
        elif web_cross:
            lead = "visible_web_context_only"
        elif normal_cross:
            lead = "visible_normal_mine_context_only"
        elif tower_damage["normal_hit_candidates"] or tower_damage["web_hit_candidates"]:
            lead = "tower_damage_trace_only"
        else:
            lead = "no_visible_mine_or_damage_lead"
        totals[f"lead:{lead}"] += 1

        tower_after_nav = {
            "warp": _intish(tower_after.get("warp")),
            "waypoint": (
                _intish(tower_after.get("targetx", tower_after.get("waypointx"))),
                _intish(tower_after.get("targety", tower_after.get("waypointy"))),
            ),
            "fuel": _intish(tower_after.get("neutronium")),
        }
        target_after_nav = {
            "warp": _intish(target_after.get("warp")),
            "waypoint": (
                _intish(target_after.get("targetx", target_after.get("waypointx"))),
                _intish(target_after.get("targety", target_after.get("waypointy"))),
            ),
            "fuel": _intish(target_after.get("neutronium")),
        }

        print({
            "game": EXPECTED_GAME,
            "turn": turn,
            "tower_ship": tower_id,
            "target_ship": target_id,
            "origin": origin,
            "waypoint": waypoint,
            "observed": observed,
            "route_distance": round(route_distance, 6),
            "observed_distance": round(observed_distance, 6),
            "lost_distance": round(route_distance - observed_distance, 6),
            "tower_hull": {
                "id": tower_hull_id,
                "tech": tower_hull.tech_level,
                "mass": tower_hull.mass,
                "special": tower_hull.special,
            },
            "target_hull": {
                "id": target_hull_id,
                "tech": target_hull.tech_level,
                "mass": target_hull.mass,
                "special": target_hull.special,
            },
            "tower_damage": tower_damage,
            "target_damage": target_damage,
            "visible_normal_crossings": tuple(_field_detail(field) for field in normal_cross),
            "visible_web_crossings": tuple(_field_detail(field) for field in web_cross),
            "visible_web_at_observed": tuple(_field_detail(field) for field in web_at_observed),
            "strong_mine": None if strong is None else {
                "category": strong.category,
                "damage_hits": strong.damage_hits,
                "slowdown_hits": strong.slowdown_hits,
            },
            "research_scaled_floor_matches": tuple(scaled_floor_matches),
            "tower_after": tower_after_nav,
            "target_after": target_after_nav,
            "lead": lead,
        })

    print("\n===== SUMMARY =====")
    for key in (
        "cases",
        "strong_mine_classifier_rows",
        "tower_normal_damage_candidate_rows",
        "tower_web_damage_candidate_rows",
        "target_damage_candidate_rows",
        "visible_normal_crossing_rows",
        "visible_web_crossing_rows",
        "observed_inside_visible_web_rows",
        "research_scaled_floor_exact_rows",
    ):
        print(f"{key}=", totals[key])
    for key in sorted(k for k in totals if k.startswith("lead:")):
        print(f"{key}=", totals[key])

    print("\n===== INTERPRETATION =====")
    print("Strong mine classification keeps the existing production evidence boundary.")
    print("Visible crossing or damage-only rows are context leads, not mine attribution; hidden fields remain possible when no visible field is present.")
    print("Scaled-floor exactness outside the current production scope is research-only and cannot promote high-tech or otherwise unsupported rows.")
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
