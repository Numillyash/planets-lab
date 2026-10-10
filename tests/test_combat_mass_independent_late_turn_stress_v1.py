from __future__ import annotations

import importlib.util
import hashlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/combat_mass_independent_late_turn_stress_v1.py"
SPEC = importlib.util.spec_from_file_location("combat_mass_late_stress", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_git_blob_source_pin_is_content_sensitive():
    raw = b"immutable-evidence\n"
    manual = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    assert M.git_blob_sha1(raw) == manual
    assert M.git_blob_sha1(raw + b"x") != manual


def test_stratified_game_holdout_is_deterministic_and_outcome_blind():
    pairs = [
        (game, turn)
        for game in (100, 101, 102, 103, 104, 105, 106)
        for turn in (5, 10, 18, 27, 40, 55)
    ]
    result, meta = M.select_early_late_windows(
        list(reversed(pairs)), excluded_games={100, 101},
        max_games=3,
    )
    assert len(result) == 6
    assert meta["eligible_game_count_before_sampling"] == 5
    assert meta["selected_game_count"] == 3
    assert not set(meta["selected_games"]) & {100, 101}
    assert len({x["game_id"] for x in result}) == 3
    assert {x["cohort"] for x in result} == {
        "EARLY_QUINTILE", "LATE_85TH_PERCENTILE"
    }
    assert sorted(x["turn"] for x in result if x["game_id"] == result[0]["game_id"]) == [
        10, 40
    ]
    assert M.select_early_late_windows(
        pairs, excluded_games={100, 101}, max_games=3
    ) == (result, meta)


@pytest.mark.parametrize("bad", [
    [(20, -1)], [(20, 0)], [(True, 5)], [(20, True)], [(0, 5)],
])
def test_invalid_candidate_turn_metadata_fails_closed(bad):
    with pytest.raises(ValueError, match="invalid archive turn"):
        M.select_early_late_windows(
            bad, excluded_games=set(), max_games=2
        )


def test_short_or_sparse_games_are_not_in_temporal_stress_cohort():
    windows, meta = M.select_early_late_windows(
        [
            (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6),
            (20, 1), (20, 2), (20, 3), (20, 4),
            (30, 1), (30, 6), (30, 11), (30, 19), (30, 29), (30, 40),
        ],
        excluded_games=set(), max_games=24,
    )
    assert meta["selected_games"] == [30]
    assert len(windows) == 2


def make_ref(game, turn, owner):
    return SimpleNamespace(
        game_id=game, archive_turn=turn-1,
        embedded_turn=turn-1, perspective_player_id=owner,
        member_id=game*100000 + turn*10 + owner,
        decoded_payload_sha256=f"{owner:064x}",
    )


def make_payload(game, turn):
    return {
        "game": {"id": game, "turn": turn-1},
        "hulls": [
            {"id": 94, "mass": 100}, {"id": 5, "mass": 170},
        ],
        "players": [
            {"id": 4, "raceid": 1},
            {"id": 5, "raceid": 2},
        ],
    }


def make_vcr(left_race=1, left_mass=150, right_mass=100):
    return {
        "left": {"hullid": 94, "objectid": 27,
                 "mass": left_mass, "raceid": left_race},
        "right": {"hullid": 94, "objectid": 42,
                  "mass": right_mass, "raceid": 2},
        "leftownerid": 4, "rightownerid": 5,
    }


def patch_fake_db(monkeypatch, *, malformed=False, left_race=1):
    def refs(conn, *, game_id, turns, include_embedded_turn):
        assert include_embedded_turn is False
        return [
            make_ref(game_id, next(iter(turns))+1, owner)
            for owner in (4, 5)
        ]
    def reconstruct(conn, refs):
        for ref in refs:
            member = make_payload(ref.game_id, ref.archive_turn+1)
            if malformed and ref.perspective_player_id == 5:
                member["hulls"] = [{"id": 94, "mass": None}]
            yield ref, member
    def vcrs(conn, *, game_id, battle_turns):
        turn = next(iter(battle_turns))
        return {
            (turn, 1): SimpleNamespace(payload=make_vcr(left_race=left_race)),
            (turn, 2): SimpleNamespace(payload=make_vcr(
                left_race=left_race, left_mass=170,
                right_mass=100) | {
                    "right": {"hullid": 0, "mass": 100}
                }),
        }
    monkeypatch.setattr(M, "member_refs_for_turns", refs)
    monkeypatch.setattr(M, "reconstruct_members", reconstruct)
    monkeypatch.setattr(M, "combat_vcr_cases_for_turns", vcrs)


def test_pre_vcr_forecast_separates_mass_from_comparator_and_race(monkeypatch):
    patch_fake_db(monkeypatch, left_race=2)
    selection = {"game_id": 900, "turn": 40, "cohort": "LATE_85TH_PERCENTILE"}
    out = M.evaluate_window(object(), selection)
    assert out["ship_vcr_count"] == 1
    assert len(out["predictions"]) == 2
    assert len(out["excluded_nonship_vcrs"]) == 1
    fed, nonfed = out["predictions"]
    assert fed["conditional_race_component"]["conditional_hull_plus_race_mass_KT"] == 150
    assert fed["Tminus1_owner_race"]["owner_raceid_Tminus1"] == 1
    assert fed["postforecast_evaluation"]["VCR_race_matches_Tminus1_roster"] is False
    assert fed["postforecast_evaluation"][
        "conditional_candidate_equals_full_observed_mass"] is True
    assert nonfed["conditional_race_component"]["conditional_hull_plus_race_mass_KT"] == 100
    assert nonfed["postforecast_evaluation"][
        "conditional_candidate_equals_full_observed_mass"] is True


def test_corrupt_tminus1_static_abstains_without_laundering_other_perspective(
    monkeypatch,
):
    patch_fake_db(monkeypatch, malformed=True)
    out = M.evaluate_window(
        object(), {"game_id": 900, "turn": 40, "cohort": "EARLY_QUINTILE"}
    )
    assert out["status"] == "TMINUS1_STATIC_MALFORMED_ABSTAINED"
    assert out["Tminus1_static_input_failures"]
    for row in out["predictions"]:
        assert row["Tminus1_static_component"]["status"] == (
            "ABSTAIN_MALFORMED_TMINUS1_STATIC"
        )
        assert row["conditional_race_component"]["conditional_hull_plus_race_mass_KT"] is None
        assert row["postforecast_evaluation"][
            "conditional_candidate_equals_full_observed_mass"] is None


def test_unknown_owner_abstains_while_other_side_remains_evaluable():
    snaps = []
    historical = []
    for owner in (4, 5):
        ref = make_ref(900, 40, owner)
        member = make_payload(900, 40)
        historical.append((ref, member))
        snaps.append(M.static.snapshot_from_member(ref, member))
    hull, hist, candidate = M.forecast_pre_vcr_side(
        snaps, historical, game=900, turn=40,
        owner=None, hull=94, malformed_tminus1=False,
    )
    assert hull["status"] == "ABSTAIN_INVALID_CURRENT_TARGET_IDENTITY"
    assert hist["owner_raceid_Tminus1"] is None
    assert candidate["conditional_hull_plus_race_mass_KT"] is None
    hull, hist, candidate = M.forecast_pre_vcr_side(
        snaps, historical, game=900, turn=40,
        owner=5, hull=94, malformed_tminus1=False,
    )
    assert hull["status"] == "RESOLVED"
    assert candidate["conditional_hull_plus_race_mass_KT"] == 100


def test_source_game_boundaries_aggregate_controls_and_full_prior_holdout(
    monkeypatch,
):
    static_groups = [
        {"game_id": 1000+i, "turn": 10, "predictions": []}
        for i in range(12)
    ]
    monkeypatch.setattr(M.race, "validate_source", lambda src: static_groups)
    static_src = {
        "selection": {"excluded_control_games": [
            2000+i for i in range(11)
        ]}
    }
    race_src = {
        "schema": M.race.SCHEMA,
        "status": "TMINUS1_RACE_BONUS_CONDITIONAL_EVIDENCE_NOT_PROMOTED",
        "source_db_sha256": M.EXPECTED_DB_SHA256,
        "summary": {
            "held_out_games": 12, "held_out_ship_VCR_sides": 30,
            "conditional_candidates_evaluable": 30,
            "conditional_candidates_matching_full_VCR_mass": 30,
            "full_combat_mass_predictions_made": 0,
        },
        "all_30_held_out_sides": [],
    }
    assert len(M.source_boundaries(static_src, race_src)) == 23
    race_src["summary"]["conditional_candidates_matching_full_VCR_mass"] = 29
    with pytest.raises(ValueError, match="prior race experiment"):
        M.source_boundaries(static_src, race_src)


def test_postforecast_factual_mass_absence_cannot_change_candidate():
    history = {"status": "RESOLVED_TMINUS1_OWNER_RACE", "owner_raceid_Tminus1": 1}
    candidate = M.race.conditional_candidate(history, 100)
    a = M.validate_after_prediction(
        conditional=candidate, historical_race=history,
        factual_mass=150, factual_raceid=1,
    )
    b = M.validate_after_prediction(
        conditional=candidate, historical_race=history,
        factual_mass=200, factual_raceid=2,
    )
    c = M.validate_after_prediction(
        conditional=candidate, historical_race=history,
        factual_mass=None, factual_raceid=None,
    )
    assert a["conditional_candidate_equals_full_observed_mass"] is True
    assert b["conditional_candidate_equals_full_observed_mass"] is False
    assert c["status"] == "ABSTAIN_INVALID_VCR_MASS_COMPARATOR"
    assert candidate["conditional_hull_plus_race_mass_KT"] == 150


def test_bash_runner_and_evidence_wrapper_are_real_and_syntactically_valid():
    runner = ROOT / "tools/run-combat-mass-independent-late-turn-stress-v1.sh"
    wrapper = ROOT / "tools/run-combat-mass-independent-late-turn-stress-v1-with-evidence.sh"
    for script in (runner, wrapper):
        subprocess.run(["bash", "-n", str(script)], check=True)
    s = runner.read_text()
    assert "mass-time-indexed-static-v1/published/report.json" in s
    assert "mass-tminus1-race-bonus-audit-v1/published/report.json" in s
    assert "CURRENT" not in s
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert M.FROZEN_STATIC_GIT_BLOB
    assert M.FROZEN_RACE_GIT_BLOB
