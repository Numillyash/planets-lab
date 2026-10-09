from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "diagnostics" / "combat_mass_rulebook_reconciliation_v2.py"
SPEC = importlib.util.spec_from_file_location("combat_mass_rulebook_reconciliation_v2", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def side(*, game=1, turn=10, vcr=1, ship=99,
         hull=35, catalog=451, actual=453,
         race=4, engine=1, original="unexplained_with_available_owner_geometry",
         left_bays=0, owner_present=True, candidate=True):
    if engine==1:
        cost=1
    elif engine==5:
        cost=25
    elif engine==6:
        cost=53
    elif engine==9:
        cost=300
    else:
        cost=None
    bonus=M.SHIELD_BONUS_BY_ENGINE.get(engine)
    scenario=[]
    if candidate and bonus:
        for n in (1,2):
            for carrier in (0,360) if left_bays and actual > 360 else (0,):
                if actual==catalog+n*bonus+carrier:
                    scenario.append({
                        "generator_count_assumed":n,
                        "one_generator_bonus":bonus,
                        "carrier_plus360_branch_assumed":carrier,
                    })
    return {
        "game_id":game,"turn":turn,"vcr_id":vcr,"ship_id":ship,
        "side":"left","owner_id":4,"race":race,"hull_id":hull,
        "catalog_hull_mass":catalog,"federation_adjusted_base":catalog,
        "observed_vcr_mass":actual,"VCR_left_baycount":left_bays,
        "tminus1_owner_engine_id":engine,
        "tminus1_owner_ship_available":owner_present,
        "tminus1_owner_clans":900 if race==12 else 0,
        "geometry":{
            "tminus1_participant_at_site":True,
            "exact_site_generators":2,
            "same_origin_and_waypoint_generators":2,
        } if owner_present else {"status":"UNKNOWN_OWNER_OR_SITE"},
        "ceil_rounding_hypotheses":{
            "status":"TMINUS1_SITE_SUPPORT" if owner_present else "UNKNOWN_ENGINE_COST",
            "match_candidates":scenario,
        },
        "original_class":original,
        "horwasp_clan_inverse_hypotheses":[
            {"base_source":"game_catalog","clan_min":900,"clan_max":900}
        ] if race==12 else [],
    }


def test_published_engine_table_not_floor_half():
    assert [M.SHIELD_BONUS_BY_ENGINE[e] for e in (1,3,5,6,7,9)] == [
        1,2,13,27,85,150,
    ]
    for engine,catalog,actual in [(1,100,102),(5,100,126),(6,100,154)]:
        item=side(engine=engine,catalog=catalog,actual=actual)
        got=M.classify(item)
        assert got["status"]=="documented_shield_bonus_numeric_match_not_precombat_proof"
        assert got["rulebook_numeric_candidates"][0]["generator_count_assumed"]==2
        assert got["Tminus1_phase_label"]=="TMINUS1_SITE_SUPPORT"


def test_d19c_external_reference_does_not_mutate_game_catalog():
    for game,actual,engine in [(217591,346,9),(325434,48,1)]:
        original=side(
            game=game,hull=1039,catalog=96,actual=actual,engine=engine,candidate=False
        )
        result=M.classify(original)
        assert result["status"]=="reference_hull_catalog_conflict_numeric_match_not_proven"
        assert result["historical_catalog_disagreement_KT"]==50
        assert result["source_catalog_mass"]==96
        assert result["reference_hull_base_mass"]==46
        assert result["rulebook_numeric_candidates"][0]["generator_count_assumed"]==2
        assert original["catalog_hull_mass"]==96


def test_missing_owner_does_not_become_generator_confirmation():
    item=side(
        game=617883,hull=94,catalog=645,actual=795,
        engine=None,owner_present=False,candidate=False,
    )
    outcome=M.classify(item)
    assert outcome["status"]=="open_missing_owner_or_other_mechanism"
    assert outcome["open_reason"]=="NO_OWNER_TMINUS1_SHIP"


def test_horwasp_inverse_kept_observational():
    item=side(
        game=217591,hull=117,catalog=125,actual=290,race=12,engine=7,
        original="horwasp_other_or_catalog_conflict",candidate=False,
    )
    result=M.classify(item)
    assert result["status"]=="horwasp_inverse_only_not_generatively_validated"
    assert result["inverse_is_oracle_observed_mass_dependent"] is True
    item["horwasp_clan_inverse_hypotheses"]=[]
    with pytest.raises(ValueError,match="Horwasp inverse"):
        M.classify(item)


def test_source_candidate_disagreement_fails_closed():
    sample=side(catalog=451,actual=453)
    sample["ceil_rounding_hypotheses"]["match_candidates"]=[]
    with pytest.raises(ValueError,match="disagree"):
        M.classify(sample)


def test_frozen_67_deduplicated_and_four_disjoint_categories():
    rows=[]
    for i in range(49):
        item=side(
            game=10,turn=1,vcr=i+1,ship=100+i%24,
            catalog=451,actual=453,engine=1,
        )
        rows.append(item)
    for i,(game,actual,engine) in enumerate([(217591,346,9),(325434,48,1)]):
        rows.append(side(
            game=game,turn=1,vcr=100+i,ship=501+i,
            hull=1039,catalog=96,actual=actual,engine=engine,candidate=False,
        ))
    for i in range(15):
        rows.append(side(
            game=20,turn=2,vcr=200+i,ship=600+i%13,
            hull=117,catalog=125,actual=290,race=12,engine=7,
            original="horwasp_other_or_catalog_conflict",candidate=False,
        ))
    rows.append(side(game=617883,turn=201,vcr=1017,ship=27,
                     hull=94,catalog=645,actual=795,
                     engine=None,owner_present=False,candidate=False))
    payload={
        "schema":M.SOURCE_SCHEMA,
        "status":"COMPLETE_ALL_67_RESIDUALS_RECONSTRUCTED_NOT_PROMOTED",
        "summary":{
            "all_residual_vcr_sides_recovered":67,
            "newly_recovered_ids":27,
            "distinct_ship_turn_groups":40,
        },
        "source":{"survey_commit":"fixture","survey_experiment_id":"a"*64},
        "all_residual_vcr_sides":rows,
    }
    result=M.build_report(payload)
    assert result["summary"]["distinct_ship_turn_groups"]==40
    assert result["summary"]["per_group"][
        "documented_shield_bonus_numeric_match_not_precombat_proof"
    ]["vcr_sides"]==49
    assert len(result["D19c_source_conflicts"])==2
    assert len(result["unresolved_cases"])==1
    payload["all_residual_vcr_sides"][1]["vcr_id"]=1
    with pytest.raises(ValueError,match="duplicate VCR"):
        M.build_report(payload)


def test_runner_syntax_and_no_database_write():
    a=ROOT/"tools"/"run-combat-mass-rulebook-reconciliation-v2.sh"
    b=ROOT/"tools"/"run-combat-mass-rulebook-reconciliation-v2-with-evidence.sh"
    subprocess.run(["bash","-n",str(a)],check=True)
    subprocess.run(["bash","-n",str(b)],check=True)
    assert "mass-residual-complete-v1/published/residuals.json" in a.read_text()
    assert "run-with-runtime-evidence.sh" in b.read_text()
    assert "corpus-db-generation" not in a.read_text()
