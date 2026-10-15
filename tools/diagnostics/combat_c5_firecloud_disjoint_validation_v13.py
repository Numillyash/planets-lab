"""V13: outcome-blind, game-disjoint Firecloud conditional passenger validation.

Only source_members game/turn metadata and T-1 owner-current snapshots
select cases, never a VCR or a ship position at turn T. All 36 T-1
windows and their predictions freeze BEFORE ANY T owner-current read.
This is historical observational comparison, not prospective validation,
proof of Chunnel execution or a canonical movement implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping,Sequence
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_chunnel_endpoint_screen_v11 as v11
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_posthost_endpoint_controls_v8 as v8

SCHEMA="planets-lab.combat-c5-firecloud-game-disjoint-validation.v13"
STATUS="OUTCOME_BLIND_TMINUS1_FIRECLOUD_PASSENGER_VALIDATION_OBSERVATIONAL"
V6_BLOB="51d21132e4db89511be59805ebe2be14014b3e7a"
V9_BLOB="4e7d707123586311456cc14e78ff774a851caa48"
GENERATION=v9.GENERATION
SHA256=v9.SHA256
FIRECLOUD_HULL_ID=56
SELECT_GAMES=12
WINDOWS_PER_GAME=3
NEGATIVE_CONTROLS_PER_WINDOW=10


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def coordinate(v:Any)->tuple[int,int]|None:
    return v11.coordinate(v)


def pinned_json(path:Path,expected:str)->dict[str,Any]:
    raw=path.read_bytes()
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if digest!=expected:raise ValueError("frozen source Git blob SHA1 changed: "+str(path))
    x=json.loads(raw)
    if not isinstance(x,dict):raise ValueError("frozen source root is not a JSON object")
    return x


def excluded_games(v6:Mapping[str,Any],v9report:Mapping[str,Any])->frozenset[int]:
    if (v6.get("schema")!="planets-lab.combat-c5-tminus1-ingress-residence.v6"
        or v6.get("source_db_sha256")!=SHA256
        or v6.get("summary",{}).get("frozen_sites")!=27):
        raise ValueError("frozen V6 identity/census changed")
    prior=v9.c5_games(v6)
    if (v9report.get("schema")!=v9.SCHEMA or v9report.get("status")!=v9.STATUS
        or v9report.get("source_db_sha256")!=SHA256
        or v9report.get("source_v6_git_blob_sha1")!=V6_BLOB):
        raise ValueError("V9 source identity/provenance changed")
    summary=v9report.get("summary")
    if (not isinstance(summary,Mapping)
        or summary.get("selected_games")!=8
        or summary.get("selected_windows")!=16
        or summary.get("selected_games_overlap_with_C5")!=0
        or summary.get("Nplus1_VCR_read") is not False):
        raise ValueError("V9 source selection changed")
    selector=v9report.get("frozen_metadata_selection")
    if not isinstance(selector,Mapping) or selector.get("no_VCR_selection") is not True:
        raise ValueError("V9 metadata selection unavailable")
    entries=selector.get("selected_game_turns")
    if not isinstance(entries,list) or len(entries)!=16:
        raise ValueError("V9 original selected windows unavailable")
    windows=set()
    games=set()
    for item in entries:
        if not isinstance(item,Mapping):
            raise ValueError("V9 window invalid")
        g,t=integer(item.get("game_id")),integer(item.get("turn"))
        if g is None or t is None or g<=0 or t<=1 or (g,t) in windows:
            raise ValueError("V9 duplicate or invalid window")
        windows.add((g,t));games.add(g)
    if len(games)!=8 or not games.isdisjoint(prior):
        raise ValueError("V9 game exclusion corrupted")
    return frozenset(prior|games)


def choose_windows(metadata:Sequence[tuple[Any,Any]], excluded:frozenset[int],
                   *,game_count:int=SELECT_GAMES)->tuple[tuple[int,int],...]:
    """Fixed metadata-only sample, no ship, VCR, minefield or outcome fields."""
    if game_count<2:raise ValueError("invalid game-count protocol")
    by_game=defaultdict(set)
    for game,turn in metadata:
        if integer(game) is None or game<=0 or integer(turn) is None or turn<0:
            raise ValueError("invalid source_members metadata")
        by_game[game].add(turn)
    eligible={}
    for g,turns in sorted(by_game.items()):
        if g in excluded:continue
        adjacent=sorted(t for t in turns if t>=2 and t-1 in turns)
        if len(adjacent)>=WINDOWS_PER_GAME:eligible[g]=adjacent
    population=sorted(eligible)
    if len(population)<game_count:
        raise ValueError("insufficient pre-registered game-disjoint metadata games")
    picked=[population[i*(len(population)-1)//(game_count-1)] for i in range(game_count)]
    if len(set(picked))!=game_count:raise ValueError("selected games not unique")
    selected=[]
    for g in picked:
        turns=eligible[g]
        # 1/4, 1/2, 3/4 deterministic metadata quantiles.
        indices=[(len(turns)-1)*i//4 for i in (1,2,3)]
        if len(set(indices))!=3:indices=[0,len(turns)//2,len(turns)-1]
        if len(set(indices))!=3:raise ValueError("insufficient distinct game-turn samples")
        selected.extend((g,turns[i]) for i in indices)
    return tuple(sorted(selected))


def eligible_edges(rows:Mapping[int,tuple[int,Mapping[str,Any]]],
                   named_hulls:Mapping[int,str]):
    """Necessary *stock Firecloud* gates, before any endpoint outcome."""
    raw_edges,raw_reasons=v11.screen_tminus1_edges(rows,named_hulls)
    reasons=Counter(raw_reasons)
    candidates=[]
    for edge in raw_edges:
        if (integer(edge["initiator_hull_id"])!=FIRECLOUD_HULL_ID or
            integer(edge["target_hull_id"])!=FIRECLOUD_HULL_ID):
            reasons["NON_STOCK_FIRECLOUD_NUMERIC_FC_EDGE"]+=1
            continue
        initiator,target=edge["initiator_ship_id"],edge["target_ship_id"]
        if initiator not in rows or target not in rows:
            raise ValueError("unbacked frozen source edge")
        actor_owner,actor=rows[initiator]
        target_owner,receiver=rows[target]
        if actor_owner!=target_owner or actor_owner!=edge["initiator_owner_id"]:
            raise ValueError("Tminus1 Firecloud owner drift")
        # Preserve a deliberately narrow scope where initiator is not
        # itself moving normally, so pre-Chunnel source is T-1 position.
        if integer(actor.get("warp"))!=0:
            reasons["INITIATOR_NOT_STATIONARY_WARP0"]+=1
            continue
        if edge["tow_order_on_initiator_or_target"] is not False:
            reasons["TOW_REQUEST_ENDPOINT_UNRESOLVED"]+=1
            continue
        if (integer(receiver.get("warp"))!=0 or
            coordinate(edge["initiator_start"]) is None or
            coordinate(edge["target_Tminus1_position"]) is None):
            raise ValueError("Tminus1 static Firecloud candidate drift")
        candidates.append({
            "initiator_ship_id":initiator,"target_ship_id":target,
            "owner_id":actor_owner,
            "initiator_Tminus1_source":edge["initiator_start"],
            "target_Tminus1_destination":edge["target_Tminus1_position"],
            "initiator_Tminus1_fuel":edge["initiator_Tminus1_fuel"],
            "target_Tminus1_fuel":edge["target_Tminus1_fuel"],
            "initiator_Tminus1_warp":0,
            "stock_hulls_verified_from_Tminus1":True,
            "execution_proven":False,
        })
    # Resolve numeric-code aliases fail-closed, before looking at T.
    initiator_counts=Counter(e["initiator_ship_id"] for e in candidates)
    ambiguous={sid for sid,c in initiator_counts.items() if c>1}
    reasons["AMBIGUOUS_TARGET_IDS_ABSTAIN"]+=sum(
        1 for e in candidates if e["initiator_ship_id"] in ambiguous)
    return ([e for e in candidates if e["initiator_ship_id"] not in ambiguous],
            dict(sorted(reasons.items())))


def freeze_window(game:int,turn:int,snapshots,raw_payloads):
    """T-1 only. Both passengers and controls selected before T exposure."""
    rows=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1)
    named=v11.hull_name_inventory(raw_payloads)
    edges,reasons=eligible_edges(rows,named)
    forecasts,excluded,total=v9.forecast_pre_window(game,turn,snapshots,raw_payloads)
    if total!=len(rows):
        raise ValueError("Tminus1 independent forecast population changed")
    by_id={x["ship_id"]:x for x in forecasts}
    if len(by_id)!=len(forecasts):
        raise ValueError("Tminus1 forecast contained duplicate ship IDs")
    records=[]
    actor_sources={tuple(e["initiator_Tminus1_source"]) for e in edges}
    target_destinations={tuple(e["target_Tminus1_destination"]) for e in edges}
    for edge in edges:
        source=tuple(edge["initiator_Tminus1_source"])
        predicted=[
            f for f in forecasts if f["Tminus1_owner_id"]==edge["owner_id"]
            and f["ship_id"] not in (edge["initiator_ship_id"],edge["target_ship_id"])
            and coordinate(f["conditional_or_model_endpoint"])==source
        ]
        passengers=[]
        for f in sorted(predicted,key=lambda x:x["ship_id"]):
            # A mine-risk forecast is only conditional on *no* mine hit.
            passengers.append({
                "ship_id":f["ship_id"],"Tminus1_owner_id":f["Tminus1_owner_id"],
                "Tminus1_hull_id":f["Tminus1_hull_id"],
                "Tminus1_model_cohort":f["cohort"],
                "conditional_on_no_mine_interference":f["conditional_no_mine_only"],
                "Tminus1_model_prechunnel_endpoint":f["conditional_or_model_endpoint"],
                "Tminus1_predicted_transport_destination":edge["target_Tminus1_destination"],
                "Tminus1_inferred_actual_arrival":False,
            })
        records.append({**edge,"Tminus1_passenger_candidates":passengers})
    normal_controls=[
        f for f in forecasts
        if f["cohort"]==v9.NORMAL
        and coordinate(f["conditional_or_model_endpoint"]) not in actor_sources
        and coordinate(f["conditional_or_model_endpoint"]) not in target_destinations
        and f["ship_id"] not in {e["initiator_ship_id"] for e in edges}
        and f["ship_id"] not in {e["target_ship_id"] for e in edges}
    ]
    controls=[{
        "ship_id":f["ship_id"],"Tminus1_owner_id":f["Tminus1_owner_id"],
        "Tminus1_hull_id":f["Tminus1_hull_id"],
        "Tminus1_model_endpoint":f["conditional_or_model_endpoint"],
        "selection_did_not_use_T_archive":True,
    } for f in sorted(normal_controls,key=lambda x:x["ship_id"])[:NEGATIVE_CONTROLS_PER_WINDOW]]
    return {
        "game_id":game,"turn":turn,"status":"TMINUS1_PREOUTCOME_FROZEN",
        "Tminus1_owner_current_ship_count":total,
        "Tminus1_normal_forecasts":len(forecasts),
        "Tminus1_rejection_counts":reasons,
        "Tminus1_movement_exclusions":dict(sorted(excluded.items())),
        "Tminus1_Firecloud_source_target_edges":records,
        "Tminus1_negative_normal_controls":controls,
        "T_archive_not_read_for_selection":True,
    }


def _current_ship(records:Mapping[int,Any],ship_id:int,owner:int,
                  hull:int|None=None):
    row=records.get(ship_id)
    if row is None or not isinstance(row[1],Mapping):
        return "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE",None
    obs_owner,raw=row
    if obs_owner!=owner:return "ABSTAIN_T_OWNER_DRIFT",None
    actual_hull=integer(raw.get("hullid",raw.get("hull_id")))
    if hull is not None and actual_hull!=hull:
        return "ABSTAIN_T_HULL_IDENTITY_DRIFT",None
    actual=coordinate((raw.get("x"),raw.get("y")))
    if actual is None:return "ABSTAIN_T_POSITION_UNAVAILABLE",None
    return "OWNER_CURRENT_T_OBSERVED",raw


def evaluate_window(frozen:Mapping[str,Any],after:Mapping[int,Any]):
    """T is only a comparator; never reselect or modify frozen subjects."""
    edges_out=[]
    for edge in frozen["Tminus1_Firecloud_source_target_edges"]:
        owner=edge["owner_id"]
        a_id,t_id=edge["initiator_ship_id"],edge["target_ship_id"]
        a_state,a=_current_ship(after,a_id,owner,FIRECLOUD_HULL_ID)
        t_state,t=_current_ship(after,t_id,owner,FIRECLOUD_HULL_ID)
        dest=coordinate(edge["target_Tminus1_destination"])
        actor_endpoint=coordinate((a.get("x"),a.get("y"))) if a else None
        target_endpoint=coordinate((t.get("x"),t.get("y"))) if t else None
        after_fuel=integer(a.get("neutronium")) if a else None
        delta=edge["initiator_Tminus1_fuel"]-after_fuel if after_fuel is not None else None
        actor_match=actor_endpoint==dest if actor_endpoint is not None else None
        target_match=target_endpoint==dest if target_endpoint is not None else None
        fuel50=delta==50 if delta is not None else None
        # Strictly an observable signature, not proof of mechanics.
        supportive=(actor_match is True and target_match is True and fuel50 is True)
        evaluated=[]
        for p in edge["Tminus1_passenger_candidates"]:
            shipstatus,ship=_current_ship(after,p["ship_id"],p["Tminus1_owner_id"],
                                          p["Tminus1_hull_id"])
            actual=coordinate((ship.get("x"),ship.get("y"))) if ship else None
            hit=actual==dest if actual is not None else None
            status=(shipstatus if ship is None else
                "T_PASSENGER_AT_PRESELECTED_TARGET" if hit
                else "T_PASSENGER_ELSEWHERE")
            evaluated.append({
                **p,"T_owner_current_position":list(actual) if actual else None,
                "T_endpoint_matches_preselected_target":hit,
                "T_observation_status":status,
                "T_actor_target_50KT_signature_present":supportive,
                "Chunnel_transport_proven":False,
            })
        edges_out.append({
            "game_id":frozen["game_id"],"turn":frozen["turn"],
            **{k:v for k,v in edge.items() if k!="Tminus1_passenger_candidates"},
            "T_actor_observation_status":a_state,
            "T_target_observation_status":t_state,
            "T_actor_position":list(actor_endpoint) if actor_endpoint else None,
            "T_target_position":list(target_endpoint) if target_endpoint else None,
            "T_actor_at_preselected_target":actor_match,
            "T_target_at_preselected_target":target_match,
            "T_actor_fuel_delta_KT":delta,
            "T_actor_fuel_delta_50KT":fuel50,
            "T_actor_target_observational_signature":(
                "SUPPORTIVE_TARGET_AND_50KT_CONCORDANCE" if supportive else
                "OBSERVATIONAL_SIGNATURE_NOT_CONFIRMED"),
            "posthost_passengers":evaluated,
            "Chunnel_executed_proven":False,
        })
    controls=[]
    for c in frozen["Tminus1_negative_normal_controls"]:
        status,ship=_current_ship(after,c["ship_id"],c["Tminus1_owner_id"],
                                  c["Tminus1_hull_id"])
        actual=coordinate((ship.get("x"),ship.get("y"))) if ship else None
        baseline=coordinate(c["Tminus1_model_endpoint"])
        controls.append({
            **c,"T_owner_current_position":list(actual) if actual else None,
            "T_model_endpoint_match":actual==baseline if actual else None,
            "T_observation_status":status,
        })
    return {
        "game_id":frozen["game_id"],"turn":frozen["turn"],
        "Tminus1_Firecloud_edge_observations":edges_out,
        "Tminus1_negative_normal_control_observations":controls,
        "T_observed_only_after_all_pre_windows_frozen":True,
    }


def build_report(conn:Any,v6:Mapping[str,Any],v9report:Mapping[str,Any]):
    excluded=excluded_games(v6,v9report)
    metadata=conn.execute(
        "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
    ).fetchall()
    selected=choose_windows(metadata,excluded)
    if len(selected)!=SELECT_GAMES*WINDOWS_PER_GAME or len(set(g for g,_ in selected))!=SELECT_GAMES:
        raise ValueError("game-disjoint protocol selection incomplete")
    print("[c5-v13] locked metadata-only windows:",selected,flush=True)
    frozen={}
    errors=[]
    for i,(game,turn) in enumerate(selected,1):
        print(f"[c5-v13] PRE [{i}/{len(selected)}] G{game} T{turn}",flush=True)
        try:
            snaps,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
            frozen[game,turn]=freeze_window(game,turn,snaps,raws)
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({"game_id":game,"turn":turn,"phase":"Tminus1",
                           "status":"ABSTAIN_PRE_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
            frozen[game,turn]=None
    # Strict two-phase barrier. No T archive was read before this point.
    results=[]
    for i,(game,turn) in enumerate(selected,1):
        print(f"[c5-v13] POST [{i}/{len(selected)}] G{game} T{turn}",flush=True)
        if frozen[game,turn] is None:continue
        try:
            current=v9.after_owner_current(conn,game=game,turn=turn)
            results.append(evaluate_window(frozen[game,turn],current))
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({"game_id":game,"turn":turn,"phase":"posthost",
                           "status":"ABSTAIN_POST_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
    if len(results)<4:raise ValueError("insufficient frozen Tminus1 windows for observational report")
    edges=[e for w in results for e in w["Tminus1_Firecloud_edge_observations"]]
    passengers=[p for e in edges for p in e["posthost_passengers"]]
    controls=[c for w in results for c in w["Tminus1_negative_normal_control_observations"]]
    signature=Counter(e["T_actor_target_observational_signature"] for e in edges)
    statuses=Counter(p["T_observation_status"] for p in passengers)
    control_status=Counter(
        "MATCH" if c["T_model_endpoint_match"] is True else
        "MISMATCH" if c["T_model_endpoint_match"] is False else
        c["T_observation_status"] for c in controls)
    by_game=defaultdict(Counter)
    for e in edges:
        # Each edge is one episode, passenger counts are not independent.
        game=e["game_id"]
        by_game[str(game)]["candidate_edges"]+=1
        by_game[str(game)]["passenger_candidates"]+=len(e["posthost_passengers"])
        if e["T_actor_target_observational_signature"]=="SUPPORTIVE_TARGET_AND_50KT_CONCORDANCE":
            by_game[str(game)]["actor_target_50KT_signatures"]+=1
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v6_git_blob_sha1":V6_BLOB,"source_v9_git_blob_sha1":V9_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "source_metadata_selection":{
            "method":"fixed 12 excluded-game metadata-spaced games x 3 adjacent turn windows; no VCR or T outcome selection",
            "excluded_source_game_ids":sorted(excluded),
            "selected_windows":[{"game_id":g,"turn":t} for g,t in selected],
            "no_posthost_T_or_VCR_in_selection":True,
            "same_public100_not_newly_collected":True,
        },
        "summary":{
            "selected_game_count":SELECT_GAMES,
            "selected_window_count":len(selected),
            "game_overlap_with_V6_and_V9":len({g for g,_ in selected}&excluded),
            "pre_or_post_context_errors":len(errors),
            "post_context_evaluated_windows":len(results),
            "Tminus1_stock_firecloud_edges":len(edges),
            "Tminus1_candidate_passenger_appearances":len(passengers),
            "distinct_candidate_game_turn_exposures":len({
                (w["game_id"],w["turn"]) for w in results if w["Tminus1_Firecloud_edge_observations"]}),
            "actor_target_observational_signatures":dict(sorted(signature.items())),
            "passenger_posthost_observation_counts":dict(sorted(statuses.items())),
            "negative_normal_control_counts":dict(sorted(control_status.items())),
            "new_Host_position_or_combat_predictions_promoted":0,
            "Nplus1_VCR_used":False,
            "Chunnel_execution_proven":False,
            "independent_new_corpus":False,
        },
        "per_game_edge_counts":{g:dict(sorted(v.items())) for g,v in sorted(by_game.items())},
        "windows":results,
        "window_errors":errors,
        "boundary":(
            "Games and turns selected from metadata independent of all VCRs and "
            "T outcomes, excluding every frozen V6 C5 game and V9 validation game. "
            "Tminus1 stock Firecloud candidate edges, normal route passenger "
            "hypotheses and ordinary negative controls are ALL frozen before T "
            "archive observations. Only stationary Warp0 initiators without Tminus1 "
            "tow requests and unambiguous targets are in scope. A mine-risk "
            "passenger's arrival is conditional on no mine hit; post-Host T may "
            "also reflect combat, chunnel, fuel transfer, refuelling or loss. "
            "Even an actor-at-target and 50KT drop plus passenger match is "
            "observational concordance, not independently executed Host phase "
            "proof. No VCR, inferred combat site or causal mine-RNG rule is "
            "used. SAME historical public100 corpus is not a new independent "
            "collection; this is game-disjoint diagnostic validation, not "
            "prospective deployment."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v6",type=Path,required=True)
    p.add_argument("--frozen-v9",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        v6=pinned_json(args.frozen_v6,V6_BLOB)
        v9report=pinned_json(args.frozen_v9,V9_BLOB)
        excluded_games(v6,v9report)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 database missing")
        print("[c5-v13] verify public100 SHA256 once",flush=True)
        started=time.monotonic()
        with db.open("rb") as fd:digest=hashlib.file_digest(fd,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("public100 checksum drift")
        print(f"[c5-v13] SHA verified in {time.monotonic()-started:.1f}s",flush=True)
        connection,_=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:result=build_report(connection,v6,v9report)
        finally:connection.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temporary=args.output.with_suffix(args.output.suffix+".tmp")
        temporary.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temporary.replace(args.output)
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 GAME DISJOINT FIRECLOUD PASSENGER VALIDATION V13 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",args.output)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
