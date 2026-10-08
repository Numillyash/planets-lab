"""Read-only Horwasp VCR clan intervals and Shield Generator waypoint audit.

Not a generative mass model: inverts a labelled unverified linear-clan
hypothesis using factual masses. T-1 waypoints do NOT establish combat-phase
colocation. No rules promoted to the combat executor.
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
for directory in (ROOT/"src",Path(__file__).resolve().parent):
    if str(directory) not in sys.path:
        sys.path.insert(0,str(directory))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,member_refs_for_turns,reconstruct_members,
)
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs

SCHEMA="planets-lab.combat-mass-phase-constraints.v1"
SOURCE_SCHEMA="planets-lab.combat-mass-owner-provenance.v3"
BROOD_REFERENCE_MASS=145


def _int(x:Any)->int|None:
    return x if isinstance(x,int) and not isinstance(x,bool) else None


def inverse_clan_interval(mass:int,base:int,capacity:int,bonus:int=0)->list[int]|None:
    """Invert assumed mass=base+floor(base*clans/capacity)+bonus exactly."""
    if any(_int(x) is None for x in (mass,base,capacity,bonus)) or base<=0 or capacity<=0 or bonus not in (0,360):
        raise ValueError("bad inverse parameters")
    delta=mass-base-bonus
    if delta<0 or delta>base:
        return None
    lower=max(0,-(-(delta*capacity)//base))
    upper=min(capacity,-(-((delta+1)*capacity)//base)-1)
    return [lower,upper] if lower<=upper else None


def _side(payload:Mapping[str,Any],ship_id:int):
    for name in ("left","right"):
        side=payload.get(name)
        if isinstance(side,Mapping) and _int(side.get("objectid"))==ship_id:
            return name,side
    return None


def mass_intervals(*,observed:int,hull_mass:int,capacity:int,
                   hull_id:int,side:str,left_bays:int|None)->list[dict[str,Any]]:
    choices=[("game_static_catalog",hull_mass)]
    if hull_id==117 and hull_mass!=BROOD_REFERENCE_MASS:
        choices.append(("EXTERNAL_BROOD_145_UNVERIFIED",BROOD_REFERENCE_MASS))
    results=[]
    for label,base in choices:
        bonuses=[0]
        if side=="right" and left_bays is not None and left_bays>0 and 2*base>=140:
            bonuses.append(360)
        for bonus in bonuses:
            interval=inverse_clan_interval(observed,base,capacity,bonus)
            if interval is not None:
                results.append({
                    "base_source":label,"base_assumed":base,
                    "carrier_plus360_branch":bonus,
                    "possible_clans":interval,
                    "boundary":"UNVERIFIED_LINEAR_CLAN_INTERPOLATION_AND_BONUS_RNG",
                })
    return results


def sequence(*,game:int,turn:int,ship_id:int,cases:Mapping, specs:Any,
             owner_tminus1_clans:int|None)->dict[str,Any]:
    events=[]
    for (_t,vcr_id),case in sorted(cases.items()):
        payload=case.payload
        match=_side(payload,ship_id)
        if match is None:
            continue
        name,side=match
        if _int(side.get("raceid"))!=12:
            raise ValueError("target Horwasp ship race changed")
        hull_id,mass=_int(side.get("hullid")),_int(side.get("mass"))
        if hull_id is None or mass is None or hull_id not in specs.hulls:
            raise ValueError("Horwasp hull/mass unavailable")
        spec=specs.hulls[hull_id]
        left=payload.get("left")
        bays=_int(left.get("baycount")) if isinstance(left,Mapping) else None
        x,y=_int(payload.get("x")),_int(payload.get("y"))
        events.append({
            "vcr_id":vcr_id,"side":name,
            "site":[x,y] if x is not None and y is not None else None,
            "observed_mass":mass,"hull_id":hull_id,
            "catalog_hull_mass":spec.mass,"cargo_capacity":spec.cargo_capacity,
            "observed_start_fighters":_int(side.get("fighters")),
            "observed_start_damage":_int(side.get("damage")),
            "observed_start_bays":_int(side.get("baycount")),
            "observed_left_bays":bays,
            "candidate_intervals":mass_intervals(
                observed=mass,hull_mass=spec.mass,capacity=spec.cargo_capacity,
                hull_id=hull_id,side=name,left_bays=bays,
            ),
        })
    changes=[]
    for a,b in zip(events,events[1:]):
        intervals=[]
        for x in a["candidate_intervals"]:
            for y in b["candidate_intervals"]:
                if x["base_source"]==y["base_source"] and x["base_assumed"]==y["base_assumed"]:
                    lo1,hi1=x["possible_clans"]
                    lo2,hi2=y["possible_clans"]
                    intervals.append({
                        "base_source":x["base_source"],
                        "possible_clan_loss_min":lo1-hi2,
                        "possible_clan_loss_max":hi1-lo2,
                        "loss_nonnegative_possible":lo1<=hi1 and lo2<=hi1,
                        "branch_before":x["carrier_plus360_branch"],
                        "branch_after":y["carrier_plus360_branch"],
                    })
        changes.append({
            "from":a["vcr_id"],"to":b["vcr_id"],
            "same_site":a["site"] is not None and a["site"]==b["site"],
            "vcr_id_gap":b["vcr_id"]-a["vcr_id"],
            "observed_fighter_start_delta":(
                b["observed_start_fighters"]-a["observed_start_fighters"]
                if a["observed_start_fighters"] is not None
                and b["observed_start_fighters"] is not None else None
            ),
            "possible_clan_loss_ranges":intervals,
            "boundary":"Observed VCR starts constrain, not predict, mutable clan losses",
        })
    return {"game_id":game,"turn":turn,"ship_id":ship_id,
            "owner_tminus1_clans":owner_tminus1_clans,
            "events":events,"transitions":changes}


def _is_generator(hull:Any)->bool:
    return hull is not None and (
        "shield generator" in hull.name.lower()
        or "shield generator" in hull.special.lower()
    )


def raw_ship_route(raw:Mapping[str,Any],specs:Any,site:tuple[int,int])->dict[str,Any]:
    hid=_int(raw.get("hullid"))
    spec=specs.hulls.get(hid)
    x,y,tx,ty=(_int(raw.get(k)) for k in ("x","y","targetx","targety"))
    return {
        "ship_id":_int(raw.get("id")),"hull_id":hid,
        "hull_name":spec.name if spec else None,
        "snapshot_xy":[x,y],"ordered_waypoint":[tx,ty],
        "at_site_in_snapshot":(x,y)==site,
        "waypoint_is_site":(tx,ty)==site,
        "warp":_int(raw.get("warp")),
        "mission":_int(raw.get("mission")),
        "damage":_int(raw.get("damage")),
        "neutronium":_int(raw.get("neutronium")),
    }


def shield_route_context(*,members:list[tuple[Any,Mapping[str,Any]]],
                         owner:int,site:tuple[int,int],ship_ids:set[int],
                         specs:Any)->list[dict[str,Any]]:
    result=[]
    for ref,member in members:
        if ref.perspective_player_id!=owner:
            continue
        ships=member.get("ships")
        if not isinstance(ships,list):
            result.append({"archive_turn":ref.archive_turn,"status":"SHIP_LIST_UNKNOWN"})
            continue
        own=[x for x in ships if isinstance(x,Mapping) and _int(x.get("ownerid"))==owner]
        targets=[raw_ship_route(x,specs,site) for x in own if _int(x.get("id")) in ship_ids]
        generators=[raw_ship_route(x,specs,site) for x in own
                    if _is_generator(specs.hulls.get(_int(x.get("hullid"))))]
        result.append({
            "archive_turn":ref.archive_turn,"perspective_player_id":owner,
            "combat_ships":targets,"owner_generators":generators,
            "total_generators":len(generators),
            "at_site_tminus1":sum(r["at_site_in_snapshot"] for r in generators),
            "waypoint_to_site":sum(r["waypoint_is_site"] for r in generators),
            "boundary":"Waypoint/order is NOT resolved combat-phase movement",
        })
    return result


def build_report(*,db:Any,source:Mapping[str,Any],dbpath:str)->dict[str,Any]:
    if source.get("schema")!=SOURCE_SCHEMA:
        raise ValueError("wrong v3 provenance schema")
    original=source.get("observations")
    if not isinstance(original,list) or len(original)!=14:
        raise ValueError("expected fourteen source V3 observations")
    horwasp={}
    shield=defaultdict(set)
    for r in original:
        game,turn,sid,race,owner=(_int(r.get(k)) for k in (
            "game_id","turn","ship_id","race_id","owner_id"
        ))
        if None in (game,turn,sid,race,owner):
            raise ValueError("incomplete selected ship identity")
        if race==12:
            tminus1=next((
                s for s in r.get("owner_perspective_snapshots",[])
                if isinstance(s,Mapping) and s.get("archive_turn")==turn-1
                and isinstance(s.get("participant"),Mapping)
            ),None)
            clans=_int(tminus1["participant"].get("clans")) if tminus1 else None
            horwasp.setdefault((game,turn,sid),clans)
        else:
            site=r.get("vcr_site")
            if isinstance(site,list) and len(site)==2 and all(_int(i) is not None for i in site):
                shield[(game,turn,owner,tuple(site))].add(sid)

    unique_game_turn=sorted({(g,t) for g,t,_ in horwasp}
                            |{(g,t) for g,t,_,_ in shield})
    specs={g:_independent_hull_specs(db,g) for g in sorted({g for g,_ in unique_game_turn})}
    cases={(g,t):combat_vcr_cases_for_turns(db,game_id=g,battle_turns={t})
           for g,t in unique_game_turn}
    sequences=[
        sequence(game=g,turn=t,ship_id=sid,specs=specs[g],
                 cases=cases[(g,t)],owner_tminus1_clans=clans)
        for (g,t,sid),clans in sorted(horwasp.items())
    ]
    shield_rows=[]
    for (g,t,owner,site),ids in sorted(shield.items()):
        refs=member_refs_for_turns(
            db,game_id=g,turns={t-1},include_embedded_turn=False
        )
        owner_refs=[ref for ref in refs if ref.perspective_player_id==owner]
        members=list(reconstruct_members(db,owner_refs))
        shield_rows.append({
            "game_id":g,"turn":t,"owner_id":owner,
            "site":list(site),"selected_combat_ship_ids":sorted(ids),
            "owner_tminus1":shield_route_context(
                members=members,owner=owner,site=site,
                ship_ids=ids,specs=specs[g],
            ),
        })
    n_events=sum(len(seq["events"]) for seq in sequences)
    n_transitions=sum(len(seq["transitions"]) for seq in sequences)
    return {
        "schema":SCHEMA,
        "status":"OBSERVATIONAL_CLAN_INTERVALS_AND_GENERATOR_ROUTES_NOT_PROMOTED",
        "source_db":dbpath,
        "summary":{
            "horwasp_ship_game_turn_groups":len(sequences),
            "horwasp_vcr_appearances":n_events,
            "horwasp_same_ship_transitions":n_transitions,
            "horwasp_invertible_observations":sum(
                bool(x["candidate_intervals"]) for seq in sequences for x in seq["events"]
            ),
            "shield_owner_site_groups":len(shield_rows),
        },
        "horwasp_sequences":sequences,"shield_owner_waypoints":shield_rows,
        "evidence_boundary":(
            "Horwasp mass inversion uses each observed VCR mass and an "
            "explicitly UNVERIFIED linear clan interpolation. Consecutive "
            "VCRs do not expose exact fighter losses or postbattle clans. "
            "Generator T-1 start/waypoint is historical order data, NOT "
            "verified combat-phase position. No extrapolation into "
            "generative mass or RNG rules is permitted."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--v3-input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        original=json.loads(args.v3_input.read_text(encoding="utf-8"))
        conn,path=connect_compact_generation_read_only(
            args.corpus_db_generation,args.corpus_db_root
        )
        try:
            report=build_report(db=conn,source=original,dbpath=str(path))
        finally:
            conn.close()
    except (OSError,TypeError,ValueError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("===== COMBAT MASS PHASE CONSTRAINTS V1 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    for seq in report["horwasp_sequences"]:
        print(f"HORWASP game={seq['game_id']} T{seq['turn']} ship={seq['ship_id']}")
        for event in seq["events"]:
            print(f"  V{event['vcr_id']} mass={event['observed_mass']} fighters={event['observed_start_fighters']} candidates={event['candidate_intervals']}")
        for tr in seq["transitions"]:
            print(f"  V{tr['from']}->V{tr['to']} same_site={tr['same_site']} possible_clan_losses={tr['possible_clan_loss_ranges']}")
    for row in report["shield_owner_waypoints"]:
        print(f"SHIELD game={row['game_id']} T{row['turn']} owner={row['owner_id']} site={row['site']}")
        for snap in row["owner_tminus1"]:
            print(f"  generators={snap.get('owner_generators')} combat_ships={snap.get('combat_ships')}")
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
