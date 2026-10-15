"""V22 batch: 16 additional game-disjoint, outcome-blind Chunnel studies.

One immutable public100 verification, 48 metadata-only selected adjacent
T-1/T windows, one complete PRE freeze, one complete POST comparison.
Three reports and one SHA256 manifest in ONE evidence publication:
   actors.json     Rule-aware stock Firecloud conditional endpoint audit
   stabilizers.json Archival game-rule/Dungeon coverage and persistence
   escorts.json    Preselected colocated ordinary passenger observations
No evidence of true Host Chunnel-phase execution is asserted.
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
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_disjoint_discriminative_chunnel_gates_v17 as v17
import combat_c5_chunnel_stabilization_provenance_v20 as v20
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_chunnel_endpoint_screen_v11 as v11

SCHEMA="planets-lab.combat-c5-ruleaware-disjoint-batch.v22"
STATUS="GAME_DISJOINT_TMINUS1_RULEAWARE_OBSERVATIONAL_NOT_ACTIVATION"
V17_BLOB="a6256b70dc63b9b7126a211245bc65ce20ece863"
V20_BLOB="3d5e1d5aeb6b0138c01bab3ec81185d0685233c0"
GENERATION=v20.GENERATION
SHA256=v20.SHA256
GAME_COUNT=16
WINDOW_COUNT=48
PHASES=("actors","stabilizers","escorts")


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def pt(x:Any)->tuple[int,int]|None:
    return v20.position(x)


def git_file(path:Path,digest:str):
    data=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
    if actual!=digest:raise ValueError("published Git blob mismatch: "+str(path))
    result=json.loads(data)
    if not isinstance(result,dict):raise ValueError("report JSON not object")
    return result


def pinned_metadata_exclusions(v17report:Mapping[str,Any],v20report:Mapping[str,Any]):
    if (v17report.get("schema")!=v17.SCHEMA or
        v17report.get("status")!=v17.STATUS or
        v17report.get("source_db_sha256")!=SHA256 or
        v17report.get("summary",{}).get("selected_game_count")!=16 or
        v17report.get("summary",{}).get("selected_window_count")!=48 or
        v17report.get("summary",{}).get("candidate_stock_firecloud_edges")!=113 or
        v17report.get("summary",{}).get("Nplus1_VCR_used") is not False):
        raise ValueError("V17 excluded cohort changed")
    if (v20report.get("schema")!=v20.SCHEMA or
        v20report.get("status")!=v20.STATUS or
        v20report.get("source_v17_git_blob_sha1")!=V17_BLOB or
        v20report.get("source_db_sha256")!=SHA256 or
        v20report.get("summary",{}).get("frozen_V17_short_distance_edges")!=13):
        raise ValueError("V20 stabilizer source changed")
    original=v17report.get("frozen_selection")
    if not isinstance(original,Mapping):raise ValueError("V17 frozen game list unavailable")
    if original.get("no_ship_outcomes_or_VCR_in_selection") is not True:
        raise ValueError("V17 source selection not outcome blind")
    prior=original.get("excluded_V6_V9_V13_V14_game_ids")
    selected=original.get("game_turns")
    if not isinstance(prior,list) or len(prior)!=57 or not isinstance(selected,list) or len(selected)!=48:
        raise ValueError("V17 excluded games/window protocol changed")
    games=set(prior)
    if len(games)!=57 or any(integer(g) is None or g<=0 for g in games):
        raise ValueError("bad frozen earlier research game IDs")
    visible=set()
    for w in selected:
        g,t=integer(w.get("game_id")),integer(w.get("turn"))
        if g is None or t is None or t<2 or (g,t) in visible or g in games:
            raise ValueError("bad V17 selected window")
        visible.add((g,t))
    selected_games={g for g,_ in visible}
    if len(selected_games)!=16:raise ValueError("V17 16 unique games not preserved")
    return frozenset(games|selected_games)


def field_features(actor,stargates,rules,races):
    source=pt(actor["source"])
    target=pt(actor["target"])
    owner=actor["owner_id"]
    near=[]
    unknown=[]
    for s in stargates:
        if not s["archived_catalog_name_confirms_dungeon_stargate"]:
            continue
        radius=s["documentation_field_radius_ly"]
        loc=pt(s["Tminus1_position"]) if s["Tminus1_position"] is not None else None
        if loc is None or radius is None:
            unknown.append(s["ship_id"])
            continue
        ds=hypot(source[0]-loc[0],source[1]-loc[1])
        dt=hypot(target[0]-loc[0],target[1]-loc[1])
        if ds<=radius:
            near.append({
                "stargate_id":s["ship_id"],"stargate_owner_id":s["owner_id"],
                "same_owner":s["owner_id"]==owner,
                "source_distance_ly":round(ds,5),
                "target_distance_ly":round(dt,5),
                "radius_ly":radius,
                "target_also_inside_Tminus1_field":dt<=radius,
                "active_at_Host_phase_proven":False,
            })
    flags=[v for k,v in rules.items()
           if k.lower().replace("_","").replace("-","").endswith("shortformatrules")]
    if len(set(flags))>1:raise ValueError("conflicting explicit short-format flags")
    short=flags[0] if flags else None
    borg=(races.get(owner)==6)
    explicit_short=(short is True and borg)
    source_valid=bool(near) or explicit_short
    distance=actor["Tminus1_distance_ly"]
    if source==target:cohort="NON_DISCRIMINATIVE_COLOCATED"
    elif actor["cohort"]=="ALL_TMINUS1_GATES_PASS":
        cohort="LONG_CONVENTIONAL_PASS"
    elif actor["single_failing_gate"]==v16.SHORT_GATE if hasattr(v16,"SHORT_GATE") else False:
        cohort="SHORT_WITH_TMINUS1_STABILIZER_WITNESS" if source_valid and distance>=1 else "SHORT_NO_DOCUMENTED_STABILIZER_WITNESS"
    elif actor["single_failing_gate"]=="DISTANCE_BELOW_100_AT_TMINUS1":
        cohort="SHORT_WITH_TMINUS1_STABILIZER_WITNESS" if source_valid and distance>=1 else "SHORT_NO_DOCUMENTED_STABILIZER_WITNESS"
    else:cohort="OTHER_ONE_FAILED_TMINUS1_GATE"
    return {
        "Tminus1_ruleaware_cohort":cohort,
        "Tminus1_owner_race_id":races.get(owner),
        "Tminus1_explicit_short_format_flag":short,
        "Tminus1_stargate_source_coverage_candidates":near,
        "Tminus1_stargate_missing_field_data":unknown,
        "Tminus1_stabilization_field_witness":source_valid,
        "Tminus1_phase_state_unproven":True,
    }


def pre_window(conn,game,turn):
    snapshots,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1)
    raw_edges,rejections=v16.potential_stock_edges(roster)
    rules,races=v20.game_rules_markers(raws,game,turn)
    catalog=v11.hull_name_inventory(raws)
    gates=v20.stabilizer_inventory(roster,catalog)
    rows=[]
    escorts=[]
    for e in raw_edges:
        src=pt(e["source"])
        features=field_features(e,gates,rules,races)
        entry={**e,**features,"game_id":game,"turn":turn,
               "Tminus1_source_target_distinct":src!=pt(e["target"])}
        rows.append(entry)
        if entry["Tminus1_ruleaware_cohort"] not in (
            "LONG_CONVENTIONAL_PASS","SHORT_WITH_TMINUS1_STABILIZER_WITNESS"):
            continue
        stack=[]
        for ship_id,(who,raw) in sorted(roster.items()):
            if pt((raw.get("x"),raw.get("y")))!=src:continue
            stack.append({
                "ship_id":ship_id,"owner_id":who,
                "Tminus1_hull_id":integer(raw.get("hullid",raw.get("hull_id"))),
                "Tminus1_warp":integer(raw.get("warp")),
                "Tminus1_fuel":integer(raw.get("neutronium")),
                "same_owner":who==e["owner_id"],
            })
        if len(stack)>300:raise ValueError("unbounded colocated ship stack")
        if not any(s["ship_id"]==e["initiator_ship_id"] for s in stack):
            raise ValueError("eligible actor missing from T-1 source ship stack")
        escorts.append({
            "game_id":game,"turn":turn,"initiator_ship_id":e["initiator_ship_id"],
            "target_ship_id":e["target_ship_id"],"owner_id":e["owner_id"],
            "target":e["target"],"Tminus1_ruleaware_cohort":entry["Tminus1_ruleaware_cohort"],
            "Tminus1_stack":stack,
        })
    return {
        "game_id":game,"turn":turn,
        "source_immutable_turn":turn-1,
        "Tminus1_edges":rows,
        "Tminus1_stargates":gates,
        "Tminus1_rule_scalar_metadata":rules,
        "Tminus1_rejections":rejections,
        "Tminus1_escorts":escorts,
        "Tminus1_frozen_before_any_T":True,
    }


def after_window(frozen:Mapping[str,Any],current:Mapping[int,Any]):
    game,turn=frozen["game_id"],frozen["turn"]
    actors=[]
    for e in frozen["Tminus1_edges"]:
        owner,actor,target=e["owner_id"],e["initiator_ship_id"],e["target_ship_id"]
        state,raw=v13._current_ship(current,actor,owner,56)
        tgtstate,tar=v13._current_ship(current,target,owner,56)
        position=pt((raw.get("x"),raw.get("y"))) if raw else None
        tgtpos=pt((tar.get("x"),tar.get("y"))) if tar else None
        origin,dest=pt(e["source"]),pt(e["target"])
        if not e["Tminus1_source_target_distinct"]:
            outcome="NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"
        elif raw is None:outcome=state
        elif position==dest:outcome="T_ACTOR_AT_DISTINCT_TARGET"
        elif position==origin:outcome="T_ACTOR_AT_SOURCE"
        else:outcome="T_ACTOR_ELSEWHERE"
        fuel=integer(raw.get("neutronium")) if raw else None
        delta=e["actor_Tminus1_fuel"]-fuel if fuel is not None else None
        actors.append({
            **e,
            "T_actor_status":outcome,
            "T_owner_current_status":state,
            "T_owner_current_position":list(position) if position else None,
            "T_target_owner_current_status":tgtstate,
            "T_target_position":list(tgtpos) if tgtpos else None,
            "T_target_at_frozen_target":(tgtpos==dest if tgtpos is not None else None),
            "T_actor_net_fuel_loss_KT":delta,
            "T_owner_current_is_not_prechunnel_phase":True,
            "actual_Chunnel_execution_proven":False,
        })
    gates=[]
    for s in frozen["Tminus1_stargates"]:
        state,raw=v13._current_ship(current,s["ship_id"],s["owner_id"],108)
        loc=pt((raw.get("x"),raw.get("y"))) if raw else None
        engine=integer(raw.get("engineid",raw.get("engine_id"))) if raw else None
        gates.append({
            **s,"game_id":game,"turn":turn,
            "T_stargate_owner_current_status":state,
            "T_stargate_position":list(loc) if loc else None,
            "T_stargate_engine":engine,
            "T_position_unchanged":(loc==pt(s["Tminus1_position"]) if loc is not None and s["Tminus1_position"] else None),
            "T_engine_unchanged":(engine==s["Tminus1_engine_id"] if engine is not None else None),
            "Host_field_activation_proven":False,
        })
    stacks=[]
    for record in frozen["Tminus1_escorts"]:
        members=[]
        for s in record["Tminus1_stack"]:
            state,raw=v13._current_ship(current,s["ship_id"],s["owner_id"],s["Tminus1_hull_id"])
            loc=pt((raw.get("x"),raw.get("y"))) if raw else None
            fuel=integer(raw.get("neutronium")) if raw else None
            delta=s["Tminus1_fuel"]-fuel if fuel is not None and s["Tminus1_fuel"] is not None else None
            members.append({
                **s,"T_owner_current_status":state,
                "T_owner_current_position":list(loc) if loc else None,
                "T_at_source_edge_target":(loc==pt(record["target"]) if loc is not None else None),
                "T_net_fuel_loss_KT":delta,"true_Chunnel_passenger_proven":False,
            })
        stacks.append({
            **{k:v for k,v in record.items() if k!="Tminus1_stack"},
            "Tminus1_stack_size":len(record["Tminus1_stack"]),
            "T_members":members,
            "T_observed_colocated_not_independent_activation_proof":True,
        })
    return actors,gates,stacks


def report_base(phase,windows,excluded):
    return {
        "schema":SCHEMA,"status":STATUS,"phase":phase,
        "source_v17_git_blob_sha1":V17_BLOB,
        "source_v20_git_blob_sha1":V20_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "metadata_selected_game_turns":[{"game_id":g,"turn":t} for g,t in windows],
        "frozen_previous_research_games":sorted(excluded),
        "all_windows_Tminus1_frozen_before_any_T":True,
        "new_canonical_Host_movement_or_combat_predictions":0,
        "actual_Chunnel_activation_proven":False,
        "Nplus1_VCR_used":False,
        "same_preexisting_public100_not_newly_collected_corpus":True,
    }


def aggregate(pre,observations,windows,excluded,errors):
    actors=[x for batch in observations for x in batch[0]]
    gates=[x for batch in observations for x in batch[1]]
    escorts=[x for batch in observations for x in batch[2]]
    by_cohort=defaultdict(Counter)
    clusters=defaultdict(set)
    for row in actors:
        cohort=row["Tminus1_ruleaware_cohort"]
        by_cohort[cohort][row["T_actor_status"]]+=1
        clusters[cohort].add((row["game_id"],row["turn"]))
    source_counts=Counter(x["Tminus1_ruleaware_cohort"]
                          for f in pre.values() if f is not None for x in f["Tminus1_edges"])
    base_summary={
        "selected_games":GAME_COUNT,"selected_windows":WINDOW_COUNT,
        "previous_research_game_overlap":len({g for g,_ in windows}&excluded),
        "posthost_compared_windows":len(observations),
        "window_context_abstentions":len(errors),
        "new_canonical_Host_movement_or_combat_predictions":0,
        "Nplus1_VCR_used":False,
    }
    candidates=[x for x in actors if x["Tminus1_ruleaware_cohort"]==
                "SHORT_WITH_TMINUS1_STABILIZER_WITNESS"]
    return (
        {
            **report_base("actors",windows,excluded),
            "summary":{
                **base_summary,
                "Tminus1_candidate_actor_edges":sum(source_counts.values()),
                "Tminus1_cohorts":dict(sorted(source_counts.items())),
                "T_cohort_endpoint_counts":{
                    c:dict(sorted(v.items())) for c,v in sorted(by_cohort.items())},
                "distinct_game_turn_clusters_by_cohort":{
                    k:len(v) for k,v in sorted(clusters.items())},
                "Tminus1_short_field_witness_candidates":len(candidates),
                "short_field_witness_distinct_games":len({c["game_id"] for c in candidates}),
                "short_field_witness_distinct_windows":len({
                    (c["game_id"],c["turn"]) for c in candidates}),
                "Host_chunnel_activation_proven":False,
            },
            "actor_Tminus1_to_T_comparisons":actors,
            "window_errors":errors,
        },
        {
            **report_base("stabilizers",windows,excluded),
            "summary":{
                **base_summary,
                "Tminus1_Dungeon_appearances":len(gates),
                "Tminus1_Dungeon_distinct_games":len({r["game_id"] for r in gates}),
                "T_Dungeon_owner_current_categories":dict(sorted(
                    Counter(g["T_stargate_owner_current_status"] for g in gates).items())),
                "T_Dungeon_position_unchanged":sum(x["T_position_unchanged"] is True for x in gates),
                "T_Dungeon_position_changed":sum(x["T_position_unchanged"] is False for x in gates),
                "T_Dungeon_engine_unchanged":sum(x["T_engine_unchanged"] is True for x in gates),
                "Host_stabilizer_phase_active_proven":False,
            },
            "Tminus1_game_rule_scalar_hints":{
                f"{g}/{t}":pre[g,t]["Tminus1_rule_scalar_metadata"]
                for g,t in windows if pre[g,t] is not None},
            "Tminus1_T_stargate_comparisons":gates,
            "window_errors":errors,
        },
        {
            **report_base("escorts",windows,excluded),
            "summary":{
                **base_summary,
                "Tminus1_preselected_actor_episodes":len(escorts),
                "Tminus1_preselected_distinct_windows":len({
                    (s["game_id"],s["turn"]) for s in escorts}),
                "Tminus1_source_ship_appearances":sum(s["Tminus1_stack_size"] for s in escorts),
                "T_owner_current_ship_at_preselected_target":sum(
                    x["T_at_source_edge_target"] is True
                    for s in escorts for x in s["T_members"]),
                "true_Chunnel_passenger_mechanism_proven":False,
            },
            "episode_preselected_source_stacks":escorts,
            "window_errors":errors,
        },
    )


def build_report(conn,v17source,v20source):
    excluded=pinned_metadata_exclusions(v17source,v20source)
    metadata=conn.execute(
        "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
    ).fetchall()
    windows=v13.choose_windows(metadata,excluded,game_count=GAME_COUNT)
    if (len(windows)!=WINDOW_COUNT or len({g for g,_ in windows})!=GAME_COUNT or
        any(g in excluded for g,_ in windows)):
        raise ValueError("new research game cohort selection changed")
    print("[c5-v22] frozen metadata-only game-turn selection:",windows,flush=True)
    pre={}
    errors=[]
    for i,(g,t) in enumerate(windows,1):
        print(f"[c5-v22] PRE [{i}/{len(windows)}] G{g} T{t}",flush=True)
        try:pre[g,t]=pre_window(conn,g,t)
        except (ValueError,TypeError,KeyError) as exc:
            pre[g,t]=None
            errors.append({"game_id":g,"turn":t,"phase":"PRE",
                           "abstain":f"{type(exc).__name__}:{exc}"})
    # HARD BARRIER: all 48 PRE contexts attempted, no T read above.
    results=[]
    for i,(g,t) in enumerate(windows,1):
        print(f"[c5-v22] POST [{i}/{len(windows)}] G{g} T{t}",flush=True)
        if pre[g,t] is None:continue
        try:
            current=v9.after_owner_current(conn,game=g,turn=t)
            results.append(after_window(pre[g,t],current))
        except (ValueError,TypeError,KeyError) as exc:
            errors.append({"game_id":g,"turn":t,"phase":"POST",
                           "abstain":f"{type(exc).__name__}:{exc}"})
    if len(results)<12:raise ValueError("insufficient eligible post-T windows")
    return aggregate(pre,results,windows,excluded,errors)


def publish_reports(folder:Path,reports):
    folder.mkdir(parents=True,exist_ok=True)
    manifest={}
    for phase,report in zip(PHASES,reports,strict=True):
        path=folder/(phase+".json")
        target=path.with_suffix(".json.tmp")
        target.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        target.replace(path)
        manifest[phase]={
            "file":path.name,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "summary":report["summary"],
        }
        print("===== C5 V22",phase,"=====")
        print("status:",report["status"])
        print("summary:",report["summary"])
        print("output:",path)
    if len(manifest)!=3 or len({x["sha256"] for x in manifest.values()})!=3:
        raise ValueError("three independent reports required")
    document={
        "schema":SCHEMA,"status":"V22_ALL_THREE_DISJOINT_HOLDOUT_REPORTS_COMPLETE",
        "phase":"manifest",
        "source_v17_git_blob_sha1":V17_BLOB,
        "source_v20_git_blob_sha1":V20_BLOB,
        "source_db_sha256":SHA256,
        "phase_reports":manifest,
        "all_three_completed":True,
        "same_public100_not_new_corpus":True,
        "activation_not_proven":True,
    }
    final=folder/"manifest.json"
    temp=folder/"manifest.json.tmp"
    temp.write_text(json.dumps(document,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    temp.replace(final)
    print("===== C5 V22 ALL THREE REPORTS COMPLETE =====")
    print("status:",document["status"])
    print("output:",final)


def main():
    p=argparse.ArgumentParser()
    for k in ("frozen-v17","frozen-v20","corpus-db-root","output-dir"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    try:
        v17source=git_file(a.frozen_v17,V17_BLOB)
        v20source=git_file(a.frozen_v20,V20_BLOB)
        pinned_metadata_exclusions(v17source,v20source)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 database unavailable")
        print("[c5-v22] pinned read-only DB SHA256 verification",flush=True)
        ts=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("public100 SHA256 drift")
        print(f"[c5-v22] verified in {time.monotonic()-ts:.1f}s",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:reports=build_report(conn,v17source,v20source)
        finally:conn.close()
        publish_reports(a.output_dir,reports)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR V22:",exc,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
