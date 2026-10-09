"""Independent static-snapshot controls and within-turn Rush capture evidence.

Reads immutable public100 and checked V2/Digest evidence. Factual VCR mass
is only a comparator; host combat result/capture is NOT predicted.
Archived ship ID has no assumed physical continuity after a destruction,
capture, postcombat build, or cross-perspective masking.
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
if str(ROOT/"src") not in sys.path:
    sys.path.insert(0,str(ROOT/"src"))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, first_last_member_refs,
    member_refs_for_turns, reconstruct_members,
)
from planets_lab.corpus.corpus_db_compact import reconstruct_compact_member
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

SCHEMA="planets-lab.combat-mass-capture-phase-controls.v1"
SOURCE_SCHEMA="planets-lab.combat-mass-temporal-static-identity.v2"
DIGEST_SCHEMA="planets-lab.combat-mass-long-survey-digest.v1"
RUSH_GAME=617883
RUSH_TURN=201
RUSH_ID=27
SITE=(1455,2615)
RUSH_EXPECTED={
    1016:{"side":"right","owner":5,"hull":94,"mass":645},
    1017:{"side":"left","owner":4,"hull":94,"mass":795},
}
STATIC_PRIORITY_TURNS=12
VCR_SIDE_FIELDS=(
    "objectid","hullid","raceid","mass","crew","damage","shield","shields",
    "fighters","baycount","torps","torpedoes","beamcount","beamid","torpedoid",
    "ammunition","name",
)
OWNER_SHIP_FIELDS=(
    "id","ownerid","hullid","engineid","mass","name","x","y","targetx",
    "targety","warp","mission","damage","crew","ammo","neutronium",
)


def _int(x:Any)->int|None:
    return x if isinstance(x,int) and not isinstance(x,bool) else None


def _row_subset(row:Mapping[str,Any],fields:tuple[str,...])->dict[str,Any]:
    return {key:row.get(key) for key in fields if key in row}


def _hull_mass_map(member:Mapping[str,Any])->dict[int,int]:
    records=member.get("hulls")
    if not isinstance(records,list):
        raise ValueError("archived static hulls missing")
    result={}
    for row in records:
        if not isinstance(row,Mapping):
            raise ValueError("invalid archived static hull row")
        hid,mass=_int(row.get("id")),_int(row.get("mass"))
        if hid is None or mass is None:
            continue
        if hid in result and result[hid]!=mass:
            raise ValueError(f"duplicate hull id {hid} conflicting mass")
        result[hid]=mass
    return result


def _all_owner_rows(member:Mapping[str,Any],owner:int)->list[Mapping[str,Any]]:
    ships=member.get("ships")
    if not isinstance(ships,list):
        return []
    return [
        s for s in ships
        if isinstance(s,Mapping) and _int(s.get("ownerid"))==owner
    ]


def _generator_ids(member:Mapping[str,Any],owner:int,site:tuple[int,int],
                   hulls:Mapping[int,Any])->list[dict[str,Any]]:
    results=[]
    for s in _all_owner_rows(member,owner):
        hid=_int(s.get("hullid"))
        hull=hulls.get(hid)
        if hull is None:
            continue
        if "shield generator" not in str(hull.name).casefold() and "shield generator" not in str(hull.special).casefold():
            continue
        x,y=_int(s.get("x")),_int(s.get("y"))
        tx,ty=_int(s.get("targetx")),_int(s.get("targety"))
        same=(x,y)==site
        waypoint=(tx,ty)==site
        if same or waypoint or (x is not None and y is not None and
                                  (x-site[0])**2+(y-site[1])**2<=81):
            results.append({
                "ship_id":_int(s.get("id")),
                "hull_id":hid,
                "origin":[x,y],
                "waypoint":[tx,ty],
                "site_exact_at_archive":same,
                "waypoint_exact_to_VCR_site":waypoint,
                "warp":_int(s.get("warp")),
                "neutronium":_int(s.get("neutronium")),
            })
    return results


def rush_combat_observations(conn:Any)->dict[str,Any]:
    vcrs=combat_vcr_cases_for_turns(
        conn,game_id=RUSH_GAME,battle_turns={RUSH_TURN}
    )
    items=[]
    for vcrid, expected in sorted(RUSH_EXPECTED.items()):
        case=vcrs.get((RUSH_TURN,vcrid))
        if case is None:
            raise ValueError(f"missing frozen VCR {vcrid}")
        raw=case.payload
        side=raw.get(expected["side"])
        if not isinstance(side,Mapping) or (
            _int(side.get("objectid"))!=RUSH_ID
            or _int(raw.get(expected["side"]+"ownerid"))!=expected["owner"]
            or _int(side.get("hullid"))!=expected["hull"]
            or _int(side.get("mass"))!=expected["mass"]
        ):
            raise ValueError(f"VCR {vcrid} identity mismatch")
        if (_int(raw.get("x")),_int(raw.get("y")))!=SITE:
            raise ValueError("Rush VCR site mismatch")
        other_key="left" if expected["side"]=="right" else "right"
        other=raw.get(other_key)
        if not isinstance(other,Mapping):
            raise ValueError("opponent VCR side unavailable")
        items.append({
            "vcr_id":vcrid,"battle_turn":RUSH_TURN,
            "same_site":list(SITE),"side":expected["side"],
            "owner_id":expected["owner"],"hull_id":expected["hull"],
            "factual_mass":expected["mass"],
            "rush_start_state":_row_subset(side,VCR_SIDE_FIELDS),
            "opponent_start_state":_row_subset(other,VCR_SIDE_FIELDS),
            "opponent_owner_id":_int(raw.get(other_key+"ownerid")),
            "source_member_names":list(case.source_members),
            "independent_source_perspectives":case.observation_count,
            "VCR_field_names":sorted(raw.keys()),
            "rush_side_field_names":sorted(side.keys()),
            "metadata_scalar_fields":{
                k:v for k,v in raw.items()
                if k not in ("left","right") and (
                    v is None or isinstance(v,(str,int,float,bool))
                )
            },
        })
    a,b=items
    return {
        "game_id":RUSH_GAME,"turn":RUSH_TURN,"ship_id":RUSH_ID,
        "VCRs":items,
        "transition":{
            "same_ship_object_id_in_two_factual_VCR_starts":True,
            "same_hull_id":a["hull_id"]==b["hull_id"],
            "owner_changed":a["owner_id"]!=b["owner_id"],
            "owner_change":[a["owner_id"],b["owner_id"]],
            "mass_delta":b["factual_mass"]-a["factual_mass"],
            "consistent_with_documented_combat_capture":True,
            "independent_capture_outcome_proven":False,
            "VCR_id_order_is_not_host_phase_proof":True,
        },
    }


def rush_archives(*,conn:Any,hulls:Mapping[int,Any])->dict[str,Any]:
    refs=member_refs_for_turns(
        conn,game_id=RUSH_GAME,turns={200,201,202},
        include_embedded_turn=False,
    )
    selected=[
        r for r in refs
        if r.perspective_player_id in (4,5)
    ]
    results=[]
    for ref,member in reconstruct_members(conn,selected):
        owner=ref.perspective_player_id
        own=_all_owner_rows(member,owner)
        target=[
            _row_subset(s,OWNER_SHIP_FIELDS)
            for s in own if _int(s.get("id"))==RUSH_ID
        ]
        gen=_generator_ids(member,owner,SITE,hulls)
        results.append({
            "archive_turn":ref.archive_turn,"owner_perspective":owner,
            "source_member_id":ref.member_id,
            "source_member_sha256":ref.decoded_payload_sha256,
            "owned_ship27":target,
            "owned_Saber_generators_near_VCR_site":gen,
            "owner_ship_list_available":isinstance(member.get("ships"),list),
            "owner_ship27_not_present_does_not_imply_nonexistence_for_other_owners":True,
        })
    if not results:
        raise ValueError("no relevant archived owner perspectives")
    return {
        "source_snapshots":results,
        "owner5_Tminus1_Rush27": [
            row for s in results if s["archive_turn"]==200 and s["owner_perspective"]==5
            for row in s["owned_ship27"] if _int(row.get("hullid"))==94
        ],
        "owner4_Tminus1_Saber_at_site": [
            row for s in results if s["archive_turn"]==200 and s["owner_perspective"]==4
            for row in s["owned_Saber_generators_near_VCR_site"]
            if row["site_exact_at_archive"]
        ],
        "owner4_T_Saber_at_site": [
            row for s in results if s["archive_turn"]==201 and s["owner_perspective"]==4
            for row in s["owned_Saber_generators_near_VCR_site"]
            if row["site_exact_at_archive"]
        ],
        "evidence_boundary":(
            "T-1 owner5 engine applies to original Rush only if owner source "
            "shows same hull, and still does not independently prove retained "
            "engine after capture. Sabers seen at T-1 are historical locations, "
            "not necessarily active at VCR start. A postcombat hull35 with "
            "the same ID cannot be treated as the same physical ship."
        ),
    }


def static_control(*,conn:Any,game:int,turn:int)->dict[str,Any]:
    if turn<1:
        raise ValueError("turn must be >=1")
    first,_=first_last_member_refs(conn,game_id=game)
    first_member=reconstruct_compact_member(conn,first.member_id)
    base=_hull_mass_map(first_member)
    refs=member_refs_for_turns(
        conn,game_id=game,turns={turn-1},
        include_embedded_turn=False,
    )
    samples=[]
    for ref,member in reconstruct_members(conn,refs):
        current=_hull_mass_map(member)
        shared=sorted(base.keys()&current.keys())
        diff=[
            {"hull_id":hid,"first_mass":base[hid],"Tminus1_mass":current[hid]}
            for hid in shared if base[hid]!=current[hid]
        ]
        samples.append({
            "source_member_id":ref.member_id,
            "perspective_player_id":ref.perspective_player_id,
            "source_member_sha256":ref.decoded_payload_sha256,
            "shared_hull_count":len(shared),
            "changed_hull_count":len(diff),
            "changed_hulls":diff[:60],
            "change_details_truncated":len(diff)>60,
            "D19c_first_mass":base.get(1039),
            "D19c_Tminus1_mass":current.get(1039),
            "full_changed_ids":[x["hull_id"] for x in diff],
        })
    if not samples:
        return {
            "game_id":game,"turn":turn,
            "status":"TMINUS1_SOURCE_MISSING",
            "first_member_id":first.member_id,
            "snapshots":[],
        }
    changed_sets={
        tuple(x["full_changed_ids"]) for x in samples
    }
    d19masses={x["D19c_Tminus1_mass"] for x in samples}
    return {
        "game_id":game,"turn":turn,"status":(
            "PERSPECTIVE_STATIC_CONFLICT_OR_SCOPE_VARIATION"
            if len(changed_sets)>1 or len(d19masses)>1
            else "SAME_CHANGE_SET_ACROSS_AVAILABLE_TMINUS1_PERSPECTIVES"
        ),
        "first_member_id":first.member_id,
        "first_member_archive_turn":first.archive_turn,
        "perspectives":len(samples),
        "Tminus1_D19c_values":sorted(
            [x for x in d19masses if x is not None]
        ),
        "first_member_D19c_mass":base.get(1039),
        "max_mass_changed_hulls":max(x["changed_hull_count"] for x in samples),
        "per_perspective":samples[:12],
        "per_perspective_truncated":len(samples)>12,
        "boundary":"T-1 static read-only cross-check, NOT a Host combat effective-spec resolver",
    }


def select_static_turns(source:Mapping[str,Any],digest:Mapping[str,Any]):
    if digest.get("schema")!=DIGEST_SCHEMA:
        raise ValueError("wrong digest source schema")
    turns=digest.get("ranked_turns")
    if not isinstance(turns,list) or len(turns)<STATIC_PRIORITY_TURNS:
        raise ValueError("insufficient source turns")
    selected=[(217591,75),(325434,149)]
    for row in turns:
        pair=(row.get("game_id"),row.get("turn"))
        if any(_int(i) is None for i in pair):
            raise ValueError("invalid digest priority turn")
        if pair not in selected and len(selected)<STATIC_PRIORITY_TURNS+2:
            selected.append(pair)
    if len(selected)!=STATIC_PRIORITY_TURNS+2:
        raise ValueError("static controls selection incomplete")
    return selected


def build_report(*,conn:Any,source:Mapping[str,Any],
                 digest:Mapping[str,Any],dbpath:str)->dict[str,Any]:
    if source.get("schema")!=SOURCE_SCHEMA or source.get("status")!=(
        "STATIC_CATALOG_DRIFT_AND_SHIP_ID_DISCONTINUITY_OBSERVATIONAL_NOT_PROMOTED"
    ):
        raise ValueError("wrong V2 source schema/status")
    originals=source.get("D19c_temporal_catalogs")
    if not isinstance(originals,list) or len(originals)!=2:
        raise ValueError("missing two D19c temporal histories")
    for row in originals:
        if row.get("Tminus1_owner_static_mass_values")!=[46]:
            raise ValueError("D19c T-1 46KT not confirmed")
    old=source.get("Rush_ship_id_discontinuity",{}).get("vcr_id_history",{})
    vcrs=old.get("vcr_appearances",[])
    if {(r["vcr_id"],r["hull_id"],r["owner_id"]) for r in vcrs}!={
        (1016,94,5),(1017,94,4)
    }:
        raise ValueError("source Rush VCR pair changed")
    s=select_static_turns(source,digest)
    controls=[static_control(conn=conn,game=g,turn=t) for g,t in s]
    rush_vcrs=rush_combat_observations(conn)
    specs_first=_hull_mass_map(
        reconstruct_compact_member(conn,first_last_member_refs(conn,game_id=RUSH_GAME)[0].member_id)
    )
    # Runtime dependency: use existing independent named Saber hull IDs,
    # not guessed generator IDs from a blind text match.
    from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs
    specs=_independent_hull_specs(conn,RUSH_GAME)
    archives=rush_archives(conn=conn,hulls=specs.hulls)
    status="INDEPENDENT_CAPTURE_AND_TEMPORAL_STATIC_CONTROLS_OBSERVATIONAL_NOT_PROMOTED"
    stats=Counter(x["status"] for x in controls)
    return {
        "schema":SCHEMA,"status":status,
        "source_db":dbpath,
        "source_v2_schema":SOURCE_SCHEMA,"source_digest_schema":DIGEST_SCHEMA,
        "summary":{
            "D19c_two_Tminus1_sources_46KT_verified":2,
            "static_game_turn_groups":len(controls),
            "static_source_status":dict(sorted(stats.items())),
            "static_groups_with_any_changed_mass":sum(
                x.get("max_mass_changed_hulls",0)>0 for x in controls
            ),
            "Rush_VCR_1016_to_1017_owner_change_observed":True,
            "Rush_owner5_Tminus1_ship27_record_count":len(archives["owner5_Tminus1_Rush27"]),
            "Rush_owner4_Tminus1_Sabers_at_site":len(archives["owner4_Tminus1_Saber_at_site"]),
            "Rush_owner4_T_Sabers_at_site":len(archives["owner4_T_Saber_at_site"]),
            "capture_outcome_independently_proven":False,
        },
        "static_snapshot_controls":controls,
        "Rush_VCR_sequence":rush_vcrs,
        "Rush_owner_snapshots":archives,
        "documentation":{
            "captured_ships_can_fight_again":"https://help.planets.nu/battle-order",
            "captures_on_crew_zero":"https://help.planets.nu/combat-basics",
            "after_combat_shipbuilding":"https://help.planets.nu/combat-host",
            "generator_rule":"https://help.planets.nu/abil-shield-generator",
        },
        "boundary":(
            "The same Rush ship ID/hull changes observed owner across VCR starts "
            "and is CONSISTENT with capture; capture success itself is not proven "
            "without combat terminal/ship ownership event evidence. Ship ID27's "
            "postcombat Victorious hull35 is not assumed continuous with the "
            "Rush hull94. Static T-1 observations are controls, not a "
            "generative Host static resolver or verified precombat unit state."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--v2-source",type=Path,required=True)
    p.add_argument("--digest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        s=json.loads(a.v2_source.read_text(encoding="utf-8"))
        d=json.loads(a.digest.read_text(encoding="utf-8"))
        conn,path=connect_compact_generation_read_only(
            a.corpus_db_generation,a.corpus_db_root
        )
        try:
            report=build_report(conn=conn,source=s,digest=d,dbpath=str(path))
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_name(a.output.name+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (ValueError,TypeError,OSError,KeyError,json.JSONDecodeError) as e:
        print("ERROR:",e,file=sys.stderr)
        return 2
    print("===== COMBAT MASS CAPTURE AND STATIC CONTROLS V1 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("Rush VCR starts:",report["Rush_VCR_sequence"]["VCRs"])
    print("Rush owner5 Tminus1:",report["Rush_owner_snapshots"]["owner5_Tminus1_Rush27"])
    print("Rush owner4 Tminus1 Sabers:",report["Rush_owner_snapshots"]["owner4_Tminus1_Saber_at_site"])
    print("static changes:",[
        {"game_id":c["game_id"],"turn":c["turn"],"status":c["status"],
         "max_changed":c.get("max_mass_changed_hulls")}
        for c in report["static_snapshot_controls"]
    ])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
