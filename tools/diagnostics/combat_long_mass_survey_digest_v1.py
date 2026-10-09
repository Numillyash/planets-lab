"""Audit frozen 80-game long-survey checkpoints without re-querying corpus.

Counts are exhaustive within original 150-VCR/turn cap; saved VCR
examples are first-N samples and NEVER exhaustive anomaly identities.
No predictive Host mass rule is promoted.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

SOURCE="planets-lab.combat-mass-long-survey.v1"
SCHEMA="planets-lab.combat-mass-long-survey-digest.v1"
UNKNOWN=("unexplained_with_available_owner_geometry",
         "horwasp_other_or_catalog_conflict")
SHIELDS=("engine_shield_1_numeric_match","engine_shield_2_numeric_match",
         "engine_shield_1_plus360_numeric_match","engine_shield_2_plus360_numeric_match")


def _count_dict(data):
    if not isinstance(data,dict):
        raise ValueError("missing counts")
    if any(not isinstance(k,str) or type(v)!=int or v<0 for k,v in data.items()):
        raise ValueError("invalid count")
    return Counter(data)


def _diverse(rows,limit):
    by_game=defaultdict(list)
    for row in rows:
        by_game[row["game_id"]].append(row)
    result=[]
    while len(result)<limit and any(by_game.values()):
        for game in sorted(by_game):
            if by_game[game] and len(result)<limit:
                result.append(by_game[game].pop(0))
    return result


def _shield_context(item):
    cls=item.get("class","")
    if cls not in SHIELDS:
        return "NOT_SHIELD"
    geo=item.get("geometry")
    if not isinstance(geo,dict):
        return "UNKNOWN_OWNER_CONTEXT"
    n=2 if "shield_2_" in cls else 1
    at_site=geo.get("exact_site_generators")
    convoy=geo.get("same_origin_and_waypoint_generators")
    if type(at_site)==int and at_site>=n and geo.get("tminus1_participant_at_site") is True:
        return "TMINUS1_SITE_CONTROL"
    if type(convoy)==int and convoy>=n:
        return "TMINUS1_COTRAVEL_CONTROL"
    return "NO_TMINUS1_SUPPORT_IN_SAVED_SAMPLE"


def _short_example(row):
    keys=("game_id","turn","vcr_id","ship_id","side","race","hull_id",
          "catalog_mass","base_mass","factual_mass","class","owner_id")
    return {k:row.get(k) for k in keys} | {
        "geometry": {k:row.get("geometry",{}).get(k) for k in (
            "engine_id","engine_cost_mc","per_generator_half_engine_cost",
            "exact_site_generators","same_origin_and_waypoint_generators",
            "tminus1_participant_at_site","waypoint_to_vcr_offset")}}
        

def build_digest(summary, checkpoint_dir):
    if summary.get("schema")!=SOURCE or summary.get("status")!="COMPLETE_OBSERVATIONAL_NOT_PROMOTED":
        raise ValueError("source survey was not completed cleanly")
    config=summary.get("config",{})
    chosen=config.get("selection")
    if not isinstance(chosen,list) or not chosen:
        raise ValueError("missing selection")
    selected={}
    for row in chosen:
        if not isinstance(row,list) or len(row)!=2:
            raise ValueError("bad game/turn selection")
        game,turns=row
        if type(game)!=int or game in selected or not isinstance(turns,list) or not turns:
            raise ValueError("duplicate or bad selected game")
        if any(type(t)!=int for t in turns) or len(set(turns))!=len(turns):
            raise ValueError("duplicate or bad turns")
        selected[game]=turns
    if summary.get("completed_games")!=len(selected) or summary.get("target_games")!=len(selected):
        raise ValueError("survey target incomplete")
    if summary.get("game_status_counts")!={"ok":len(selected)}:
        raise ValueError("survey contains failed games")
    identity=summary.get("identity_sha256")
    if not isinstance(identity,str) or len(identity)!=64:
        raise ValueError("source experiment identity missing")
    counts=Counter()
    games=[]; turns=[]; anomalies=[]; shields=[]; changes=[]
    sampled=Counter()
    sampled_timelines=0
    for game,expected_turns in selected.items():
        path=checkpoint_dir/f"game-{game}.json"
        if not path.is_file():
            raise ValueError(f"missing checkpoint game={game}")
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema")!=SOURCE or data.get("identity")!=identity:
            raise ValueError(f"stale checkpoint game={game}")
        result=data.get("result",{})
        record_turns=result.get("turns")
        if (result.get("game_id")!=game or result.get("status")!="ok"
            or result.get("errors")!=[] or not isinstance(record_turns,list)
            or [r.get("turn") for r in record_turns]!=expected_turns):
            raise ValueError(f"invalid game/turn coverage game={game}")
        local=Counter()
        for turn_record in record_turns:
            c=_count_dict(turn_record.get("counts"))
            t=turn_record["turn"]
            if 2*c["ship_vcrs"]-c["missing_effective_side_or_hull_catalog"]!=c["side_observations"]:
                raise ValueError(f"side denominator game={game} T{t}")
            if c["ship_vcrs"]+c["non_ship_vcr"]!=c["unique_vcrs_examined"]:
                raise ValueError(f"VCR denominator game={game} T{t}")
            if sum(v for k,v in c.items() if k.startswith("class:"))!=c["side_observations"]:
                raise ValueError(f"mass class total game={game} T{t}")
            if c["unique_vcrs_examined"]>c["unique_vcrs_available"]:
                raise ValueError("VCR cap broken")
            local.update(c);counts.update(c)
            ex=turn_record.get("examples")
            timeline=turn_record.get("horwasp_timelines")
            if not isinstance(ex,list) or not isinstance(timeline,list):
                raise ValueError("checkpoint examples absent")
            cap=config.get("max_examples_per_turn")
            if type(cap)!=int or len(ex)>cap or len(timeline)>cap:
                raise ValueError("checkpoint detail sample truncated/incompatible")
            for e in ex:
                if e.get("game_id")!=game or e.get("turn")!=t:
                    raise ValueError("example provenance mismatch")
                label=e.get("class")
                sampled[label]+=1
                if label in UNKNOWN:
                    anomalies.append(_short_example(e))
                if label in SHIELDS:
                    sh=_short_example(e)
                    sh["Tminus1_control"]=_shield_context(e)
                    shields.append(sh)
            sampled_timelines+=len(timeline)
            for l in timeline:
                if l.get("game_id")!=game or l.get("turn")!=t:
                    raise ValueError("timeline provenance mismatch")
                for tr in l.get("transitions",[]):
                    if tr.get("mass_delta") != 0:
                        changes.append({
                            "game_id":game,"turn":t,"ship_id":l.get("ship_id"),
                            "from_vcr":tr.get("from"),"to_vcr":tr.get("to"),
                            "mass_delta":tr.get("mass_delta"),
                            "fighter_start_delta":tr.get("fighter_start_delta"),
                            "same_site":tr.get("same_site"),
                            "candidate_clan_changes":tr.get("candidate_clan_changes",[])[:4],
                        })
            turns.append({
                "game_id":game,"turn":t,
                "side_observations":c["side_observations"],
                "ship_vcrs":c["ship_vcrs"],
                "unresolved":sum(c["class:"+u] for u in UNKNOWN),
                "horwasp_transitions":c["horwasp_same_ship_vcr_transitions"],
                "saved_examples":len(ex),
                "max_examples":cap,
            })
        games.append({
            "game_id":game,"side_observations":local["side_observations"],
            "ship_vcrs":local["ship_vcrs"],
            "unresolved_numeric":local["class:"+UNKNOWN[0]],
            "unresolved_horwasp":local["class:"+UNKNOWN[1]],
            "horwasp_changed_mass_transitions":local["horwasp_changed_mass_between_appearances"],
            "horwasp_transitions":local["horwasp_same_ship_vcr_transitions"],
            "engine_shield_numeric":sum(local["class:"+x] for x in SHIELDS),
            "owner_Tminus1_missing":local["participant_Tminus1_owner_missing"],
        })
    if counts!=_count_dict(summary.get("summary")):
        raise ValueError("per-game checkpoints disagree with published aggregate")
    all_unresolved=sum(counts["class:"+u] for u in UNKNOWN)
    sampled_unresolved=sum(sampled[u] for u in UNKNOWN)
    if sampled_unresolved>all_unresolved:
        raise ValueError("sample anomaly count exceeds aggregate")
    games.sort(key=lambda x:(-(x["unresolved_numeric"]+x["unresolved_horwasp"]),
                              -x["horwasp_changed_mass_transitions"],x["game_id"]))
    turns.sort(key=lambda x:(-x["unresolved"],-x["horwasp_transitions"],
                              x["game_id"],x["turn"]))
    changes.sort(key=lambda r:(-abs(r["mass_delta"]),r["game_id"],r["turn"],r["ship_id"]))
    controls=Counter(x["Tminus1_control"] for x in shields)
    return {
        "schema":SCHEMA,
        "status":"COMPLETE_DIGEST_OBSERVATIONAL_NOT_PROMOTED",
        "source":{
            "source_sha":config.get("source_sha"),
            "identity_sha256":identity,
            "games_verified":len(games),
            "turns_verified":len(turns),
            "recomputed_counts_match_published":True,
        },
        "counts":{
            "ship_vcrs":counts["ship_vcrs"],
            "side_observations":counts["side_observations"],
            "missing_side_or_catalog":counts["missing_effective_side_or_hull_catalog"],
            "unresolved_mass_sides":all_unresolved,
            "unresolved_non_horwasp":counts["class:"+UNKNOWN[0]],
            "unresolved_horwasp":counts["class:"+UNKNOWN[1]],
            "unresolved_VCR_details_saved":sampled_unresolved,
            "unresolved_VCR_details_unsaved":all_unresolved-sampled_unresolved,
            "engine_shield_arithmetic_sides":sum(counts["class:"+x] for x in SHIELDS),
            "saved_shield_detail_samples":len(shields),
            "horwasp_changed_mass_transitions":counts["horwasp_changed_mass_between_appearances"],
            "horwasp_transitions":counts["horwasp_same_ship_vcr_transitions"],
            "saved_horwasp_timelines":sampled_timelines,
        },
        "ranked_games":games,"ranked_turns":turns,
        "sampled_unresolved_examples":_diverse(anomalies,35),
        "Tminus1_shield_sample_control_counts":dict(sorted(controls.items())),
        "sampled_shield_controls":_diverse(shields,32),
        "sampled_horwasp_mass_changes":_diverse(changes,40),
        "coverage_boundary":{
            "original_per_turn_VCR_cap":config.get("max_vcrs_per_turn"),
            "original_first_N_examples_per_turn":config.get("max_examples_per_turn"),
            "all_game_turn_class_counts_are_complete_within_VCR_cap":True,
            "saved_example_VCR_identities_are_NOT_exhaustive":True,
            "unsaved_case_ids_need_targeted_corpus_rescan":True,
        },
        "evidence_boundary":(
            "Factual current VCR mass was used to classify numeric patterns, "
            "not independently predict Host mass. T-1 site/co-travel generator "
            "geometry does not prove precombat effects; Shield Generator "
            "control frequencies apply to first-N examples only. "
            "Horwasp clan intervals are conditional inversions; differences "
            "across observed VCR starts are not predictive attrition laws."
        ),
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--survey-summary",type=Path,required=True)
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        survey=json.loads(args.survey_summary.read_text(encoding="utf-8"))
        digest=build_digest(survey,args.checkpoint_dir)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=args.output.with_suffix(".tmp")
        temp.write_text(json.dumps(digest,sort_keys=True,indent=2,ensure_ascii=False)+"\n",
                        encoding="utf-8")
        temp.replace(args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc)
        return 2
    print("===== COMBAT LONG MASS SURVEY DIGEST V1 =====")
    print("status:",digest["status"])
    print("source:",digest["source"])
    print("counts:",digest["counts"])
    print("shield_sample_controls:",digest["Tminus1_shield_sample_control_counts"])
    print("top_games:",digest["ranked_games"][:10])
    print("top_turns:",digest["ranked_turns"][:10])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
