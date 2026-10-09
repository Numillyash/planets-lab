from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/combat_mass_time_indexed_static_v1.py"
SPEC = importlib.util.spec_from_file_location("mass_time_indexed_static_v1", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def _ref(owner, member_id, turn=74, embedded=74, game=217591):
    return SimpleNamespace(
        game_id=game, archive_turn=turn, embedded_turn=embedded,
        perspective_player_id=owner, member_id=member_id,
        decoded_payload_sha256=f"{member_id:064x}",
    )


def _member(turn=74, game=217591, mass=46, brood=145):
    return {"game": {"id": game, "turn": turn},
            "hulls": [{"id": 1039, "mass": mass},
                      {"id": 117, "mass": brood},
                      {"id": 94, "mass": 495}]}


def _snaps(mass=46):
    return [
        M.snapshot_from_member(_ref(4, 101), _member(mass=mass)),
        M.snapshot_from_member(_ref(5, 102), _member(mass=mass)),
    ]


def test_independent_static_component_predicted_without_vcr_mass():
    predicted = M.forecast_component(
        _snaps(), game_id=217591, battle_turn=75,
        owner_id=4, hull_id=1039,
    )
    assert predicted["status"] == "RESOLVED"
    assert predicted["predicted_hull_mass_KT"] == 46
    assert predicted["source_archive_turn"] == 74
    assert predicted["full_combat_mass_prediction_KT"] is None
    assert predicted["source_member_ids"] == [101, 102]
    # Observed VCR mass cannot alter the prediction; only evaluation changes.
    assert M.evaluate_forecast(predicted, 48)["difference_factual_minus_component_KT"] == 2
    assert M.evaluate_forecast(predicted, 196)["difference_factual_minus_component_KT"] == 150
    assert predicted["predicted_hull_mass_KT"] == 46


def test_brood_new_hull_mass_not_first_catalog():
    p = M.forecast_component(
        _snaps(), game_id=217591, battle_turn=75,
        owner_id=5, hull_id=117,
    )
    assert p["predicted_hull_mass_KT"] == 145
    assert not M.evaluate_forecast(p, 290)["component_equals_factual_mass"]


def test_conflicting_static_is_not_majority_voted_or_oracle_fit():
    s = _snaps()
    s[1] = M.snapshot_from_member(_ref(5, 102), _member(mass=96))
    value = M.forecast_component(
        s, game_id=217591, battle_turn=75, owner_id=4, hull_id=1039,
    )
    assert value["status"] == "CONFLICTING_TMINUS1_STATIC"
    assert value["predicted_hull_mass_KT"] is None


@pytest.mark.parametrize("owner,hull,expected", [
    (3, 1039, "MISSING_OWNER_PERSPECTIVE"),
    (4, 999, "MISSING_HULL_IN_PERSPECTIVE"),
])
def test_fail_closed_owner_and_catalog_gaps(owner, hull, expected):
    assert M.resolve_mass(
        _snaps(), game_id=217591, battle_turn=75,
        owner_id=owner, hull_id=hull,
    )["status"] == expected


def test_future_and_stale_archives_never_used_as_fallback():
    later = M.snapshot_from_member(_ref(4, 150, turn=75, embedded=75),
                                   _member(turn=75, mass=600))
    older = M.snapshot_from_member(_ref(4, 151, turn=73, embedded=73),
                                   _member(turn=73, mass=96))
    assert M.resolve_mass(
        [later, older], game_id=217591, battle_turn=75,
        owner_id=4, hull_id=1039,
    )["status"] == "MISSING_EXACT_TMINUS1"
    contaminated = M.Snapshot(
        217591, 74, 75, 4, 100, "a"*64, {1039: 600}
    )
    assert M.resolve_mass(
        [contaminated], game_id=217591, battle_turn=75,
        owner_id=4, hull_id=1039,
    )["status"] == "UNTRUSTED_EMBEDDED_TURN"


def test_snapshot_validates_game_turn_digest_and_duplicate_hull():
    with pytest.raises(ValueError, match="embedded turn mismatch"):
        M.snapshot_from_member(_ref(4, 101), _member(turn=75))
    with pytest.raises(ValueError, match="duplicate archived hull"):
        m = _member()
        m["hulls"].append({"id": 1039, "mass": 96})
        M.snapshot_from_member(_ref(4, 101), m)
    with pytest.raises(ValueError, match="incomplete"):
        m = _member()
        m["hulls"][0]["mass"] = None
        M.snapshot_from_member(_ref(4, 101), m)
    with pytest.raises(ValueError, match="game identity"):
        M.snapshot_from_member(_ref(4, 101), _member(game=7))


def test_independent_holdout_selection_excludes_entire_control_games():
    candidates = [(217591, 149), (217591, 75), (900, 11),
                  (900, 10), (901, 12), (902, 23), (901, 13)]
    assert M.select_holdout_pairs(candidates, excluded_games={217591}) == [
        (900, 10), (900, 11), (901, 12), (901, 13), (902, 23)
    ]


def test_runner_gates_v1_and_verifies_pinned_db():
    a = ROOT / "tools/run-combat-mass-time-indexed-static-v1.sh"
    b = ROOT / "tools/run-combat-mass-time-indexed-static-v1-with-evidence.sh"
    c = ROOT / "tools/run-combat-mass-predictive-pipeline-v1.sh"
    for script in (a, b, c):
        subprocess.run(["bash", "-n", str(script)], check=True)
    assert M.GENERATION_SHA256 in a.read_text()
    assert "--reconciliation" in a.read_text()
    assert "run-with-runtime-evidence.sh" in b.read_text()
    assert "run-combat-mass-temporal-reconciliation-v1-with-evidence.sh" in c.read_text()


def test_holdout_candidate_sql_uses_vcr_existence_and_tminus1_without_mass():
    class Conn:
        def execute(self, sql):
            self.sql = sql
            return self
        def fetchall(self):
            return [(900, 10), (900, 11), (901, 12)]
    conn = Conn()
    assert M._candidate_pairs(conn) == [(900, 10), (900, 11), (901, 12)]
    assert "typed_vcrs" in conn.sql
    assert "archive_turn - 1" in conn.sql
    assert "data.mass" not in conn.sql.lower()


def test_no_vcr_early_turn_does_not_discard_remaining_game_turns():
    pairs = M.select_holdout_pairs(
        [(900, 10), (900, 11), (901, 12)], excluded_games=set()
    )
    assert pairs[:2] == [(900, 10), (900, 11)]
    # Live loop must remember a game ONLY after successfully finding VCRs.
    script = SCRIPT.read_text()
    assert "completed_games.add(game)" in script
    assert script.index("if not cases:") < script.index("completed_games.add(game)")
    assert "no matching VCR; trying next eligible turn" in script


def test_progress_and_single_corpus_hash(capsys):
    M._progress("game=900 T11 predicting")
    assert "[static-v1] game=900 T11 predicting" in capsys.readouterr().out
    shell = (ROOT / "tools/run-combat-mass-time-indexed-static-v1.sh").read_text()
    script = SCRIPT.read_text()
    assert "sha256sum" not in shell
    assert script.count('hashlib.file_digest(stream, "sha256")') == 1
    assert "flush=True" in script
    assert "candidate game-turns:" in script
