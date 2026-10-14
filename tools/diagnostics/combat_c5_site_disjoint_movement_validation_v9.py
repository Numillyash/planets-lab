"""V9: fixed-protocol, C5-site-DISJOINT T-1 -> T movement validation.

GAME selection is based exclusively on public100 archive-member metadata.
Exclude every game in frozen C5 V6 and select deterministic game/turn pairs
without inspecting VCRs, T ship outcomes, or mine-hit evidence. All T-1
forecasts are completed before the T comparator phase. This is a held-out
*site-game* cohort, not an independently collected/new game corpus.

No battle-site, combat pair, mine-hit roll, terminal event or Host precombat
position is inferred. The T archive is a post-Host endpoint comparator only.
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

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns, reconstruct_members
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot,mechanics_projection
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.corpus.movement_differential import (
    _entity_map,_intish,_planet_tuples_by_turn,_settings_warp_well_state_by_turn
)
from planets_lab.corpus.movement_residual_context import _storm_consensus_by_turn
from planets_lab.corpus.movement_mine_context import MineEvidenceContext
from planets_lab.corpus.movement_topology_diagnostics import (
    MapTopologyEvidence,_topology_candidates,_unique_bool,_unique_int,_unique_shape
)
from planets_lab.data.nu_static import import_static_all
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from combat_host_candidate_set_audit import (
    _owner_rows_for_turn,_tow_target_ids,_potential_chunnel_source_sites
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import (
    _normal_position_prediction,_inbound_transfer_targets,_find_named_setting,_boolish
)
from combat_host_candidate_set_v2_audit import _foreign_mine_route_risk
from combat_c5_posthost_endpoint_controls_v8 import (
    compare_posthost,owner_current_after_records
)

SCHEMA="planets-lab.combat-c5-site-disjoint-movement-validation.v9"
STATUS="SITE_DISJOINT_TMINUS1_POSTHOST_MOVEMENT_EVALUATION_NOT_HOST_COMBAT_PROMOTED"
V6_BLOB="51d21132e4db89511be59805ebe2be14014b3e7a"
V6_SCHEMA="planets-lab.combat-c5-tminus1-ingress-residence.v6"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
# Exact previously published public100 checksum; never use CURRENT.
SHA256="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
MINE="NORMAL_MINE_RISK_CONDITIONAL_NO_HIT"
NORMAL="NORMAL_MODEL_NO_INDEXED_MINE_RISK"
GAMES=8
PAIRS_PER_GAME=2


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def pinned(path:Path)->dict[str,Any]:
    raw=path.read_bytes()
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\x00"+raw).hexdigest()
    if digest!=V6_BLOB:raise ValueError("V6 source Git blob changed")
    obj=json.loads(raw)
    if not isinstance(obj,dict):raise ValueError("V6 source is not JSON object")
    if (obj.get("schema")!=V6_SCHEMA or
        obj.get("status")!="PRE_N_SITE_INGRESS_VS_RESIDENCE_OBSERVATIONAL_NOT_PROMOTED" or
        obj.get("source_db_sha256")!=SHA256):
        raise ValueError("V6 source provenance invalid")
    summary=obj.get("summary")
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in {
        "frozen_sites":27,"frozen_adjacent_transitions":63,
        "evaluated_transitions":56,"source_uninspected":7,
        "NO_PAIR_transitions":25,"new_battle_predictions":0,"Nplus1_used":False,
    }.items()):
        raise ValueError("V6 frozen cohort/count changed")
    return obj


def c5_games(v6:Mapping[str,Any])->frozenset[int]:
    sites=v6.get("sites")
    if not isinstance(sites,list) or len(sites)!=27:raise ValueError("V6 site population changed")
    keys=[]
    for s in sites:
        if not isinstance(s,Mapping):raise ValueError("bad V6 site")
        key=tuple(integer(s.get(k)) for k in ("game_id","turn","x","y"))
        if None in key or key[0]<=0:raise ValueError("bad V6 site identity")
        keys.append(key)
    if len(keys)!=len(set(keys)):raise ValueError("V6 duplicated site")
    return frozenset(x[0] for x in keys)


def select_holdout_windows(
    source_member_rows:Sequence[tuple[Any,Any]],
    excluded_games:frozenset[int],
    *,games:int=GAMES,pairs_per_game:int=PAIRS_PER_GAME,
)->tuple[tuple[int,int],...]:
    """Metadata-only, reproducible game and turn selection. ZERO ship/VCR access."""
    if games<2 or pairs_per_game!=2:raise ValueError("invalid fixed protocol")
    by_game=defaultdict(set)
    for gid,turn in source_member_rows:
        if (integer(gid) is None or gid<=0 or integer(turn) is None or turn<0):
            raise ValueError("malformed source_members game/turn metadata")
        by_game[gid].add(turn)
    available={}
    for game,ts in sorted(by_game.items()):
        if game in excluded_games:continue
        eligible=sorted(t for t in ts if t>=2 and t-1 in ts)
        if len(eligible)>=pairs_per_game:available[game]=eligible
    population=sorted(available)
    if len(population)<games:
        raise ValueError(f"insufficient C5-disjoint metadata games: {len(population)}")
    # Uniform deterministic coverage of the sorted metadata population.
    picked=[population[i*(len(population)-1)//(games-1)] for i in range(games)]
    if len(set(picked))!=games:raise ValueError("game selection duplicates")
    selected=[]
    for game in picked:
        candidates=available[game]
        # Choose early/late available pairs before observing T data.
        first=candidates[(len(candidates)-1)//3]
        second=candidates[(2*(len(candidates)-1))//3]
        if second==first:
            first,second=candidates[0],candidates[-1]
        if first==second:raise ValueError("not enough distinct metadata turn pairs")
        selected.extend(((game,first),(game,second)))
    return tuple(sorted(selected))


def pre_snapshots(conn:Any,*,game:int,before:int):
    """Read ONLY exact T-1 perspectives. Reject embedded-turn mismatch."""
    refs=member_refs_for_turns(conn,game_id=game,turns={before},include_embedded_turn=False)
    if not refs:raise ValueError("missing exact Tminus1 owner perspectives")
    snapshots=[]
    raw_payloads=[]
    for ref,parsed in reconstruct_members(conn,refs):
        if (ref.game_id!=game or ref.archive_turn!=before or
            ref.embedded_turn!=before or
            not isinstance(parsed.get("game"),Mapping) or
            integer(parsed["game"].get("id"))!=game or
            integer(parsed["game"].get("turn"))!=before):
            raise ValueError("untrusted Tminus1 archive identity")
        projection=mechanics_projection(parsed,member=ref.turn_member.name)
        player=projection.get("player")
        if not isinstance(player,Mapping) or integer(player.get("id"))!=ref.perspective_player_id:
            raise ValueError("Tminus1 perspective player mismatch")
        snapshots.append(ArchiveTurnSnapshot(
            member=ref.turn_member,game_id=game,
            player_id=ref.perspective_player_id,embedded_turn=before,
            snapshot_hash=ref.decoded_payload_sha256,mechanics_payload=projection
        ))
        raw_payloads.append(parsed)
    return tuple(snapshots),tuple(raw_payloads)


def resolve_pre_context(game:int,before:int,snapshots:Sequence[Any],raw_payloads:Sequence[Mapping[str,Any]]):
    """No full-history last turn, no after-T archive state, no VCR inputs."""
    if not snapshots or len(snapshots)!=len(raw_payloads):
        raise ValueError("missing Tminus1 pre context")
    specs=None
    for raw in raw_payloads:
        current=NuStaticSpecs.from_catalog(import_static_all(raw))
        if not current.hulls or not current.engines:
            raise ValueError("missing exact Tminus1 engine/hull catalog")
        if specs is None:specs=current
        elif (specs.hulls!=current.hulls or specs.engines!=current.engines):
            raise ValueError("conflicting exact Tminus1 static catalogs")
    candidates={}
    for raw in raw_payloads:
        for root in ("settings","game"):
            item=raw.get(root)
            if isinstance(item,(Mapping,list,tuple)):
                candidates.update(_topology_candidates(item,prefix=root))
    sphere=_unique_bool(candidates,"sphere")
    if sphere is None:raise ValueError("Tminus1 sphere topology unknown")
    topology=effective_sphere_topology(
        game_id=game,topology=MapTopologyEvidence(
            sphere=sphere,mapwidth=_unique_int(candidates,"mapwidth"),
            mapheight=_unique_int(candidates,"mapheight"),
            mapshape=_unique_shape(candidates),
            first_member=snapshots[0].member.name,last_member=snapshots[-1].member.name,
            stable=True,first_candidates=candidates,last_candidates=candidates,
        )
    )
    flags=set()
    for raw in raw_payloads:
        for val in _find_named_setting(raw,"nuionstorms"):
            flag=_boolish(val)
            if flag is not None:flags.add(flag)
    nuionstorms=next(iter(flags)) if len(flags)==1 else None
    entities=_entity_map(snapshots)
    planets=tuple(_planet_tuples_by_turn(entities,include_ineligible=True).get(before,()))
    warp_wells,_legacy=_settings_warp_well_state_by_turn(snapshots)
    eligible=getattr(entities,"warp_well_planet_ids_by_turn",{}).get(before)
    eligible=frozenset(int(x) for x in eligible) if eligible is not None else None
    storms,conflict,invalid=_storm_consensus_by_turn(snapshots)
    if before in conflict or before in invalid:
        raise ValueError("Tminus1 ion-storm snapshots conflicted or invalid")
    return dict(specs=specs,topology=topology,nuionstorms=nuionstorms,
                planets=planets,warp_wells_enabled=warp_wells.get(before),
                eligible_warp_well_planet_ids=eligible,
                storms=storms.get(before,()),
                mine_context=MineEvidenceContext(
                    snapshots=tuple(snapshots),specs=specs,topology=topology,
                    ship_groups=group_perspective_records(snapshots,"ship")
                ))


def forecast_pre_window(game:int,turn:int,snapshots:Sequence[Any],raw_payloads:Sequence[Mapping[str,Any]]):
    before=turn-1
    context=resolve_pre_context(game,before,snapshots,raw_payloads)
    groups=group_perspective_records(snapshots,"ship")
    rows=_owner_rows_for_turn(groups,before)
    races,_conflicts=_player_races(snapshots)
    tow_targets=_tow_target_ids(rows)
    chunnel_sites=_potential_chunnel_source_sites(rows)
    transfers=_inbound_transfer_targets(rows)
    forecasts=[]
    excluded=Counter()
    for sid,(owner,raw) in sorted(rows.items()):
        race=races.get(owner)
        predicted,source=_normal_position_prediction(
            game_id=game,ship_id=sid,owner_id=owner,raw=raw,race_id=race,
            specs=context["specs"],planets=context["planets"],
            warp_wells_enabled=context["warp_wells_enabled"],
            eligible_warp_well_planet_ids=context["eligible_warp_well_planet_ids"],
            inbound_transfer_targets=transfers,tow_targets=tow_targets,
            chunnel_source_sites=chunnel_sites,sphere=context["topology"].sphere,
            storms=context["storms"],nuionstorms=context["nuionstorms"])
        if predicted is None or not source.startswith("normal_move"):
            excluded[source]+=1;continue
        hull=_intish(raw.get("hullid",raw.get("hull_id")))
        mine=_foreign_mine_route_risk(
            context=context["mine_context"],before_turn=before,
            owner_id=owner,raw=raw,race_id=race,hull_id=hull)
        if mine=="normal_mine_route_risk":
            cohort=MINE
        elif mine is None:
            cohort=NORMAL
        else:
            excluded[mine]+=1;continue
        forecasts.append({
            "game_id":game,"before_turn":before,"after_turn":turn,
            "ship_id":sid,"Tminus1_owner_id":owner,
            "Tminus1_hull_id":hull,"Tminus1_source":mine or source,
            "cohort":cohort,
            "conditional_or_model_endpoint":list(predicted),
            "frozen_v7_witness":False,
            "conditional_no_mine_only":cohort==MINE,
        })
    return forecasts,excluded,len(rows)


def after_owner_current(conn:Any,*,game:int,turn:int):
    """Used ONLY after the forecast-freeze phase has finished."""
    refs=member_refs_for_turns(conn,game_id=game,turns={turn},include_embedded_turn=False)
    if not refs:raise ValueError("T archive perspectives unavailable")
    snapshots=[]
    for ref,parsed in reconstruct_members(conn,refs):
        if (ref.archive_turn!=turn or ref.embedded_turn!=turn or
            not isinstance(parsed.get("game"),Mapping) or
            integer(parsed["game"].get("id"))!=game or
            integer(parsed["game"].get("turn"))!=turn):
            raise ValueError("posthost T perspective archive identity invalid")
        projection=mechanics_projection(parsed,member=ref.turn_member.name)
        snapshots.append(ArchiveTurnSnapshot(
            member=ref.turn_member,game_id=game,player_id=ref.perspective_player_id,
            embedded_turn=turn,snapshot_hash=ref.decoded_payload_sha256,
            mechanics_payload=projection))
    return owner_current_after_records(tuple(snapshots),turn)


def build_report(conn:Any,v6:Mapping[str,Any])->dict[str,Any]:
    excluded=c5_games(v6)
    # This query is metadata ONLY: no VCR, positions or after-state fields.
    metadata=conn.execute(
        "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
    ).fetchall()
    selected=select_holdout_windows(metadata,excluded)
    print("[c5-holdout] site-disjoint preselected windows:",selected,flush=True)
    frozen={}
    errors=[]
    input_counts=Counter()
    exclusions=Counter()
    # Phase 1: finish the complete cohort of T-1 predictions first.
    for i,(game,turn) in enumerate(selected,1):
        print(f"[c5-holdout] PRE [{i}/{len(selected)}] G{game} T{turn}",flush=True)
        try:
            snapshots,raws=pre_snapshots(conn,game=game,before=turn-1)
            rows,excluded_rows,seen=forecast_pre_window(game,turn,snapshots,raws)
            frozen[(game,turn)]=rows
            input_counts["owner_current_Tminus1_ships"]+=seen
            input_counts["pre_forecast_rows"]+=len(rows)
            exclusions.update(excluded_rows)
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({"game_id":game,"turn":turn,"phase":"Tminus1",
                           "status":"ABSTAIN_WINDOW_PRE_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
            frozen[(game,turn)]=[]
    # Phase 2: T owner-current observations are consulted ONLY now.
    counts=defaultdict(Counter)
    by_game=defaultdict(lambda:defaultdict(Counter))
    by_window=defaultdict(lambda:defaultdict(Counter))
    mismatch_examples=defaultdict(list)
    total_comparisons=0
    for i,(game,turn) in enumerate(selected,1):
        print(f"[c5-holdout] POST [{i}/{len(selected)}] G{game} T{turn}",flush=True)
        try:actual=after_owner_current(conn,game=game,turn=turn)
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({"game_id":game,"turn":turn,"phase":"posthost",
                           "status":"ABSTAIN_WINDOW_POST_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
            actual={}
        for forecast in frozen[(game,turn)]:
            record=compare_posthost(forecast,actual)
            cls=record["cohort"];status=record["comparison_status"]
            counts[cls][status]+=1
            by_game[str(game)][cls][status]+=1
            by_window[f"{game}/{turn}"][cls][status]+=1
            total_comparisons+=1
            if status=="POSTHOST_ENDPOINT_MISMATCH" and len(mismatch_examples[cls])<24:
                mismatch_examples[cls].append(record)
    if input_counts["pre_forecast_rows"]<100 or sum(bool(x) for x in frozen.values())<4:
        raise ValueError("insufficient held-out Tminus1 forecasts; refuse empty validation")
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v6_git_blob_sha1":V6_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "frozen_metadata_selection":{
            "method":"source_members-game-turn-only; exclude V6 game IDs; evenly-spaced 8 games x 2 pairs",
            "excluded_c5_game_ids":sorted(excluded),
            "selected_game_turns":[{"game_id":g,"turn":t} for g,t in selected],
            "source_member_metadata_pair_count":len(metadata),
            "no_VCR_selection":True,
        },
        "summary":{
            "selected_games":len(set(g for g,_ in selected)),
            "selected_windows":len(selected),
            "selected_games_overlap_with_C5":len(set(g for g,_ in selected)&excluded),
            "pre_forecast_rows":input_counts["pre_forecast_rows"],
            "Tminus1_owner_current_ships":input_counts["owner_current_Tminus1_ships"],
            "posthost_compared_rows":total_comparisons,
            "window_context_abstentions":len(errors),
            "excluded_pre_sources":dict(sorted(exclusions.items())),
            "cohort_posthost_status_counts":{
                c:dict(sorted(v.items())) for c,v in sorted(counts.items())},
            "new_Host_combat_predictions":0,
            "Nplus1_VCR_read":False,
            "actual_mine_hit_inferred":False,
            "independent_new_corpus":False,
        },
        "per_game_status_counts":{
            g:{c:dict(sorted(v.items())) for c,v in sorted(k.items())}
            for g,k in sorted(by_game.items())},
        "per_game_turn_status_counts":{
            g:{c:dict(sorted(v.items())) for c,v in sorted(k.items())}
            for g,k in sorted(by_window.items())},
        "mismatch_examples":dict(sorted(mismatch_examples.items())),
        "window_errors":errors,
        "boundary":(
            "No VCRs or post-Host outcome fields used in game/turn selection. "
            "Forecasts use exact T-1 owner-current ships, T-1 static catalogs, "
            "T-1 topology/settings/fields and established normal planner. "
            "T archived owner-current coordinates are consulted only in the "
            "later comparison phase. T is after Host, not precombat. "
            "Risk-exposed normal no-hit endpoint is conditional, not factual "
            "mine RNG; missing/owner-changed/destroyed/unobserved ships are "
            "abstentions. This site-disjoint cohort is sampled from the SAME "
            "previously studied public100, not an independently new corpus; "
            "no claims of prospectivity, causal mine events or Host combat "
            "queue reconstruction."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-v6",type=Path,required=True)
    parser.add_argument("--corpus-db-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    try:
        source=pinned(a.frozen_v6)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 missing")
        print("[c5-holdout] verifying pinned public100 checksum",flush=True)
        t=time.monotonic()
        with db.open("rb") as fd:sha=hashlib.file_digest(fd,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("immutable public100 SHA256 drift")
        print(f"[c5-holdout] read-only SHA verified in {time.monotonic()-t:.1f}s",flush=True)
        conn,p=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=build_report(conn,source)
        finally:conn.close()
        report["db_path"]=str(p)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(a.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 SITE-DISJOINT MOVEMENT T-1 -> T VALIDATION V9 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
