"""Independent cross-game observational combat mass hypothesis controls.

Classic hull mass, Federation +50, and the 60% +360 anti-carrier branch
are documented. Whether the 140 KT eligibility threshold uses bare hull
or an already adjusted mass is NOT documented unambiguously and remains a
candidate rule. Horwasp full-cargo mass can reach 2*hull mass, but that is
an endpoint, NOT a general Horwasp mass formula.

Do not wire this audit into probabilistic combat or use current-VCR mass
as a predictive input. Read-only immutable public100 evidence only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIAG = Path(__file__).resolve().parent
for folder in (ROOT / "src", DIAG):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,
    member_refs_for_turns,
    reconstruct_members,
)
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs
from combat_multigame_conditional_coverage_v2 import choose_game_turns

SCHEMA = "planets-lab.combat-mass-crossgame-controls.v1"
ANCHORS = ((400330, 141), (217591, 149), (253449, 82))
HORWASP_RACE_ID = 12


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _side(
    *, side_name: str, side: Mapping[str, Any],
    left: Mapping[str, Any], specs: Any,
) -> dict[str, Any]:
    if side_name not in ("left", "right"):
        raise ValueError("invalid side")
    hull_id = _integer(side.get("hullid"))
    observed = _integer(side.get("mass"))
    race = _integer(side.get("raceid"))
    ship_id = _integer(side.get("objectid"))
    if hull_id is None or hull_id <= 0 or observed is None or race is None:
        raise ValueError("side hull/mass/race unavailable")
    hull = specs.hulls.get(hull_id)
    if hull is None:
        raise ValueError(f"hull {hull_id} missing from static specs")
    base = hull.mass + (50 if race == 1 else 0)
    left_bays = _integer(left.get("baycount"))
    left_carrier = bool(left_bays is not None and left_bays > 0)
    eligible_hull = (
        side_name == "right" and left_carrier and hull.mass >= 140
    )
    eligible_adjusted = (
        side_name == "right" and left_carrier and base >= 140
    )
    original = sorted({base, *( [base+360] if eligible_hull else [] )})
    adjusted = sorted({base, *( [base+360] if eligible_adjusted else [] )})
    horwasp_endpoint = (
        2 * hull.mass if race == HORWASP_RACE_ID else None
    )
    if observed in original:
        category = "classic_hull_threshold"
    elif race == HORWASP_RACE_ID and observed == horwasp_endpoint:
        category = "horwasp_full_load_endpoint_candidate"
    elif observed in adjusted and observed not in original:
        category = "federation_adjusted_threshold_candidate"
    else:
        category = "unresolved_mass_residual"
    return {
        "side": side_name,
        "ship_id": ship_id,
        "hull_id": hull_id,
        "hull_name": hull.name,
        "race_id": race,
        "hull_mass": hull.mass,
        "federation_adjusted_base": base,
        "factual_mass": observed,
        "left_carrier_observed": left_carrier,
        "hull_threshold_bonus_eligible": eligible_hull,
        "adjusted_threshold_bonus_eligible": eligible_adjusted,
        "original_candidates": original,
        "adjusted_threshold_candidates": adjusted,
        "horwasp_full_load_endpoint": horwasp_endpoint,
        "horwasp_cargo_capacity": (
            hull.cargo_capacity if race == HORWASP_RACE_ID else None
        ),
        "category": category,
        "residual_from_adjusted_base": observed-base,
        "evidence_boundary": (
            "Observational comparison, not a Host mass setter. The "
            "adjusted-threshold branch is unverified; Horwasp 2x is "
            "a documented full-load endpoint only, with precombat clans "
            "still requiring independent confirmation."
        ),
    }


def classify_ship_case(
    *, case: Any, specs: Any, game_id: int, turn: int,
) -> dict[str, Any]:
    payload = case.payload
    left, right = payload.get("left"), payload.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise ValueError("invalid VCR sides")
    rows = [
        _side(side_name="left", side=left, left=left, specs=specs),
        _side(side_name="right", side=right, left=left, specs=specs),
    ]
    return {
        "game_id": game_id,
        "turn": turn,
        "vcr_id": case.vcr_id,
        "side_pair": [r["ship_id"] for r in rows],
        "sides": rows,
        "seed_recorded_observational_only": _integer(payload.get("seed")),
    }


def _brood_before_turn_context(connection: Any, specs: Any) -> dict[str, Any]:
    game_id, turn, ship_id = 253449, 82, 48
    refs = member_refs_for_turns(
        connection, game_id=game_id, turns={turn-1},
        include_embedded_turn=False,
    )
    rows: list[dict[str, Any]] = []
    for ref, member in reconstruct_members(connection, refs):
        if ref.perspective_player_id != HORWASP_RACE_ID:
            continue
        ships = member.get("ships")
        if not isinstance(ships, list):
            continue
        for ship in ships:
            if not isinstance(ship, Mapping) or _integer(ship.get("id")) != ship_id:
                continue
            owner = _integer(ship.get("ownerid"))
            if owner != HORWASP_RACE_ID:
                continue
            hull_id = _integer(ship.get("hullid"))
            hull = specs.hulls.get(hull_id)
            raw_clans = _integer(ship.get("clans"))
            cap = hull.cargo_capacity if hull is not None else None
            rows.append({
                "archive_turn":ref.archive_turn,
                "perspective_player_id":ref.perspective_player_id,
                "ship_id":ship_id,
                "hull_id":hull_id,
                "observed_clans":raw_clans,
                "catalog_cargo_capacity":cap,
                "observed_full_load_at_tminus1": (
                    raw_clans >= cap
                    if raw_clans is not None and cap is not None and cap > 0
                    else None
                ),
                "raw_mass":_integer(ship.get("mass")),
                "raw_neutronium":_integer(ship.get("neutronium")),
                "evidence_boundary": (
                    "T-1 OWNER-perspective snapshot only, not proof of "
                    "clan occupancy immediately before combat at T."
                ),
            })
    return {
        "game_id":game_id, "turn":turn, "ship_id":ship_id,
        "owner_perspective_rows":rows,
        "source": "tminus1_owner_archive_snapshot",
    }


def build_report(
    *, connection: Any, db_path: str,
    extra_candidate_games: int = 20,
    max_vcrs_per_turn: int = 120,
) -> dict[str, Any]:
    if extra_candidate_games < 0 or max_vcrs_per_turn <= 0:
        raise ValueError("invalid bounds")
    selected = list(ANCHORS)
    if extra_candidate_games:
        candidates = choose_game_turns(
            connection, max_candidate_games=extra_candidate_games,
            turns_per_game=1,
        )
        for game_id, turns in candidates:
            if turns:
                key = (game_id, turns[0].turn)
                if key not in selected:
                    selected.append(key)

    counts: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    per_turn: list[dict[str, Any]] = []
    contexts: dict[int, Any] = {}
    for game_id, turn in selected:
        try:
            specs = _independent_hull_specs(connection, game_id)
            contexts[game_id] = specs
            all_cases = combat_vcr_cases_for_turns(
                connection, game_id=game_id, battle_turns={turn}
            )
        except (ValueError, OSError, TypeError) as exc:
            errors.append({"game_id":game_id,"turn":turn,"stage":"corpus","error":str(exc)})
            continue
        rows: list[dict[str, Any]] = []
        rejected: Counter[str] = Counter()
        all_observations = sorted(all_cases.items())
        for (_t, _vcr_id), case in all_observations[:max_vcrs_per_turn]:
            try:
                row = classify_ship_case(
                    case=case, specs=specs, game_id=game_id,turn=turn
                )
                rows.append(row)
                for side in row["sides"]:
                    counts[side["category"]] += 1
                    if side["hull_threshold_bonus_eligible"]:
                        counts["classic_carrier_eligible_sides"] += 1
                    elif side["adjusted_threshold_bonus_eligible"]:
                        counts["fed_adjusted_only_eligible_sides"] += 1
            except ValueError as exc:
                rejected[str(exc)] += 1
        counts["ship_vs_ship_vcrs_compared"] += len(rows)
        per_turn.append({
            "game_id":game_id,
            "turn":turn,
            "anchor":(game_id,turn) in ANCHORS,
            "unique_vcrs_available":len(all_observations),
            "unique_vcrs_examined":min(len(all_observations),max_vcrs_per_turn),
            "truncated":len(all_observations)>max_vcrs_per_turn,
            "rejections":dict(sorted(rejected.items())),
            "rows":rows,
        })
        counts["turns_compared"] += 1
    brood = (
        _brood_before_turn_context(connection,contexts[253449])
        if 253449 in contexts else None
    )
    return {
        "schema":SCHEMA,
        "status":"OBSERVATIONAL_CROSSGAME_NOT_PROMOTED",
        "source_public100_db":db_path,
        "anchors":[list(v) for v in ANCHORS],
        "summary":dict(sorted(counts.items())),
        "turns_selected":len(selected),
        "turns_compared":len(per_turn),
        "errors":errors,
        "per_turn":per_turn,
        "brood_precombat_candidate_context":brood,
        "sources": [
            "https://help.planets.nu/combat-mass",
            "https://help.planets.nu/horwasp-ships",
            "https://help.planets.nu/horwasp-combat-strength",
        ],
        "evidence_boundary": (
            "Exhaustive per-turn up to documented maximum; all evaluated "
            "masses are factual VCR observations. Classic hull threshold, "
            "hypothetical Federation-adjusted 140 threshold and Horwasp "
            "fully loaded 2x endpoint are compared, not combined into an "
            "asserted Host formula. Other modifiers remain possible. "
            "No combat RNG reconstruction or scenario probabilities "
            "are validated. No current VCR observation is used for "
            "a predictive mass or seed setter."
        ),
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--extra-games",type=int,default=20)
    p.add_argument("--max-vcrs-per-turn",type=int,default=120)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        conn,dbpath=connect_compact_generation_read_only(
            a.corpus_db_generation,a.corpus_db_root
        )
        try:
            report=build_report(
                connection=conn,db_path=str(dbpath),
                extra_candidate_games=a.extra_games,
                max_vcrs_per_turn=a.max_vcrs_per_turn,
            )
        finally:
            conn.close()
    except (ValueError,TypeError,OSError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("===== CROSS-GAME COMBAT MASS CONTROLS V1 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("games_turns:",report["turns_compared"],"errors:",len(report["errors"]))
    for t in report["per_turn"]:
        print(f"game={t['game_id']} turn={t['turn']} vcrs={t['unique_vcrs_examined']}/{t['unique_vcrs_available']} rejects={t['rejections']}")
        for row in t["rows"]:
            exceptions=[s for s in row["sides"] if s["category"]!="classic_hull_threshold"]
            for s in exceptions:
                print(
                    f"  V{row['vcr_id']} {s['side']} ship={s['ship_id']} "
                    f"race={s['race_id']} hullmass={s['hull_mass']} "
                    f"vcr={s['factual_mass']} base={s['federation_adjusted_base']} "
                    f"class={s['category']}"
                )
    print("brood_tminus1_owner:",report["brood_precombat_candidate_context"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
