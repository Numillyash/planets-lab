from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from planets_lab.rules.combat.site_input_adapter import (
    EvidenceInputUnresolved,potential_tminus1_site_arrivals,
)

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_parent_queue_arrival_uncertainty_v4.py"
SPEC=importlib.util.spec_from_file_location("c5_arrival_v4",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def pred(ship, *, owner=3, source="normal_mine_route_risk",
         x=100,y=200,tx=101,ty=200,position=None,race=4):
    return {"ship_id":ship,"owner_id":owner,"hull_id":35,
            "race_id":race,"position":position,"source":source,
            "raw":{"id":ship,"ownerid":owner,"x":x,"y":y,
                   "targetx":tx,"targety":ty,"warp":1}}


def test_tminus1_waypoint_and_start_can_invalidate_exhausted_queue():
    rows={12:pred(12),13:pred(13,x=101,y=200,tx=130,ty=210),
          14:pred(14,x=150,y=150,tx=180,ty=180)}
    seen=potential_tminus1_site_arrivals(
        predictions=rows,active_ships={1:{"owner_id":8}},
        site=(101,200))
    assert [s.ship_id for s in seen]==[12,13]
    assert seen[0].waypoint_at_site and not seen[0].start_at_site
    assert seen[1].start_at_site and not seen[1].waypoint_at_site
    assert seen[0].position_source=="normal_mine_route_risk"


def test_no_future_no_oracle_and_no_physical_position_inferred():
    rows={12:pred(12,position=(101,200)),
          13:pred(13,position=(99,199)),
          14:pred(14)}
    initial=dict(rows)
    selected=potential_tminus1_site_arrivals(
        predictions=rows,active_ships={1:{"owner_id":8}},site=(101,200))
    assert [s.ship_id for s in selected]==[14]
    assert rows==initial
    assert "next_vcr" not in potential_tminus1_site_arrivals.__code__.co_varnames


def test_same_owner_and_removed_no_fake_opponents():
    rows={12:pred(12,owner=8),
          13:pred(13,owner=3),
          14:pred(14,owner=5)}
    selected=potential_tminus1_site_arrivals(
        predictions=rows,active_ships={1:{"owner_id":8}},
        previously_removed_ship_ids=frozenset({14}),site=(101,200))
    assert [s.ship_id for s in selected]==[13]
    none=potential_tminus1_site_arrivals(
        predictions={12:pred(12,owner=8)},
        active_ships={1:{"owner_id":8}},site=(101,200))
    assert not none


def test_invalid_identity_horwasp_or_unresolved_nonlocal_not_admitted():
    rows={
        12:pred(12,race=12),
        13:pred(13,x=200,y=250,tx=240,ty=270),
        14:pred(14),
        15:pred(15,owner=2),
    }
    rows[14]["raw"]["ownerid"]=99
    selected=potential_tminus1_site_arrivals(
        predictions=rows,active_ships={1:{"owner_id":8}},site=(101,200))
    assert [s.ship_id for s in selected]==[15]
    with pytest.raises(EvidenceInputUnresolved):
        potential_tminus1_site_arrivals(
            predictions=rows,active_ships={},site=(True,200))


def test_unguarded_no_pair_not_promoted_even_when_index_is_empty():
    frozen={"from_vcr_id":111,"status":"ABSTAIN_PARENT_STANDARD_NO_PAIR",
            "factual_comparison":{"exact":None}}
    payload={"leftownerid":8,"rightownerid":9,
             "left":{"objectid":1},"right":{"objectid":2}}
    guarded=M.guarded_transition(
        frozen=frozen,predictions={12:pred(12)},
        current_vcr_payload=payload,site=(101,200))
    assert guarded["risk_status"]=="ABSTAIN_PLAUSIBLE_UNRESOLVED_TMINUS1_ARRIVALS"
    assert guarded["independent_Tminus1_plausible_arrival_count"]==1
    assert guarded["future_Nplus1_used"] is False
    assert guarded["original_next_pair_or_side_changed"] is False
    negative=M.guarded_transition(
        frozen=frozen,predictions={12:pred(12,x=140,y=150,tx=141,ty=151)},
        current_vcr_payload=payload,site=(101,200))
    assert negative["risk_status"]=="NO_PAIR_NOT_PROVEN_NO_ARRIVALS_IN_LIMITED_TMINUS1_INDEX"


def test_original_predictions_cannot_become_claimed_full_host_results():
    payload={"leftownerid":8,"rightownerid":9,
             "left":{"objectid":1},"right":{"objectid":2}}
    frozen={"from_vcr_id":111,"status":"CONDITIONAL_PARENT_STANDARD_N_TO_NPLUS1",
            "factual_comparison":{"exact":True},"prediction":{"pair":[1,2]}}
    result=M.guarded_transition(
        frozen=frozen,predictions={12:pred(12)},
        current_vcr_payload=payload,site=(101,200))
    assert result["risk_status"]=="ORIGINAL_VERDICT_UNCHANGED_OBSERVATIONAL_RISK"
    assert result["original_conditional_v2_exact"] is True
    assert result["original_next_pair_or_side_changed"] is False


def test_frozen_transition_accounting_preserves_multiplicity_and_missing():
    site={"adjacent_pairs":[(100,101),(101,102)]}
    first={"from_vcr_id":100,"to_vcr_id":101}
    second={"from_vcr_id":101,"to_vcr_id":102}
    M._validate_frozen_transition_membership(site,{"transitions":[first],"missing":1})
    M._validate_frozen_transition_membership(
        site,{"transitions":[first,second],"missing":0})
    # Old set-only logic incorrectly accepted a duplicated first row with
    # missing=1: two serialized rows, but only one unique transition.
    with pytest.raises(ValueError,match="duplicate frozen V2"):
        M._validate_frozen_transition_membership(
            site,{"transitions":[first,dict(first)],"missing":1})
    with pytest.raises(ValueError,match="membership/count drift"):
        M._validate_frozen_transition_membership(
            site,{"transitions":[first,{"from_vcr_id":101,"to_vcr_id":103}],
                  "missing":0})
    for invalid in (-1,True,"1",None):
        with pytest.raises(ValueError,match="list/count unavailable"):
            M._validate_frozen_transition_membership(
                site,{"transitions":[first],"missing":invalid})
    with pytest.raises(ValueError,match="duplicate census"):
        M._validate_frozen_transition_membership(
            {"adjacent_pairs":[(100,101),(100,101)]},
            {"transitions":[first],"missing":1})


def test_missing_tminus1_index_is_abstention_not_empty_safe_index():
    frozen={"from_vcr_id":111,"status":"ABSTAIN_PARENT_STANDARD_NO_PAIR",
            "factual_comparison":{"exact":None}}
    payload={"leftownerid":8,"rightownerid":9,
             "left":{"objectid":1},"right":{"objectid":2}}
    with pytest.raises(ValueError,match="T-1 prediction index unavailable"):
        M.guarded_transition(
            frozen=frozen,predictions=None,
            current_vcr_payload=payload,site=(101,200))
    with pytest.raises(EvidenceInputUnresolved,match="T-1 .* index unavailable"):
        potential_tminus1_site_arrivals(
            predictions=None,active_ships={1:{"owner_id":8}},
            site=(101,200))


def test_provenance_pins_and_evidence_wrapper():
    run=ROOT/"tools/run-combat-c5-parent-queue-arrival-uncertainty-v4.sh"
    wrapper=ROOT/"tools/run-combat-c5-parent-queue-arrival-uncertainty-v4-with-evidence.sh"
    for file in (run,wrapper):
        subprocess.run(["bash","-n",str(file)],check=True)
    source=run.read_text()
    assert M.CENSUS_SHA1 in source and M.V2_SHA1 in source
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "/CURRENT" not in source
