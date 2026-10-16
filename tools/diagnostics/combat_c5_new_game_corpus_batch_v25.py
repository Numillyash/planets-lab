"""V25 independently acquired finished-game archive cohort, 3 frozen analyses.

The selected *games* are disjoint from the original 100. Selection is
metadata-only and completed before this code sees any ship observations.
The new games are retrospective archives, NOT prospectively observed
real-time Host traces. T-1 candidacy/field evidence is frozen across
all metadata-selected windows before reading any T archive.

Reports: actors.json, fields.json, passengers.json, manifest.json.
No raw friendly code, secret, account names, or private payload exposed.
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
for parent in (ROOT/"src",Path(__file__).resolve().parent):
    if str(parent) not in sys.path:sys.path.insert(0,str(parent))
import duckdb
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_chunnel_stabilization_provenance_v20 as v20
import combat_c5_chunnel_endpoint_screen_v11 as v11

SCHEMA="planets-lab.combat-c5-new-game-corpus-batch.v25"
STATUS="NEWLY_ACQUIRED_GAME_DISJOINT_RETROSPECTIVE_TMINUS1_RULEAWARE_OBSERVATIONAL"
REPORTS=("actors","fields","passengers")
GAME_COUNT=8
MAX_WINDOWS_PER_GAME=24


def as_int(value:Any)->int|None:
    return value if type(value) is int else None


def loc(value:Any)->tuple[int,int]|None:
    return v20.position(value)


def ids(path:Path)->frozenset[int]:
    out=set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():continue
        item=json.loads(line)
        game=as_int(item.get("game_id")) if isinstance(item,Mapping) else None
        if game is None or game<=0 or game in out:
            raise ValueError("duplicate or invalid selected/baseline game ID")
        out.add(game)
    return frozenset(out)


def audit_population(selected:Path,baseline:Path,conn):
    new,old=ids(selected),ids(baseline)
    if len(old)!=100 or len(new)!=GAME_COUNT or new&old:
        raise ValueError("not exactly 100 baseline and 8 disjoint new games")
    db_ids={row[0] for row in conn.execute(
        "SELECT game_id FROM source_archives").fetchall()}
    if db_ids!=new:raise ValueError("new compact DB game membership differs from selected manifest")
    return new,old


def windows_from_metadata(metadata,selected):
    by_game=defaultdict(set)
    for game,turn in metadata:
        if as_int(game) is None or as_int(turn) is None or game<=0 or turn<0:
            raise ValueError("invalid archive metadata")
        if game in selected:by_game[game].add(turn)
    if set(by_game)!=set(selected):raise ValueError("new game missing source members")
    out=[]
    for game in sorted(selected):
        turns=sorted(t for t in by_game[game] if t>=2 and t-1 in by_game[game])
        if len(turns)<3:raise ValueError("new game insufficient adjacent archival turns")
        n=min(MAX_WINDOWS_PER_GAME,len(turns))
        picks=[i*(len(turns)-1)//(n-1) for i in range(n)]
        if len(set(picks))!=n:raise ValueError("duplicate quantile indices")
        out.extend((game,turns[i]) for i in picks)
    return tuple(out)


def field_evidence(edge,gates,rules,races):
    source=loc(edge["source"])
    target=loc(edge["target"])
    near=[]
    for gate in gates:
        if not gate["archived_catalog_name_confirms_dungeon_stargate"]:continue
        radius=gate["documentation_field_radius_ly"]
        point=loc(gate["Tminus1_position"]) if gate["Tminus1_position"] else None
        if radius is None or point is None:continue
        ds=hypot(source[0]-point[0],source[1]-point[1])
        dt=hypot(target[0]-point[0],target[1]-point[1])
        if ds<=radius:near.append({
            "stargate_id":gate["ship_id"],"stargate_owner_id":gate["owner_id"],
            "same_owner":gate["owner_id"]==edge["owner_id"],
            "source_distance_ly":round(ds,5),
            "target_distance_ly":round(dt,5),
            "radius_ly":radius,
            "target_also_inside_field":dt<=radius,
            "active_at_actual_Host_phase_proven":False,
        })
    candidates=[v for k,v in rules.items() if
                k.lower().replace("_","").replace("-","").endswith("shortformatrules")]
    if len(set(candidates))>1:raise ValueError("contradictory short-format rule")
    rule=candidates[0] if candidates else None
    cyborg=rule is True and races.get(edge["owner_id"])==6
    return {
        "Tminus1_stargate_coverage":near,
        "Tminus1_explicit_shortformat":rule,
        "Tminus1_explicit_cyborg_stabilization":cyborg,
        "Tminus1_short_field_witness":bool(near) or cyborg,
        "Tminus1_stabilizer_absence_unproven":True,
    }


def pre_window(conn,game,turn):
    snaps,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snaps,"ship"),turn-1)
    intents,rejections=v16.potential_stock_edges(roster)
    rules,races=v20.game_rules_markers(raws,game,turn)
    gates=v20.stabilizer_inventory(roster,v11.hull_name_inventory(raws))
    edges=[]
    passengers=[]
    for e in intents:
        source,target=loc(e["source"]),loc(e["target"])
        if source==target:cohort="NON_DISCRIMINATIVE_COLOCATED"
        elif e["cohort"]=="ALL_TMINUS1_GATES_PASS":
            cohort="LONG_CONVENTIONAL_PASS"
        elif e["single_failing_gate"]=="DISTANCE_BELOW_100_AT_TMINUS1":
            cohort="SHORT_ONE_GATE_FAILED"
        else:cohort="OTHER_SINGLE_FAILED_GATE"
        field=field_evidence(e,gates,rules,races) if cohort=="SHORT_ONE_GATE_FAILED" else {
            "Tminus1_short_field_witness":False,
            "Tminus1_stargate_coverage":[],
            "Tminus1_stabilizer_absence_unproven":True,
        }
        row={
            **{k:v for k,v in e.items() if k!="friendlycode"},
            "game_id":game,"turn":turn,
            "Tminus1_cohort":cohort,
            **field,
        }
        edges.append(row)
        if cohort not in ("LONG_CONVENTIONAL_PASS","SHORT_ONE_GATE_FAILED"):
            continue
        if cohort=="LONG_CONVENTIONAL_PASS" and any(
            p["game_id"]==game and p["turn"]==turn and p["Tminus1_cohort"]=="LONG_CONVENTIONAL_PASS"
            for p in passengers):
            continue  # one deterministic long-stack control per game/turn
        stack=[]
        for sid,(owner,raw) in sorted(roster.items()):
            if loc((raw.get("x"),raw.get("y")))!=source:continue
            stack.append({
                "ship_id":sid,"owner_id":owner,
                "hull_id":as_int(raw.get("hullid",raw.get("hull_id"))),
                "warp":as_int(raw.get("warp")),
                "fuel":as_int(raw.get("neutronium")),
                "same_owner_as_actor":owner==e["owner_id"],
            })
        if len(stack)>300 or not any(x["ship_id"]==e["initiator_ship_id"] for x in stack):
            raise ValueError("unbounded or missing actor in preselected Tminus1 source stack")
        passengers.append({
            "game_id":game,"turn":turn,
            "initiator_ship_id":e["initiator_ship_id"],
            "target_ship_id":e["target_ship_id"],
            "owner_id":e["owner_id"],
            "Tminus1_cohort":cohort,
            "Tminus1_destination":e["target"],
            "Tminus1_source_stack":stack,
        })
    return {
        "game_id":game,"turn":turn,"Tminus1_candidates":edges,
        "Tminus1_gates":gates,"Tminus1_rule_safe_scalars":rules,
        "Tminus1_escort_exposures":passengers,"Tminus1_exclusions":rejections,
        "all_Tminus1_data_frozen_before_T":True,
    }


def compare_window(frozen,after):
    actors=[]
    for e in frozen["Tminus1_candidates"]:
        state,rec=v13._current_ship(after,e["initiator_ship_id"],e["owner_id"],56)
        pos=loc((rec.get("x"),rec.get("y"))) if rec else None
        start,target=loc(e["source"]),loc(e["target"])
        if e["Tminus1_cohort"]=="NON_DISCRIMINATIVE_COLOCATED":
            outcome="NON_DISCRIMINATIVE_COLOCATED"
        elif rec is None:outcome=state
        elif pos==target:outcome="AT_DISTINCT_FROZEN_TARGET"
        elif pos==start:outcome="AT_SOURCE"
        else:outcome="ELSEWHERE"
        after_fuel=as_int(rec.get("neutronium")) if rec else None
        actors.append({
            **e,"T_status":outcome,
            "T_owner_current_status":state,
            "T_position":list(pos) if pos else None,
            "T_net_fuel_loss_KT":e["actor_Tminus1_fuel"]-after_fuel
                if after_fuel is not None else None,
            "Host_Chunnel_activation_proven":False,
        })
    gates=[]
    for gate in frozen["Tminus1_gates"]:
        state,rec=v13._current_ship(after,gate["ship_id"],gate["owner_id"],108)
        at=loc((rec.get("x"),rec.get("y"))) if rec else None
        engine=as_int(rec.get("engineid",rec.get("engine_id"))) if rec else None
        gates.append({
            **gate,
            "game_id":frozen["game_id"],"turn":frozen["turn"],
            "T_owner_current_status":state,
            "T_position":list(at) if at else None,
            "T_position_unchanged":at==loc(gate["Tminus1_position"])
                if at is not None and gate["Tminus1_position"] else None,
            "T_engine_unchanged":engine==gate["Tminus1_engine_id"]
                if engine is not None else None,
            "Host_field_active_proven":False,
        })
    passengers=[]
    for original in frozen["Tminus1_escort_exposures"]:
        target=loc(original["Tminus1_destination"])
        members=[]
        for s in original["Tminus1_source_stack"]:
            state,rec=v13._current_ship(after,s["ship_id"],s["owner_id"],s["hull_id"])
            at=loc((rec.get("x"),rec.get("y"))) if rec else None
            members.append({
                **s,"T_owner_current_status":state,
                "T_at_frozen_target":at==target if at is not None else None,
                "T_position":list(at) if at else None,
                "Chunnel_passenger_mechanism_proven":False,
            })
        passengers.append({
            **{k:v for k,v in original.items() if k!="Tminus1_source_stack"},
            "Tminus1_stack_size":len(original["Tminus1_source_stack"]),
            "T_members":members,
        })
    return actors,gates,passengers


def create_reports(selected,baseline,generation,sha,windows,frozen,post,errors):
    actors=[e for a,_,_ in post for e in a]
    fields=[e for _,gg,_ in post for e in gg]
    passengers=[e for _,_,ps in post for e in ps]
    by_cohort=defaultdict(Counter)
    for e in actors:by_cohort[e["Tminus1_cohort"]][e["T_status"]]+=1
    short=[e for e in actors if e["Tminus1_cohort"]=="SHORT_ONE_GATE_FAILED"]
    short_witness=[e for e in short if e["Tminus1_short_field_witness"]]
    root={
        "schema":SCHEMA,"status":STATUS,
        "generation":generation,"generation_sha256":sha,
        "baseline_game_ids_sha256":hashlib.sha256(
            ",".join(map(str,sorted(baseline))).encode()).hexdigest(),
        "selected_game_ids":sorted(selected),
        "Tminus1_frozen_before_first_T":True,
        "Nplus1_VCR_used":False,
        "Host_Chunnel_activation_or_combat_predictions_promoted":0,
        "newly_acquired_archival_games_not_live_prospective_Host_observations":True,
    }
    common={
        "selected_disjoint_games":len(selected),
        "baseline_games_excluded":len(baseline),
        "metadata_selected_adjacent_windows":len(windows),
        "Tminus1_contexts_available":sum(x is not None for x in frozen.values()),
        "posthost_compared_windows":len(post),
        "context_errors":len(errors),
    }
    return (
        {**root,"phase":"actors",
         "summary":{
             **common,
             "Tminus1_stock_chunnel_candidate_edges":len(actors),
             "Tminus1_frozen_cohort_counts":dict(sorted(Counter(
                 x["Tminus1_cohort"] for x in actors).items())),
             "T_endpoint_by_cohort":{k:dict(sorted(v.items()))
                                     for k,v in sorted(by_cohort.items())},
             "short_Tminus1_documented_field_witnesses":len(short_witness),
             "short_field_witness_distinct_games":len({x["game_id"] for x in short_witness}),
             "short_field_witness_distinct_game_turn_windows":len({
                 (x["game_id"],x["turn"]) for x in short_witness}),
             "actual_Host_chunnel_activation_proven":False},
         "preselected_actor_Tminus1_T_observations":actors,
         "window_errors":errors},
        {**root,"phase":"fields",
         "summary":{
             **common,"Tminus1_Dungeon_Stargate_appearances":len(fields),
             "Tminus1_Dungeon_games":len({x["game_id"] for x in fields}),
             "T_Dungeon_position_unchanged":sum(x["T_position_unchanged"] is True for x in fields),
             "T_Dungeon_engine_unchanged":sum(x["T_engine_unchanged"] is True for x in fields),
             "actual_stabilizer_activation_proven":False},
         "Tminus1_to_T_stargate_appearances":fields,
         "Tminus1_rule_scalar_hints":{
             f"{g}/{t}":frozen[g,t]["Tminus1_rule_safe_scalars"]
             for g,t in windows if frozen[g,t] is not None},
         "window_errors":errors},
        {**root,"phase":"passengers",
         "summary":{
             **common,
             "preselected_Tminus1_source_episodes":len(passengers),
             "preselected_distinct_game_turns":len({
                 (x["game_id"],x["turn"]) for x in passengers}),
             "preselected_source_ship_appearances":sum(x["Tminus1_stack_size"] for x in passengers),
             "same_owner_at_frozen_target":sum(m["T_at_frozen_target"] is True and
                 m["same_owner_as_actor"] for e in passengers for m in e["T_members"]),
             "different_owner_at_frozen_target":sum(m["T_at_frozen_target"] is True and
                 not m["same_owner_as_actor"] for e in passengers for m in e["T_members"]),
             "Host_passenger_mechanism_proven":False},
         "Tminus1_preselected_source_stack_posthost_comparisons":passengers,
         "window_errors":errors},
    )


def publish(outdir,reports):
    outdir.mkdir(parents=True,exist_ok=True)
    items={}
    for phase,doc in zip(REPORTS,reports,strict=True):
        target=outdir/(phase+".json")
        tmp=target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        tmp.replace(target)
        items[phase]={"filename":target.name,
                      "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                      "summary":doc["summary"]}
        print("===== C5 NEW CORPUS V25:",phase,"=====")
        print("summary:",doc["summary"])
        print("output:",target)
    manifest={
        "schema":SCHEMA,"status":"V25_NEW_GAME_CORPUS_THREE_REPORTS_COMPLETE",
        "all_three_complete":len(items)==3,
        "generation":reports[0]["generation"],
        "generation_sha256":reports[0]["generation_sha256"],
        "selected_game_ids":reports[0]["selected_game_ids"],
        "reports":items,
        "CURRENT_modified":False,
        "newly_collected_games_but_retrospective_archival_outcomes":True,
        "Host_mechanics_proven":False,
    }
    target=outdir/"manifest.json"
    tmp=target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    tmp.replace(target)
    print("===== C5 V25 ALL THREE NEW CORPUS REPORTS COMPLETE =====")
    print("status:",manifest["status"])
    print("generation:",manifest["generation"])
    print("generation_sha256:",manifest["generation_sha256"])
    print("output:",target)


def run(conn,new,old,generation,sha):
    rows=conn.execute(
        "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
    ).fetchall()
    windows=windows_from_metadata(rows,new)
    print(f"[c5-v25] selected metadata-only windows: {len(windows)} / {len(new)} new games",flush=True)
    frozen={}
    errors=[]
    for n,(game,turn) in enumerate(windows,1):
        print(f"[c5-v25] PRE [{n}/{len(windows)}] G{game} T{turn}",flush=True)
        try:frozen[game,turn]=pre_window(conn,game,turn)
        except (ValueError,TypeError,KeyError) as e:
            frozen[game,turn]=None
            errors.append({"game_id":game,"turn":turn,"phase":"PRE",
                           "reason":f"{type(e).__name__}:{e}"})
    # No T snapshots were read above; ALL source windows are now fixed.
    compared=[]
    for n,(game,turn) in enumerate(windows,1):
        print(f"[c5-v25] POST [{n}/{len(windows)}] G{game} T{turn}",flush=True)
        if frozen[game,turn] is None:continue
        if not frozen[game,turn]["Tminus1_candidates"] and not frozen[game,turn]["Tminus1_gates"]:
            continue
        try:
            current=v9.after_owner_current(conn,game=game,turn=turn)
            compared.append(compare_window(frozen[game,turn],current))
        except (ValueError,TypeError,KeyError) as e:
            errors.append({"game_id":game,"turn":turn,"phase":"POST",
                           "reason":f"{type(e).__name__}:{e}"})
    if len(compared)<3:raise ValueError("too few T owner-current comparisons")
    return create_reports(new,old,generation,sha,windows,frozen,compared,errors)


def main():
    a=argparse.ArgumentParser()
    for name in ("corpus-db","selected-manifest","baseline-manifest","output-dir"):
        a.add_argument("--"+name,type=Path,required=True)
    args=a.parse_args()
    try:
        db=args.corpus_db.resolve()
        if not db.is_file():raise ValueError("explicit new-generation DB absent")
        print("[c5-v25] hashing new immutable compact generation",flush=True)
        begin=time.monotonic()
        with db.open("rb") as stream:sha=hashlib.file_digest(stream,"sha256").hexdigest()
        print(f"[c5-v25] read-only SHA256={sha}, {time.monotonic()-begin:.1f}s",flush=True)
        conn=duckdb.connect(str(db),read_only=True)
        try:
            new,old=audit_population(args.selected_manifest,args.baseline_manifest,conn)
            reports=run(conn,new,old,str(db),sha)
        finally:conn.close()
        publish(args.output_dir,reports)
    except (OSError,ValueError,TypeError,KeyError,duckdb.Error,json.JSONDecodeError) as exc:
        print("ERROR V25:",exc,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
