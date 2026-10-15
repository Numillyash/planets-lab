"""V21 batched research: three distinct read-only analyses, ONE server command.

Phases:
  geometry    Frozen V20 short-edge source/target field geometry
  persistence Exact T-1/T owner-current stabilizer survival/position
  escorts     T-1 colocated ship exposure versus owner-current T endpoints
  manifest    Validate all three reports without reading the database

All V20 study identities are pinned by exact published Git blob; all
T-1 state/forecasts must freeze BEFORE any T observation per phase.
No retrospective Chunnel activation, combat, VCR, or mine claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping
from math import hypot
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for directory in (ROOT/"src",Path(__file__).resolve().parent):
    if str(directory) not in sys.path:sys.path.insert(0,str(directory))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_chunnel_stabilization_provenance_v20 as v20
import combat_c5_chunnel_chain_graph_audit_v19 as v19
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_firecloud_disjoint_validation_v13 as v13

SCHEMA="planets-lab.combat-c5-stabilization-batch.v21"
STATUS="RETROSPECTIVE_STABILIZER_GEOMETRY_PERSISTENCE_AND_ESCORTS_NOT_ACTIVATION_PROOF"
V20_BLOB="3d5e1d5aeb6b0138c01bab3ec81185d0685233c0"
V19_BLOB=v20.V19_BLOB
GENERATION=v20.GENERATION
SHA256=v20.SHA256
WINDOWS=9
CASES=13
PHASES=("geometry","persistence","escorts")
CASE467=(467386,75,467,80)


def number(x:Any)->int|None:
    return x if type(x) is int else None


def point(x:Any)->tuple[int,int]|None:
    return v20.position(x)


def data_file(path:Path,sha:str):
    raw=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if actual!=sha:raise ValueError(f"published report blob SHA1 mismatch: {path}")
    val=json.loads(raw)
    if not isinstance(val,dict):raise ValueError("published source not an object")
    return val


def frozen_sources(v20report:Mapping[str,Any],v19report:Mapping[str,Any]):
    if (v20report.get("schema")!=v20.SCHEMA or
        v20report.get("status")!=v20.STATUS or
        v20report.get("source_v19_git_blob_sha1")!=V19_BLOB or
        v20report.get("source_db_sha256")!=SHA256 or
        v20report.get("source_v17_git_blob_sha1")!=v20.V17_BLOB):
        raise ValueError("V20 source provenance drift")
    summary=v20report.get("summary")
    checks={
        "frozen_V17_48_windows_113_edges":True,
        "frozen_V17_short_distance_edges":13,
        "frozen_V17_short_distance_windows":9,
        "discriminative_short_edges":4,
        "colocated_nondiscriminative_edges":9,
        "Tminus1_all_window_data_frozen_before_T":True,
        "Host_stabilizer_activation_or_25LY_Chunnel_proven":False,
        "new_Host_movement_or_combat_predictions":0,
        "Nplus1_VCR_used":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in checks.items()):
        raise ValueError("V20 fixed 13/9 cohort or scientific guard changed")
    if (v19report.get("schema")!=v19.SCHEMA or
        v19report.get("status")!=v19.STATUS or
        v19report.get("source_db_sha256")!=SHA256 or
        v19report.get("summary",{}).get("Tminus1_eligible_short_to_long_graph_chains")!=2):
        raise ValueError("V19 fixed graph source drift")
    cases=v20report.get("short_edge_evaluations")
    if not isinstance(cases,list) or len(cases)!=CASES:
        raise ValueError("V20 short-edge case population incomplete")
    bykey={}
    for e in cases:
        if not isinstance(e,Mapping):raise ValueError("V20 edge malformed")
        key=tuple(number(e.get(k)) for k in
            ("game_id","turn","initiator_ship_id","target_ship_id"))
        if (None in key or min(key)<=0 or key in bykey or
            e.get("V17_observational_after_T_status_not_used_to_select") is not True or
            e.get("actual_host_stabilization_or_short_Chunnel_proven") is not False or
            point(e.get("Tminus1_source")) is None or point(e.get("Tminus1_target")) is None):
            raise ValueError("V20 edge identity malformed/duplicated")
        bykey[key]=e
    windows=tuple(sorted({k[:2] for k in bykey}))
    if (len(windows)!=WINDOWS or CASE467 not in bykey or
        sum(bool(x["Tminus1_source_target_distinct"]) for x in cases)!=4):
        raise ValueError("V20 9 windows/4 discriminative cases changed")
    origins=v20report.get("Tminus1_window_metadata")
    if not isinstance(origins,Mapping) or len(origins)!=WINDOWS:
        raise ValueError("V20 metadata windows incomplete")
    return bykey,windows,origins


def read_pre(conn,game,turn):
    snapshots,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    return _owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1),raws


def verify_ship(roster,ship_id,owner,location,*,hull=None):
    entry=roster.get(ship_id)
    if entry is None or entry[0]!=owner:
        raise ValueError("frozen Tminus1 ship owner/current changed")
    rec=entry[1]
    if point((rec.get("x"),rec.get("y")))!=point(location):
        raise ValueError("frozen Tminus1 source/target coordinate changed")
    if hull is not None and number(rec.get("hullid",rec.get("hull_id")))!=hull:
        raise ValueError("frozen Tminus1 hull identity changed")
    return rec


def verify_stargate(roster,src):
    sid,owner=src["ship_id"],src["owner_id"]
    rec=verify_ship(roster,sid,owner,src["Tminus1_position"],hull=108)
    if number(rec.get("engineid",rec.get("engine_id")))!=src["Tminus1_engine_id"]:
        raise ValueError("frozen Tminus1 Stargate engine drift")
    expected=(100+50*src["Tminus1_engine_id"]
              if src["Tminus1_engine_id"] is not None and
              1<=src["Tminus1_engine_id"]<=9 else None)
    if expected!=src["documentation_field_radius_ly"]:
        raise ValueError("documented field radius source drift")
    return rec


def base_record(phase):
    return {
        "schema":SCHEMA,"phase":phase,"status":STATUS,
        "source_v20_git_blob_sha1":V20_BLOB,
        "source_v19_git_blob_sha1":V19_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "observed_phase_not_chunnel_execution_proof":True,
        "new_Host_movement_or_combat_predictions":0,
        "Nplus1_VCR_used":False,
    }


def geometry(conn,cases,windows,metadata):
    """Experiment A: field source AND destination margins, no T archive."""
    observations=[]
    for i,(game,turn) in enumerate(windows,1):
        print(f"[c5-batch-v21/geometry] Tminus1 [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        roster,_=read_pre(conn,game,turn)
        source_meta=metadata[str(game)+"/"+str(turn)]
        stabilizers=source_meta["Tminus1_stock_dungeon_stargate_inventory"]
        for s in stabilizers:verify_stargate(roster,s)
        for key,edge in sorted(cases.items()):
            if key[:2]!=(game,turn):continue
            verify_ship(roster,edge["initiator_ship_id"],edge["owner_id"],
                        edge["Tminus1_source"],hull=56)
            verify_ship(roster,edge["target_ship_id"],edge["owner_id"],
                        edge["Tminus1_target"],hull=56)
            src,dst=point(edge["Tminus1_source"]),point(edge["Tminus1_target"])
            fields=[]
            for s in stabilizers:
                if not s["archived_catalog_name_confirms_dungeon_stargate"]:continue
                if s["Tminus1_position"] is None or s["documentation_field_radius_ly"] is None:
                    fields.append({"stargate_id":s["ship_id"],"coverage_status":"ABSTAIN_POSITION_OR_ENGINE"})
                    continue
                loc=point(s["Tminus1_position"])
                radius=s["documentation_field_radius_ly"]
                a=hypot(loc[0]-src[0],loc[1]-src[1])
                b=hypot(loc[0]-dst[0],loc[1]-dst[1])
                fields.append({
                    "stargate_id":s["ship_id"],"stargate_owner_id":s["owner_id"],
                    "owner_matches_chunnel_actor":s["owner_id"]==edge["owner_id"],
                    "radius_ly":radius,
                    "source_distance_ly":round(a,5),
                    "target_distance_ly":round(b,5),
                    "source_margin_ly":round(radius-a,5),
                    "target_margin_ly":round(radius-b,5),
                    "source_inside_field_on_Tminus1":a<=radius,
                    "target_inside_field_on_Tminus1":b<=radius,
                    "active_during_actual_Chunnel_unverified":True,
                })
            observations.append({
                "game_id":game,"turn":turn,
                "initiator_ship_id":edge["initiator_ship_id"],
                "target_ship_id":edge["target_ship_id"],
                "Tminus1_distinct_source_target":edge["Tminus1_source_target_distinct"],
                "Tminus1_explicit_short_format_flag":edge["Tminus1_explicit_short_format_rule_flag"],
                "Tminus1_fields":fields,
                "Tminus1_any_documented_source_field":any(
                    f.get("source_inside_field_on_Tminus1") is True for f in fields),
                "Tminus1_any_documented_target_field":any(
                    f.get("target_inside_field_on_Tminus1") is True for f in fields),
                "Tminus1_all_field_states_unproven":True,
            })
    if len(observations)!=CASES:raise ValueError("geometry 13-edge census changed")
    case=next(x for x in observations if
              (x["game_id"],x["turn"],x["initiator_ship_id"],x["target_ship_id"])==CASE467)
    if not any(x["stargate_id"]==446 and x["radius_ly"]==550 for x in case["Tminus1_fields"]):
        raise ValueError("G467386/T75 #446 source stabilizer no longer observed")
    return {
        **base_record("geometry"),
        "summary":{
            "windows":len(windows),"frozen_short_edges":len(observations),
            "geometrically_distinct_edges":sum(x["Tminus1_distinct_source_target"] for x in observations),
            "source_inside_documented_field":sum(x["Tminus1_any_documented_source_field"] for x in observations),
            "target_inside_documented_field":sum(x["Tminus1_any_documented_target_field"] for x in observations),
            "G467386_T75_467_to_80_source_inside_field":case["Tminus1_any_documented_source_field"],
            "G467386_T75_467_to_80_target_inside_field":case["Tminus1_any_documented_target_field"],
            "field_active_in_Host_phase_proven":False,
            "T_archives_read":False,
        },
        "G467386_T75_467_to_80":case,"edge_geometry":observations,
    }


def persistence(conn,cases,windows,metadata):
    """Experiment B: freeze exact T-1 stabilizer ships, THEN read T."""
    pre=[]
    for i,(g,t) in enumerate(windows,1):
        print(f"[c5-batch-v21/persistence] PRE [{i}/{len(windows)}] G{g} T{t}",flush=True)
        roster,_=read_pre(conn,g,t)
        for s in metadata[str(g)+"/"+str(t)]["Tminus1_stock_dungeon_stargate_inventory"]:
            verify_stargate(roster,s)
            pre.append({
                "game_id":g,"turn":t,"ship_id":s["ship_id"],"owner_id":s["owner_id"],
                "Tminus1_position":s["Tminus1_position"],"Tminus1_engine":s["Tminus1_engine_id"],
                "Tminus1_documented_radius":s["documentation_field_radius_ly"],
                "Tminus1_hull":108,
            })
    post=[]
    for i,(g,t) in enumerate(windows,1):
        print(f"[c5-batch-v21/persistence] POST [{i}/{len(windows)}] G{g} T{t}",flush=True)
        records=v9.after_owner_current(conn,game=g,turn=t)
        for s in pre:
            if (s["game_id"],s["turn"])!=(g,t):continue
            state,raw=v13._current_ship(records,s["ship_id"],s["owner_id"],108)
            loc=point((raw.get("x"),raw.get("y"))) if raw is not None else None
            engine=number(raw.get("engineid",raw.get("engine_id"))) if raw is not None else None
            post.append({
                **s,
                "T_owner_current_status":state,
                "T_owner_current_position":list(loc) if loc else None,
                "T_engine_id":engine,
                "T_stargate_position_unchanged":(loc==point(s["Tminus1_position"]) if loc is not None else None),
                "T_stargate_engine_unchanged":(engine==s["Tminus1_engine"] if engine is not None else None),
                "stabilization_active_during_chunnel_proven":False,
            })
    episodes={(z["game_id"],z["turn"]) for z in pre}
    return {
        **base_record("persistence"),
        "summary":{
            "frozen_short_windows":len(windows),
            "Tminus1_Dungeon_ship_appearances":len(pre),
            "Tminus1_Dungeon_windows":len(episodes),
            "T_owner_current_categories":dict(sorted(Counter(z["T_owner_current_status"] for z in post).items())),
            "T_positions_unchanged":sum(z["T_stargate_position_unchanged"] is True for z in post),
            "T_positions_changed":sum(z["T_stargate_position_unchanged"] is False for z in post),
            "T_engine_unchanged":sum(z["T_stargate_engine_unchanged"] is True for z in post),
            "all_Tminus1_stargates_frozen_before_first_T":True,
            "active_field_or_Chunnel_executed_proven":False,
        },
        "stargate_Tminus1_to_T":post,
    }


def escorts(conn,cases,windows,metadata):
    """Experiment C: conditional colocated/passenger candidates at T-1 only."""
    selected=tuple(sorted((k,v) for k,v in cases.items()
                          if v["Tminus1_source_target_distinct"]))
    if len(selected)!=4:raise ValueError("four original distinct short edges changed")
    relevant=tuple(sorted({k[:2] for k,_ in selected}))
    pre=[]
    for i,(g,t) in enumerate(relevant,1):
        print(f"[c5-batch-v21/escorts] PRE [{i}/{len(relevant)}] G{g} T{t}",flush=True)
        roster,_=read_pre(conn,g,t)
        for key,edge in selected:
            if key[:2]!=(g,t):continue
            src=point(edge["Tminus1_source"])
            owner=edge["owner_id"]
            verify_ship(roster,edge["initiator_ship_id"],owner,src,hull=56)
            ships=[]
            for sid,(who,raw) in sorted(roster.items()):
                if point((raw.get("x"),raw.get("y")))!=src:continue
                ships.append({
                    "ship_id":sid,"owner_id":who,
                    "Tminus1_hull_id":number(raw.get("hullid",raw.get("hull_id"))),
                    "Tminus1_warp":number(raw.get("warp")),
                    "Tminus1_fuel":number(raw.get("neutronium")),
                    "same_owner_as_actor":who==owner,
                    "independent_ship_at_source_Tminus1_only":True,
                })
            if not any(s["ship_id"]==edge["initiator_ship_id"] for s in ships):
                raise ValueError("T-1 original actor omitted from colocated stack")
            if len(ships)>300:raise ValueError("unbounded T-1 stacked fleet")
            pre.append({
                "game_id":g,"turn":t,"actor_id":edge["initiator_ship_id"],
                "target_id":edge["target_ship_id"],"owner_id":owner,
                "source":edge["Tminus1_source"],"target":edge["Tminus1_target"],
                "Tminus1_stack":ships,
            })
    # Freeze all four T-1 stacks before any post-T read.
    post=[]
    for i,(g,t) in enumerate(relevant,1):
        print(f"[c5-batch-v21/escorts] POST [{i}/{len(relevant)}] G{g} T{t}",flush=True)
        current=v9.after_owner_current(conn,game=g,turn=t)
        for entry in pre:
            if (entry["game_id"],entry["turn"])!=(g,t):continue
            dest=point(entry["target"])
            members=[]
            for ship in entry["Tminus1_stack"]:
                state,raw=v13._current_ship(
                    current,ship["ship_id"],ship["owner_id"],ship["Tminus1_hull_id"])
                loc=point((raw.get("x"),raw.get("y"))) if raw is not None else None
                fuel=number(raw.get("neutronium")) if raw is not None else None
                delta=(ship["Tminus1_fuel"]-fuel if fuel is not None and
                       ship["Tminus1_fuel"] is not None else None)
                members.append({
                    **ship,"T_status":state,
                    "T_owner_current_position":list(loc) if loc else None,
                    "T_at_frozen_target":(loc==dest if loc is not None else None),
                    "T_net_fuel_decrease_KT":delta,
                    "passenger_transport_caused_by_Chunnel_proven":False,
                })
            post.append({**{k:v for k,v in entry.items() if k!="Tminus1_stack"},
                         "Tminus1_stack_size":len(entry["Tminus1_stack"]),
                         "stack_T_comparisons":members,
                         "T_owning_actor_at_target":next(
                             s["T_at_frozen_target"] for s in members if s["ship_id"]==entry["actor_id"]),
                         "independent_chunnel_activation_proven":False})
    if len(post)!=4:raise ValueError("four distinct short episode census changed")
    special=next(e for e in post if (e["game_id"],e["turn"],e["actor_id"],e["target_id"])==CASE467)
    return {
        **base_record("escorts"),
        "summary":{
            "Tminus1_distinct_short_edges":len(post),
            "Tminus1_distinct_game_turn_windows":len(relevant),
            "preselected_Tminus1_colocated_ship_appearances":sum(len(x["stack_T_comparisons"]) for x in post),
            "G467386_T75_467_stack_size":special["Tminus1_stack_size"],
            "G467386_T75_467_stack_owner_current_at_target":sum(
                x["T_at_frozen_target"] is True for x in special["stack_T_comparisons"]),
            "all_Tminus1_stacks_frozen_before_first_T":True,
            "movement_mechanism_or_Chunnel_activation_proven":False,
        },
        "G467386_T75_467_to_80":special,
        "episode_stacks":post,
    }


def make_manifest(directory:Path):
    files={}
    for phase in PHASES:
        path=directory/(phase+".json")
        if not path.is_file():raise ValueError("missing batched phase report: "+phase)
        doc=json.loads(path.read_text(encoding="utf-8"))
        if (doc.get("schema")!=SCHEMA or doc.get("phase")!=phase or
            doc.get("status")!=STATUS or
            doc.get("source_v20_git_blob_sha1")!=V20_BLOB or
            doc.get("source_db_sha256")!=SHA256 or
            doc.get("Nplus1_VCR_used") is not False):
            raise ValueError("phase report provenance error: "+phase)
        files[phase]={
            "relative_report":phase+".json",
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "summary":doc["summary"],
        }
    return {
        **base_record("manifest"),
        "status":"ALL_THREE_PINNED_V21_RESEARCH_PHASES_PUBLISHED_TOGETHER",
        "three_experiments_completed":True,
        "phase_reports":files,
        "research_caveat":(
            "This is ONE independently evidence-published BATCH of THREE "
            "read-only diagnostics on the SAME preselected historical "
            "V17/V20 public100 cohort, not three new heldout studies. "
            "No posthoc engine activation, a 25LY special rule or "
            "production combat/movement inference proven."
        ),
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=(*PHASES,"manifest"),required=True)
    p.add_argument("--frozen-v20",type=Path)
    p.add_argument("--frozen-v19",type=Path)
    p.add_argument("--corpus-db-root",type=Path)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.phase=="manifest":
            result=make_manifest(args.output_dir)
        else:
            if args.frozen_v20 is None or args.frozen_v19 is None or args.corpus_db_root is None:
                raise ValueError("missing exact pinned V19/V20 corpus source arguments")
            v20report=data_file(args.frozen_v20,V20_BLOB)
            v19report=data_file(args.frozen_v19,V19_BLOB)
            cases,windows,metadata=frozen_sources(v20report,v19report)
            database=args.corpus_db_root/GENERATION
            if not database.is_file():raise ValueError("pinned public100 generation missing")
            print(f"[c5-batch-v21/{args.phase}] verifying SHA256 of immutable DB",flush=True)
            start=time.monotonic()
            with database.open("rb") as fd: actual=hashlib.file_digest(fd,"sha256").hexdigest()
            if actual!=SHA256:raise ValueError("public100 immutable DB checksum mismatch")
            print(f"[c5-batch-v21/{args.phase}] database read-only verified in {time.monotonic()-start:.1f}s",flush=True)
            conn,_=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
            try:
                result={"geometry":geometry,"persistence":persistence,"escorts":escorts}[args.phase](
                    conn,cases,windows,metadata)
            finally:conn.close()
        args.output_dir.mkdir(parents=True,exist_ok=True)
        target=args.output_dir/(args.phase+".json")
        temp=target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(target)
    except (OSError,ValueError,TypeError,KeyError,IndexError,json.JSONDecodeError) as e:
        print(f"ERROR V21 phase {args.phase}: {e}",file=sys.stderr)
        return 2
    print("===== C5 STABILIZATION BATCH V21:",args.phase,"=====")
    print("status:",result["status"])
    print("summary:",result.get("summary",result.get("three_experiments_completed")))
    print("output:",target)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
