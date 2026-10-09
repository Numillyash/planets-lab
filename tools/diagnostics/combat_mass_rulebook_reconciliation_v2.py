"""Checkpoint documented mass-bonus arithmetic against 67 factual VCR residuals.

Research only: this postprocessor does not reconstruct phase-accurate
shield-generator position or mutable Horwasp clans. The external Nu
rulebook is a separate cited source, not an override of game catalogs.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

SOURCE_SCHEMA = "planets-lab.combat-mass-complete-residuals.v1"
SCHEMA = "planets-lab.combat-mass-rulebook-reconciliation.v2"
SHIELD_BONUS_BY_ENGINE = {
    1: 1, 2: 1, 3: 2, 4: 2, 5: 13,
    6: 27, 7: 85, 8: 100, 9: 150,
}
DOCUMENTED_D19C_HULL_ID = 1039
DOCUMENTED_D19C_HULL_MASS = 46
OUTCOME_LABELS = {
    "documented_shield_bonus_numeric_match_not_precombat_proof",
    "reference_hull_catalog_conflict_numeric_match_not_proven",
    "horwasp_inverse_only_not_generatively_validated",
    "open_missing_owner_or_other_mechanism",
}
URLS = {
    "shield_generator": "https://help.planets.nu/abil-shield-generator",
    "combat_mass": "https://help.planets.nu/combat-mass",
    "race_sheet": "https://help.planets.nu/RaceSheetPlus",
    "horwasp": "https://help.planets.nu/horwasp-ships",
}


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _key(row: Mapping[str, Any]) -> tuple[int, int, int, str]:
    keys = [row.get(name) for name in ("game_id", "turn", "vcr_id")]
    if any(_int(value) is None for value in keys) or row.get("side") not in ("left", "right"):
        raise ValueError("invalid factual VCR side identity")
    return keys[0], keys[1], keys[2], row["side"]


def published_shield_candidates(
    *, observed_mass: int, base_mass: int, engine_id: int | None,
    side: str, left_bays: int,
) -> list[dict[str, int]]:
    """Rulebook arithmetic only; no generator-count/Host RNG prediction."""
    bonus = SHIELD_BONUS_BY_ENGINE.get(engine_id)
    if bonus is None or bonus <= 0:
        return []
    choices = (0, 360) if side == "right" and left_bays > 0 else (0,)
    return [
        {
            "generator_count_assumed": number,
            "documented_bonus_per_generator": bonus,
            "carrier_360_branch_assumed": carrier,
        }
        for number in (1, 2)
        for carrier in choices
        if observed_mass == base_mass + number * bonus + carrier
    ]


def classify(row: Mapping[str, Any]) -> dict[str, Any]:
    game, turn, vcr, side = _key(row)
    race = _int(row.get("race"))
    hull_id = _int(row.get("hull_id"))
    base = _int(row.get("federation_adjusted_base"))
    mass = _int(row.get("observed_vcr_mass"))
    left_bays = _int(row.get("VCR_left_baycount"))
    engine = _int(row.get("tminus1_owner_engine_id"))
    if None in (race, hull_id, base, mass, left_bays):
        raise ValueError("incomplete factual residual")
    if row.get("original_class") not in (
        "unexplained_with_available_owner_geometry",
        "horwasp_other_or_catalog_conflict",
    ):
        raise ValueError("not a source residual class")
    original = row["original_class"]
    source_rounding = row.get("ceil_rounding_hypotheses")
    if not isinstance(source_rounding, Mapping):
        raise ValueError("missing original independently labelled candidate")
    geometry = row.get("geometry") or {}
    if not isinstance(geometry, Mapping):
        raise ValueError("malformed owner T-1 geometry")

    output = {
        "game_id":game, "turn":turn, "vcr_id":vcr, "side":side,
        "ship_id":row.get("ship_id"), "owner_id":row.get("owner_id"),
        "race":race, "hull_id":hull_id,
        "source_catalog_mass":row.get("catalog_hull_mass"),
        "source_federation_adjusted_base":base,
        "factual_vcr_mass_comparator":mass,
        "Tminus1_engine_id":engine,
        "Tminus1_owner_state_available":row.get("tminus1_owner_ship_available"),
        "Tminus1_generator_geometry":{
            "participant_at_combat_site_Tminus1":geometry.get("tminus1_participant_at_site"),
            "generator_count_at_VCR_site_Tminus1":geometry.get("exact_site_generators"),
            "same_origin_waypoint_generator_count":geometry.get("same_origin_and_waypoint_generators"),
        },
        "rulebook_numeric_candidates":[],
        "status":None,
    }
    if race == 12:
        inverse = row.get("horwasp_clan_inverse_hypotheses")
        if not isinstance(inverse, list) or not inverse:
            raise ValueError("expected bounded Horwasp inverse mass scenarios")
        output["status"]="horwasp_inverse_only_not_generatively_validated"
        output["horwasp_scenario_count"]=len(inverse)
        output["Horwasp_Tminus1_clans_if_known"]=row.get("tminus1_owner_clans")
        output["source_game_hull_catalog_not_overridden"]=True
        output["inverse_is_oracle_observed_mass_dependent"]=True
        return output

    if original != "unexplained_with_available_owner_geometry":
        raise ValueError("non-Horwasp residual class mismatch")
    rulebook=published_shield_candidates(
        observed_mass=mass,base_mass=base,engine_id=engine,
        side=side,left_bays=left_bays,
    )
    source_candidates=source_rounding.get("match_candidates",[])
    if not isinstance(source_candidates,list):
        raise ValueError("malformed prior rounding candidates")
    source_projected={
        (c.get("generator_count_assumed"),c.get("carrier_plus360_branch_assumed"))
        for c in source_candidates
        if isinstance(c,Mapping)
    }
    official_projected={
        (c["generator_count_assumed"],c["carrier_360_branch_assumed"])
        for c in rulebook
    }
    if official_projected != source_projected:
        raise ValueError("documented bonus and existing ceil arithmetic disagree")

    if rulebook:
        output["status"]="documented_shield_bonus_numeric_match_not_precombat_proof"
        output["rulebook_numeric_candidates"]=rulebook
        output["Tminus1_phase_label"]=source_rounding.get("status")
        return output

    # Distinct **external reference** from the historical game catalog.
    # This must NEVER mutate specs or silently replace NuStaticSpecs.
    if hull_id == DOCUMENTED_D19C_HULL_ID:
        alt = published_shield_candidates(
            observed_mass=mass,
            base_mass=DOCUMENTED_D19C_HULL_MASS,
            engine_id=engine,side=side,left_bays=left_bays,
        )
        if alt and row.get("catalog_hull_mass") != DOCUMENTED_D19C_HULL_MASS:
            output["status"]="reference_hull_catalog_conflict_numeric_match_not_proven"
            output["reference_hull_base_mass"]=DOCUMENTED_D19C_HULL_MASS
            output["reference_hull_source"]="OFFICIAL_RACESHEETPLUS_D19C"
            output["historical_catalog_disagreement_KT"]=(
                row["catalog_hull_mass"]-DOCUMENTED_D19C_HULL_MASS
            )
            output["rulebook_numeric_candidates"]=alt
            output["requires_catalog_provenance_audit"]=True
            return output

    output["status"]="open_missing_owner_or_other_mechanism"
    output["open_reason"]=(
        "NO_OWNER_TMINUS1_SHIP"
        if row.get("tminus1_owner_ship_available") is False
        else "NO_DOCUMENTED_SHIELD_OR_REFERENCE_HULL_NUMERIC_MATCH"
    )
    return output


def build_report(input_json: Mapping[str, Any]) -> dict[str, Any]:
    if input_json.get("schema") != SOURCE_SCHEMA:
        raise ValueError("wrong complete-residual source schema")
    if input_json.get("status") != "COMPLETE_ALL_67_RESIDUALS_RECONSTRUCTED_NOT_PROMOTED":
        raise ValueError("residual source must be completed")
    original = input_json.get("summary", {})
    rows = input_json.get("all_residual_vcr_sides")
    if not isinstance(rows,list) or len(rows)!=original.get("all_residual_vcr_sides_recovered"):
        raise ValueError("factual source observation count mismatch")
    if len(rows) != 67 or original.get("newly_recovered_ids") != 27:
        raise ValueError("expected frozen 67/27 research checkpoint")
    classified=[]
    identities=set()
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("bad observed residual row")
        item=classify(row)
        identity=(item["game_id"],item["turn"],item["vcr_id"],item["side"])
        if identity in identities:
            raise ValueError("duplicate VCR side")
        identities.add(identity)
        classified.append(item)
    labels=Counter(row["status"] for row in classified)
    if set(labels)-OUTCOME_LABELS or sum(labels.values())!=67:
        raise ValueError("classification coverage or label mismatch")
    expected={
        "documented_shield_bonus_numeric_match_not_precombat_proof":49,
        "reference_hull_catalog_conflict_numeric_match_not_proven":2,
        "horwasp_inverse_only_not_generatively_validated":15,
        "open_missing_owner_or_other_mechanism":1,
    }
    if labels != Counter(expected):
        raise ValueError(f"unexpected frozen V1 reconciliation profile: {dict(labels)}")
    if len({(r["game_id"],r["turn"],r["ship_id"]) for r in classified}) != original.get("distinct_ship_turn_groups"):
        raise ValueError("ship/turn group denominator changed")

    per_label={}
    for label in expected:
        matching=[r for r in classified if r["status"]==label]
        per_label[label]={
            "vcr_sides":len(matching),
            "distinct_ship_turns":len({(r["game_id"],r["turn"],r["ship_id"]) for r in matching}),
            "distinct_games":len({r["game_id"] for r in matching}),
        }
    rounding=[r for r in classified if r["status"]=="documented_shield_bonus_numeric_match_not_precombat_proof"]
    by_engine=Counter(str(r["Tminus1_engine_id"]) for r in rounding)
    by_phase=Counter(str(r["Tminus1_phase_label"]) for r in rounding)
    d19=[r for r in classified if r["status"]=="reference_hull_catalog_conflict_numeric_match_not_proven"]
    if any(r["historical_catalog_disagreement_KT"] != 50 for r in d19):
        raise ValueError("D19c discrepancy not the independently documented 46 vs 96 KT")
    return {
        "schema":SCHEMA,
        "status":"DOCUMENTED_ARITHMETIC_AND_SOURCE_CONFLICTS_CHECKPOINTED_NOT_HOST_PREDICTIVE",
        "source":{
            "v1_schema":SOURCE_SCHEMA,
            "runtime": "runtime-logs/combat-mass-complete-residuals-v1/20261009T164712Z_614b20e04efe",
            "source_commit":input_json["source"]["survey_commit"],
            "survey_identity":input_json["source"]["survey_experiment_id"],
            "all_67_observations_reconciled":True,
        },
        "summary":{
            "factual_vcr_sides":67,
            "distinct_ship_turn_groups":original["distinct_ship_turn_groups"],
            "repeated_observations":67-original["distinct_ship_turn_groups"],
            "per_group":per_label,
            "documented_bonus_engine_breakdown":dict(sorted(by_engine.items())),
            "rulebook_match_tminus1_phase_evidence":dict(sorted(by_phase.items())),
            "remaining_without_nonhorwasp_numeric_alternative":1,
            "horwasp_interpolation_is_NOT_independently_validated":True,
            "D19c_46KT_is_external_reference_NOT_replacement_of_game_catalog":True,
        },
        "rulebook":{
            "shield_bonus_KT_by_engine_id":SHIELD_BONUS_BY_ENGINE,
            "D19c_reference_hull_id":DOCUMENTED_D19C_HULL_ID,
            "D19c_reference_mass_KT":DOCUMENTED_D19C_HULL_MASS,
            "URLs":URLS,
        },
        "all_67_classifications":classified,
        "D19c_source_conflicts":d19,
        "unresolved_cases":[r for r in classified if r["status"]=="open_missing_owner_or_other_mechanism"],
        "evidence_boundary":(
            "The documented Shield Generator engine table independently supports integer "
            "bonus values, but the observed current-VCR mass is used to choose "
            "number of generators and possible +360 branch. The actual active "
            "generators, exact host phase and RNG remain unpredicted. The official "
            "D19c reference 46 disagrees with the game catalog 96: numerical "
            "agreement is NOT authorization to replace per-game static values. "
            "Horwasp clan inversions are calculated from factual VCR mass and "
            "do not reconstruct preceding damage/attrition. Counts are VCR sides, "
            "and must not be mistaken for independent ship/game sample sizes."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        src=json.loads(a.source.read_text(encoding="utf-8"))
        result=build_report(src)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(a.output.suffix+".tmp")
        tmp.write_text(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc)
        return 2
    print("===== COMBAT MASS RULEBOOK RECONCILIATION V2 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("D19c_catalog_conflicts:",result["D19c_source_conflicts"])
    print("unresolved_cases:",result["unresolved_cases"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
