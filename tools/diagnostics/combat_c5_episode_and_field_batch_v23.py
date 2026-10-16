"""V23: ONE run, THREE studies, on fixed V22 episodes + new games.

1. Correct unit of analysis: observed actors grouped by episode/window/game.
2. Pre-selected source stacks: compare own/foreign ownership and T endpoint.
3. Outcome-blind T-1 scan of unused public100 games for documented short
   stabilizer exposure, followed by T owner-current comparison ONLY AFTER
   all scan windows freeze.

All results observational. Historical public100 is NOT a new corpus.
No N+1 VCR, combat queue change, or Chunnel activation assertion.
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
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_chunnel_stabilization_provenance_v20 as v20
import combat_c5_firecloud_disjoint_validation_v13 as v13

SCHEMA="planets-lab.combat-c5-episode-field-discovery-batch.v23"
STATUS="V22_EPISODE_RECONCILIATION_AND_NEW_TMINUS1_FIELD_SCAN_OBSERVATIONAL"
V22_MANIFEST_BLOB="ef6ad48b2f8f8e0c054525c2bdc19780f465d92a"
V22_ACTORS_BLOB="77b76ac6726e8ad08ab505b7ac112c513aeb89e5"
V22_ESCORTS_BLOB="2174e1e7675296b229674e56b5f68d1f087908f1"
V22_STABILIZERS_BLOB="37a2924a705017fbca7b6cbf9177321beb6623a3"
GENERATION=v20.GENERATION
SHA256=v20.SHA256
MAX_GAMES=16
WINDOWS_PER_GAME=24
MIN_WINDOWS_PER_GAME=6
REPORTS=("episodes","ownership","field_scan")


def as_int(x:Any)->int|None:
    return x if type(x) is int else None


def pt(x:Any):
    return v20.position(x)


def pinned(path:Path,digest:str):
    data=path.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
    if sha!=digest:raise ValueError("published Git blob mismatch: "+str(path))
    value=json.loads(data)
    if not isinstance(value,dict):raise ValueError("source not JSON object")
    return value,data


def frozen_v22(manifest,actors,escorts,stabilizers,data):
    for name,report,digest in (
        ("actors",actors,V22_ACTORS_BLOB),
        ("escorts",escorts,V22_ESCORTS_BLOB),
        ("stabilizers",stabilizers,V22_STABILIZERS_BLOB)):
        if (report.get("schema")!="planets-lab.combat-c5-ruleaware-disjoint-batch.v22" or
            report.get("status")!="GAME_DISJOINT_TMINUS1_RULEAWARE_OBSERVATIONAL_NOT_ACTIVATION" or
            report.get("phase")!=name or
            report.get("source_db_sha256")!=SHA256 or
            report.get("Nplus1_VCR_used") is not False):
            raise ValueError("V22 report provenance changed: "+name)
        if manifest.get("phase_reports",{}).get(name,{}).get("sha256")!=hashlib.sha256(data[name]).hexdigest():
            raise ValueError("V22 manifest/report hash mismatch: "+name)
    if (manifest.get("status")!="V22_ALL_THREE_DISJOINT_HOLDOUT_REPORTS_COMPLETE" or
        manifest.get("all_three_completed") is not True or
        manifest.get("source_db_sha256")!=SHA256 or
        actors.get("summary",{}).get("Tminus1_candidate_actor_edges")!=57 or
        actors.get("summary",{}).get("Tminus1_short_field_witness_candidates")!=0 or
        actors.get("summary",{}).get("selected_windows")!=48 or
        escorts.get("summary",{}).get("Tminus1_preselected_actor_episodes")!=36 or
        escorts.get("summary",{}).get("Tminus1_source_ship_appearances")!=351 or
        stabilizers.get("summary",{}).get("Tminus1_Dungeon_appearances")!=6):
        raise ValueError("V22 fixed observational denominators changed")
    previous=actors.get("frozen_previous_research_games")
    selected=actors.get("metadata_selected_game_turns")
    if not isinstance(previous,list) or len(previous)!=73 or len(set(previous))!=73:
        raise ValueError("V22 previous game exclusion drift")
    if not isinstance(selected,list) or len(selected)!=48:
        raise ValueError("V22 frozen 48 windows missing")
    pairs={(w["game_id"],w["turn"]) for w in selected}
    games={g for g,_ in pairs}
    if len(pairs)!=48 or len(games)!=16 or games&set(previous):
        raise ValueError("V22 selected game/window identity drift")
    a=actors.get("actor_Tminus1_to_T_comparisons")
    e=escorts.get("episode_preselected_source_stacks")
    if not isinstance(a,list) or len(a)!=57 or not isinstance(e,list) or len(e)!=36:
        raise ValueError("V22 actor/stack row denominator drift")
    if sum(x.get("Tminus1_stack_size",0) for x in e)!=351:
        raise ValueError("V22 preselected stack denominator drift")
    return frozenset(games|set(previous))


def report_base(phase):
    return {
        "schema":SCHEMA,"status":STATUS,"phase":phase,
        "source_v22_manifest_git_blob_sha1":V22_MANIFEST_BLOB,
        "source_v22_actors_git_blob_sha1":V22_ACTORS_BLOB,
        "source_v22_escorts_git_blob_sha1":V22_ESCORTS_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "Host_chunnel_or_combat_predictions_promoted":0,
        "actual_Chunnel_activation_proven":False,
        "Nplus1_VCR_used":False,"same_historical_public100_corpus":True,
    }


def episode_reconciliation(actors):
    """One game/turn episode is not one ship. No confidence inflation."""
    rows=actors["actor_Tminus1_to_T_comparisons"]
    by_gate=defaultdict(Counter)
    by_cohort=defaultdict(Counter)
    by_window=defaultdict(list)
    by_game=defaultdict(Counter)
    for r in rows:
        g,t=r["game_id"],r["turn"]
        cohort=r["Tminus1_ruleaware_cohort"]
        by_cohort[cohort][r["T_actor_status"]]+=1
        if r["single_failing_gate"]:
            by_gate[r["single_failing_gate"]][r["T_actor_status"]]+=1
        by_window[g,t].append(r)
        by_game[g][cohort]+=1
    long=[r for r in rows if r["Tminus1_ruleaware_cohort"]=="LONG_CONVENTIONAL_PASS"]
    other=[r for r in rows if r["Tminus1_ruleaware_cohort"]=="OTHER_ONE_FAILED_TMINUS1_GATE"]
    if (len(long)!=36 or len(other)!=13 or
        any(r["T_actor_status"]!="T_ACTOR_AT_DISTINCT_TARGET" for r in long) or
        any(r["T_actor_status"]=="T_ACTOR_AT_DISTINCT_TARGET" for r in other)):
        raise ValueError("V22 positive/negative observational endpoint drift")
    episodes=[]
    for (g,t),members in sorted(by_window.items()):
        cohorts=Counter(m["Tminus1_ruleaware_cohort"] for m in members)
        episodes.append({
            "game_id":g,"turn":t,"candidate_actor_count":len(members),
            "Tminus1_cohort_counts":dict(sorted(cohorts.items())),
            "T_observed_status_counts":dict(sorted(Counter(
                m["T_actor_status"] for m in members).items())),
            "ship_count_not_independent_host_activation_count":True,
        })
    return {
        **report_base("episodes"),
        "summary":{
            "V22_frozen_games":16,"V22_frozen_windows":48,
            "Tminus1_actor_rows":len(rows),"Tminus1_active_episode_windows":len(episodes),
            "LONG_CONVENTIONAL_PASS_actor_rows":len(long),
            "LONG_CONVENTIONAL_PASS_episode_windows":len({
                (r["game_id"],r["turn"]) for r in long}),
            "LONG_CONVENTIONAL_PASS_distinct_games":len({r["game_id"] for r in long}),
            "OTHER_SINGLE_GATE_FAIL_actor_rows":len(other),
            "OTHER_SINGLE_GATE_FAIL_episode_windows":len({
                (r["game_id"],r["turn"]) for r in other}),
            "OTHER_SINGLE_GATE_FAIL_distinct_games":len({r["game_id"] for r in other}),
            "observed_endpoint_counts_by_gate":{
                k:dict(sorted(v.items())) for k,v in sorted(by_gate.items())},
            "observed_endpoint_counts_by_cohort":{
                k:dict(sorted(v.items())) for k,v in sorted(by_cohort.items())},
            "different_game_turn_episodes_not_independent_Host_mechanic_proofs":True,
        },
        "episode_windows":episodes,
        "by_game_cohort_counts":{str(g):dict(sorted(v.items())) for g,v in sorted(by_game.items())},
    }


def ownership_analysis(escorts,actors):
    """Check every published preselected co-located ship exactly once per episode."""
    episodes=escorts["episode_preselected_source_stacks"]
    orig={(a["game_id"],a["turn"],a["initiator_ship_id"],a["target_ship_id"]):a
          for a in actors["actor_Tminus1_to_T_comparisons"]}
    if len(orig)!=57:raise ValueError("V22 candidate actor identity duplicated")
    seen=set()
    per_episode=[]
    counters=defaultdict(Counter)
    for ep in episodes:
        key=(ep["game_id"],ep["turn"],ep["initiator_ship_id"],ep["target_ship_id"])
        if key in seen or key not in orig:raise ValueError("escort episode duplicate/unbacked")
        seen.add(key)
        if ep["Tminus1_ruleaware_cohort"]!="LONG_CONVENTIONAL_PASS":
            raise ValueError("V22 field-free escort cohort changed")
        members=ep["T_members"]
        if not isinstance(members,list) or len(members)!=ep["Tminus1_stack_size"]:
            raise ValueError("V22 escort stack count drift")
        if len({m["ship_id"] for m in members})!=len(members):
            raise ValueError("duplicate source member within one ship stack")
        same=[m for m in members if m["same_owner"]]
        foreign=[m for m in members if not m["same_owner"]]
        if not any(m["ship_id"]==ep["initiator_ship_id"] for m in same):
            raise ValueError("actor missing from own source stack")
        for m in members:
            group="SAME_OWNER" if m["same_owner"] else "DIFFERENT_OWNER"
            status=m["T_owner_current_status"]
            position_match=m["T_at_source_edge_target"]
            outcome=("AT_TARGET" if position_match is True else
                     "NOT_AT_TARGET" if position_match is False else
                     "ABSTAIN_OWNER_CURRENT")
            counters[group][outcome]+=1
            counters[group][status]+=1
        per_episode.append({
            "game_id":ep["game_id"],"turn":ep["turn"],
            "initiator_ship_id":ep["initiator_ship_id"],
            "target_ship_id":ep["target_ship_id"],
            "source_stack_size":len(members),
            "same_owner_ship_appearances":len(same),
            "different_owner_ship_appearances":len(foreign),
            "same_owner_at_target":sum(x["T_at_source_edge_target"] is True for x in same),
            "different_owner_at_target":sum(x["T_at_source_edge_target"] is True for x in foreign),
            "source_stack_foreign_ship_not_automatically_eligible_passenger":True,
            "actual_host_escort_mechanic_proven":False,
        })
    if len(per_episode)!=36 or sum(x["source_stack_size"] for x in per_episode)!=351:
        raise ValueError("V22 36/351 escort denominators changed")
    return {
        **report_base("ownership"),
        "summary":{
            "frozen_episode_count":len(per_episode),
            "frozen_source_ship_appearances":351,
            "episode_windows":len({(e["game_id"],e["turn"]) for e in per_episode}),
            "same_owner_appearances":sum(e["same_owner_ship_appearances"] for e in per_episode),
            "different_owner_appearances":sum(e["different_owner_ship_appearances"] for e in per_episode),
            "same_owner_at_frozen_target":sum(e["same_owner_at_target"] for e in per_episode),
            "different_owner_at_frozen_target":sum(e["different_owner_at_target"] for e in per_episode),
            "by_ownership_and_posthost_status":{
                k:dict(sorted(v.items())) for k,v in sorted(counters.items())},
            "same_source_shared_trajectory_does_not_prove_passenger_eligibility":True,
        },
        "per_episode_stacks":per_episode,
    }


def select_unused_metadata(metadata,excluded):
    by_game=defaultdict(set)
    for g,t in metadata:
        if (as_int(g) is None or as_int(t) is None or g<=0 or t<0):
            raise ValueError("source_members metadata invalid")
        by_game[g].add(t)
    options={}
    for g,turns in sorted(by_game.items()):
        if g in excluded:continue
        possible=sorted(t for t in turns if t>=2 and t-1 in turns)
        if len(possible)>=MIN_WINDOWS_PER_GAME:options[g]=possible
    games=sorted(options)
    if len(games)<3:raise ValueError("too few remaining unused games")
    if len(games)>MAX_GAMES:
        games=[games[i*(len(games)-1)//(MAX_GAMES-1)] for i in range(MAX_GAMES)]
    selected=[]
    for g in games:
        turns=options[g]
        n=min(len(turns),WINDOWS_PER_GAME)
        indices=[i*(len(turns)-1)//(n-1) for i in range(n)]
        if len(set(indices))!=n:raise ValueError("window quantile selection duplicated")
        selected.extend((g,turns[i]) for i in indices)
    if any(g in excluded for g,_ in selected) or len({g for g,_ in selected})!=len(games):
        raise ValueError("new game-disjoint selection failed")
    return tuple(sorted(selected))


def source_field_witness(edge,roster,gates,rules,races):
    src=pt(edge["source"])
    if src is None:raise ValueError("missing source point")
    radius_fields=[]
    for gate in gates:
        if not gate["archived_catalog_name_confirms_dungeon_stargate"]:
            continue
        radius=gate["documentation_field_radius_ly"]
        loc=pt(gate["Tminus1_position"]) if gate["Tminus1_position"] is not None else None
        if radius is None or loc is None:continue
        dist=hypot(src[0]-loc[0],src[1]-loc[1])
        if dist<=radius:radius_fields.append({
            "stargate_id":gate["ship_id"],
            "same_owner":gate["owner_id"]==edge["owner_id"],
            "distance_ly":round(dist,5),"radius_ly":radius,
            "Host_field_actually_active_proven":False,
        })
    short_format=[v for key,v in rules.items()
        if key.lower().replace("_","").replace("-","").endswith("shortformatrules")]
    if len(set(short_format))>1:raise ValueError("conflicting Short Format rules")
    short=short_format[0] if short_format else None
    return {
        "Tminus1_documented_field_witnesses":radius_fields,
        "Tminus1_short_format_cyborg_rule_explicit":short is True and races.get(edge["owner_id"])==6,
        "Tminus1_field_absence_not_proven":True,
    }


def pre_scan(conn,game,turn):
    snaps,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snaps,"ship"),turn-1)
    raw,reasons=v16.potential_stock_edges(roster)
    rules,races=v20.game_rules_markers(raws,game,turn)
    catalog=v20.v11.hull_name_inventory(raws)
    gates=v20.stabilizer_inventory(roster,catalog)
    short=[]
    long=[]
    for e in raw:
        if pt(e["source"])==pt(e["target"]):continue
        if e["cohort"]=="ALL_TMINUS1_GATES_PASS":
            # Every eligible long pair is a control; selected without T.
            long.append(e)
        elif e["single_failing_gate"]=="DISTANCE_BELOW_100_AT_TMINUS1" and e["Tminus1_distance_ly"]>=1:
            witness=source_field_witness(e,roster,gates,rules,races)
            qualifies=bool(witness["Tminus1_documented_field_witnesses"]) or witness[
                "Tminus1_short_format_cyborg_rule_explicit"]
            short.append({
                **e,**witness,
                "game_id":game,"turn":turn,
                "Tminus1_field_witness_status":(
                    "TMINUS1_DOCUMENTED_FIELD_WITNESS" if qualifies else
                    "ABSTAIN_NO_DOCUMENTED_FIELD_WITNESS"),
            })
    return {
        "game_id":game,"turn":turn,
        "Tminus1_short_distinct":short,
        "Tminus1_long_control":long,
        "Tminus1_rejections":reasons,
        "Tminus1_Dungeon_ship_count":len(gates),
        "Tminus1_all_cases_frozen_before_T":True,
    }


def compare_scan(pre,current):
    rows=[]
    for kind,items in (("SHORT",pre["Tminus1_short_distinct"]),
                       ("LONG",pre["Tminus1_long_control"])):
        for e in items:
            status,actor=v13._current_ship(current,e["initiator_ship_id"],e["owner_id"],56)
            pos=pt((actor.get("x"),actor.get("y"))) if actor else None
            dst,src=pt(e["target"]),pt(e["source"])
            label=status if actor is None else ("AT_DISTINCT_FROZEN_TARGET" if pos==dst else
                    "AT_FROZEN_SOURCE" if pos==src else "ELSEWHERE")
            rows.append({
                "game_id":pre["game_id"],"turn":pre["turn"],
                "initiator_ship_id":e["initiator_ship_id"],
                "target_ship_id":e["target_ship_id"],
                "owner_id":e["owner_id"],
                "Tminus1_cohort":kind,
                "Tminus1_short_field_status":e.get("Tminus1_field_witness_status"),
                "Tminus1_distance_ly":e["Tminus1_distance_ly"],
                "Tminus1_source":e["source"],"Tminus1_target":e["target"],
                "Tminus1_documented_field_witnesses":e.get("Tminus1_documented_field_witnesses",[]),
                "T_observation_status":label,
                "T_actor_owner_current_observation_status":status,
                "T_actor_position":list(pos) if pos is not None else None,
                "Host_Chunnel_activation_proven":False,
            })
    return rows


def field_discovery(conn,metadata,excluded):
    selected=select_unused_metadata(metadata,excluded)
    frozen={}
    errors=[]
    for i,(g,t) in enumerate(selected,1):
        print(f"[c5-v23/field] PRE [{i}/{len(selected)}] G{g} T{t}",flush=True)
        try:frozen[g,t]=pre_scan(conn,g,t)
        except (ValueError,TypeError,KeyError) as err:
            errors.append({"game_id":g,"turn":t,"phase":"PRE",
                           "abstain":f"{type(err).__name__}:{err}"})
            frozen[g,t]=None
    # HARD PRE-TO-POST BARRIER. No T archive queried above.
    evaluated=[]
    for i,(g,t) in enumerate(selected,1):
        print(f"[c5-v23/field] POST [{i}/{len(selected)}] G{g} T{t}",flush=True)
        if frozen[g,t] is None:continue
        if not frozen[g,t]["Tminus1_short_distinct"] and not frozen[g,t]["Tminus1_long_control"]:
            continue
        try:current=v9.after_owner_current(conn,game=g,turn=t)
        except (ValueError,TypeError,KeyError) as err:
            errors.append({"game_id":g,"turn":t,"phase":"POST",
                           "abstain":f"{type(err).__name__}:{err}"})
            continue
        evaluated.extend(compare_scan(frozen[g,t],current))
    short=[e for e in evaluated if e["Tminus1_cohort"]=="SHORT"]
    witness=[e for e in short if e["Tminus1_short_field_status"]=="TMINUS1_DOCUMENTED_FIELD_WITNESS"]
    long=[e for e in evaluated if e["Tminus1_cohort"]=="LONG"]
    pre_short=sum(len(x["Tminus1_short_distinct"]) for x in frozen.values() if x is not None)
    pre_long=sum(len(x["Tminus1_long_control"]) for x in frozen.values() if x is not None)
    counts=defaultdict(Counter)
    for e in evaluated:
        key=e["Tminus1_short_field_status"] if e["Tminus1_cohort"]=="SHORT" else "LONG"
        counts[key][e["T_observation_status"]]+=1
    return {
        **report_base("field_scan"),
        "summary":{
            "selected_previous_games_excluded":len(excluded),
            "metadata_selected_unused_games":len({g for g,_ in selected}),
            "metadata_selected_adjacent_windows":len(selected),
            "source_context_abstentions":sum(e["phase"]=="PRE" for e in errors),
            "post_context_abstentions":sum(e["phase"]=="POST" for e in errors),
            "Tminus1_distinct_short_candidate_edges":pre_short,
            "Tminus1_long_controls":pre_long,
            "posthost_compared_short_edges":len(short),
            "posthost_compared_long_controls":len(long),
            "short_with_Tminus1_documented_field_witness":len(witness),
            "short_witness_distinct_games":len({e["game_id"] for e in witness}),
            "short_witness_distinct_windows":len({
                (e["game_id"],e["turn"]) for e in witness}),
            "posthost_outcomes_by_frozen_cohort":{
                k:dict(sorted(v.items())) for k,v in sorted(counts.items())},
            "all_unused_game_Tminus1_freezes_before_first_T":True,
            "zero_exposure_not_rule_refutation":len(witness)==0,
            "Host_field_activation_or_Chunnel_proven":False,
            "no_new_public_corpus":True,
        },
        "metadata_selected_game_turns":[{"game_id":g,"turn":t} for g,t in selected],
        "posthost_short_and_long_comparisons":evaluated,
        "window_errors":errors,
        "boundary":(
            "The field scan is new game-disjoint windows but belongs to "
            "the same previously used public100 historical database. "
            "Select games and turns using metadata only, then freeze all "
            "Tminus1 records and qualifying gate candidates BEFORE "
            "reading T. Field source coverage and game flags at Tminus1 "
            "do not prove activation during Host. Missing fields or "
            "missing flags mean unknown, not absent. Comparisons are "
            "posthost observations, not a true phase trace. Results of "
            "individual ships in the same episode are correlated. "
            "No future VCR, canon Host activation or combat promotion."
        ),
    }


def publish(folder,reports):
    folder.mkdir(parents=True,exist_ok=True)
    index={}
    for phase,obj in zip(REPORTS,reports,strict=True):
        file=folder/(phase+".json")
        temp=file.with_suffix(".json.tmp")
        temp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(file)
        index[phase]={
            "file":file.name,
            "sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
            "summary":obj["summary"],
        }
        print("===== C5 V23",phase,"=====")
        print("status:",obj["status"])
        print("summary:",obj["summary"])
        print("output:",file)
    doc={
        "schema":SCHEMA,
        "status":"V23_EPISODES_OWNERSHIP_FIELD_SCAN_COMPLETE",
        "phase":"manifest","all_three_complete":len(index)==3,
        "source_v22_manifest_git_blob_sha1":V22_MANIFEST_BLOB,
        "source_db_sha256":SHA256,
        "phase_reports":index,
        "outcome_selected_field_candidates":False,
        "one_evidence_publication":True,
        "Host_activations_proven":False,
    }
    file=folder/"manifest.json"
    temp=file.with_suffix(".json.tmp")
    temp.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    temp.replace(file)
    print("===== C5 V23 ALL THREE REPORTS COMPLETE =====")
    print("status:",doc["status"])
    print("output:",file)


def main():
    p=argparse.ArgumentParser()
    for name in ("frozen-v22-manifest","frozen-v22-actors","frozen-v22-escorts",
                 "frozen-v22-stabilizers","corpus-db-root","output-dir"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    try:
        source={}
        payload={}
        names=(
            ("manifest",a.frozen_v22_manifest,V22_MANIFEST_BLOB),
            ("actors",a.frozen_v22_actors,V22_ACTORS_BLOB),
            ("escorts",a.frozen_v22_escorts,V22_ESCORTS_BLOB),
            ("stabilizers",a.frozen_v22_stabilizers,V22_STABILIZERS_BLOB),
        )
        for name,path,digest in names:
            source[name],payload[name]=pinned(path,digest)
        exclusions=frozen_v22(source["manifest"],source["actors"],source["escorts"],
                              source["stabilizers"],payload)
        a1=episode_reconciliation(source["actors"])
        a2=ownership_analysis(source["escorts"],source["actors"])
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned immutable public100 absent")
        print("[c5-v23] one pinned public100 SHA256 check",flush=True)
        ts=time.monotonic()
        with db.open("rb") as stream:sha=hashlib.file_digest(stream,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("pinned immutable public100 SHA256 mismatch")
        print(f"[c5-v23] read-only DB verified in {time.monotonic()-ts:.1f}s",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:
            metadata=conn.execute(
                "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
            ).fetchall()
            a3=field_discovery(conn,metadata,exclusions)
        finally:conn.close()
        publish(a.output_dir,(a1,a2,a3))
    except (OSError,ValueError,TypeError,KeyError,IndexError,json.JSONDecodeError) as exc:
        print("ERROR V23:",exc,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
