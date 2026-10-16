"""M2 transition checkpoint: repeatable multi-turn planetary Host baseline.

This does not validate the simulation against NuHost. It verifies existing
canonical phases compose in the documented supported relative order, do not
mutate source states, and remain deterministic for explicit full-information
inputs. Excluded Host phases and archive comparison remain unresolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT/"src") not in sys.path:
    sys.path.insert(0, str(ROOT/"src"))

from planets_lab.core import Cargo, GameState, MineralDeposit, NativePopulation, Planet, Player
from planets_lab.sim import PLANETARY_HOST_PHASE_ORDER, PlanetaryHostPipeline, TurnOrders

SCHEMA="planets-lab.planetary-multiturn-baseline.v1"
PHASES=PLANETARY_HOST_PHASE_ORDER
TURN_COUNT=3


def fixture() -> GameState:
    return GameState(
        game_id="m2-internal-reference",
        turn=7,
        players={1: Player(id=1,race_id=1),2: Player(id=2,race_id=3)},
        planets={
            1: Planet(
                id=1,x=100,y=100,owner_id=1,temperature=50,
                cargo=Cargo(clans=100,supplies=11,megacredits=25),
                ground_neutronium=MineralDeposit(amount=500,density=20),
                ground_duranium=MineralDeposit(amount=1000,density=100),
                factories=100,mines=100,defense_posts=50,happiness=90,tax_rate=0,
                natives=NativePopulation(race_id=2,clans=1000,government_id=8,happiness=90,tax_rate=0),
            ),
            2: Planet(
                id=2,x=500,y=500,owner_id=2,temperature=50,
                cargo=Cargo(clans=300,supplies=9,megacredits=10),
                ground_tritanium=MineralDeposit(amount=1000,density=60),
                factories=15,mines=45,happiness=100,tax_rate=0,
            ),
            3: Planet(
                id=3,x=1000,y=1000,owner_id=None,
                cargo=Cargo(supplies=2,megacredits=1),
                ground_molybdenum=MineralDeposit(amount=600,density=75),
                factories=70,mines=70,
            ),
        },
    )


def snapshot(state: GameState) -> dict[str,object]:
    planets=[]
    for planet_id in sorted(state.planets):
        p=state.planets[planet_id]
        planets.append({
            "id":p.id,"owner_id":p.owner_id,
            "supplies":p.cargo.supplies,"megacredits":p.cargo.megacredits,
            "colonist_clans":p.cargo.clans,"native_clans":None if p.natives is None else p.natives.clans,
            "happiness":p.happiness,
            "minerals":{
                name:{
                    "surface":getattr(p.cargo,name),
                    "ground":getattr(p,"ground_"+name).amount,
                }
                for name in ("neutronium","duranium","tritanium","molybdenum")
            },
        })
    return {"turn":state.turn,"planets":planets}


def trajectory(seed:int=23)->dict[str,object]:
    engine=PlanetaryHostPipeline().engine()
    if tuple(x.name for x in engine.phases)!=PHASES:
        raise ValueError("canonical planetary relative-phase order drift")
    state=fixture()
    original=snapshot(state)
    trace=[]
    for _ in range(TURN_COUNT):
        old=snapshot(state)
        next_state,events=engine.step(state,TurnOrders.empty(),seed=seed)
        if snapshot(state)!=old:
            raise ValueError("HostEngine mutated the input state in place")
        if next_state.turn!=state.turn+1:
            raise ValueError("HostEngine turn increment inconsistent")
        for planet in next_state.planets.values():
            p=planet
            for value in (p.cargo.supplies,p.cargo.megacredits,
                          p.cargo.neutronium,p.cargo.duranium,
                          p.cargo.tritanium,p.cargo.molybdenum):
                if value<0:raise ValueError("resource went negative")
            for name in ("neutronium","duranium","tritanium","molybdenum"):
                if getattr(p,"ground_"+name).amount<0:
                    raise ValueError("ground mineral reserve negative")
        trace.append({
            "from_turn":state.turn,"to_turn":next_state.turn,
            "events":[
                {"phase":event.phase,"kind":event.kind,"entity_id":event.entity_id}
                for event in events
            ],
            "after":snapshot(next_state),
        })
        state=next_state
    if snapshot(fixture())!=original:
        raise ValueError("baseline fixture not reproducible")
    return {"initial":original,"steps":trace,"final":snapshot(state)}


def build_report()->dict[str,object]:
    run_a=trajectory(seed=23)
    run_b=trajectory(seed=23)
    if run_a!=run_b:raise ValueError("same input and RNG seed changed baseline result")
    event_counts=Counter(e["kind"] for step in run_a["steps"] for e in step["events"])
    final=run_a["final"]
    initial=run_a["initial"]
    after_unowned=next(p for p in final["planets"] if p["id"]==3)
    before_unowned=next(p for p in initial["planets"] if p["id"]==3)
    if after_unowned["supplies"]!=before_unowned["supplies"] or after_unowned["megacredits"]!=before_unowned["megacredits"]:
        raise ValueError("unowned planet incorrectly received colony factory/tax output")
    raw=json.dumps(run_a,sort_keys=True,separators=(",",":")).encode()
    return {
        "schema":SCHEMA,"status":"M2_INTERNAL_MULTITURN_BASELINE_TESTED_NOT_NUHOST_DIFFERENTIAL",
        "phase_names":PHASES,"rng_seed":23,"turns_compared":TURN_COUNT,
        "internal_trace_sha256":hashlib.sha256(raw).hexdigest(),
        "summary":{
            "initial_turn":initial["turn"],"last_turn":final["turn"],
            "planet_count":len(initial["planets"]),
            "multi_turn_deterministic":True,
            "original_state_unchanged":True,
            "unowned_factory_tax_did_not_activate":True,
            "event_counts":dict(sorted(event_counts.items())),
            "factual_NuHost_archives_compared":0,
            "NuHost_phase_differential_verified":False,
            "complete_planetary_host_implemented":False,
            "canonical_combat_C5_changes":0,
        },
        "trace":run_a,
        "unimplemented_surfaces":[
            "terraforming","pillage_plunder","rebel_ground_attack",
            "campaign_enlighten","campaign_ore_condensing",
            "starbase_ship_construction","real_game_multi_turn_differential",
        ],
    }


def main()->int:
    args=argparse.ArgumentParser()
    args.add_argument("--output",type=Path,required=True)
    opts=args.parse_args()
    try:
        report=build_report()
        opts.output.parent.mkdir(parents=True,exist_ok=True)
        staged=opts.output.with_suffix(".json.tmp")
        staged.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        staged.replace(opts.output)
        print("===== M2 PLANETARY MULTITURN BASELINE V1 =====")
        print("status:",report["status"])
        print("summary:",report["summary"])
        print("output:",opts.output)
    except (ValueError,TypeError,OSError) as exc:
        print("ERROR M2:",exc,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
