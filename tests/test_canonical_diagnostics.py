from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.diagnose_canonical_cli import (
    _failure_kind,
    _unresolved_starbase_diagnostics,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot
from planets_lab.data import NuLoadTurnError


def test_unresolved_starbase_diagnostics_are_mechanical_and_privacy_safe() -> None:
    snapshot = ArchiveTurnSnapshot(
        member=TurnMember(player=1, turn=12, name="player1-turn12.trn"),
        game_id=620917,
        player_id=1,
        embedded_turn=12,
        snapshot_hash="fixture",
        mechanics_payload={
            "planets": [
                {
                    "id": 45,
                    "ownerid": 0,
                    "clans": 0,
                    "defense": 10,
                    "friendlycode": "dont-print",
                    "name": "secret-ish",
                }
            ],
            "starbases": [
                {
                    "planetid": 45,
                    "ownerid": 0,
                    "fighters": 20,
                    "defense": 30,
                    "name": "dont-print-base",
                }
            ],
        },
    )

    diagnostics = _unresolved_starbase_diagnostics(snapshot)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["player"] == 1
    assert diagnostic["planet_id"] == 45
    assert diagnostic["starbase_ownerid"] == 0
    assert diagnostic["planet_ownerid"] == 0
    assert diagnostic["planet_clans"] == 0
    assert diagnostic["starbase_fighters"] == 20
    assert "name" in diagnostic["starbase_present_keys"]
    assert "friendlycode" in diagnostic["planet_present_keys"]
    assert "secret-ish" not in repr(diagnostic)
    assert "dont-print" not in repr(diagnostic)
    assert "dont-print-base" not in repr(diagnostic)


def test_failure_kind_classifies_known_canonical_boundaries() -> None:
    assert (
        _failure_kind(NuLoadTurnError("starbase on planet 45 has no resolvable owner"))
        == "starbase_no_resolvable_owner"
    )
    assert (
        _failure_kind(ValueError("unowned ghost ship 7 has non-zero warp 5"))
        == "ghost_nonzero_warp"
    )
    assert (
        _failure_kind(ValueError("unowned ship 7 has non-zero crew 12"))
        == "ghost_nonzero_crew"
    )


def test_canonical_diagnostics_cli_imports() -> None:
    from planets_lab.corpus.diagnose_canonical_cli import main

    assert callable(main)
