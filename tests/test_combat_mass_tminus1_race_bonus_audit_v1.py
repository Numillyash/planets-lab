from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/combat_mass_tminus1_race_bonus_audit_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_mass_tminus1_race_bonus", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def ref(owner: int, member: int, game: int = 235762,
        turn: int = 7, embedded: int = 7):
    return SimpleNamespace(
        game_id=game, archive_turn=turn, embedded_turn=embedded,
        perspective_player_id=owner, member_id=member,
    )


def payload(game: int = 235762, turn: int = 7, race: int = 1,
            owner: int = 5):
    return {
        "game": {"id": game, "turn": turn},
        "players": [{"id": owner, "raceid": race},
                    {"id": 3 if owner != 3 else 5, "raceid": 2}],
    }


def samples(*, race: int = 1, owner: int = 5):
    return [
        (ref(owner, 101), payload(race=race, owner=owner)),
        (ref(3 if owner != 3 else 5, 102), payload(race=race, owner=owner)),
    ]


def test_independent_player_race_produces_fed_candidate_without_vcr_mass():
    race = M.resolve_owner_race(samples(), game_id=235762, turn=8, owner=5)
    assert race["status"] == "RESOLVED_TMINUS1_OWNER_RACE"
    assert race["owner_raceid_Tminus1"] == 1
    assert race["perspectives_checked"] == 2
    candidate = M.conditional_candidate(race, 90)
    assert candidate["assumed_federation_bonus_KT"] == 50
    assert candidate["conditional_hull_plus_race_mass_KT"] == 140
    assert candidate["full_combat_mass_prediction_KT"] is None
    a = M.evaluate(candidate, race, factual_mass=140, factual_raceid=1)
    b = M.evaluate(candidate, race, factual_mass=300, factual_raceid=3)
    assert a["conditional_candidate_equals_full_observed_mass"] is True
    assert b["conditional_candidate_equals_full_observed_mass"] is False
    assert candidate["conditional_hull_plus_race_mass_KT"] == 140


def test_non_fed_negative_control_predicts_no_documented_race_increment():
    historical = M.resolve_owner_race(
        samples(race=2), game_id=235762, turn=8, owner=5
    )
    candidate = M.conditional_candidate(historical, 90)
    assert candidate["assumed_federation_bonus_KT"] == 0
    assert candidate["conditional_hull_plus_race_mass_KT"] == 90
    assert M.evaluate(candidate, historical, factual_mass=90, factual_raceid=2)[
        "conditional_candidate_equals_full_observed_mass"
    ] is True


def test_owner_slot_is_not_equated_with_race():
    # Owner5 may control Federation; owner1 may control a different race.
    historical = M.resolve_owner_race(
        [(ref(1, 101), payload(race=2, owner=1)),
         (ref(3, 102), payload(race=2, owner=1))],
        game_id=235762, turn=8, owner=1,
    )
    assert historical["status"] == "RESOLVED_TMINUS1_OWNER_RACE"
    assert historical["owner_raceid_Tminus1"] == 2
    assert M.conditional_candidate(historical, 170)["assumed_federation_bonus_KT"] == 0


@pytest.mark.parametrize("mutation,status", [
    ("race_conflict", "ABSTAIN_CONFLICTING_TMINUS1_OWNER_RACE"),
    ("missing_roster", "ABSTAIN_TMINUS1_PLAYER_ROSTER_MISSING"),
    ("missing_owner", "ABSTAIN_OWNER_NOT_IN_PLAYER_ROSTER"),
    ("duplicate_owner", "ABSTAIN_DUPLICATE_OWNER_PLAYER_ROW"),
    ("bad_race", "ABSTAIN_UNSUPPORTED_OR_MISSING_RACE"),
    ("future_state", "ABSTAIN_UNTRUSTED_TMINUS1_PROVENANCE"),
])
def test_fail_closed_on_conflicting_or_missing_tminus1_roster(mutation, status):
    history = samples()
    if mutation == "race_conflict":
        history[1][1]["players"][0]["raceid"] = 2
    elif mutation == "missing_roster":
        del history[1][1]["players"]
    elif mutation == "missing_owner":
        history[1][1]["players"] = []
    elif mutation == "duplicate_owner":
        history[1][1]["players"].append({"id": 5, "raceid": 1})
    elif mutation == "bad_race":
        history[1][1]["players"][0]["raceid"] = 0
    elif mutation == "future_state":
        history[1] = (ref(3, 102, turn=8, embedded=8),
                      payload(turn=8))
    result = M.resolve_owner_race(history, game_id=235762, turn=8, owner=5)
    assert result["status"] == status
    assert result["owner_raceid_Tminus1"] is None
    assert M.conditional_candidate(result, 90)[
        "conditional_hull_plus_race_mass_KT"
    ] is None


def test_missing_tminus1_owner_perspective_fails_closed():
    history = [(ref(3, 102), payload())]
    assert M.resolve_owner_race(
        history, game_id=235762, turn=8, owner=5,
    )["status"] == "ABSTAIN_OWNER_PERSPECTIVE_MISSING"


def sample_source():
    groups = []
    for game in range(900, 912):
        rows = []
        for idx, (side, mass) in enumerate(
            [("left", 100), ("right", 150 if game in (908, 909) else 100)]
        ):
            rows.append({
                "game_id": game, "turn": 10, "vcr_id": idx+1, "side": side,
                "target_owner_id": 1, "target_hull_id": 5,
                "forecast": {"status": "RESOLVED", "predicted_hull_mass_KT": 100},
                "evaluation": {"status": "COMPARATOR_AVAILABLE", "factual_vcr_mass_KT": mass,
                               "difference_factual_minus_component_KT": mass-100},
            })
        if game in (910, 911):
            rows += [
                {"game_id": game, "turn": 10, "vcr_id": 3, "side": "left",
                 "target_owner_id": 5, "target_hull_id": 9,
                 "forecast": {"status": "RESOLVED", "predicted_hull_mass_KT": 90},
                 "evaluation": {"status": "COMPARATOR_AVAILABLE", "factual_vcr_mass_KT": 140,
                                "difference_factual_minus_component_KT": 50}},
                {"game_id": game, "turn": 10, "vcr_id": 3, "side": "right",
                 "target_owner_id": 2, "target_hull_id": 9,
                 "forecast": {"status": "RESOLVED", "predicted_hull_mass_KT": 90},
                 "evaluation": {"status": "COMPARATOR_AVAILABLE", "factual_vcr_mass_KT": 90,
                                "difference_factual_minus_component_KT": 0}},
            ]
        groups.append({"game_id": game, "turn": 10,
                       "vcr_side_count": len(rows), "predictions": rows})
    # 24 + 4 = 28; add another regular two ship sides.
    groups[0]["predictions"] += [
        {"game_id": 900, "turn": 10, "vcr_id": 4, "side": side,
         "target_owner_id": 2, "target_hull_id": 5,
         "forecast": {"status": "RESOLVED", "predicted_hull_mass_KT": 100},
         "evaluation": {"status": "COMPARATOR_AVAILABLE", "factual_vcr_mass_KT": 100,
                        "difference_factual_minus_component_KT": 0}}
        for side in ("left", "right")
    ]
    groups[0]["vcr_side_count"] = len(groups[0]["predictions"])
    return {
        "schema": M.SOURCE_SCHEMA,
        "status": "EXPERIMENTAL_TMINUS1_STATIC_COMPONENT_PREDICTION_NOT_PROMOTED",
        "corpus_sha256": M.EXPECTED_SHA256,
        "summary": {
            "held_out_games_with_VCRs": 12, "held_out_vcr_sides": 30,
            "static_resolution_statuses": {"RESOLVED": 30},
            "component_equals_full_factual_mass_count": 26,
        },
        "held_out_results": groups,
    }


def test_frozen_baseline_report_rejects_duplicate_or_changed_identities():
    sample = sample_source()
    assert len(M.validate_source(sample)) == 12
    sample["held_out_results"][0]["predictions"][1]["side"] = "left"
    # VCR IDs in synthetic example remain different; force duplicate key.
    sample["held_out_results"][0]["predictions"][1]["vcr_id"] = 1
    with pytest.raises(ValueError, match="duplicate"):
        M.validate_source(sample)


def test_evidence_runners_syntax_and_source_gating():
    runner = ROOT / "tools/run-combat-mass-tminus1-race-bonus-audit-v1.sh"
    wrapper = ROOT / "tools/run-combat-mass-tminus1-race-bonus-audit-v1-with-evidence.sh"
    for p in (runner, wrapper):
        subprocess.run(["bash", "-n", str(p)], check=True)
    assert "mass-time-indexed-static-v1/published/report.json" in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "read-only" in runner.read_text()
