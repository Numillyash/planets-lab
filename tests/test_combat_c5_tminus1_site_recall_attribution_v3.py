from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_tminus1_site_recall_attribution_v3.py"
SPEC=importlib.util.spec_from_file_location("c5_spatial_recall_v3",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def predicted(ship,*,owner=2,pos=(100,200),source="NORMAL_MOVEMENT",raw=(40,50)):
    return {
        "ship_id":ship,"owner_id":owner,"position":pos,"source":source,
        "raw":{"id":ship,"ownerid":owner,"x":raw[0],"y":raw[1],
               "warp":5,"targetx":100,"targety":200}
    }


def test_site_position_equality_and_non_integer_fail_closed():
    assert M.same_site((100,200),100,200)
    assert M.same_site([100,200],100,200)
    assert not M.same_site((100,201),100,200)
    assert not M.same_site(("100",200),100,200)
    assert not M.same_site((True,200),100,200)
    assert not M.same_site(None,100,200)


def test_distinguish_missing_wrong_unresolved_owner_and_correct_Tminus1():
    records={
        12:predicted(12,pos=(100,200)),
        13:predicted(13,pos=(101,200)),
        14:predicted(14,pos=None,source="TOW_UNRESOLVED"),
        15:predicted(15,owner=3),
    }
    expected={
        12:"TMINUS1_PREDICTS_FACTUAL_SITE",
        13:"TMINUS1_PREDICTS_DIFFERENT_SITE",
        14:"TMINUS1_POSITION_UNRESOLVED",
        15:"TMINUS1_OWNER_DIFFERS_FROM_NEXT_VCR",
        16:"TMINUS1_SHIP_NOT_IN_OWNER_ARCHIVE",
    }
    for sid,status in expected.items():
        row=M.predicted_next_participant(
            ship_id=sid,owner_id=2,site=(100,200),
            predictions=records,current_ship_ids=frozenset((12,)),
            history_ship_ids=frozenset((12,14)))
        assert row["Tminus1_position_class"]==status
        assert row["factual_next_identity_used_only_for_posthoc_attribution"]
        if sid==12:
            assert row["in_prior_N"] and row["seen_at_site_before_or_during_N"]
        if sid==14:
            assert row["source"]=="TOW_UNRESOLVED"
            assert row["predicted_position"] is None
        if sid==13:
            assert row["raw_Tminus1_x_y"]==[40,50]
    with pytest.raises(ValueError,match="invalid factual next ship"):
        M.predicted_next_participant(
            ship_id=0,owner_id=2,site=(100,200),predictions=records,
            current_ship_ids=frozenset(),history_ship_ids=frozenset())


def test_two_ship_classification_not_conflated_with_full_host_prediction():
    a={"Tminus1_position_class":"TMINUS1_PREDICTS_FACTUAL_SITE"}
    b={"Tminus1_position_class":"TMINUS1_POSITION_UNRESOLVED"}
    c={"Tminus1_position_class":"TMINUS1_SHIP_NOT_IN_OWNER_ARCHIVE"}
    assert M.outcome_class([a,a])=="NEXT_PAIR_BOTH_TMINUS1_AT_SITE"
    assert M.outcome_class([a,b])=="NEXT_PAIR_ONE_TMINUS1_AT_SITE"
    assert M.outcome_class([b,b])=="NEXT_PAIR_NEITHER_TMINUS1_AT_SITE"
    assert M.outcome_class([a,c])=="NEXT_PAIR_MISSING_TMINUS1_SHIP"


def test_future_identity_only_inside_posthoc_inspection():
    context={
        "predictions":{12:predicted(12),13:predicted(13,pos=None)},
        "factual_queue":[
            {"vcr_id":10,"left_ship_id":12,"right_ship_id":20},
            {"vcr_id":11,"left_ship_id":12,"right_ship_id":13},
        ]
    }
    frozen={"from_vcr_id":10,"to_vcr_id":11,
            "status":"ABSTAIN_PARENT_STANDARD_NO_PAIR",
            "prediction":None,"factual_comparison":{"exact":None}}
    future={**context["factual_queue"][1],"owners_by_ship_id":{12:2,13:2}}
    out=M.inspect_after_v2_verdict(
        frozen_transition=frozen,current=context["factual_queue"][0],
        next_row=future,site=(100,200),context=context)
    assert out["frozen_conditional_V2_status"]==frozen["status"]
    assert out["posthoc_next_pair_Tminus1_class"]=="NEXT_PAIR_ONE_TMINUS1_AT_SITE"
    assert out["from_VCR"]==10 and out["to_VCR"]==11
    assert out["next_VCR_used_in_prediction"] is False
    assert out["posthoc_factual_Nplus1_dependent"] is True
    assert out["posthoc_next_ship_Tminus1_positions"][0]["in_prior_N"]
    assert out["posthoc_next_ship_Tminus1_positions"][1]["source"]=="NORMAL_MOVEMENT"


def test_frozen_future_chronology_and_missing_owner_fail_closed():
    context={"predictions":{12:predicted(12)},
             "factual_queue":[{"vcr_id":10,"left_ship_id":12,"right_ship_id":20}]}
    verdict={"from_vcr_id":10,"to_vcr_id":11,
             "status":"ABSTAIN_PARENT_STANDARD_NO_PAIR",
             "prediction":None}
    n={"vcr_id":10,"left_ship_id":12,"right_ship_id":20}
    future={"vcr_id":11,"left_ship_id":12,"right_ship_id":13}
    with pytest.raises(ValueError,match="owner mapping"):
        M.inspect_after_v2_verdict(
            frozen_transition=verdict,current=n,next_row=future,
            site=(100,200),context=context)
    bad={**verdict,"to_vcr_id":13}
    with pytest.raises(ValueError,match="adjacent"):
        M.inspect_after_v2_verdict(
            frozen_transition=bad,current=n,next_row={**future,"vcr_id":13},
            site=(100,200),context=context)


def test_frozen_source_integrity_and_runner():
    assert len(M.CENSUS_BLOB)==40 and len(M.CONDITIONAL_V2_BLOB)==40
    run=ROOT/"tools/run-combat-c5-tminus1-site-recall-attribution-v3.sh"
    wrapper=ROOT/"tools/run-combat-c5-tminus1-site-recall-attribution-v3-with-evidence.sh"
    for name in (run,wrapper):
        subprocess.run(["bash","-n",str(name)],check=True)
    r=run.read_text()
    assert M.CENSUS_BLOB in r and M.CONDITIONAL_V2_BLOB in r
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "/CURRENT" not in r
