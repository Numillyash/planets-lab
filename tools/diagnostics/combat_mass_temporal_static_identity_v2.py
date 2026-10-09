"""Time-indexed static catalog and VCR ship-ID discontinuity audit.

This is an observational, fail-closed gate. Uses the immutable public100
corpus and the published previous owner-provenance report. In particular,
the public turn-0 hull catalog is NOT allowed to silently override the
owner-perspective precombat-turn static records, and a ship ID observed
with different hull/owner across sources is NOT a stable physical identity.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,member_refs_for_turns,reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs

SCHEMA="planets-lab.combat-mass-temporal-static-identity.v2"
SOURCE_SCHEMA="planets-lab.combat-mass-catalog-owner-provenance.v1"
D19C_GAMES={(217591,75,756,758),(325434,149,1075,274)}
RUSH=(617883,201,1017,27)
SOURCE_CATALOG_MASS=96
CURRENT_D19C_CATALOG_MASS=46


def _int(value:Any)->int|None:
    return value if isinstance(value,int) and not isinstance(value,bool) else None


def _records(member:Mapping[str,Any],hull_id:int=1039)->dict[str,Any]:
    result={}
    for collection in ("hulls","hullsall"):
        items=member.get(collection)
        if items is None:
            result[collection]={"status":"MISSING_COLLECTION","records":[]}
            continue
        if not isinstance(items,list):
            raise ValueError(f"unexpected static collection {collection}")
        records=[]
        for raw in items:
            if not isinstance(raw,Mapping):
                raise ValueError("invalid static row")
            if _int(raw.get("id"))==hull_id:
                records.append({
                    "mass":_int(raw.get("mass")),
                    "name":raw.get("name"),
                    "parentid":_int(raw.get("parentid")),
                    "engine_count":_int(raw.get("engines")),
                    "cargo":_int(raw.get("cargo")),
                })
        result[collection]={"status":"PRESENT","records":records}
    return result


def _single_hull_mass(member:Mapping[str,Any])->int|None:
    found=_records(member)["hulls"]["records"]
    if len(found)>1:
        raise ValueError("multiple static hull records for 1039")
    return found[0]["mass"] if found else None


def select_target_owner_refs(refs:list[Any],owner:int)->list[Any]:
    by_turn=defaultdict(list)
    for ref in refs:
        if ref.perspective_player_id==owner:
            by_turn[ref.archive_turn].append(ref)
    selected=[]
    for turn in sorted(by_turn):
        candidates=sorted(by_turn[turn],key=lambda r:(r.member_id,r.source_member_name))
        # Multiple conflicting owner sources on one turn would invalidate
        # inference; the audit deliberately preserves all such duplicates.
        selected.extend(candidates)
    return selected


def temporal_static_rows(*,conn:Any,game:int,owner:int,last_turn:int)->dict[str,Any]:
    # Scan one owner across every available archived turn up to the target,
    # rather than comparing only "first" and "last" (which leaks future state).
    refs=member_refs_for_turns(
        conn,game_id=game,turns=set(range(0,last_turn+1)),
        include_embedded_turn=False,
    )
    selected=select_target_owner_refs(refs,owner)
    if not selected:
        raise ValueError("no owner-perspective static chronology")
    raw_rows=[]
    by_turn=defaultdict(set)
    for ref,member in reconstruct_members(conn,selected):
        mass=_single_hull_mass(member)
        by_turn[ref.archive_turn].add(mass)
        raw_rows.append({
            "archive_turn":ref.archive_turn,
            "embedded_turn":ref.embedded_turn,
            "member_id":ref.member_id,
            "perspective_player_id":ref.perspective_player_id,
            "decoded_payload_sha256":ref.decoded_payload_sha256,
            "D19c_hulls_mass":mass,
            "D19c_static":_records(member),
        })
    inconsistent=[
        {"archive_turn":t,"values":sorted(v,key=lambda x:(x is None,x))}
        for t,v in sorted(by_turn.items()) if len(v)>1
    ]
    compressed=[]
    for row in raw_rows:
        mass=row["D19c_hulls_mass"]
        if not compressed or compressed[-1]["mass"]!=mass:
            compressed.append({
                "mass":mass,"first_observed_turn":row["archive_turn"],
                "last_observed_turn":row["archive_turn"],
                "first_member_id":row["member_id"],
                "observations":1,
            })
        else:
            compressed[-1]["last_observed_turn"]=row["archive_turn"]
            compressed[-1]["observations"]+=1
    last_before=[x for x in raw_rows if x["archive_turn"]==last_turn-1]
    first=[x for x in raw_rows if x["archive_turn"]==0]
    before_values=sorted({x["D19c_hulls_mass"] for x in last_before if x["D19c_hulls_mass"] is not None})
    first_values=sorted({x["D19c_hulls_mass"] for x in first if x["D19c_hulls_mass"] is not None})
    return {
        "game_id":game,"owner_id":owner,"combat_turn":last_turn,
        "source_owner_members_inspected":len(raw_rows),
        "archive_turns_with_owner_static":len(by_turn),
        "archive_turns_missing_owner_static":sorted(set(range(last_turn+1))-set(by_turn)),
        "T0_owner_static_mass_values":first_values,
        "Tminus1_owner_static_mass_values":before_values,
        "transition_segments_in_member_order":compressed,
        "conflicting_owner_static_same_turn":inconsistent,
        "all_owner_static_history":raw_rows,
        "source_is_time_indexed_not_global_first_member":True,
    }


def vcr_id_history(*,conn:Any,game:int,turn:int,ship_id:int)->dict[str,Any]:
    matches=[]
    by_turn=Counter()
    for candidate_turn in range(turn-1,turn+2):
        cases=combat_vcr_cases_for_turns(
            conn,game_id=game,battle_turns={candidate_turn}
        )
        for (t,vcr_id),case in sorted(cases.items()):
            payload=case.payload
            for side in ("left","right"):
                part=payload.get(side)
                if not isinstance(part,Mapping) or _int(part.get("objectid"))!=ship_id:
                    continue
                other=payload.get("right" if side=="left" else "left")
                if not isinstance(other,Mapping):
                    other={}
                row={
                    "turn":t,"vcr_id":vcr_id,"side":side,
                    "object_id":ship_id,
                    "owner_id":_int(payload.get(side+"ownerid")),
                    "race_id":_int(part.get("raceid")),
                    "hull_id":_int(part.get("hullid")),
                    "mass":_int(part.get("mass")),
                    "factual_site":[_int(payload.get("x")),_int(payload.get("y"))],
                    "other_side":{
                        "object_id":_int(other.get("objectid")),
                        "hull_id":_int(other.get("hullid")),
                        "owner_id":_int(payload.get(("right" if side=="left" else "left")+"ownerid")),
                    },
                    "observation_count":case.observation_count,
                }
                matches.append(row)
                by_turn[t]+=1
    return {
        "game_id":game,"target_turn":turn,"ship_id":ship_id,
        "lookback_current_forward_turns":[turn-1,turn,turn+1],
        "vcr_appearances":matches,
        "vcr_appearances_by_turn":dict(sorted(by_turn.items())),
        "distinct_hull_owner_identities":sorted({
            (r["turn"],r["owner_id"],r["hull_id"])
            for r in matches
        },key=lambda a:(a[0],str(a[1]),str(a[2]))),
        "VCR_ID_ORDER_NOT_PROVEN_HOST_COMBAT_PHASE_ORDER":True,
    }


def archive_ship_id_states(case:Mapping[str,Any])->list[dict[str,Any]]:
    states=[]
    for snapshot in case["archive_snapshots"]:
        prov=snapshot["provenance"]
        for s in snapshot["target"].get("target_ships",[]):
            states.append({
                "archive_turn":prov["archive_turn"],
                "source_member_id":prov["member_id"],
                "perspective_player_id":prov["perspective_player_id"],
                "perspective_is_owner_of_target_VCR":snapshot["perspective_is_owner"],
                "source_owner_id":_int(s.get("ownerid")),
                "hull_id":_int(s.get("hullid")),
                "engine_id":_int(s.get("engineid")) if snapshot["perspective_is_owner"] else None,
                "engine_id_masked_or_untrusted_from_foreign_perspective":not snapshot["perspective_is_owner"],
                "same_owner_generators_at_archived_location":s.get(
                    "same_owner_shield_generator_ids_at_snapshot_ship_xy",[]
                ),
                "xy":[_int(s.get("x")),_int(s.get("y"))],
            })
    return states


def build_report(*,conn:Any,source:Mapping[str,Any],dbpath:str)->dict[str,Any]:
    if source.get("schema")!=SOURCE_SCHEMA or source.get("status")!="THREE_MASS_SOURCE_PROVENANCE_CASES_OBSERVED_NOT_PROMOTED":
        raise ValueError("incomplete V1 provenance input")
    cases=source.get("cases")
    if not isinstance(cases,list) or len(cases)!=3:
        raise ValueError("expected three frozen source cases")
    seen=set()
    d19=[]
    rush_case=None
    for case in cases:
        key=(case.get("game_id"),case.get("turn"),case.get("vcr_id"),case.get("ship_id"))
        if key in seen:
            raise ValueError("duplicate frozen source case")
        seen.add(key)
        if key in D19C_GAMES:
            if case.get("hull_id")!=1039 or case["typed_first_member_hull"]["mass"]!=SOURCE_CATALOG_MASS:
                raise ValueError("expected D19c first-member catalog mass 96")
            hist=temporal_static_rows(
                conn=conn,game=case["game_id"],owner=case["owner_id"],
                last_turn=case["turn"],
            )
            if hist["Tminus1_owner_static_mass_values"]!=[CURRENT_D19C_CATALOG_MASS]:
                raise ValueError("the T-1 source static does not support D19c mass46")
            if hist["conflicting_owner_static_same_turn"]:
                raise ValueError("conflicting owner static values at same turn")
            hist["VCR_mass_comparator"]=case["factual_vcr_mass"]
            hist["expected_two_generator_rulebook_arithmetic_mass"]=(
                CURRENT_D19C_CATALOG_MASS+
                (300 if case["game_id"]==217591 else 2)
            )
            if hist["VCR_mass_comparator"]!=hist["expected_two_generator_rulebook_arithmetic_mass"]:
                raise ValueError("VCR arithmetic is not independently corroborated")
            d19.append(hist)
        elif key==(RUSH[0],RUSH[1],RUSH[2],RUSH[3]):
            rush_case=case
        else:
            raise ValueError("unrecognized source case")
    if len(d19)!=2 or rush_case is None:
        raise ValueError("missing D19c or Rush source")
    rush_states=archive_ship_id_states(rush_case)
    vcrs=vcr_id_history(conn=conn,game=RUSH[0],turn=RUSH[1],ship_id=RUSH[3])
    target=[
        x for x in vcrs["vcr_appearances"]
        if x["turn"]==201 and x["vcr_id"]==1017 and x["hull_id"]==94
    ]
    if len(target)!=1 or target[0]["owner_id"]!=4 or target[0]["mass"]!=795:
        raise ValueError("Rush source VCR identity mismatch")
    before=[
        r for r in rush_states if r["archive_turn"]==200
        and r["source_owner_id"]==5 and r["hull_id"]==94
    ]
    at=[
        r for r in rush_states if r["archive_turn"]==201
        and r["source_owner_id"]==4 and r["hull_id"]==35
    ]
    if not before or not at:
        raise ValueError("Rush ship-ID cross-snapshot discontinuity not retained")
    owner_at=[r for r in at if r["perspective_is_owner_of_target_VCR"]]
    if not owner_at or any(r["engine_id"]!=9 for r in owner_at):
        raise ValueError("observed T ship-ID owner-engine state changed unexpectedly")
    rush={
        "source_case":{"game_id":617883,"turn":201,"vcr_id":1017,"ship_id":27},
        "source_vcr":{"mass":795,"hull_id":94,"owner_id":4},
        "raw_archive_ID_states":rush_states,
        "vcr_id_history":vcrs,
        "distinct_physical_identity_unresolved":True,
        "Tminus1_rush_owner5":len(before),
        "T_owner4_victorious_engine9":len(owner_at),
        "T_owner_engine9_is_NOT_verified_equipment_of_T_VCR_Rush":True,
        "possible_explanations_not_disambiguated":[
            "ship_id_reuse_after_destruction_or_capture",
            "foreign_intelligence_stale_or_masked",
            "VCR_id_vs_archived_ship_id_identity_semantics",
            "multiple combat_or_build_phases_inside_same_turn",
        ],
    }
    return {
        "schema":SCHEMA,
        "status":"STATIC_CATALOG_DRIFT_AND_SHIP_ID_DISCONTINUITY_OBSERVATIONAL_NOT_PROMOTED",
        "source_db":dbpath,
        "source_v1_schema":SOURCE_SCHEMA,
        "summary":{
            "d19c_games_scanned":len(d19),
            "Tminus1_D19c_mass46_confirmed":len(d19),
            "first_member_mass96_known":len(d19),
            "Rush_VCR_ship_id":27,
            "Rush_Tminus1_owner5_hull94_to_T_owner4_hull35_discontinuity":True,
        },
        "D19c_temporal_catalogs":d19,
        "Rush_ship_id_discontinuity":rush,
        "evidence_boundary":(
            "The T-1 owner static hull mass is independent of observed VCR mass "
            "but this audit does not prove NuHost's effective static source "
            "or the exact combat-phase generator count. A ship ID seen in "
            "different archives/VCRs with different hull/owner is not a "
            "demonstrably continuous physical vessel; T archived engine9 of "
            "Victorious cannot be retroactively attributed to the Rush VCR. "
            "No game catalog overrides or combat predictor rules promoted."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--source-v1",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        src=json.loads(a.source_v1.read_text(encoding="utf-8"))
        conn,path=connect_compact_generation_read_only(
            a.corpus_db_generation,a.corpus_db_root
        )
        try:
            report=build_report(conn=conn,source=src,dbpath=str(path))
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== MASS TEMPORAL STATIC AND SHIP ID AUDIT V2 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    for item in report["D19c_temporal_catalogs"]:
        print("game:",item["game_id"],"T:",item["combat_turn"],"T0:",item["T0_owner_static_mass_values"],
              "Tminus1:",item["Tminus1_owner_static_mass_values"],
              "segments:",item["transition_segments_in_member_order"],
              "member_count:",item["source_owner_members_inspected"])
    print("Rush VCR appearances:",report["Rush_ship_id_discontinuity"]["vcr_id_history"]["vcr_appearances"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
