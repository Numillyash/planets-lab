"""Read-only bounded mass-residual triage on public100 T-1/T snapshots.

Observes exact factual side combat masses only AFTER the already published
conditional ensemble flagged an out-of-set comparison. Records catalogue
baseline and bounded pre/post turn ship/setting provenance. No new mass
mechanic is inferred or fed back into the conditional simulator.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for folder in (ROOT / "src", DIAGNOSTICS):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns,
    reconstruct_members,
)
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs

SCHEMA = "planets-lab.combat-mass-residual-triage.v1"
TARGETS = ((217591, 149, 2390), (253449, 82, 611))
SHIP_FIELDS = (
    "id", "ownerid", "hullid", "engineid", "engine", "beams",
    "beamid", "torps", "torpedoid", "bays", "ammo", "mass",
    "x", "y", "targetx", "targety", "warp", "shield", "damage",
    "crew", "friendlycode", "mission", "mission1target",
)
SETTINGS_TERMS = (
    "shield", "engine", "combat", "fed", "race", "advantage",
    "campaign", "mass", "crew",
)


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _candidate_side(
    side: Mapping[str, Any], *, side_name: str,
    other_side: Mapping[str, Any], specs: Any,
) -> dict[str, Any]:
    ship = _integer(side.get("objectid"))
    hull_id = _integer(side.get("hullid"))
    observed = _integer(side.get("mass"))
    race = _integer(side.get("raceid"))
    if ship is None or hull_id is None or observed is None:
        raise ValueError("factual participant mass/hull/ship missing")
    hull = specs.hulls.get(hull_id)
    if hull is None:
        raise ValueError(f"hull catalog missing hull_id={hull_id}")
    base = hull.mass + (50 if race == 1 else 0)
    other_bays = _integer(other_side.get("baycount"))
    carrier = bool(
        side_name == "right" and hull.mass >= 140
        and other_bays is not None and other_bays > 0
    )
    candidates = [base] + ([base + 360] if carrier else [])
    return {
        "side": side_name, "ship_id": ship,
        "factual_owner_id": _integer(side.get("ownerid")),
        "factual_race_id": race,
        "factual_hull_id": hull_id,
        "hull_name": hull.name, "hull_catalog_mass": hull.mass,
        "hull_special_text": hull.special,
        "factual_mass": observed,
        "catalog_plus_fed_base": base,
        "right_vs_left_carrier_possible": carrier,
        "documented_mass_candidates": candidates,
        "mass_inside_candidates": observed in candidates,
        "delta_from_documented_base": observed - base,
        "residuals_after_possible_branches": [
            {"candidate_mass": mass, "unexplained_delta": observed - mass}
            for mass in candidates
        ],
        "effective_bays": _integer(side.get("baycount")),
        "factual_shield": _integer(side.get("shield")),
        "factual_damage": _integer(side.get("damage")),
        "factual_engine_type": _integer(side.get("engineid")),
    }


def triage_case(
    *,
    game_id: int, turn: int, vcr_id: int,
    payload: Mapping[str, Any], specs: Any,
    archived_members: list[tuple[Any, Mapping[str, Any]]],
) -> dict[str, Any]:
    left, right = payload.get("left"), payload.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise ValueError("VCR left/right missing")
    sides = [
        _candidate_side(left, side_name="left", other_side=right, specs=specs),
        _candidate_side(right, side_name="right", other_side=left, specs=specs),
    ]
    participant_ids = {side["ship_id"] for side in sides}
    side_by_id = {side["ship_id"]: side for side in sides}
    x, y = _integer(payload.get("x")), _integer(payload.get("y"))
    vcr_site = [x, y] if x is not None and y is not None else None
    source_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    co_located_shield_candidates: list[dict[str, Any]] = []
    known_setting_samples: list[dict[str, Any]] = []
    settings_keys = set()

    for ref, member in archived_members:
        if ref.archive_turn not in {turn - 1, turn}:
            continue
        member_game = member.get("game")
        if not isinstance(member_game, Mapping) or _integer(member_game.get("id")) != game_id:
            continue
        raw_settings = member.get("settings")
        if isinstance(raw_settings, Mapping):
            settings_keys.update(str(key) for key in raw_settings.keys())
            interested = {
                str(k): v for k, v in raw_settings.items()
                if isinstance(v, (str, int, float, bool, type(None)))
                and any(word in str(k).casefold() for word in SETTINGS_TERMS)
            }
            if interested and len(known_setting_samples) < 4:
                item = {"archive_turn": ref.archive_turn,
                        "perspective_player_id": ref.perspective_player_id,
                        "selected_game_settings": interested}
                if item not in known_setting_samples:
                    known_setting_samples.append(item)

        ships = member.get("ships")
        if not isinstance(ships, list):
            continue
        for ship in ships:
            if not isinstance(ship, Mapping):
                continue
            ship_id = _integer(ship.get("id"))
            if ship_id is None:
                continue
            hull_id = _integer(ship.get("hullid"))
            hull = specs.hulls.get(hull_id) if hull_id is not None else None
            hull_name = hull.name if hull is not None else None
            special = hull.special if hull is not None else None
            if ship_id in participant_ids:
                row = {
                    "archive_turn": ref.archive_turn,
                    "perspective_player_id": ref.perspective_player_id,
                    "hull_name": hull_name,
                    "hull_special_text": special,
                    "raw": {key: ship[key] for key in SHIP_FIELDS if key in ship},
                }
                if row not in source_rows[ship_id] and len(source_rows[ship_id]) < 6:
                    source_rows[ship_id].append(row)

            # This is a proximity CANDIDATE only: T-1/T raw positions do not
            # prove that a shield generator participated at precombat time.
            is_generator = any(
                "shield generator" in (name or "").casefold()
                for name in (hull_name, special)
            )
            pos_match = (
                vcr_site is not None
                and _integer(ship.get("x")) == x
                and _integer(ship.get("y")) == y
            )
            if not is_generator or not pos_match or ship_id in participant_ids:
                continue
            candidate = {
                "ship_id": ship_id,
                "archive_turn": ref.archive_turn,
                "perspective_player_id": ref.perspective_player_id,
                "candidate_hull_name": hull_name,
                "ownerid_in_raw": _integer(ship.get("ownerid")),
                "x": x, "y": y,
                "provenance": "raw_snapshot_location_only_not_combat_phase_proof",
            }
            if candidate not in co_located_shield_candidates and len(co_located_shield_candidates) < 20:
                co_located_shield_candidates.append(candidate)

    for side in sides:
        sid = side["ship_id"]
        side["archive_raw_ship_observations"] = source_rows.get(sid, [])
        engine_candidates = sorted({
            _integer(row["raw"].get("engineid"))
            for row in source_rows.get(sid, [])
            if _integer(row["raw"].get("engineid")) is not None
        })
        side["observed_engine_ids"] = engine_candidates
        side["engine_costs_from_catalog"] = [
            {
                "engine_id": engine,
                "engine_name": specs.engines[engine].name,
                "catalog_engine_cost_mc": specs.engines[engine].cost.megacredits,
                "possible_shield_generator_bonus_half_mc": (
                    specs.engines[engine].cost.megacredits // 2
                ),
                "classification": "unproven_local_modifier_candidate_only",
            }
            for engine in engine_candidates if engine in specs.engines
        ]
        side["shield_generator_candidates_at_vcr_xy"] = [
            item for item in co_located_shield_candidates
            if item["ownerid_in_raw"] == (
                side["factual_owner_id"] if side["factual_owner_id"] is not None
                else _integer(payload.get(
                    "leftownerid" if side["side"] == "left" else "rightownerid"
                ))
            )
        ]

    return {
        "game_id": game_id, "battle_turn": turn, "vcr_id": vcr_id,
        "vcr_site": vcr_site,
        "factual_vcr_seed_recorded_not_used": _integer(payload.get("seed")),
        "factual_owner_ids": {
            "left": _integer(payload.get("leftownerid")),
            "right": _integer(payload.get("rightownerid")),
        },
        "sides": sides,
        "sampled_relevant_settings": known_setting_samples,
        "settings_key_names": sorted(settings_keys),
        "evidence_boundary": (
            "Historical factual VCR masses identify residuals. Archived "
            "T-1/T ship positions and engines are observation candidates, "
            "not independent proof of precombat colocation. Shield Generator "
            "bonuses and engine-shield settings are NOT promoted until confirmed "
            "with independently observed game rules and positive/negative "
            "controls. This diagnostic does not simulate combat."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--corpus-db-generation", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        conn, db_path = connect_compact_generation_read_only(
            a.corpus_db_generation, a.corpus_db_root
        )
        try:
            rows = []
            for game_id, turn, vcr_id in TARGETS:
                cases = combat_vcr_cases_for_turns(
                    conn, game_id=game_id, battle_turns={turn}
                )
                case = cases.get((turn, vcr_id))
                if case is None:
                    raise ValueError(f"missing VCR {game_id} T{turn} V{vcr_id}")
                specs = _independent_hull_specs(conn, game_id)
                refs = member_refs_for_turns(
                    conn, game_id=game_id, turns={turn - 1, turn},
                    include_embedded_turn=False,
                )
                members = list(reconstruct_members(conn, refs))
                rows.append(triage_case(
                    game_id=game_id, turn=turn, vcr_id=vcr_id,
                    payload=case.payload, specs=specs,
                    archived_members=members,
                ))
        finally:
            conn.close()
    except (TypeError, ValueError, OSError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2

    report = {
        "schema": SCHEMA,
        "status": "OBSERVATIONAL_RESIDUALS_NOT_PROMOTED",
        "database_path": str(db_path),
        "source_v2_run": (
            "runtime-logs/multigame-conditional-combat-coverage-v2/"
            "20261008T054704Z_c00fe36cfa15"
        ),
        "cases": rows,
        "residual_count": sum(
            side["mass_inside_candidates"] is False
            for case in rows for side in case["sides"]
        ),
        "evidence_boundary": (
            "Read-only factual VCR diagnostic and T-1/T snapshot context. "
            "Mass and modifiers are observational; no fitted parameter "
            "or result supplied to the predictive combat simulator."
        ),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print("===== COMBAT MASS RESIDUAL TRIAGE V1 =====")
    print("status:", report["status"])
    print("residual_sides:", report["residual_count"])
    for case in rows:
        print(f"game={case['game_id']} T{case['battle_turn']} V{case['vcr_id']} site={case['vcr_site']}")
        for side in case["sides"]:
            print(
                f"  {side['side']} ship={side['ship_id']} "
                f"hull={side['factual_hull_id']} ({side['hull_name']}) "
                f"base={side['catalog_plus_fed_base']} "
                f"vcr_mass={side['factual_mass']} "
                f"candidates={side['documented_mass_candidates']} "
                f"residuals={side['residuals_after_possible_branches']} "
                f"engine_ids={side['observed_engine_ids']} "
                f"shield_generator_nearby={len(side['shield_generator_candidates_at_vcr_xy'])}"
            )
        print("  relevant_settings:", case["sampled_relevant_settings"][:2])
    print("output:", a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
