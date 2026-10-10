from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/combat_mass_late_residual_prestate_audit_v1.py"
SPEC = importlib.util.spec_from_file_location("late_residual_phase_audit", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def ref(owner=4, game=800, turn=40, member=101):
    return SimpleNamespace(game_id=game, archive_turn=turn-1,
                           embedded_turn=turn-1, perspective_player_id=owner,
                           member_id=member)


def historical(owner=4, game=800, turn=40, clans=500, sg_id=300):
    return {
        "game": {"id": game, "turn": turn-1},
        "ships": [
            {"id": 27, "ownerid": owner, "hullid": 117,
             "engineid": 9, "clans": clans, "x": 120, "y": 220,
             "targetx": 130, "targety": 220},
            {"id": sg_id, "ownerid": owner, "hullid": 406,
             "x": 130, "y": 220},
        ],
        "hulls": [
            {"id": 117, "mass": 145, "cargo": 900, "name": "Brood"},
            {"id": 406, "mass": 80, "name": "Saber Shield Generator"},
        ],
    }


def frozen_side(delta=360, race=2):
    mass = 100 + delta
    return {
        "game_id": 800, "turn": 40, "cohort": "LATE_85TH_PERCENTILE",
        "vcr_id": 1, "side": "right",
        "identity_from_current_VCR_not_predicted":
            {"owner_id": 4, "ship_id": 27, "hull_id": 117},
        "Tminus1_static_component": {"status": "RESOLVED",
                                    "predicted_hull_mass_KT": 100},
        "Tminus1_owner_race": {"status": "RESOLVED_TMINUS1_OWNER_RACE",
                              "owner_raceid_Tminus1": race},
        "conditional_race_component":
            {"status": "CONDITIONAL_DOCUMENTED_RACE_COMPONENT",
             "conditional_hull_plus_race_mass_KT": 100},
        "postforecast_evaluation": {
            "status": "COMPARATOR_AVAILABLE",
            "observed_vcr_mass_KT": mass,
            "factual_minus_conditional_candidate_KT": delta,
            "conditional_candidate_equals_full_observed_mass": delta == 0,
        },
    }


def vcr_payload(delta=360, left_bays=8, race=2):
    return {
        "x": 130, "y": 220, "leftownerid": 3, "rightownerid": 4,
        "left": {"hullid": 9, "objectid": 99,
                 "raceid": 3, "mass": 180, "baycount": left_bays},
        "right": {"hullid": 117, "objectid": 27, "raceid": race,
                  "mass": 100 + delta, "baycount": 0},
    }


def test_documented_source_blob_pin():
    raw = b"hello\n"
    expected = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    assert M.blob_sha1(raw) == expected
    assert M.blob_sha1(raw+b"x") != expected


@pytest.mark.parametrize("delta,side,race,left_bays,expected", [
    (0, "right", 4, 8, "BASELINE_EQUALITY_CONTROL"),
    (360, "right", 4, 8, "RIGHT_PLUS360_NUMERIC_CANDIDATE"),
    (360, "left", 4, 8, "OTHER_POSITIVE_OR_NEGATIVE_RESIDUAL"),
    (360, "right", 12, 8, "HORWASP_MUTABLE_MASS_OPEN"),
    (145, "left", 12, 0, "HORWASP_MUTABLE_MASS_OPEN"),
    (1, "right", 4, None, "OTHER_POSITIVE_OR_NEGATIVE_RESIDUAL"),
])
def test_observed_numeric_labels_do_not_promote_host_rules(
    delta, side, race, left_bays, expected,
):
    result = M.classify_observed_residual(
        delta=delta, side=side, raceid=race,
        left_vcr_bays=left_bays,
    )
    assert result["class"] == expected
    assert result["host_random_branch_predicted"] is False
    assert result["horwasp_clan_attrition_predicted"] is False
    assert result["shield_generator_activation_predicted"] is False


def test_owner_ship_from_only_owner_tminus1_and_exact_archive():
    refs = [(ref(4, member=101), historical()),
            (ref(4, member=102), historical())]
    output = M._owner_ship_in_archive(
        refs, game=800, turn=40, owner=4, ship_id=27,
    )
    assert output["status"] == "RESOLVED_TMINUS1_OWNER_SHIP"
    assert output["tminus1_ship"]["clans"] == 500
    assert output["tminus1_ship"]["engineid"] == 9
    assert output["owner_member_ids"] == [101, 102]
    out = M._site_and_sg_context(refs, owner=4, site=(130, 220))
    assert out["Tminus1_exact_site_generator_count"] == 1
    assert out["activation_proven"] is False


def test_owner_ship_conflicts_and_future_snapshot_never_oracle_backfill():
    a = (ref(4, member=101), historical())
    b = (ref(4, member=102), historical(clans=600))
    assert M._owner_ship_in_archive(
        [a,b], game=800, turn=40, owner=4, ship_id=27,
    )["status"] == "ABSTAIN_CONFLICTING_TMINUS1_OWNER_SHIP"
    f = ref(4, turn=41, member=102)
    assert M._owner_ship_in_archive(
        [a,(f,historical(turn=41))],
        game=800, turn=40, owner=4, ship_id=27,
    )["status"] == "ABSTAIN_INVALID_HISTORICAL_PROVENANCE"
    assert M._owner_ship_in_archive(
        [(ref(owner=3), historical(owner=3))],
        game=800, turn=40, owner=4, ship_id=27,
    )["status"] == "ABSTAIN_MISSING_OWNER_PERSPECTIVE"


def test_missing_owner_tminus1_clans_are_not_inferred_from_mass():
    h = historical(clans=None)
    output = M._owner_ship_in_archive(
        [(ref(),h)], game=800, turn=40, owner=4, ship_id=27
    )
    assert output["status"] == "RESOLVED_TMINUS1_OWNER_SHIP"
    assert output["tminus1_ship"]["clans"] is None


def test_full_annotation_retrospective_carrier_and_independent_owner_clans():
    old = frozen_side(delta=360, race=2)
    w = {"game_id": 800, "turn": 40, "cohort": "LATE_85TH_PERCENTILE"}
    row = M.annotate_side(
        w, old, vcr_payload(delta=360, left_bays=8),
        [(ref(), historical())],
    )
    assert row["observational_residual"]["class"] == "RIGHT_PLUS360_NUMERIC_CANDIDATE"
    assert row["observational_residual"]["carrier_side_and_VCR_bays_condition"] is True
    assert row["retrospective_VCR_site_Tminus1_SG_geometry"][
        "Tminus1_exact_site_generator_count"
    ] == 1
    assert row["documented_SG_bonus_if_activated_KT"] == 150
    assert row["independent_Tminus1_clan_and_capacity"] == {
        "clans": 500,
        "hull_cargo_capacity": 900,
        "independently_precombat_seen": True,
    }
    # Changing observed VCR mass without changing original frozen evidence
    # must fail rather than silently re-interpret the residual.
    with pytest.raises(ValueError, match="identity drift"):
        M.annotate_side(w, old, vcr_payload(delta=361),
                        [(ref(), historical())])


def test_vcr_race_disagreement_is_not_silent():
    w = {"game_id": 800, "turn": 40, "cohort": "LATE_85TH_PERCENTILE"}
    with pytest.raises(ValueError, match="identity drift"):
        M.annotate_side(w, frozen_side(), vcr_payload(race=3),
                        [(ref(), historical())])


def test_runner_and_wrapper_have_valid_bash_and_do_not_touch_current():
    script = ROOT / "tools/run-combat-mass-late-residual-prestate-audit-v1.sh"
    wrapper = ROOT / "tools/run-combat-mass-late-residual-prestate-audit-v1-with-evidence.sh"
    for path in (script, wrapper):
        subprocess.run(["bash", "-n", str(path)], check=True)
    assert "CURRENT" not in script.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "mass-independent-late-turn-stress-v1/published/report.json" in script.read_text()
