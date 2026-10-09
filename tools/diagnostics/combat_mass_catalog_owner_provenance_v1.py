"""Targeted catalog provenance / missing-owner evidence for three residual VCRs.

Read-only public100 probe:
* D19c hull 1039 official reference 46 KT vs imported game hull 96 KT:
  compare raw 'hulls' and 'hullsall' arrays from first, last and
  archived owner snapshots, keeping source/member identities.
* Rush Class carrier #27: seek pre/post archival OWNER and bounded
  foreign-perspective observations without interpolating an engine.

A static source record, T-1 order and factual VCR refer to different
evidence layers; this instrument never promotes combat-mass mechanisms.
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
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0,str(Path(__file__).resolve().parent))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,
    first_last_member_refs, member_refs_for_turns, reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_compact import reconstruct_compact_member
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs

SCHEMA="planets-lab.combat-mass-catalog-owner-provenance.v1"
SOURCE_SCHEMA="planets-lab.combat-mass-rulebook-reconciliation.v2"
TARGETS={(217591,75,756,"right"),(325434,149,1075,"left"),
         (617883,201,1017,"left")}
HULLS=(39,94,1039,1041)


def _int(x:Any)->int|None:
    if isinstance(x,bool) or x is None:
        return None
    try:
        if isinstance(x,(int,str)):
            return int(x)
    except ValueError:
        return None
    return None


def select_cases(src:Mapping[str,Any])->list[dict[str,Any]]:
    if src.get("schema")!=SOURCE_SCHEMA:
        raise ValueError("unexpected rulebook reconciliation schema")
    cases=src.get("D19c_source_conflicts")
    unresolved=src.get("unresolved_cases")
    if not isinstance(cases,list) or len(cases)!=2 or not isinstance(unresolved,list) or len(unresolved)!=1:
        raise ValueError("expected exactly 2 D19c plus 1 open Rush")
    selected=[*cases,*unresolved]
    ids=set()
    for row in selected:
        if not isinstance(row,Mapping):
            raise ValueError("malformed input case")
        key=tuple(row.get(k) for k in ("game_id","turn","vcr_id","side"))
        if key not in TARGETS or key in ids:
            raise ValueError("input VCR identity mismatch or duplicate")
        ids.add(key)
    if ids!=TARGETS:
        raise ValueError("target three VCR identities incomplete")
    return sorted(selected,key=lambda r:(r["game_id"],r["turn"],r["vcr_id"]))


def static_collection_rows(member:Mapping[str,Any])->dict[str,Any]:
    """Losslessly retain limited raw ID-specific records per collection."""
    result={}
    for collection in ("hulls","hullsall"):
        raw=member.get(collection)
        if raw is None:
            result[collection]={"collection_status":"MISSING","records":[]}
            continue
        if not isinstance(raw,list):
            raise ValueError(f"static {collection} is not a list")
        matches=[]
        for item in raw:
            if not isinstance(item,Mapping):
                raise ValueError("malformed static hull record")
            hid=_int(item.get("id"))
            if hid not in HULLS:
                continue
            matches.append({
                "id":hid,"name":item.get("name"),"mass":_int(item.get("mass")),
                "parentid":_int(item.get("parentid")),
                "cargo":_int(item.get("cargo")),
                "engine_count":_int(item.get("engines")),
                "special":item.get("special"),
            })
        result[collection]={
            "collection_status":"PRESENT",
            "total_records":len(raw),
            "records":matches,
        }
    return result


def _member_provenance(ref:Any)->dict[str,Any]:
    return {
        "member_id":ref.member_id,
        "archive_turn":ref.archive_turn,
        "embedded_turn":ref.embedded_turn,
        "perspective_player_id":ref.perspective_player_id,
        "source_member_name":ref.source_member_name,
        "decoded_payload_sha256":ref.decoded_payload_sha256,
    }


def participant_snapshot(member:Mapping[str,Any],*,target_ship:int,
                         target_owner:int,specs:Any)->dict[str,Any]:
    ships=member.get("ships")
    if not isinstance(ships,list):
        return {"ship_list_status":"UNAVAILABLE","target_ships":[]}
    selected=[]
    for ship in ships:
        if not isinstance(ship,Mapping) or _int(ship.get("id"))!=target_ship:
            continue
        fields=("id","ownerid","hullid","engineid","mass","clans",
                "x","y","targetx","targety","warp","mission",
                "damage","ammo","neutronium")
        s={k:ship.get(k) for k in fields}
        engine_id=_int(ship.get("engineid"))
        engine=specs.engines.get(engine_id)
        s["engine_mc_cost_from_first_member_catalog"]=(
            engine.cost.megacredits if engine else None
        )
        s["target_owner_matches"]=(_int(ship.get("ownerid"))==target_owner)
        own_sg=[]
        sx,sy=_int(ship.get("x")),_int(ship.get("y"))
        if sx is not None and sy is not None and s["target_owner_matches"]:
            for candidate in ships:
                if not isinstance(candidate,Mapping) or _int(candidate.get("ownerid"))!=target_owner:
                    continue
                sid=_int(candidate.get("id"))
                if sid==target_ship:
                    continue
                hid=_int(candidate.get("hullid"))
                hull=specs.hulls.get(hid)
                if hull is None or (
                    "shield generator" not in hull.name.casefold()
                    and "shield generator" not in hull.special.casefold()
                ):
                    continue
                if _int(candidate.get("x"))==sx and _int(candidate.get("y"))==sy:
                    own_sg.append(sid)
        s["same_owner_shield_generator_ids_at_snapshot_ship_xy"]=sorted(own_sg)
        selected.append(s)
    return {
        "ship_list_status":"PRESENT",
        "ship_records_total":len(ships),
        "target_ships":selected,
        "target_ship_seen":bool(selected),
    }


def snapshot_selection(refs:list[Any],*,owner:int,turn:int)->tuple[list[Any],dict[str,Any]]:
    """T-3..T+1 owner snapshots + limited T-1 and T peers (not omniscience)."""
    selected=[]
    owner_counts=Counter()
    peer_counts=Counter()
    for ref in refs:
        if ref.perspective_player_id==owner:
            owner_counts[ref.archive_turn]+=1
            if owner_counts[ref.archive_turn]<=3:
                selected.append(ref)
        elif ref.archive_turn in (turn-1,turn):
            peer_counts[ref.archive_turn]+=1
            if peer_counts[ref.archive_turn]<=3:
                selected.append(ref)
    return selected,{
        "owner_source_members_available_by_turn":dict(sorted(owner_counts.items())),
        "owner_source_members_selected_per_turn_cap":3,
        "foreign_perspective_selected_per_turn_cap":3,
        "peer_source_members_available_in_Tminus1_and_T":dict(sorted(peer_counts.items())),
        "temporal_boundary":"archive_turn is an archived source label; current VCR is a distinct Host-phase fact",
    }


def _static_compare(static_snapshots:list[dict[str,Any]])->dict[str,Any]:
    masses=defaultdict(set)
    for snap in static_snapshots:
        for collection,data in snap["static"].items():
            for raw in data["records"]:
                if raw["mass"] is not None:
                    masses[(collection,str(raw["id"]))].add(raw["mass"])
    return {
        "observed_raw_masses_by_collection_and_hull_id":{
            f"{c}:{hid}":sorted(values) for (c,hid),values in sorted(masses.items())
        },
        "static_source_observations_are_not_host_mass_rules":True,
    }


def build_report(*,conn:Any,src:Mapping[str,Any],dbpath:str)->dict[str,Any]:
    inputs=select_cases(src)
    rows=[]
    for selected in inputs:
        game,turn,vcr,side=(selected[k] for k in ("game_id","turn","vcr_id","side"))
        owner,ship_id,hull_id,mass=(
            selected["owner_id"],selected["ship_id"],selected["hull_id"],
            selected["factual_vcr_mass_comparator"]
        )
        cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
        case=cases.get((turn,vcr))
        if case is None:
            raise ValueError("frozen VCR case missing from public100")
        factual_side=case.payload.get(side)
        if not isinstance(factual_side,Mapping):
            raise ValueError("target factual VCR side missing")
        if (
            _int(factual_side.get("objectid"))!=ship_id
            or _int(factual_side.get("hullid"))!=hull_id
            or _int(factual_side.get("mass"))!=mass
            or _int(case.payload.get(side+"ownerid"))!=owner
        ):
            raise ValueError("frozen VCR/owner/mass mismatch")

        specs=_independent_hull_specs(conn,game)
        typed=specs.hulls.get(hull_id)
        if typed is None or typed.mass!=selected["source_catalog_mass"]:
            raise ValueError("typed catalog baseline mismatch")
        first,last=first_last_member_refs(conn,game_id=game)
        base_refs=[]
        used=set()
        for label,ref in (("first",first),("last",last)):
            if ref.member_id not in used:
                base_refs.append((label,ref))
                used.add(ref.member_id)
        catalogs=[]
        for label,ref in base_refs:
            member=reconstruct_compact_member(conn,ref.member_id)
            catalogs.append({
                "snapshot_label":label,
                "provenance":_member_provenance(ref),
                "static":static_collection_rows(member),
            })
        all_turns=set(range(max(0,turn-3),turn+2))
        refs=member_refs_for_turns(
            conn,game_id=game,turns=all_turns,include_embedded_turn=False
        )
        choices,scope=snapshot_selection(refs,owner=owner,turn=turn)
        history=[]
        seen_ids=set()
        for ref,member in reconstruct_members(conn,choices):
            if ref.member_id in seen_ids:
                continue
            seen_ids.add(ref.member_id)
            source=participant_snapshot(
                member,target_ship=ship_id,target_owner=owner,specs=specs
            )
            entry={
                "provenance":_member_provenance(ref),
                "perspective_is_owner":ref.perspective_player_id==owner,
                "target":source,
            }
            if ref.archive_turn in (turn-1,turn) and ref.perspective_player_id==owner:
                entry["static"]=static_collection_rows(member)
            history.append(entry)
        before=[r for r in history if r["perspective_is_owner"] and r["provenance"]["archive_turn"]==turn-1]
        after=[r for r in history if r["perspective_is_owner"] and r["provenance"]["archive_turn"]>=turn]
        earlier=[r for r in history if r["perspective_is_owner"] and r["provenance"]["archive_turn"]<turn-1]
        foreign=[r for r in history if not r["perspective_is_owner"]]
        observations={
            "Tminus1_owner_perspective_present":bool(before),
            "Tminus1_ship_seen_by_owner":any(r["target"].get("target_ship_seen") for r in before),
            "previous_owner_ships_visible":sum(bool(r["target"].get("target_ship_seen")) for r in earlier),
            "T_and_after_owner_ship_seen":any(r["target"].get("target_ship_seen") for r in after),
            "foreign_perspective_ship_seen_Tminus1_or_T":any(r["target"].get("target_ship_seen") for r in foreign),
            "owner_perspective_source_missing_not_equal_ship_absent":True,
        }
        rows.append({
            "game_id":game,"turn":turn,"vcr_id":vcr,"side":side,
            "ship_id":ship_id,"owner_id":owner,"hull_id":hull_id,
            "factual_vcr_mass":mass,"factual_vcr_site":[
                _int(case.payload.get("x")),_int(case.payload.get("y"))
            ],
            "vcr_input_observation_count":case.observation_count,
            "typed_first_member_hull":{
                "mass":typed.mass,"name":typed.name,"parent_id":typed.parent_id,
            },
            "static_first_last":catalogs,
            "static_first_last_mass_comparison":_static_compare(catalogs),
            "archive_selection_scope":scope,
            "archive_snapshots":history,
            "temporal_observation_counts":observations,
            "not_proven":{
                "phase_accurate_precombat_engine":True,
                "phase_accurate_active_generators":True,
                "effective_hull_catalog_selection":True,
            },
        })
    return {
        "schema":SCHEMA,
        "status":"THREE_MASS_SOURCE_PROVENANCE_CASES_OBSERVED_NOT_PROMOTED",
        "source_rulebook_schema":SOURCE_SCHEMA,
        "source_db":dbpath,
        "summary":{
            "cases_checked":len(rows),
            "D19c_case_count":sum(r["hull_id"]==1039 for r in rows),
            "Rush_case_count":sum(r["hull_id"]==94 for r in rows),
            "D19c_hullsall_reference46_present_in_first_last":sum(
                any(raw["id"]==1039 and raw["mass"]==46
                    for entry in r["static_first_last"]
                    for raw in entry["static"]["hullsall"]["records"])
                for r in rows if r["hull_id"]==1039
            ),
            "Rush_owner_ship_seen_in_T_and_after":any(
                r["temporal_observation_counts"]["T_and_after_owner_ship_seen"]
                for r in rows if r["hull_id"]==94
            ),
        },
        "cases":rows,
        "reference":{
            "official_D19c_mass":46,
            "official_D19c_link":"https://help.planets.nu/RaceSheetPlus",
            "shield_generator_rule":"https://help.planets.nu/abil-shield-generator",
        },
        "boundary":(
            "Archived compact member static hulls and hullsall are source records, "
            "not an independently proven effective Host hull selection. "
            "Owner T-1/T archive records are not exact combat-phase snapshots. "
            "An absent owner archive record is not a zero engine or missing ship. "
            "Current VCR mass is used only to identify/verify cases. "
            "No probabilistic executor or production code is updated."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--rulebook-input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        source=json.loads(a.rulebook_input.read_text(encoding="utf-8"))
        conn,path=connect_compact_generation_read_only(a.corpus_db_generation,a.corpus_db_root)
        try:
            report=build_report(conn=conn,src=source,dbpath=str(path))
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_name(a.output.name+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
        print("===== MASS CATALOG AND OWNER PROVENANCE V1 =====")
        print("status:",report["status"])
        print("summary:",report["summary"])
        for case in report["cases"]:
            print(f"game={case['game_id']} T{case['turn']} V{case['vcr_id']} "
                  f"ship={case['ship_id']} hull={case['hull_id']} "
                  f"static_masses={case['static_first_last_mass_comparison']['observed_raw_masses_by_collection_and_hull_id']} "
                  f"owner_visibility={case['temporal_observation_counts']}")
        print("output:",a.output)
        return 0
    except (OSError,TypeError,ValueError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
