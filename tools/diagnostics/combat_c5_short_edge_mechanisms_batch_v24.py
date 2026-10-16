"""V24: one evidence run, three fixed-cohort short-Chunnel controls.

(A) T-1-only short->eligible-long graph, evaluated against archived T
(B) all eight V23 short actor/target orders and alternate endpoints
(C) exact T-1 Dungeon Stabilizer radius/owner and T persistence

The eight V23 short candidates are POSTHOC targets of this study.
No novel validation score or Host-phase Chunnel execution inference.
Freeze ALL seven T-1 windows BEFORE any fresh T archive reads.
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
for root in (ROOT/"src",Path(__file__).resolve().parent):
    if str(root) not in sys.path:sys.path.insert(0,str(root))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_chunnel_stabilization_provenance_v20 as v20
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_chunnel_endpoint_screen_v11 as v11

SCHEMA="planets-lab.combat-c5-short-edge-mechanisms-batch.v24"
STATUS="POSTHOC_V23_SHORT_EDGES_GRAPH_ORDERS_STABILIZER_NOT_CAUSAL"
V23_FIELD_BLOB="9d5dab0cdd8969313c795a56efea939de83242b4"
V23_MANIFEST_BLOB="12c0648b5b123caa50ef8d974ed7dc3d2bab4c9b"
GENERATION=v20.GENERATION
SHA256=v20.SHA256
OUTPUTS=("chains","orders","stabilizers")
SHORT=8
LONG=375
EXPECTED_CHAIN_1=(449095,121,361,114,443)
EXPECTED_CHAIN_2=(449095,121,396,218,548)


def num(v:Any)->int|None:
    return v if type(v) is int else None


def xy(v:Any)->tuple[int,int]|None:
    return v20.position(v)


def git_pinned(path:Path, sha:str):
    blob=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\x00"+blob).hexdigest()
    if actual!=sha:raise ValueError("published source blob changed: "+str(path))
    doc=json.loads(blob)
    if not isinstance(doc,dict):raise ValueError("source report invalid")
    return doc,blob


def freeze_source(field:Mapping[str,Any],manifest:Mapping[str,Any],payload:bytes):
    if (field.get("schema")!="planets-lab.combat-c5-episode-field-discovery-batch.v23"
        and field.get("schema")!="planets-lab.combat-c5-episode-field-batch.v23"):
        # Grounded actual schema is read from the canonical V23 code (see tests).
        raise ValueError("V23 field schema mismatch")
    if (field.get("status")!="V22_EPISODE_RECONCILIATION_AND_NEW_TMINUS1_FIELD_SCAN_OBSERVATIONAL" or
        field.get("phase")!="field_scan" or
        field.get("source_db_sha256")!=SHA256 or
        field.get("Nplus1_VCR_used") is not False):
        raise ValueError("V23 source provenance mismatch")
    sm=field.get("summary")
    if not isinstance(sm,Mapping) or any(sm.get(k)!=v for k,v in {
        "selected_previous_games_excluded":89,
        "metadata_selected_unused_games":11,
        "metadata_selected_adjacent_windows":264,
        "Tminus1_distinct_short_candidate_edges":8,
        "Tminus1_long_controls":375,
        "short_with_Tminus1_documented_field_witness":2,
        "short_witness_distinct_games":1,
        "short_witness_distinct_windows":2,
        "all_unused_game_Tminus1_freezes_before_first_T":True,
        "Host_field_activation_or_Chunnel_proven":False,
        "no_new_public_corpus":True,
    }.items()):raise ValueError("V23 immutable 8/375 denominator drift")
    if (manifest.get("status")!="V23_EPISODES_OWNERSHIP_FIELD_SCAN_COMPLETE" or
        manifest.get("all_three_complete") is not True or
        manifest.get("phase_reports",{}).get("field_scan",{}).get("sha256")!=hashlib.sha256(payload).hexdigest()):
        raise ValueError("V23 completeness manifest mismatch")
    rows=field.get("posthost_short_and_long_comparisons")
    if not isinstance(rows,list) or len(rows)!=SHORT+LONG:
        raise ValueError("V23 8 short + 375 long row count drift")
    short,long={},{}
    for row in rows:
        if not isinstance(row,Mapping):raise ValueError("V23 malformed comparison row")
        key=tuple(num(row.get(x)) for x in ("game_id","turn","initiator_ship_id","target_ship_id"))
        if (any(x is None or x<=0 for x in key) or
            xy(row.get("Tminus1_source")) is None or
            xy(row.get("Tminus1_target")) is None or
            row.get("Host_Chunnel_activation_proven") is not False):
            raise ValueError("V23 baseline ship/phase identity drift")
        group=row.get("Tminus1_cohort")
        if group=="SHORT":dest=short
        elif group=="LONG":dest=long
        else:raise ValueError("unexpected V23 cohort")
        if key in dest:raise ValueError("duplicate V23 candidate identity")
        dest[key]=row
    windows=tuple(sorted({(g,t) for g,t,_,_ in short}))
    if len(short)!=SHORT or len(long)!=LONG or len(windows)!=7:
        raise ValueError("V23 frozen short candidate/window count drift")
    if (449095,121,361,114) not in short or (449095,121,396,218) not in short or (449095,141,547,229) not in short:
        raise ValueError("G449095 critical short episodes missing")
    return short,long,windows


def frozen_chains(short,long):
    """Graph only T-1 edge IDs, owner, endpoint geometry; no T outcome."""
    by_actor=defaultdict(list)
    for (g,t,a,b),row in long.items():
        by_actor[g,t,a].append(row)
    chains=[]
    for (g,t,a,b),first in sorted(short.items()):
        for next_edge in by_actor.get((g,t,b),()):
            if (first["owner_id"]!=next_edge["owner_id"] or
                xy(first["Tminus1_target"])!=xy(next_edge["Tminus1_source"]) or
                a==next_edge["target_ship_id"]):
                continue
            chains.append({
                "game_id":g,"turn":t,
                "short_actor_id":a,"middle_firecloud_id":b,
                "downstream_target_id":next_edge["target_ship_id"],
                "owner_id":first["owner_id"],
                "Tminus1_short_start":first["Tminus1_source"],
                "Tminus1_short_target":first["Tminus1_target"],
                "Tminus1_downstream_target":next_edge["Tminus1_target"],
                "Tminus1_downstream_distance_ly":next_edge["Tminus1_distance_ly"],
                "Tminus1_field_witness":first["Tminus1_short_field_status"],
                "Tminus1_chain_graph_only":True,
            })
    return chains


def keep_ship(ship_id,roster):
    entry=roster.get(ship_id)
    if entry is None:return {"ship_id":ship_id,"Tminus1_ship_status":"ABSTAIN_MISSING_OWNER_CURRENT"}
    owner,raw=entry
    origin=xy((raw.get("x"),raw.get("y")))
    if origin is None:raise ValueError("missing Tminus1 ship coordinates")
    point=xy((raw.get("targetx"),raw.get("targety")))
    return {
        "ship_id":ship_id,"owner_id":owner,
        "Tminus1_ship_status":"OWNER_CURRENT",
        "Tminus1_position":list(origin),
        "Tminus1_waypoint":list(point) if point is not None else None,
        "Tminus1_warp":num(raw.get("warp")),
        "Tminus1_hull_id":num(raw.get("hullid",raw.get("hull_id"))),
        "Tminus1_mission":num(raw.get("mission")),
        "Tminus1_fuel":num(raw.get("neutronium")),
        "Tminus1_damage":num(raw.get("damage")),
    }


def freeze_window(conn,game,turn,short,long,chains):
    snapshots,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1)
    source_edges,_=v16.potential_stock_edges(roster)
    indexed={(x["initiator_ship_id"],x["target_ship_id"]):x for x in source_edges}
    candidates=[(key,row) for key,row in short.items() if key[:2]==(game,turn)]
    rule,race=v20.game_rules_markers(raws,game,turn)
    stargates=v20.stabilizer_inventory(roster,v11.hull_name_inventory(raws))
    ids=set()
    candidates_out=[]
    for key,c in sorted(candidates):
        _,_,a,b=key
        chk=indexed.get((a,b))
        if (chk is None or chk.get("cohort")!="ONE_TMINUS1_GATE_FAILS" or
            chk.get("single_failing_gate")!="DISTANCE_BELOW_100_AT_TMINUS1" or
            chk["owner_id"]!=c["owner_id"] or
            xy(chk["source"])!=xy(c["Tminus1_source"]) or
            xy(chk["target"])!=xy(c["Tminus1_target"])):
            raise ValueError("V23 short edge differs from independently reconstructed Tminus1")
        ids.update((a,b))
        attached=[chain for chain in chains if
                  (chain["game_id"],chain["turn"],chain["short_actor_id"],chain["middle_firecloud_id"])==key]
        for ch in attached:ids.add(ch["downstream_target_id"])
        actor=roster[a][1]
        candidate={
            "game_id":game,"turn":turn,"initiator_ship_id":a,"target_ship_id":b,
            "owner_id":c["owner_id"],"Tminus1_source":c["Tminus1_source"],
            "Tminus1_target":c["Tminus1_target"],
            "Tminus1_distance_ly":c["Tminus1_distance_ly"],
            "Tminus1_fuel":chk["actor_Tminus1_fuel"],
            "Tminus1_initiator_warp":chk["actor_Tminus1_warp"],
            "Tminus1_waypoint":list(xy((actor.get("targetx"),actor.get("targety"))))
                if xy((actor.get("targetx"),actor.get("targety"))) is not None else None,
            "Tminus1_mission":num(actor.get("mission")),
            "Tminus1_frozen_downstream_chains":attached,
            "Tminus1_colocated_ships":[
                {"ship_id":sid,"owner_id":owner,"warp":num(r.get("warp"))}
                for sid,(owner,r) in sorted(roster.items())
                if xy((r.get("x"),r.get("y")))==xy(c["Tminus1_source"])],
            "Tminus1_tow_request_ship_ids":[
                sid for sid,(_owner,r) in sorted(roster.items())
                if num(r.get("mission"))==v16.TOW_MISSION_ID and
                num(r.get("mission1target")) in (a,b)],
            "Tminus1_rule_game_scalar_hints":rule,
            "Tminus1_actor_race_id":race.get(c["owner_id"]),
            "Tminus1_field_status_reported_V23":c["Tminus1_short_field_status"],
            "Tminus1_stabilization_phase_verified":False,
        }
        candidates_out.append(candidate)
    for gate in stargates:ids.add(gate["ship_id"])
    ships=[keep_ship(sid,roster) for sid in sorted(ids)]
    if any(x["Tminus1_ship_status"]!="OWNER_CURRENT" for x in ships):
        raise ValueError("incomplete targeted ship Tminus1 owner current")
    # Check exact field geometry independently of the published V23 labels.
    field=[]
    for candidate in candidates_out:
        src=xy(candidate["Tminus1_source"])
        dst=xy(candidate["Tminus1_target"])
        for gate in stargates:
            if not gate["archived_catalog_name_confirms_dungeon_stargate"]:
                continue
            loc=xy(gate["Tminus1_position"]) if gate["Tminus1_position"] else None
            radius=gate["documentation_field_radius_ly"]
            if loc is None or radius is None:continue
            a=hypot(loc[0]-src[0],loc[1]-src[1])
            b=hypot(loc[0]-dst[0],loc[1]-dst[1])
            field.append({
                "game_id":game,"turn":turn,
                "actor_id":candidate["initiator_ship_id"],
                "target_id":candidate["target_ship_id"],
                "dungeon_id":gate["ship_id"],"dungeon_owner_id":gate["owner_id"],
                "same_owner":gate["owner_id"]==candidate["owner_id"],
                "Tminus1_source_distance_to_field":round(a,5),
                "Tminus1_target_distance_to_field":round(b,5),
                "documentary_radius_ly":radius,
                "source_margin_ly":round(radius-a,5),
                "target_margin_ly":round(radius-b,5),
                "source_covered_on_Tminus1":a<=radius,
                "target_covered_on_Tminus1":b<=radius,
                "active_during_Chunnel_Host_phase_proven":False,
            })
    return {
        "game_id":game,"turn":turn,
        "Tminus1_targeted_cases":candidates_out,
        "Tminus1_selected_ship_roster":ships,
        "Tminus1_dungeon_inventory":stargates,
        "Tminus1_field_geometry":field,
        "Tminus1_all_features_frozen_before_T":True,
    }


def compare_window(frozen,after,short,long):
    by_ship={}
    for ship in frozen["Tminus1_selected_ship_roster"]:
        status,raw=v13._current_ship(
            after,ship["ship_id"],ship["owner_id"],ship["Tminus1_hull_id"])
        pos=xy((raw.get("x"),raw.get("y"))) if raw is not None else None
        fuel=num(raw.get("neutronium")) if raw is not None else None
        engine=num(raw.get("engineid",raw.get("engine_id"))) if raw is not None else None
        by_ship[ship["ship_id"]]={
            **ship,"T_status":status,
            "T_position":list(pos) if pos is not None else None,
            "T_fuel_net_loss":ship["Tminus1_fuel"]-fuel if fuel is not None and ship["Tminus1_fuel"] is not None else None,
            "T_engine":engine,
        }
    cases=[]
    for c in frozen["Tminus1_targeted_cases"]:
        key=(c["game_id"],c["turn"],c["initiator_ship_id"],c["target_ship_id"])
        original=short[key]
        actor=by_ship[c["initiator_ship_id"]]
        target=by_ship[c["target_ship_id"]]
        p=xy(actor["T_position"]) if actor["T_position"] is not None else None
        expected=xy(original["T_actor_position"]) if original["T_actor_position"] is not None else None
        if (p!=expected or
            (p is None)!=(original["T_observation_status"].startswith("ABSTAIN"))):
            raise ValueError("V23 short actor owner-current T drift")
        downstream=[]
        for ch in c["Tminus1_frozen_downstream_chains"]:
            mid=by_ship[ch["middle_firecloud_id"]]
            dest=xy(ch["Tminus1_downstream_target"])
            downstream.append({
                **ch,
                "T_first_actor_at_downstream_destination":p==dest if p is not None else None,
                "T_middle_actor_at_downstream_destination":(
                    xy(mid["T_position"])==dest if mid["T_position"] else None),
                "T_first_actor_at_original_short_target":(
                    p==xy(c["Tminus1_target"]) if p is not None else None),
                "independent_host_chunnel_activation_proven":False,
            })
        src,dst=xy(c["Tminus1_source"]),xy(c["Tminus1_target"])
        wp=xy(c["Tminus1_waypoint"]) if c["Tminus1_waypoint"] is not None else None
        warp=c["Tminus1_initiator_warp"]
        raw_normal_candidate=warp is not None and warp>0 and wp==dst and hypot(
            dst[0]-src[0],dst[1]-src[1])<=warp**2
        cases.append({
            **c,
            "T_actor_observation":actor,
            "T_target_observation":target,
            "T_actor_matches_original_short_target":(p==dst if p is not None else None),
            "T_actor_direct_waypoint_warp_geometric_candidate":raw_normal_candidate,
            "T_destination_matches_raw_Tminus1_waypoint":p==wp if p is not None and wp is not None else None,
            "T_actor_matches_downstream_eligible_long_target":any(
                r["T_first_actor_at_downstream_destination"] is True for r in downstream),
            "frozen_downstream_chain_T_comparisons":downstream,
            "observational_only":True,
        })
    # stargate comparison after every Tminus1 window frozen.
    gates=[]
    for gate in frozen["Tminus1_dungeon_inventory"]:
        ship=by_ship.get(gate["ship_id"])
        if ship is None:raise ValueError("T-1 Stargate missing from audit roster")
        gates.append({
            "game_id":frozen["game_id"],"turn":frozen["turn"],
            "ship_id":gate["ship_id"],"owner_id":gate["owner_id"],
            "Tminus1_position":gate["Tminus1_position"],
            "Tminus1_engine_id":gate["Tminus1_engine_id"],
            "T_owner_current_status":ship["T_status"],
            "T_owner_current_position":ship["T_position"],
            "T_position_unchanged":ship["T_position"]==gate["Tminus1_position"]
                if ship["T_position"] is not None else None,
            "T_engine_unchanged":ship["T_engine"]==gate["Tminus1_engine_id"]
                if ship["T_engine"] is not None else None,
            "actual_Host_field_activation_proven":False,
        })
    return cases,gates


def summarize(short,long,windows,pre,post):
    cases=[c for a,_ in post for c in a]
    fields=[x for item in pre.values() for x in item["Tminus1_field_geometry"]]
    gates=[x for _,ls in post for x in ls]
    graph_chains=[x for c in cases for x in c["frozen_downstream_chain_T_comparisons"]]
    classif=Counter()
    for c in cases:
        if c["T_actor_matches_downstream_eligible_long_target"]:
            cls="AT_DOWNSTREAM_LONG_DESTINATION"
        elif c["T_actor_matches_original_short_target"]:
            cls="AT_ORIGINAL_SHORT_TARGET"
        elif c["T_actor_observation"]["T_position"]==c["Tminus1_source"]:
            cls="AT_SOURCE"
        elif c["T_actor_observation"]["T_position"] is None:
            cls="ABSTAIN_T_OWNER_CURRENT"
        else:cls="ELSEWHERE"
        classif[cls]+=1
    root={
        "schema":SCHEMA,"status":STATUS,
        "source_v23_field_scan_git_blob_sha1":V23_FIELD_BLOB,
        "source_v23_manifest_git_blob_sha1":V23_MANIFEST_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "Tminus1_all_windows_frozen_before_any_T":True,
        "actual_chunnel_activation_or_movement_phase_proven":False,
        "new_Host_movement_or_combat_predictions":0,
        "Nplus1_VCR_used":False,"independent_new_corpus":False,
        "boundary":(
            "V24 examines exactly eight V23-selected short edges, and "
            "the selection is retrospective. Graph edges are Tminus1-only "
            "and require ID, owner and exact shared target/source location. "
            "A short candidate observed at a downstream eligible long "
            "destination may have been transported by another Host-phase "
            "mechanism; same endpoint does not prove short-Chunnel execution. "
            "A source=target difference of 1LY is NOT automatically a "
            "Chunnel or an ordinary warp-well step; frozen raw waypoint, "
            "Warp, Tow orders and T owner-current support only observational "
            "comparisons. Dungeon stabilized-field radius at Tminus1 does "
            "not prove activation at the later Host phase. Multi-ship "
            "same-site evidence is correlated. No production rules promoted."
        ),
    }
    common={
        "frozen_V23_short_edge_count":len(short),
        "frozen_V23_conventional_long_edge_controls":len(long),
        "targeted_Tminus1_windows":len(windows),
        "G449095_T121_361_to_114_to_443_chain":
            any((c["game_id"],c["turn"],c["short_actor_id"],c["middle_firecloud_id"],c["downstream_target_id"])==EXPECTED_CHAIN_1 for c in graph_chains),
        "G449095_T121_396_to_218_to_548_chain":
            any((c["game_id"],c["turn"],c["short_actor_id"],c["middle_firecloud_id"],c["downstream_target_id"])==EXPECTED_CHAIN_2 for c in graph_chains),
    }
    return (
        {**root,"phase":"chains",
         "summary":{**common,
                    "Tminus1_eligible_short_to_long_chains":len(graph_chains),
                    "chain_window_clusters":len({(x["game_id"],x["turn"]) for x in graph_chains}),
                    "first_actor_T_at_downstream_long_destination":sum(x["T_first_actor_at_downstream_destination"] is True for x in graph_chains),
                    "first_actor_T_at_original_short_target":sum(x["T_first_actor_at_original_short_target"] is True for x in graph_chains),
                    "G449095_both_T121_short_actors_at_frozen_long_destinations":all(
                        any(x["T_first_actor_at_downstream_destination"] is True and
                            (x["game_id"],x["turn"],x["short_actor_id"],x["middle_firecloud_id"],x["downstream_target_id"])==key for x in graph_chains)
                        for key in (EXPECTED_CHAIN_1,EXPECTED_CHAIN_2)),
                    "Chunnel_chain_execution_proven":False},
         "frozen_Tminus1_chain_T_observations":graph_chains},
        {**root,"phase":"orders",
         "summary":{**common,
                    "eight_actor_observed_endpoint_categories":dict(sorted(classif.items())),
                    "Tminus1_warp_geometric_waypoint_candidates":sum(c["T_actor_direct_waypoint_warp_geometric_candidate"] for c in cases),
                    "Tminus1_tow_request_appearances":sum(len(c["Tminus1_tow_request_ship_ids"]) for c in cases),
                    "G449095_T141_547_to_229_observed_at_1LY_target":any(
                        c["game_id"]==449095 and c["turn"]==141 and
                        c["initiator_ship_id"]==547 and c["T_actor_matches_original_short_target"]
                        for c in cases),
                    "actual_movement_or_chunnel_execution_proven":False},
         "Tminus1_orders_and_T_observations":cases},
        {**root,"phase":"stabilizers",
         "summary":{**common,
                    "Tminus1_documented_dungeon_field_actor_geometry_rows":len(fields),
                    "Tminus1_short_actor_source_field_coverage_rows":sum(f["source_covered_on_Tminus1"] for f in fields),
                    "Tminus1_short_actor_source_field_foreign_owner_rows":sum(f["source_covered_on_Tminus1"] and not f["same_owner"] for f in fields),
                    "Tminus1_field_target_inside_rows":sum(f["target_covered_on_Tminus1"] for f in fields),
                    "Tminus1_stargate_ship_appearances":len(gates),
                    "T_stargate_position_unchanged":sum(g["T_position_unchanged"] is True for g in gates),
                    "Host_stabilization_activation_proven":False},
         "Tminus1_documented_field_geometry":fields,
         "Tminus1_to_T_stargate_persistence":gates},
    )


def publish(folder,reports):
    folder.mkdir(parents=True,exist_ok=True)
    index={}
    for phase,report in zip(OUTPUTS,reports,strict=True):
        path=folder/(phase+".json")
        temp=path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(path)
        index[phase]={
            "file":path.name,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "summary":report["summary"],
        }
        print("===== C5 V24",phase,"=====")
        print("status:",report["status"])
        print("summary:",report["summary"])
        print("output:",path)
    manifest={
        "schema":SCHEMA,"phase":"manifest",
        "status":"V24_SHORT_EDGE_THREE_MECHANISM_AUDITS_COMPLETE",
        "all_three_complete":len(index)==3,
        "source_v23_field_scan_git_blob_sha1":V23_FIELD_BLOB,
        "source_v23_manifest_git_blob_sha1":V23_MANIFEST_BLOB,
        "source_db_sha256":SHA256,
        "reports":index,
        "Host_activation_proven":False,
    }
    dest=folder/"manifest.json"
    tmp=dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(dest)
    print("===== C5 V24 MANIFEST COMPLETE =====")
    print("status:",manifest["status"])
    print("output:",dest)


def build_report(conn,field,manifest,raw):
    short,long,windows=freeze_source(field,manifest,raw)
    chains=frozen_chains(short,long)
    pre={}
    for n,(g,t) in enumerate(windows,1):
        print(f"[c5-v24] PRE [{n}/{len(windows)}] G{g} T{t}",flush=True)
        pre[g,t]=freeze_window(conn,g,t,short,long,chains)
    # STRICT: no POST archive read until ALL seven source rosters frozen.
    observed=[]
    for n,(g,t) in enumerate(windows,1):
        print(f"[c5-v24] POST [{n}/{len(windows)}] G{g} T{t}",flush=True)
        after=v9.after_owner_current(conn,game=g,turn=t)
        observed.append(compare_window(pre[g,t],after,short,long))
    return summarize(short,long,windows,pre,observed)


def main():
    p=argparse.ArgumentParser()
    for key in ("frozen-v23-field","frozen-v23-manifest","corpus-db-root","output-dir"):
        p.add_argument("--"+key,type=Path,required=True)
    opt=p.parse_args()
    try:
        field,raw=git_pinned(opt.frozen_v23_field,V23_FIELD_BLOB)
        manifest,_=git_pinned(opt.frozen_v23_manifest,V23_MANIFEST_BLOB)
        freeze_source(field,manifest,raw)
        db=opt.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("missing immutable public100 generation")
        print("[c5-v24] verifying pinned public100 SHA256 once",flush=True)
        began=time.monotonic()
        with db.open("rb") as fd:digest=hashlib.file_digest(fd,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("public100 checksum drift")
        print(f"[c5-v24] hash verified in {time.monotonic()-began:.1f}s, read-only",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,opt.corpus_db_root)
        try:reports=build_report(conn,field,manifest,raw)
        finally:conn.close()
        publish(opt.output_dir,reports)
    except (OSError,ValueError,TypeError,KeyError,IndexError,json.JSONDecodeError) as err:
        print("ERROR V24:",err,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
