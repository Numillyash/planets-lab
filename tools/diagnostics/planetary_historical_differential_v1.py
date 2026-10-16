"""M2 historical planetary differential: four observational families in ONE run.

Game/window selection is metadata-only from newly acquired public8.
All T-1 owner-current, perspective-authenticated planet input records
and deterministic canonical planetary Host simulations are frozen before
ANY T archive is opened. T postHost state is not a phase trace and is
not attributed uniquely to the simulated phase. No combat/Chunnel rules
or C5 source code modified.

Output: supplies, taxes, minerals, populations, manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for d in (ROOT/"src",Path(__file__).resolve().parent):
    if str(d) not in sys.path:sys.path.insert(0,str(d))
import duckdb
from planets_lab.core import GameState,Player
from planets_lab.data.nu_loadturn import _planet as import_planet
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.sim import PlanetaryHostPipeline,TurnOrders
from planets_lab.sim.population_phases import UnsupportedPopulationRule
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.planetary-historical-differential.v1"
STATUS="M2_ARCHIVAL_OWNER_CURRENT_CONDITIONAL_TMINUS1_TO_T_NOT_CAUSAL"
GENERATION="corpus-v2compact-c5-v25-public8-20261016.duckdb"
DB_SHA256="af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a"
V25_MANIFEST_BLOB="2c89d5320b31b2f12d9235192a8ac31240549052"
FAMILIES=("supplies","taxes","minerals","populations")
GAMES=8
WINDOWS_PER_GAME=4
MAX_PLANETS_PER_WINDOW=24

MINERALS=("neutronium","duranium","tritanium","molybdenum")
FIELDS={
    "supplies":("supplies",),
    "taxes":("megacredits",),
    "minerals":tuple(f"{prefix}{m}" for m in MINERALS for prefix in ("","ground")),
    "populations":("clans","nativeclans"),
}
# A measured delta may differ from a Host phase because archive post-state
# includes player orders, combat, transfers, abilities and unrelated phases.
# Input aliases and output fields must actually occur in BOTH snapshots.
ALIASES={
    "supplies":("supplies",),"megacredits":("megacredits",),
    "clans":("clans",),"nativeclans":("nativeclans","native_clans"),
    **{m:(m,) for m in MINERALS},
    **{f"ground{m}":(f"ground{m}",) for m in MINERALS},
}
SOURCE_REQUIRE={
    "supplies":(("clans",),("factories",),("supplies",)),
    "taxes":(("clans",),("megacredits",),("colonisttaxrate","taxrate"),("colonisthappypoints","happiness")),
    "minerals":(("mines",),),
    "populations":(("clans",),("temp","temperature"),("colonisthappypoints","happiness"),("colonisttaxrate","taxrate")),
}


def intval(v:Any)->int|None:
    return v if type(v) is int else None


def int_field(raw:Mapping[str,Any],aliases:tuple[str,...])->int|None:
    for key in aliases:
        if key in raw:return intval(raw[key])
    return None


def value(p:Any,field:str)->int|None:
    if field=="clans":return p.cargo.clans
    if field=="nativeclans":return p.natives.clans if p.natives is not None else 0
    if field.startswith("ground"):return getattr(p,"ground_"+field[6:]).amount
    return getattr(p.cargo,field)


def frozen_manifest(path:Path)->tuple[int,...]:
    raw=path.read_bytes()
    calculated=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if calculated!=V25_MANIFEST_BLOB:raise ValueError("V25 pinned new corpus manifest Git blob drift")
    doc=json.loads(raw)
    if (doc.get("status")!="V25_NEW_GAME_CORPUS_THREE_REPORTS_COMPLETE"
        or doc.get("generation_sha256")!=DB_SHA256
        or doc.get("CURRENT_modified") is not False):
        raise ValueError("V25 new corpus provenance mismatch")
    ids=doc.get("selected_game_ids")
    if (not isinstance(ids,list) or len(ids)!=GAMES or
        any(intval(x) is None or x<=0 for x in ids) or
        len(set(ids))!=GAMES):
        raise ValueError("V25 exact eight game identities invalid")
    return tuple(sorted(ids))


def choose_metadata_windows(rows,selected):
    by_game=defaultdict(set)
    for game,turn in rows:
        if intval(game) is None or intval(turn) is None or turn<0:
            raise ValueError("invalid source archive metadata")
        if game in selected:by_game[game].add(turn)
    if set(by_game)!=set(selected):raise ValueError("selected game missing source metadata")
    windows=[]
    for game in sorted(selected):
        available=sorted(t for t in by_game[game] if t>=2 and t-1 in by_game[game])
        if len(available)<WINDOWS_PER_GAME:
            raise ValueError("insufficient adjacent planet archival windows")
        indices=[i*(len(available)-1)//(WINDOWS_PER_GAME-1)
                 for i in range(WINDOWS_PER_GAME)]
        if len(set(indices))!=WINDOWS_PER_GAME:
            raise ValueError("duplicate metadata quantile")
        windows.extend((game,available[i]) for i in indices)
    return tuple(windows)


def raw_owner_current_planets(snapshots,turn:int):
    grouped=group_perspective_records(snapshots,"planet")
    present={}
    status=Counter()
    for (archive_turn,pid),rows in sorted(grouped.items()):
        if archive_turn!=turn:raise ValueError("planet snapshot archive turn drift")
        current=[r for r in rows if r.infoturn==turn and r.embedded_turn==turn]
        if not current:
            status["ABSTAIN_PLANET_STALE"]+=1
            continue
        owns=set()
        for r in current:
            owner=int_field(r.raw,("ownerid","owner_id"))
            if owner is not None and owner>0:owns.add(owner)
        if len(owns)!=1:
            status["ABSTAIN_OWNER_UNKNOWN_OR_CONFLICT"]+=1
            continue
        owner=next(iter(owns))
        authoritative=[r for r in current if r.player_id==owner
                       and int_field(r.raw,("ownerid","owner_id"))==owner]
        if len(authoritative)!=1:
            status["ABSTAIN_NO_UNIQUE_OWNER_CURRENT"]+=1
            continue
        present[pid]=(owner,authoritative[0].raw)
    return present,status


def race_for_owner(snapshots,owner:int)->int|None:
    values=set()
    for snap in snapshots:
        if snap.player_id!=owner or snap.archive_turn!=snap.embedded_turn:
            continue
        player=snap.mechanics_payload.get("player",{})
        if isinstance(player,Mapping):
            race=int_field(player,("raceid","race_id"))
            if race is not None and race>0:values.add(race)
    return next(iter(values)) if len(values)==1 else None


def missing_pre_fields(family:str,raw:Mapping[str,Any])->list[str]:
    expected=SOURCE_REQUIRE[family]
    absent=[ "|".join(names) for names in expected
             if int_field(raw,names) is None]
    for field in FIELDS[family]:
        if int_field(raw,ALIASES[field]) is None:absent.append(field)
    if family=="minerals":
        for name in MINERALS:
            if int_field(raw,("density"+name,)) is None:
                absent.append("density"+name)
    if family=="supplies":
        native=int_field(raw,("nativeclans","native_clans"))
        if native is not None and native>0 and int_field(raw,("nativetype","nativerace","nativeraceid")) is None:
            absent.append("native_race")
    if family=="taxes":
        native=int_field(raw,("nativeclans","native_clans"))
        if native is not None and native>0:
            for names in (("nativegovernment","nativegovernmentid"),
                          ("nativehappypoints","nativehappiness"),
                          ("nativetaxrate",)):
                if int_field(raw,names) is None:absent.append("|".join(names))
    return sorted(set(absent))


def pre_window(conn,game:int,turn:int):
    snaps,_=v9.pre_snapshots(conn,game=game,before=turn-1)
    rows,coverage=raw_owner_current_planets(snaps,turn-1)
    selected=sorted(rows)[:MAX_PLANETS_PER_WINDOW]
    frozen=[]
    for pid in selected:
        owner,raw=rows[pid]
        race=race_for_owner(snaps,owner)
        item={
            "game_id":game,"turn":turn,"planet_id":pid,"owner_id":owner,
            "race_id":race,
            "Tminus1_input_selected_without_T_observation":True,
        }
        if race is None:
            item["Tminus1_status"]="ABSTAIN_RACE_UNAVAILABLE"
            item["expected"]={}
            item["before"]={}
            item["source_missing"]={}
            frozen.append(item)
            continue
        try:
            planet=import_planet(raw)
            if planet.id!=pid or planet.owner_id!=owner:
                raise ValueError("raw planet owner identity changed")
            state=GameState(game_id=game,turn=turn-1,
                            players={owner:Player(id=owner,race_id=race)},
                            planets={pid:planet})
            next_state,events=PlanetaryHostPipeline().engine().step(
                state,TurnOrders.empty(),seed=23)
            sim=next_state.planets[pid]
            item["Tminus1_status"]="MODEL_CONDITIONAL"
            item["source_missing"]={
                family:missing_pre_fields(family,raw) for family in FAMILIES}
            item["expected"]={
                name:{field:value(sim,field) for field in FIELDS[name]}
                for name in FAMILIES}
            item["before"]={
                name:{field:int_field(raw,ALIASES[field]) for field in FIELDS[name]}
                for name in FAMILIES}
            item["predicted_internal_events"]=sorted({e.kind for e in events})
        except (ValueError,TypeError,NotImplementedError,UnsupportedPopulationRule) as exc:
            # Event-level exceptions mean the simulator is not applicable.
            item["Tminus1_status"]="ABSTAIN_MODEL_UNSUPPORTED"
            item["abstain_exception_type"]=type(exc).__name__
            item["expected"]={}
            item["before"]={}
            item["source_missing"]={}
        frozen.append(item)
    return {"game_id":game,"turn":turn,
            "Tminus1_planets":frozen,
            "Tminus1_owner_current_coverage":dict(sorted(coverage.items())),
            "all_source_predictions_frozen_before_ANY_T":True}


def post_window(conn,game,turn):
    snaps,_=v9.pre_snapshots(conn,game=game,before=turn)
    return raw_owner_current_planets(snaps,turn)[0]


def compare(frozen,after):
    rows={name:[] for name in FAMILIES}
    for item in frozen["Tminus1_planets"]:
        pid=item["planet_id"]
        post=after.get(pid)
        for family,fields in FIELDS.items():
            result={
                "game_id":item["game_id"],"turn":item["turn"],"planet_id":pid,
                "owner_id":item["owner_id"],"race_id":item["race_id"],
                "family":family,
                "Tminus1_to_T_phase_attribution_proven":False,
            }
            if item["Tminus1_status"]!="MODEL_CONDITIONAL":
                result["status"]=item["Tminus1_status"]
            elif post is None:
                result["status"]="ABSTAIN_T_OWNER_CURRENT_MISSING"
            elif post[0]!=item["owner_id"]:
                result["status"]="ABSTAIN_OWNER_CHANGED"
            elif item["source_missing"][family]:
                result["status"]="ABSTAIN_TMINUS1_REQUIRED_FIELDS_MISSING"
                result["missing_fields"]=item["source_missing"][family]
            else:
                raw=post[1]
                observations={field:int_field(raw,ALIASES[field]) for field in fields}
                if any(v is None or v<0 for v in observations.values()):
                    result["status"]="ABSTAIN_T_REQUIRED_FIELDS_MISSING"
                else:
                    predicted=item["expected"][family]
                    initial=item["before"][family]
                    result["status"]=(
                        "CONDITIONAL_EXACT_ALL_FIELDS" if predicted==observations else
                        "CONDITIONAL_MISMATCH_UNATTRIBUTED")
                    result["Tminus1"]=initial
                    result["model_T"]=predicted
                    result["archive_T"]=observations
                    result["delta_model"]={k:predicted[k]-initial[k] for k in fields}
                    result["delta_archive"]={k:observations[k]-initial[k] for k in fields}
            rows[family].append(result)
    return rows


def reports(selected,windows,frozen,comparison):
    roots={}
    for family in FAMILIES:
        rows=comparison[family]
        counts=Counter(x["status"] for x in rows)
        exact=counts.get("CONDITIONAL_EXACT_ALL_FIELDS",0)
        mismatch=counts.get("CONDITIONAL_MISMATCH_UNATTRIBUTED",0)
        roots[family]={
            "schema":SCHEMA,"status":STATUS,"family":family,
            "source_corpus_sha256":DB_SHA256,
            "source_V25_manifest_git_blob_sha1":V25_MANIFEST_BLOB,
            "source_game_ids":list(selected),
            "all_Tminus1_windows_frozen_before_first_T":True,
            "new_C5_rule_or_combat_executor_changes":0,
            "real_Host_phase_mechanism_proven":False,
            "conditional_simulation_not_true_Host_causal_attribution":True,
            "summary":{
                "metadata_selected_games":len(selected),
                "metadata_selected_windows":len(windows),
                "Tminus1_authentic_owner_planet_rows":len(rows),
                "comparable_qualified_rows":exact+mismatch,
                "conditionally_all_field_exact":exact,
                "conditionally_all_field_mismatch":mismatch,
                "abstention_count":len(rows)-exact-mismatch,
                "status_counts":dict(sorted(counts.items())),
                "exact_compared_window_clusters":len({
                    (x["game_id"],x["turn"]) for x in rows
                    if x["status"]=="CONDITIONAL_EXACT_ALL_FIELDS"}),
                "mismatch_compared_window_clusters":len({
                    (x["game_id"],x["turn"]) for x in rows
                    if x["status"]=="CONDITIONAL_MISMATCH_UNATTRIBUTED"}),
                "NuHost_component_formulas_verified_causally":False,
                "C5_Chunnel_research_experiments_run":0,
            },
            "Tminus1_frozen_conditional_predictions_and_archived_T":rows,
        }
    return roots


def publish(folder,items):
    folder.mkdir(parents=True,exist_ok=True)
    index={}
    for name in FAMILIES:
        path=folder/(name+".json")
        temp=path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(items[name],sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(path)
        index[name]={
            "file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "summary":items[name]["summary"],
        }
        print("===== M2 HISTORICAL DIFFERENTIAL",name,"=====")
        print("status:",items[name]["status"])
        print("summary:",items[name]["summary"])
        print("output:",path)
    manifest={
        "schema":SCHEMA,
        "status":"M2_FOUR_FAMILY_HISTORICAL_ARCHIVE_COMPARISONS_COMPLETE",
        "all_four_complete":len(index)==4,
        "reports":index,"new_corpus_sha256":DB_SHA256,
        "source_V25_manifest_git_blob_sha1":V25_MANIFEST_BLOB,
        "read_only_no_CURRENT_modification":True,
        "causal_NuHost_parity_claimed":False,
        "C5_frozen_not_reopened":True,
    }
    dest=folder/"manifest.json"
    temp=dest.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    temp.replace(dest)
    print("===== M2 HISTORICAL DIFFERENTIAL ALL FOUR REPORTS COMPLETE =====")
    print("status:",manifest["status"])
    print("output:",dest)



def run_windows(conn,windows):
    """One global PRE freeze, then POST; testable absolute phase barrier."""
    pre={}
    for i,(game,turn) in enumerate(windows,1):
        print(f"[m2-archive-v1] PRE [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        pre[game,turn]=pre_window(conn,game,turn)
    # ABSOLUTE GLOBAL BARRIER: only now inspect any T archive record.
    grouped={name:[] for name in FAMILIES}
    for i,(game,turn) in enumerate(windows,1):
        print(f"[m2-archive-v1] POST [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        after=post_window(conn,game,turn)
        result=compare(pre[game,turn],after)
        for family in FAMILIES:grouped[family].extend(result[family])
    return pre,grouped


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--database",type=Path,required=True)
    parser.add_argument("--v25-manifest",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    try:
        selected=frozen_manifest(args.v25_manifest)
        db=args.database.resolve()
        if not db.is_file() or db.name!=GENERATION:
            raise ValueError("new public8 explicit corpus DB absent")
        print("[m2-archive-v1] verify original V25 public8 SHA256 once",flush=True)
        t0=time.monotonic()
        with db.open("rb") as fd:sha=hashlib.file_digest(fd,"sha256").hexdigest()
        if sha!=DB_SHA256:raise ValueError("public8 immutable generation SHA256 drift")
        print(f"[m2-archive-v1] SHA verified in {time.monotonic()-t0:.1f}s",flush=True)
        conn=duckdb.connect(str(db),read_only=True)
        try:
            games={int(row[0]) for row in conn.execute(
                "SELECT game_id FROM source_archives").fetchall()}
            if games!=set(selected):raise ValueError("V25 selected game IDs differ from corpus")
            metadata=conn.execute(
                "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
            ).fetchall()
            windows=choose_metadata_windows(metadata,selected)
            pre,grouped=run_windows(conn,windows)
            if not any(grouped.values()):
                raise ValueError("no owner-current source planets selected")
            output=reports(selected,windows,pre,grouped)
        finally:conn.close()
        publish(args.output_dir,output)
    except (OSError,TypeError,ValueError,KeyError,duckdb.Error,json.JSONDecodeError) as e:
        print("ERROR M2 archival:",e,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
