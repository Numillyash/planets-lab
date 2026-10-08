"""Prestate-only MASS hypothesis projection from frozen v3 owner snapshots.

This is a read-only, explicitly CONDITIONAL experiment. The projection
function accepts a game hull catalog mass and T-1 owner snapshot only.
It never takes factual VCR combat mass; comparison occurs later in report.

Shield Generator effects require T-1 exact XY co-location AND known engine;
movement to/from combat may still change conditions. Horwasp clan interpolation
and canonical Brood mass are hypotheses, not proven Host algorithms. The
optional +360 right branch is a possibility, NOT a prediction of its RNG.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "planets-lab.combat-mass-owner-provenance.v3"
SCHEMA = "planets-lab.combat-mass-prestate-hypothesis.v4"
REFERENCE_BROOD_MASS = 145
REFERENCE_URL = "https://help.planets.nu/RaceSheetPlus"
SG_URL = "https://help.planets.nu/abil-shield-generator"
HORWASP_URL = "https://help.planets.nu/horwasp-ships"


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _before_owner(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    turn = _integer(row.get("turn"))
    snapshots = row.get("owner_perspective_snapshots")
    if turn is None or not isinstance(snapshots, list):
        return None
    matches = [
        snap for snap in snapshots if isinstance(snap, Mapping)
        and snap.get("archive_turn") == turn - 1
        and isinstance(snap.get("participant"), Mapping)
    ]
    return matches[0] if len(matches) == 1 else None


def project_mass_candidates(prestate: Mapping[str, Any]) -> dict[str, Any]:
    """Derive arithmetic candidates from T-1 owner data, never current VCR mass.

    Explicitly include assumptions/provenance so a numerical match is not
    mistaken for a validated rule. Right +360 requires additional carrier
    and Host RNG checks not established by the owner-only v3 source.
    """
    race = _integer(prestate.get("race_id"))
    hull = _integer(prestate.get("catalog_hull_mass"))
    capacity = _integer(prestate.get("catalog_cargo_capacity"))
    hull_id = _integer(prestate.get("hull_id"))
    side = prestate.get("side")
    snap = prestate.get("owner_tminus1")
    site = prestate.get("vcr_site")
    if race is None or hull is None or hull <= 0 or hull_id is None or side not in ("left","right"):
        raise ValueError("prestate race/catalog hull/side unresolved")
    if snap is not None and not isinstance(snap, Mapping):
        raise ValueError("prestate owner snapshot malformed")
    participant = snap.get("participant") if isinstance(snap, Mapping) else None
    if not isinstance(participant, Mapping):
        return {
            "projection_status": "TMINUS1_OWNER_SHIP_UNAVAILABLE",
            "candidate_masses": [],
            "source_tminus1": None,
            "assumptions": ["owner-perspective T-1 ship state missing"],
            "horwasp_reference_alternative": False,
            "shield_generator_prestate_support": None,
        }

    raw = participant.get("raw")
    if not isinstance(raw, Mapping):
        raise ValueError("owner participant raw ship missing")
    candidates: list[dict[str, Any]]=[]
    assumptions: list[str]=[]
    horwasp_alt = False
    sg_support = None
    clans = _integer(participant.get("clans"))
    if race == 12:
        if capacity is None or capacity <= 0 or clans is None or clans < 0:
            return {
                "projection_status":"HORWASP_CLANS_OR_CAPACITY_UNRESOLVED",
                "candidate_masses": [],
                "source_tminus1":snap.get("archive_turn"),
                "assumptions":["cannot interpolate clans without owner T-1 clans/capacity"],
                "horwasp_reference_alternative":False,
                "shield_generator_prestate_support":None,
            }
        if clans > capacity:
            raise ValueError("Horwasp clans exceed game catalog cargo capacity")
        # Full-load 2x is documented. The linear interpolation is an
        # UNVERIFIED arithmetic hypothesis even if empirical results match.
        bases = [("game_specific_hull_catalog",hull)]
        if hull_id==117 and hull!=REFERENCE_BROOD_MASS:
            bases.append(("external_reference_brood_145",REFERENCE_BROOD_MASS))
            horwasp_alt=True
        for label,base in bases:
            full = clans==capacity
            base_mass=2*base if full else base + (base*clans//capacity)
            candidates.append({
                "mass":base_mass, "scenario":label,
                "rule_status":(
                    "documented_full_load_endpoint_using_assumed_reference_base"
                    if full and label!="game_specific_hull_catalog"
                    else "documented_full_load_endpoint" if full
                    else "unverified_linear_clan_fraction"
                ),
            })
            if side=="right" and base_mass>=140:
                candidates.append({
                    "mass":base_mass+360,
                    "scenario":label+"_right_plus360",
                    "rule_status":"unverified_combined_carrier_branch",
                })
        assumptions.extend([
            "T-1 clans assumed unchanged until this particular combat",
            "Horwasp partial-clan linear interpolation is unverified",
            "right +360 scenario lacks independently proven opponent carrier/RNG decision",
        ])
        if horwasp_alt:
            assumptions.append(
                "145 KT Brood reference from published RaceSheetPlus differs from game hull catalog"
            )
        status="HORWASP_TMINUS1_CONDITIONAL_CANDIDATES"
    else:
        base=hull+(50 if race==1 else 0)
        raw_x,raw_y=_integer(raw.get("x")),_integer(raw.get("y"))
        xy = [raw_x,raw_y] if raw_x is not None and raw_y is not None else None
        at_site=(isinstance(site,list) and len(site)==2 and xy==site)
        generators=snap.get("owner_shield_generators_at_vcr_coordinates")
        if not isinstance(generators,list):
            raise ValueError("owner generator observations unavailable")
        engine_cost=_integer(participant.get("engine_cost_mc"))
        if at_site and engine_cost is not None and engine_cost>0:
            # Even when T-1 co-located, unknown movement/Host phases can
            # disable generators; enumerate both NO and T-1 observed support
            # branches instead of assuming efficacy.
            n=min(len(generators),2)
            sg_support={
                "owner_ship_at_vcr_site_tminus1":True,
                "nearby_same_owner_generator_count":len(generators),
                "engine_id":_integer(participant.get("engine_id")),
                "engine_cost_mc":engine_cost,
                "per_generator_mass":engine_cost//2,
                "n_generators_capped_at_2":n,
                "temporal_status":"TMINUS1_ONLY_NOT_PRECOMBAT_PROOF",
            }
            sg_bonuses=[0]
            if n:
                sg_bonuses.append(n*(engine_cost//2))
            status="SHIELD_GENERATOR_TMINUS1_SITE_CANDIDATES"
            assumptions.append("T-1 colocation is not proof of combat-phase generator effect")
        else:
            sg_bonuses=[0]
            sg_support={
                "owner_ship_at_vcr_site_tminus1":at_site,
                "nearby_same_owner_generator_count":len(generators),
                "engine_id":_integer(participant.get("engine_id")),
                "engine_cost_mc":engine_cost,
                "temporal_status":"NO_INFERENCE_ABOUT_PRECOMBAT_GENERATORS",
            }
            status="NO_VALID_TMINUS1_GENERATOR_SITE_PROJECTION"
            assumptions.append("mass baseline excludes unknown arrival/movement of generators")
        for extra in sg_bonuses:
            candidates.append({
                "mass":base+extra,
                "scenario":"base_only" if extra==0 else "engine_cost_half_times_Tminus1_generators",
                "rule_status":"documented_numerical_rule_with_unverified_phase",
            })
            if side=="right" and base+extra>=140:
                candidates.append({
                    "mass":base+extra+360,
                    "scenario":"right_plus360_after_"+str(extra)+"_generator_bonus",
                    "rule_status":"unverified_carrier_eligibility_and_rng",
                })
        assumptions.append("right +360 is only a possible branch; left carrier and Host RNG unresolved")
    masses=sorted({entry["mass"] for entry in candidates})
    return {
        "projection_status":status,
        "candidate_masses":masses,
        "candidate_details":candidates,
        "source_tminus1":snap.get("archive_turn"),
        "source_clans":clans,
        "horwasp_reference_alternative":horwasp_alt,
        "shield_generator_prestate_support":sg_support,
        "assumptions":assumptions,
    }


def build_report(source: Mapping[str, Any], *, path: str) -> dict[str, Any]:
    if source.get("schema") != SOURCE_SCHEMA:
        raise ValueError("unexpected v3 source schema")
    rows = source.get("observations")
    if not isinstance(rows,list) or len(rows)!=14:
        raise ValueError("expected 14 published v3 source observations")
    report_rows=[]
    counts: Counter[str]=Counter()
    unique_ships: dict[tuple[int,int,int],list[dict[str,Any]]]=defaultdict(list)
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("invalid observation row")
        factual_mass=_integer(row.get("factual_combat_mass"))
        if factual_mass is None:
            raise ValueError("factual comparator missing")
        known={
            key:row.get(key)
            for key in ("race_id","catalog_hull_mass",
                        "catalog_cargo_capacity","hull_id","side","vcr_site")
        }
        known["owner_tminus1"]=_before_owner(row)
        # This function is called with no factual combat mass.
        projection=project_mass_candidates(known)
        matches=factual_mass in projection["candidate_masses"]
        counts[projection["projection_status"]]+=1
        counts["numeric_candidate_match" if matches else "numeric_candidate_nonmatch"]+=1
        if row.get("signature")=="unresolved_nonadditive":
            counts["original_six_match" if matches else "original_six_unmatched"]+=1
        result={
            "game_id":row["game_id"],"turn":row["turn"],"vcr_id":row["vcr_id"],
            "ship_id":row["ship_id"],"side":row["side"],"race_id":row["race_id"],
            "source_signature":row["signature"],
            "factual_mass_checked_after_projection":factual_mass,
            "mass_in_prestate_candidates":matches,
            "projection":projection,
        }
        report_rows.append(result)
        unique_ships[(row["game_id"],row["turn"],row["ship_id"])].append(result)
    unique_summary={
        "distinct_ship_game_turn_groups":len(unique_ships),
        "groups_with_at_least_one_match":sum(
            any(r["mass_in_prestate_candidates"] for r in rs)
            for rs in unique_ships.values()
        ),
        "groups_with_all_matches":sum(
            all(r["mass_in_prestate_candidates"] for r in rs)
            for rs in unique_ships.values()
        ),
        "groups_without_match":sum(
            not any(r["mass_in_prestate_candidates"] for r in rs)
            for rs in unique_ships.values()
        ),
    }
    return {
        "schema":SCHEMA,
        "status":"CONDITIONAL_PRESTATE_HYPOTHESES_NOT_PROMOTED",
        "source_v3_file":path,
        "summary":{
            **dict(sorted(counts.items())), **unique_summary,
            "evaluated_factual_sides":len(report_rows),
            "observed_zero_OR_unknown_generator_count_is_not_absence_of_Host_support":True,
        },
        "observations":report_rows,
        "documentation":{
            "shield_generator":SG_URL,
            "horwasp":HORWASP_URL,
            "brood_reference_catalog":REFERENCE_URL,
        },
        "evidence_boundary":(
            "Predictor only consumes game hull catalog and T-1 owner-perspective "
            "snapshot. The VCR mass is compared only after candidates are "
            "derived. Full-load 2x is documented but Horwasp partial-load "
            "interpolation, canonical Brood 145 in a game catalog showing "
            "125, phase-accurate Shield Generator support, right-vs-carrier "
            "eligibility and RNG branch are NOT independently proven. "
            "T-1 snapshots and game ID grouping are not a held-out "
            "validation set. No mass rule promoted to the real executor."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        source=json.loads(a.input.read_text(encoding="utf-8"))
        report=build_report(source,path=str(a.input))
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc)
        return 2
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("===== COMBAT MASS PRESTATE PROJECTION V4 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    for row in report["observations"]:
        print(
            f"game={row['game_id']} T{row['turn']} V{row['vcr_id']} "
            f"ship={row['ship_id']} signature={row['source_signature']} "
            f"candidates={row['projection']['candidate_masses']} "
            f"factual={row['factual_mass_checked_after_projection']} "
            f"match={row['mass_in_prestate_candidates']} "
            f"status={row['projection']['projection_status']}"
        )
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
