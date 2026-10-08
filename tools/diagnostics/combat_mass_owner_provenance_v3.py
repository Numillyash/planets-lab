"""Read-only owner-perspective triage for six residual mass observations.

Compares factual current-VCR residual identities against T-1/T archived
owner-visible ship clans, engine, and Shield Generator inventory. A T-1
coordinate is NOT proof of combat-phase colocation. No Host rules promoted.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT / "src", Path(__file__).resolve().parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns, reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs

SCHEMA = "planets-lab.combat-mass-owner-provenance.v3"
SOURCE = "planets-lab.combat-mass-composition-signatures.v2"
CONTROLS = {
    "fed_threshold_ordering_hypothesis": 1,
    "horwasp_partial_load_numeric_candidate": 2,
    "horwasp_double_plus_360_candidate": 1,
    "one_transwarp_shield_generator_numeric_candidate": 1,
    "two_transwarp_shield_generators_numeric_candidate": 1,
    "one_generator_plus_360_numeric_candidate": 1,
    "two_generators_plus_360_numeric_candidate": 1,
}
SHIP_KEYS = ("id", "ownerid", "hullid", "engineid", "clans", "x", "y",
             "targetx", "targety", "warp", "mass", "damage", "ammo")


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def select_observations(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    if source.get("schema") != SOURCE:
        raise ValueError("unexpected v2 source schema")
    examples = source.get("examples_by_signature")
    if not isinstance(examples, Mapping):
        raise ValueError("missing v2 examples")
    residuals = examples.get("unresolved_nonadditive")
    if not isinstance(residuals, list) or len(residuals) != 6:
        raise ValueError("expected all six unresolved mass examples")
    selections: list[dict[str, Any]] = []
    for signature, limit in (("unresolved_nonadditive", 6), *CONTROLS.items()):
        group = examples.get(signature, [])
        if not isinstance(group, list):
            raise ValueError("invalid example group")
        for row in group[:limit]:
            if not isinstance(row, Mapping):
                raise ValueError("malformed signature row")
            if row.get("side") not in ("left", "right"):
                raise ValueError("malformed side")
            if any(_int(row.get(k)) is None for k in (
                "game_id", "turn", "vcr_id", "ship_id", "hull_id", "factual_mass"
            )):
                raise ValueError("incomplete signature row identity")
            selections.append({**row, "signature":signature})
    return selections


def _shield_gen(spec: Any) -> bool:
    return spec is not None and (
        "shield generator" in spec.name.casefold()
        or "shield generator" in spec.special.casefold()
    )


def owner_evidence(*, members: list[tuple[Any, Mapping[str, Any]]],
                   owner_id: int, ship_id: int,
                   site: tuple[int,int] | None, specs: Any) -> list[dict[str, Any]]:
    observations=[]
    for ref, member in members:
        if ref.perspective_player_id != owner_id:
            continue
        ships = member.get("ships")
        if not isinstance(ships, list):
            continue
        participant=None
        nearby=[]
        all_generators=0
        for raw in ships:
            if not isinstance(raw,Mapping) or _int(raw.get("ownerid"))!=owner_id:
                continue
            sid=_int(raw.get("id"))
            hull_id=_int(raw.get("hullid"))
            spec=specs.hulls.get(hull_id)
            if sid==ship_id:
                engine_id=_int(raw.get("engineid"))
                engine=specs.engines.get(engine_id)
                clans=_int(raw.get("clans"))
                capacity=spec.cargo_capacity if spec else None
                participant={
                    "raw":{k:raw[k] for k in SHIP_KEYS if k in raw},
                    "clans":clans,
                    "cargo_capacity":capacity,
                    "clans_fraction_of_catalog_capacity":(
                        round(clans/capacity,6)
                        if clans is not None and capacity and capacity>0 else None
                    ),
                    "engine_id":engine_id,
                    "engine_cost_mc":engine.cost.megacredits if engine else None,
                    "numeric_shield_bonus_half_engine_cost":(
                        engine.cost.megacredits//2 if engine else None
                    ),
                }
            if _shield_gen(spec):
                all_generators+=1
                xy=(_int(raw.get("x")),_int(raw.get("y")))
                if site is not None and xy==site:
                    nearby.append({
                        "ship_id":sid,"hull_id":hull_id,
                        "x":xy[0],"y":xy[1],
                        "targetx":_int(raw.get("targetx")),
                        "targety":_int(raw.get("targety")),
                    })
        observations.append({
            "archive_turn":ref.archive_turn,
            "perspective_player_id":ref.perspective_player_id,
            "participant":participant,
            "owner_shield_generator_inventory_count":all_generators,
            "owner_shield_generators_at_vcr_coordinates":nearby[:20],
            "nearby_generators_truncated":len(nearby)>20,
            "temporal_boundary":"Snapshot position is not precombat position",
        })
    return observations


def build_report(connection: Any, source: Mapping[str,Any], path: str) -> dict[str,Any]:
    chosen=select_observations(source)
    groups=defaultdict(list)
    for row in chosen:
        groups[(row["game_id"],row["turn"])].append(row)
    results=[]
    by_hull=defaultdict(dict)
    for (game_id,turn), items in sorted(groups.items()):
        specs=_independent_hull_specs(connection,game_id)
        cases=combat_vcr_cases_for_turns(connection,game_id=game_id,battle_turns={turn})
        owners=set()
        for row in items:
            case=cases.get((turn,row["vcr_id"]))
            if case is None:
                raise ValueError(f"VCR {game_id}/{turn}/{row['vcr_id']} missing")
            key="leftownerid" if row["side"]=="left" else "rightownerid"
            owner=_int(case.payload.get(key))
            if owner is not None:
                owners.add(owner)
        refs=member_refs_for_turns(connection,game_id=game_id,
                                   turns={turn-1,turn},include_embedded_turn=False)
        raw=list(reconstruct_members(connection,[
            ref for ref in refs if ref.perspective_player_id in owners
        ]))
        for row in items:
            case=cases[(turn,row["vcr_id"])]
            side=case.payload.get(row["side"])
            if not isinstance(side,Mapping):
                raise ValueError("VCR side missing")
            identity=(_int(side.get("objectid")),_int(side.get("hullid")),_int(side.get("mass")))
            expected=(row["ship_id"],row["hull_id"],row["factual_mass"])
            if identity!=expected:
                raise ValueError("factual VCR conflicts with frozen signature")
            owner_key="leftownerid" if row["side"]=="left" else "rightownerid"
            owner=_int(case.payload.get(owner_key))
            if owner is None or owner<1:
                raise ValueError("owner of VCR participant unavailable")
            hull=specs.hulls.get(row["hull_id"])
            if hull is None:
                raise ValueError("participant hull missing from game catalog")
            x,y=_int(case.payload.get("x")),_int(case.payload.get("y"))
            site=(x,y) if x is not None and y is not None else None
            snapshots=owner_evidence(members=raw,owner_id=owner,
                                     ship_id=row["ship_id"],site=site,specs=specs)
            results.append({
                "signature":row["signature"],
                "game_id":game_id,"turn":turn,"vcr_id":row["vcr_id"],
                "side":row["side"],"ship_id":row["ship_id"],
                "hull_id":row["hull_id"],"race_id":_int(side.get("raceid")),
                "owner_id":owner,"factual_combat_mass":identity[2],
                "catalog_hull_mass":hull.mass,
                "catalog_cargo_capacity":hull.cargo_capacity,
                "catalog_hull_name":hull.name,
                "vcr_site":list(site) if site is not None else None,
                "owner_perspective_snapshots":snapshots,
                "tminus1_owner_ship_seen":any(
                    x["archive_turn"]==turn-1 and x["participant"] is not None
                    for x in snapshots
                ),
            })
            by_hull[row["hull_id"]][game_id]={
                "catalog_mass":hull.mass,"name":hull.name,
                "cargo_capacity":hull.cargo_capacity,
            }
    counts=Counter(row["signature"] for row in results)
    if counts["unresolved_nonadditive"]!=6:
        raise ValueError("not all original unresolved examples triaged")
    return {
        "schema":SCHEMA,"status":"OWNER_PROVENANCE_OBSERVATIONAL_NOT_PROMOTED",
        "source_schema":SOURCE,"database_path":path,
        "summary":{
            "observations":len(results),
            "unresolved_targeted":counts["unresolved_nonadditive"],
            "owner_Tminus1_ship_seen":sum(r["tminus1_owner_ship_seen"] for r in results),
            "game_turns":len(groups),
            "signatures":dict(sorted(counts.items())),
        },
        "game_specific_hulls":{
            str(hull_id):{str(game):data for game,data in sorted(games.items())}
            for hull_id,games in sorted(by_hull.items())
        },
        "observations":results,
        "evidence_boundary":(
            "Factual VCR mass is used solely to identify and verify historical "
            "examples. Only T-1/T owner-perspective raw snapshots are sampled. "
            "No historical coordinate proves presence of an active generator "
            "at combat, no clan count proves precombat population, and no "
            "mass or RNG formula is promoted to the combat evaluator."
        ),
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--signatures",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        original=json.loads(a.signatures.read_text(encoding="utf-8"))
        conn,path=connect_compact_generation_read_only(
            a.corpus_db_generation,a.corpus_db_root
        )
        try:
            report=build_report(conn,original,str(path))
        finally:
            conn.close()
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as e:
        print("ERROR:",e,file=sys.stderr)
        return 2
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("===== COMBAT MASS OWNER PROVENANCE V3 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    for row in report["observations"]:
        before=[s for s in row["owner_perspective_snapshots"]
                if s["archive_turn"]==row["turn"]-1]
        detail=[{
            "clans":s["participant"]["clans"] if s["participant"] else None,
            "engine_id":s["participant"]["engine_id"] if s["participant"] else None,
            "generators_at_site":len(s["owner_shield_generators_at_vcr_coordinates"])
        } for s in before]
        print(
            f"game={row['game_id']} T{row['turn']} V{row['vcr_id']} "
            f"ship={row['ship_id']} hullmass={row['catalog_hull_mass']} "
            f"vcrmass={row['factual_combat_mass']} signature={row['signature']} "
            f"owner_Tminus1={detail}"
        )
    print("game_specific_hulls:",report["game_specific_hulls"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
