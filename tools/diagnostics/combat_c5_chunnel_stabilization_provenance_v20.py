"""V20: prove or abstain on T-1 stabilizer provenance for V17 short edges.

Official rules: default Chunnel minimum 100 LY; Short Format Cyborg
Chunnel Stabilization Field reduces it to 1 LY, as does the Dungeon
Class Stargate field, radius 100+50*engine tech (150..550 LY).
Neither rule is inferred merely because a short-edge actor later moves.

All 13 published V17 short-distance actor edges and their nine windows
are frozen and T-1 snapshots examined BEFORE any T owner-current reads.
Published posthost T is only a diagnostic comparator, not selection.
Never emit player names, private game descriptions or raw friendly codes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from math import hypot
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for parent in (ROOT/"src",Path(__file__).resolve().parent):
    if str(parent) not in sys.path:sys.path.insert(0,str(parent))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_chunnel_chain_graph_audit_v19 as v19
import combat_c5_disjoint_discriminative_chunnel_gates_v17 as v17
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_chunnel_endpoint_screen_v11 as v11

SCHEMA="planets-lab.combat-c5-chunnel-stabilization-provenance.v20"
STATUS="V17_SHORT_EDGES_TMINUS1_STABILIZATION_COVERAGE_OBSERVATIONAL"
V17_BLOB=v19.V17_BLOB
V19_BLOB="572d14d348235694402148273c7085d212301eac"
GENERATION=v19.GENERATION
SHA256=v19.SHA256
SHORT_GATE="DISTANCE_BELOW_100_AT_TMINUS1"
SHORT_COUNT=13
WINDOW_COUNT=9
DUNGEON_HULL=108


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def position(x:Any)->tuple[int,int]|None:
    return v19.xy(x)


def frozen_file(path:Path,digest:str):
    raw=path.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if sha!=digest:raise ValueError("frozen published Git blob drift: "+str(path))
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError("source report malformed")
    return value


def preselect(v17report:Mapping[str,Any],v19report:Mapping[str,Any]):
    if (v17report.get("schema")!=v17.SCHEMA or
        v17report.get("status")!=v17.STATUS or
        v17report.get("source_db_sha256")!=SHA256 or
        v17report.get("summary",{}).get("candidate_stock_firecloud_edges")!=113 or
        v17report.get("summary",{}).get("selected_window_count")!=48 or
        v17report.get("summary",{}).get("Nplus1_VCR_used") is not False):
        raise ValueError("V17 113/48 evidence provenance changed")
    if (v19report.get("schema")!=v19.SCHEMA or
        v19report.get("status")!=v19.STATUS or
        v19report.get("source_v17_git_blob_sha1")!=V17_BLOB or
        v19report.get("source_db_sha256")!=SHA256 or
        v19report.get("summary",{}).get("Tminus1_eligible_short_to_long_graph_chains")!=2 or
        v19report.get("summary",{}).get("G467386_T75_467_to_80_has_outgoing_eligible_long_edge") is not False or
        v19report.get("summary",{}).get("Nplus1_VCR_used") is not False):
        raise ValueError("V19 frozen chain evidence changed")
    windows=v17report.get("windows")
    if not isinstance(windows,list) or len(windows)!=48:raise ValueError("V17 windows truncated")
    short={}
    for w in windows:
        for edge in w["edges"]:
            if edge.get("single_failing_gate")!=SHORT_GATE:continue
            key=(w["game_id"],w["turn"],edge["initiator_ship_id"],edge["target_ship_id"])
            if (key in short or edge.get("cohort")!="ONE_TMINUS1_GATE_FAILS" or
                edge.get("Host_Chunnel_activation_or_inactivation_proven") is not False or
                position(edge.get("source")) is None or
                position(edge.get("target")) is None):
                raise ValueError("V17 short edge identity corrupted")
            short[key]=edge
    selected=tuple(sorted({key[:2] for key in short}))
    distinct=[x for x in short.values() if x["Tminus1_source_differs_from_target"]]
    coloc=[x for x in short.values() if not x["Tminus1_source_differs_from_target"]]
    if (len(short)!=SHORT_COUNT or len(selected)!=WINDOW_COUNT or
        len(distinct)!=4 or len(coloc)!=9 or
        (467386,75,467,80) not in short):
        raise ValueError("V17 frozen 13/9/4/9 short cohort changed")
    return short,selected


def game_rules_markers(raws, game:int, turn:int):
    """Keep only mechanical scalar hints; no free-text or private material."""
    markers=defaultdict(set)
    races=defaultdict(set)
    for payload in raws:
        g=payload.get("game")
        if not isinstance(g,Mapping) or integer(g.get("id"))!=game or integer(g.get("turn"))!=turn-1:
            raise ValueError("Tminus1 raw game/turn mismatch")
        for root in ("settings","game"):
            section=payload.get(root)
            if section is None:continue
            if not isinstance(section,Mapping):
                raise ValueError("game metadata not an object")
            for k,v in section.items():
                if not isinstance(k,str):continue
                lowered=k.lower().replace("_","").replace("-","")
                if not any(t in lowered for t in ("shortformat","shortgame","chunnelstabil","shortformatrules","leagueshort")):
                    continue
                if type(v) is bool or (type(v) is int and v in (0,1)):
                    markers[root+"."+k].add(bool(v))
                elif type(v) is str and v.casefold().strip() in ("true","false","enabled","disabled"):
                    markers[root+"."+k].add(v.casefold().strip() in ("true","enabled"))
        for k in ("gametype","scenarioid","maptype","isacademy"):
            val=g.get(k)
            if type(val) in (int,bool):markers["game."+k].add(val)
        settings=payload.get("settings")
        if isinstance(settings,Mapping):
            for k in ("shortdescription","gametype","shortformatrules"):
                val=settings.get(k)
                if k=="gametype" and type(val) is int:
                    markers["settings.gametype"].add(val)
                elif k=="shortformatrules" and type(val) in (bool,int) and val in (False,True,0,1):
                    markers["settings.shortformatrules"].add(bool(val))
        players=payload.get("players")
        if isinstance(players,list):
            for player in players:
                if not isinstance(player,Mapping):continue
                sid,race=integer(player.get("id")),integer(player.get("raceid"))
                if sid is not None and race is not None:races[sid].add(race)
        player=payload.get("player")
        if isinstance(player,Mapping):
            sid,race=integer(player.get("id")),integer(player.get("raceid"))
            if sid is not None and race is not None:races[sid].add(race)
    if any(len(vals)>1 for vals in markers.values()) or any(len(vals)>1 for vals in races.values()):
        raise ValueError("conflicting Tminus1 rule/race metadata across perspectives")
    return {k:next(iter(v)) for k,v in sorted(markers.items())},{
        k:next(iter(v)) for k,v in sorted(races.items())}


def stabilizer_inventory(roster, hull_names:Mapping[int,str]):
    """Candidates only. Hull and engine ID are NOT proof that field was active."""
    name=hull_names.get(DUNGEON_HULL,"")
    if not isinstance(name,str):raise ValueError("bad archived hull name")
    valid_hull="dungeon" in name.casefold() and "stargate" in name.casefold()
    candidates=[]
    for ship_id,(owner,raw) in sorted(roster.items()):
        hull=integer(raw.get("hullid",raw.get("hull_id")))
        if hull!=DUNGEON_HULL:continue
        loc=position((raw.get("x"),raw.get("y")))
        engine=integer(raw.get("engineid",raw.get("engine_id")))
        possible_radius=100+50*engine if engine is not None and 1<=engine<=9 else None
        candidates.append({
            "ship_id":ship_id,"owner_id":owner,
            "hull_id":hull,"archived_catalog_name_confirms_dungeon_stargate":valid_hull,
            "Tminus1_position":list(loc) if loc else None,
            "Tminus1_engine_id":engine,
            "documentation_field_radius_ly":possible_radius if valid_hull else None,
            "Tminus1_field_activation_verified":False,
        })
    return candidates


def freeze_window(conn:Any,game:int,turn:int,selected):
    snaps,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snaps,"ship"),turn-1)
    rules,races=game_rules_markers(raws,game,turn)
    catalog=v11.hull_name_inventory(raws)
    stabilizers=stabilizer_inventory(roster,catalog)
    edges=[]
    for key,case in sorted(selected.items()):
        if key[:2]!=(game,turn):continue
        actor,target,owner=(case[x] for x in ("initiator_ship_id","target_ship_id","owner_id"))
        for sid,p in ((actor,position(case["source"])),(target,position(case["target"]))):
            own=roster.get(sid)
            if own is None or own[0]!=owner or position((own[1].get("x"),own[1].get("y")))!=p or integer(own[1].get("hullid"))!=56:
                raise ValueError("V17 Tminus1 actor/target context drift")
        start=position(case["source"])
        feasible=[]
        unknown=[]
        for s in stabilizers:
            if not s["archived_catalog_name_confirms_dungeon_stargate"]:continue
            loc=position(s["Tminus1_position"]) if s["Tminus1_position"] is not None else None
            radius=s["documentation_field_radius_ly"]
            if loc is None or radius is None:
                unknown.append(s["ship_id"])
                continue
            distance=hypot(start[0]-loc[0],start[1]-loc[1])
            if distance<=radius:
                feasible.append({
                    "stargate_ship_id":s["ship_id"],
                    "stargate_owner_id":s["owner_id"],
                    "distance_from_actor_ly":round(distance,5),
                    "radius_from_engine_ly":radius,
                    "same_owner":s["owner_id"]==owner,
                    "field_active_at_Chunnel_phase_proven":False,
                })
        shortflag=[bool(v) for k,v in rules.items() if k.lower().replace("_","").endswith("shortformatrules")]
        if len(set(shortflag))>1:raise ValueError("conflicting short-format rule flags")
        explicit_flag=shortflag[0] if shortflag else None
        race=races.get(owner)
        field_status=(
            "TMINUS1_EXPLICIT_SHORT_FORMAT_FIELD_FLAG_FOR_CYBORG" if explicit_flag is True and race==6
            else "TMINUS1_STARGATE_FIELD_POSSIBLE_WITHIN_DOCUMENTED_RADIUS" if feasible
            else "TMINUS1_SHORT_FORMAT_FLAG_TRUE_OTHER_RACE" if explicit_flag is True
            else "ABSTAIN_STABILIZATION_FIELD_STATE_UNPROVEN")
        edges.append({
            "game_id":game,"turn":turn,"initiator_ship_id":actor,
            "target_ship_id":target,"owner_id":owner,
            "owner_Tminus1_race_id":race,
            "Tminus1_source":case["source"],"Tminus1_target":case["target"],
            "Tminus1_distance_ly":case["Tminus1_distance_ly"],
            "Tminus1_source_target_distinct":case["Tminus1_source_differs_from_target"],
            "Tminus1_documented_stabilizer_coverage_candidates":feasible,
            "Tminus1_stabilizer_missing_position_or_engine_candidates":unknown,
            "Tminus1_explicit_short_format_rule_flag":explicit_flag,
            "Tminus1_stabilization_coverage_status":field_status,
            "V17_observational_after_T_status_not_used_to_select":True,
        })
    return {
        "game_id":game,"turn":turn,
        "Tminus1_safe_game_rule_markers":rules,
        "Tminus1_stock_dungeon_stargate_inventory":stabilizers,
        "Tminus1_short_edge_features":edges,
        "Tminus1_all_features_frozen_before_posthost_T":True,
    }


def compare_posthost(frozen,after,original):
    reports=[]
    for edge in frozen["Tminus1_short_edge_features"]:
        key=(edge["game_id"],edge["turn"],edge["initiator_ship_id"],edge["target_ship_id"])
        case=original[key]
        status,row=v19.v16.v15.get_observation(after,edge["initiator_ship_id"],edge["owner_id"],56)
        actual=position((row.get("x"),row.get("y"))) if row else None
        expected=position(case["T_actor_position"]) if case.get("T_actor_position") is not None else None
        if case["T_actor_status"].startswith("ABSTAIN"):
            if row is not None:raise ValueError("V17 T actor abstention no longer reproducible")
        elif actual!=expected:
            raise ValueError("V17 short-edge final T actor coordinate drift")
        reports.append({
            **edge,
            "V17_frozen_posthost_actor_status":case["T_actor_status"],
            "reverified_T_owner_current_status":status,
            "T_reverified_actor_position":list(actual) if actual else None,
            "T_actor_at_distinct_Tminus1_target":actual==position(edge["Tminus1_target"]) if actual is not None and edge["Tminus1_source_target_distinct"] else None,
            "actual_host_stabilization_or_short_Chunnel_proven":False,
        })
    return reports


def build_report(conn,v17src,v19src):
    cases,windows=preselect(v17src,v19src)
    frozen={}
    for i,(game,turn) in enumerate(windows,1):
        print(f"[c5-v20] PRE [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        frozen[game,turn]=freeze_window(conn,game,turn,cases)
    # HARD BARRIER: ALL nine Tminus1 archives frozen before any T archive reads.
    after=[]
    for i,(game,turn) in enumerate(windows,1):
        print(f"[c5-v20] POST [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        current=v9.after_owner_current(conn,game=game,turn=turn)
        after.extend(compare_posthost(frozen[game,turn],current,cases))
    if len(after)!=SHORT_COUNT:raise ValueError("V17 short cohort incomplete")
    candidate_counts=Counter(x["Tminus1_stabilization_coverage_status"] for x in after)
    gamecounts=defaultdict(Counter)
    for x in after:gamecounts[str(x["game_id"])][x["Tminus1_stabilization_coverage_status"]]+=1
    anomaly=next(x for x in after if (x["game_id"],x["turn"],x["initiator_ship_id"],x["target_ship_id"])==(467386,75,467,80))
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v17_git_blob_sha1":V17_BLOB,
        "source_v19_git_blob_sha1":V19_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_V17_48_windows_113_edges":True,
            "frozen_V17_short_distance_edges":SHORT_COUNT,
            "frozen_V17_short_distance_windows":WINDOW_COUNT,
            "discriminative_short_edges":sum(x["Tminus1_source_target_distinct"] for x in after),
            "colocated_nondiscriminative_edges":sum(not x["Tminus1_source_target_distinct"] for x in after),
            "Tminus1_stabilization_evidence_categories":dict(sorted(candidate_counts.items())),
            "G467386_T75_467_80_Tminus1_coverage_status":anomaly["Tminus1_stabilization_coverage_status"],
            "Tminus1_all_window_data_frozen_before_T":True,
            "Host_stabilizer_activation_or_25LY_Chunnel_proven":False,
            "new_Host_movement_or_combat_predictions":0,
            "Nplus1_VCR_used":False,
        },
        "per_game_Tminus1_stabilization_evidence":{g:dict(sorted(x.items())) for g,x in sorted(gamecounts.items())},
        "G467386_T75_467_80_stabilization_audit":anomaly,
        "short_edge_evaluations":after,
        "Tminus1_window_metadata":{
            str(g)+"/"+str(t):{
                "Tminus1_safe_game_rule_markers":f["Tminus1_safe_game_rule_markers"],
                "Tminus1_stock_dungeon_stargate_inventory":f["Tminus1_stock_dungeon_stargate_inventory"],
            } for (g,t),f in sorted(frozen.items())},
        "boundary":(
            "This is retrospective attribution of preselected V17 short-distance "
            "Firecloud edges within the SAME historical public100, not a new "
            "heldout activation predictor. The official conventional Chunnel "
            "minimum is 100LY, reduced to 1LY under Short Format Cyborg "
            "Stabilization Field or within a Dungeon Class Stargate field "
            "(engine-dependent range 150..550LY). Tminus1 game settings "
            "might omit the rule flag, and ship hull108 plus spatial range "
            "alone cannot establish field activation at the later Host phase; "
            "other owners/turn-phases can matter. Only explicit safe scalar "
            "settings are retained; NO player secrets, names, raw FC codes "
            "or free-text settings. A missing indicator is ABSTAIN, not evidence "
            "the ability was disabled. One short edge ending at a far target "
            "is not proof of a short Chunnel. Original V17 actor T statuses "
            "only checked after all Tminus1 features freeze. No future VCR "
            "or canonical movement/combat promotion."
        ),
    }


def main()->int:
    a=argparse.ArgumentParser()
    for k in ("frozen-v17","frozen-v19","corpus-db-root","output"):
        a.add_argument("--"+k,type=Path,required=True)
    o=a.parse_args()
    try:
        v17src=frozen_file(o.frozen_v17,V17_BLOB)
        v19src=frozen_file(o.frozen_v19,V19_BLOB)
        preselect(v17src,v19src)
        db=o.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 not found")
        print("[c5-v20] checking immutable public100 SHA256",flush=True)
        ts=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("public100 hash changed")
        print(f"[c5-v20] pinned read-only DB verified in {time.monotonic()-ts:.1f}s",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,o.corpus_db_root)
        try:report=build_report(conn,v17src,v19src)
        finally:conn.close()
        o.output.parent.mkdir(parents=True,exist_ok=True)
        temp=o.output.with_suffix(o.output.suffix+".tmp")
        temp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(o.output)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 V20 TMINUS1 STABILIZATION COVERAGE AND SHORT CHUNNEL CONTROLS =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",o.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
