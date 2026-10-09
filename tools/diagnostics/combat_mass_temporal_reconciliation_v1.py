"""Read-only reconciliation of 67 mass residuals with independent T-1 static.

Consumes ONLY two frozen, published evidence JSON files and checks all 14
control game-turns before comparing 67 factual VCR sides with prior-owner
T-1 static hull masses. Does not infer exact combat phase or simulate VCR.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SOURCE_CONTROLS="planets-lab.combat-mass-capture-phase-controls.v1"
SOURCE_RESIDUALS="planets-lab.combat-mass-complete-residuals.v1"
SCHEMA="planets-lab.combat-mass-temporal-reconciliation.v1"
BONUSES_BY_ENGINE={1:1,2:1,3:2,4:2,5:13,6:27,7:85,8:100,9:150}
KNOWN_D19C={(217591,75,756,"right"),(325434,149,1075,"left")}
KNOWN_BROOD={
    (217591,149,2405,"left"),(217591,149,2406,"right"),
    (217591,149,2421,"right"),(217591,149,2422,"right"),
    (217591,149,2423,"right"),
}


def _integer(value:Any)->int|None:
    return value if type(value) is int else None


def _key(row:Mapping[str,Any])->tuple[int,int,int,str]:
    g,t,v,s=(row.get(k) for k in ("game_id","turn","vcr_id","side"))
    if any(_integer(x) is None for x in (g,t,v)) or s not in ("left","right"):
        raise ValueError("invalid factual VCR identity")
    return (g,t,v,s)


def _control_mass_map(c:Mapping[str,Any])->dict[int,dict[str,int]]:
    if c.get("status")!="SAME_CHANGE_SET_ACROSS_AVAILABLE_TMINUS1_PERSPECTIVES":
        raise ValueError("static snapshots have unsupported disagreement")
    perspectives=c.get("per_perspective")
    if not isinstance(perspectives,list) or not perspectives:
        raise ValueError("T-1 perspectives missing")
    if c.get("per_perspective_truncated"):
        raise ValueError("cannot assert all-perspective agreement when truncated")
    normalized=[]
    for snap in perspectives:
        if snap.get("change_details_truncated"):
            raise ValueError("changed hull details truncated")
        rows=snap.get("changed_hulls")
        if not isinstance(rows,list):
            raise ValueError("changed hull details unavailable")
        current={}
        for row in rows:
            hid,old,new=(
                _integer(row.get(k)) for k in ("hull_id","first_mass","Tminus1_mass")
            )
            if None in (hid,old,new) or hid in current or old==new:
                raise ValueError("invalid or duplicate mass-change record")
            current[hid]={"first_mass":old,"Tminus1_mass":new}
        if snap.get("changed_hull_count")!=len(current):
            raise ValueError("changed hull count mismatch")
        normalized.append(current)
    if any(p!=normalized[0] for p in normalized[1:]):
        raise ValueError("T-1 perspectives disagree on hull mass")
    if c.get("max_mass_changed_hulls")!=len(normalized[0]):
        raise ValueError("control mass change aggregate mismatch")
    return normalized[0]


def _classify_temporal(row:Mapping[str,Any],new_mass:int)->dict[str,Any]:
    race,engine,mass,catalog,hull,side,clans=(
        row.get("race"),row.get("tminus1_owner_engine_id"),
        row.get("observed_vcr_mass"),row.get("catalog_hull_mass"),
        row.get("hull_id"),row.get("side"),row.get("tminus1_owner_clans")
    )
    if any(_integer(v) is None for v in (race,mass,catalog,hull)):
        raise ValueError("incomplete source observed case")
    observations=[]
    if race==12:
        capacity=row.get("catalog_cargo_capacity")
        if _integer(capacity) is None or capacity<=0:
            raise ValueError("Horwasp cargo capacity unavailable")
        for bonus in (0,360) if side=="right" and row.get("VCR_left_baycount",0)>0 else (0,):
            if mass==2*new_mass+bonus:
                observations.append({
                    "branch":"HORWASP_FULL_LOAD_ENDPOINT",
                    "reference_precombat_catalog_mass":new_mass,
                    "cargo_capacity":capacity,
                    "Tminus1_clans":clans,
                    "Tminus1_full_load_independently_seen":clans==capacity if _integer(clans) is not None else None,
                    "right_carrier_bonus_assumed":bonus,
                    "mass_candidate":2*new_mass+bonus,
                })
    else:
        for n in (1,2):
            if engine not in BONUSES_BY_ENGINE:
                continue
            for bonus in (0,360) if side=="right" and row.get("VCR_left_baycount",0)>0 else (0,):
                projected=new_mass+n*BONUSES_BY_ENGINE[engine]+bonus
                if mass==projected:
                    obs={
                        "branch":"DOCUMENTED_SHIELD_GENERATOR_ARITHMETIC",
                        "reference_precombat_catalog_mass":new_mass,
                        "engine":engine,
                        "generators_assumed":n,
                        "documented_bonus_per_generator":BONUSES_BY_ENGINE[engine],
                        "right_carrier_bonus_assumed":bonus,
                        "mass_candidate":projected,
                    }
                    geom=row.get("geometry") or {}
                    atsite=geom.get("exact_site_generators")
                    obs["generator_count_Tminus1_at_VCR_site"]=atsite
                    obs["Tminus1_site_support_for_assumed_n"]=(
                        atsite>=n and geom.get("tminus1_participant_at_site") is True
                        if _integer(atsite) is not None else None
                    )
                    observations.append(obs)
    return {
        "game_id":row["game_id"],"turn":row["turn"],"vcr_id":row["vcr_id"],
        "side":row["side"],"ship_id":row["ship_id"],"race":race,
        "hull_id":hull,"first_catalog_mass":catalog,
        "Tminus1_static_mass":new_mass,"factual_vcr_mass":mass,
        "source_original_class":row["original_class"],
        "Tminus1_source_changed_by_KT":new_mass-catalog,
        "arithmetic_candidates":observations,
        "numeric_match_without_oracle_as_input":bool(observations),
        "boundary":"VCR factual mass SELECTS matching arithmetic branch; Host phase/SG activation or carrier RNG not proven",
    }


def capture_candidate(controls:Mapping[str,Any])->dict[str,Any]:
    seq=controls.get("Rush_VCR_sequence",{}).get("VCRs",[])
    if len(seq)!=2 or [s.get("vcr_id") for s in seq]!=[1016,1017]:
        raise ValueError("frozen two Rush VCRs not available")
    r0,r1=seq
    owner=controls.get("Rush_owner_snapshots",{})
    old=owner.get("owner5_Tminus1_Rush27",[])
    saber=owner.get("owner4_Tminus1_Saber_at_site",[])
    if len(old)!=1 or old[0].get("engineid")!=9 or old[0].get("hullid")!=94:
        raise ValueError("independent original Rush engine missing/changed")
    if len(saber)!=1 or saber[0].get("ship_id")!=406:
        raise ValueError("independent recipient-owned Saber missing/changed")
    a,b=r0.get("rush_start_state",{}),r1.get("rush_start_state",{})
    facts={
        "same_hull":a.get("hullid")==b.get("hullid")==94,
        "same_id":a.get("objectid")==b.get("objectid")==27,
        "owner_transition":(r0.get("owner_id"),r1.get("owner_id"))==(5,4),
        "same_combat_site":r0.get("same_site")==r1.get("same_site")==[1455,2615],
        "initial_crew28":a.get("crew")==28,
        "next_crew10":b.get("crew")==10,
        "engine9_from_owner5_Tminus1":True,
        "Saber406_owned_by_owner4_Tminus1_at_battle_site":True,
        "factual_mass_transition":(r0.get("factual_mass"),r1.get("factual_mass"))==(645,795),
    }
    if not all(facts.values()):
        raise ValueError("Rush independently observed input identity changed")
    proposed=645+BONUSES_BY_ENGINE[old[0]["engineid"]]
    if proposed!=b["mass"] or b["mass"]!=795:
        raise ValueError("Rush formula does not reconcile")
    return {
        "game_id":617883,"turn":201,"vcrs":[1016,1017],"ship_id":27,
        "independently_observed_inputs":facts,
        "independent_candidate_formula":{
            "initial_static_battle_mass_KT":645,
            "original_owner_Tminus1_engine_id":9,
            "documented_SG_bonus_KT":150,
            "one_new_owner_Tminus1_Saber_at_site":406,
            "candidate_second_combat_mass_KT":proposed,
            "second_factual_combat_mass_KT":b["mass"],
        },
        "hypothesis":"CAPTURE_RECOMPUTES_NEW_OWNER_SHIELD_GENERATOR_BONUS",
        "capture_between_VCRs_is_strongly_supported_not_terminal_outcome_verified":True,
        "precombat_generator_activation_still_not_phase_independently_proven":True,
        "later_T201_id27_Victorious_is_NOT_assumed_continuous_with_Rush":True,
    }


def build_report(controls:Mapping[str,Any],residuals:Mapping[str,Any])->dict[str,Any]:
    if controls.get("schema")!=SOURCE_CONTROLS or controls.get("status")!=(
        "INDEPENDENT_CAPTURE_AND_TEMPORAL_STATIC_CONTROLS_OBSERVATIONAL_NOT_PROMOTED"
    ):
        raise ValueError("invalid capture control source")
    if residuals.get("schema")!=SOURCE_RESIDUALS or residuals.get("status")!=(
        "COMPLETE_ALL_67_RESIDUALS_RECONSTRUCTED_NOT_PROMOTED"
    ):
        raise ValueError("invalid complete residual source")
    ref=controls.get("static_snapshot_controls")
    if not isinstance(ref,list) or len(ref)!=14:
        raise ValueError("exact fourteen original static controls required")
    control_maps={}
    static_changed=[]
    for c in ref:
        key=(c.get("game_id"),c.get("turn"))
        if key in control_maps:
            raise ValueError("duplicate selected static control")
        changes=_control_mass_map(c)
        control_maps[key]=changes
        if changes:
            static_changed.append({
                "game_id":key[0],"turn":key[1],"perspectives":c["perspectives"],
                "changed_hulls":[{"hull_id":hid,**fields}
                                 for hid,fields in sorted(changes.items())],
            })
    if len(static_changed)!=6:
        raise ValueError("original six changed static controls no longer reconcile")
    rows=residuals.get("all_residual_vcr_sides")
    if not isinstance(rows,list) or len(rows)!=67:
        raise ValueError("source 67 side identities missing")
    matches=[]
    seen=set()
    for row in rows:
        key=_key(row)
        if key in seen:
            raise ValueError("duplicate source VCR side")
        seen.add(key)
        ch=control_maps.get(key[:2],{}).get(row["hull_id"])
        if ch is None:
            continue
        if ch["first_mass"]!=row["catalog_hull_mass"]:
            raise ValueError("source first static baseline mismatch")
        matches.append(_classify_temporal(row,ch["Tminus1_mass"]))
    if len(matches)!=7:
        raise ValueError("expected seven residuals changed by T-1 hull mass")
    target={_key(r) for r in matches}
    if target!=KNOWN_D19C|KNOWN_BROOD:
        raise ValueError("original changed-mass identity set shifted")
    if any(not row["numeric_match_without_oracle_as_input"] for row in matches):
        raise ValueError("some target T-1 arithmetic does not match")
    independent_brood=[
        r for r in matches
        if r["hull_id"]==117 and any(
            s["Tminus1_full_load_independently_seen"] is True
            for s in r["arithmetic_candidates"]
        )
    ]
    uncertain_brood=[
        r for r in matches if r["hull_id"]==117 and r not in independent_brood
    ]
    if len(independent_brood)!=4 or len(uncertain_brood)!=1:
        raise ValueError("Horwasp independently seen clan load profile drifted")
    counts=Counter(r["hull_id"] for r in matches)
    if counts!={117:5,1039:2}:
        raise ValueError("unexpected source hull changes")
    capture=capture_candidate(controls)
    return {
        "schema":SCHEMA,
        "status":"TEMPORAL_STATIC_AND_CAPTURE_RECONCILED_OBSERVATIONAL_NOT_PROMOTED",
        "summary":{
            "static_control_game_turns_checked":len(ref),
            "game_turns_with_static_mass_drift":len(static_changed),
            "residual_VCR_sides":67,
            "residuals_with_direct_Tminus1_changed_hull":len(matches),
            "D19c_reconciled_numeric_sides":counts[1039],
            "Brood_reconciled_numeric_sides":counts[117],
            "Brood_full_Tminus1_clans_independently_seen":len(independent_brood),
            "Brood_Tminus1_clans_unavailable":len(uncertain_brood),
            "residual_sides_unaffected_by_direct_confirmed_mass_changes":67-len(matches),
            "Rush_capture_mass_recalculation_candidate":True,
        },
        "all_14_static_controls_with_changes":static_changed,
        "seven_Tminus1_changed_hull_residuals":matches,
        "Rush_same_turn_capture_and_generator_hypothesis":capture,
        "boundary":(
            "T-1 archived hull mass is independent of a factual VCR mass and "
            "can resolve a stale first-member static source. But arithmetic "
            "branches are selected retrospectively against factual mass. "
            "Horwasp start-to-start clan attrition, carrier RNG, true combat "
            "capture terminal status and SG activation phase remain NOT "
            "generatively verified. The 14 static controls are targeted, "
            "not a random population sample. This report makes NO rules "
            "changes to production, combat planner or probabilistic evaluator."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--capture-controls",type=Path,required=True)
    p.add_argument("--complete-residuals",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        controls=json.loads(a.capture_controls.read_text(encoding="utf-8"))
        residuals=json.loads(a.complete_residuals.read_text(encoding="utf-8"))
        report=build_report(controls,residuals)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_name(a.output.name+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== MASS TEMPORAL RECONCILIATION V1 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    for row in report["seven_Tminus1_changed_hull_residuals"]:
        print(f"game={row['game_id']} T{row['turn']} V{row['vcr_id']} hull={row['hull_id']} "
              f"first={row['first_catalog_mass']} Tminus1={row['Tminus1_static_mass']} "
              f"observed={row['factual_vcr_mass']} choices={row['arithmetic_candidates']}")
    print("Rush:",report["Rush_same_turn_capture_and_generator_hypothesis"]["independent_candidate_formula"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
