from planets_lab.corpus.movement_horwasp_ballistic_context import (
    _classify_ballistic_formula,
    _effective_ballistic_topology,
    _historical_ballistic_hulls,
    _historical_mite_hulls,
    _previous_mode,
    ballistic_vector,
)
from planets_lab.corpus.movement_topology_diagnostics import MapTopologyEvidence


def _flat_topology() -> MapTopologyEvidence:
    return MapTopologyEvidence(
        sphere=False,
        mapwidth=2150,
        mapheight=2150,
        mapshape=0,
        first_member="first.trn",
        last_member="last.trn",
        stable=True,
        first_candidates={},
        last_candidates={},
    )


def _sphere_topology(*, width: int = 2150, height: int = 2150, stable: bool = True) -> MapTopologyEvidence:
    return MapTopologyEvidence(
        sphere=True,
        mapwidth=width,
        mapheight=height,
        mapshape=1,
        first_member="first.trn",
        last_member="last.trn",
        stable=stable,
        first_candidates={},
        last_candidates={},
    )


def test_ballistic_vector_uses_planets_compass_and_signed_rounding() -> None:
    assert ballistic_vector(warp=9, heading=60, accelerated=False) == (70, 41)
    assert ballistic_vector(warp=6, heading=238, accelerated=False) == (-31, -19)
    assert ballistic_vector(warp=6, heading=0, accelerated=True) == (0, 54)


def test_historical_ballistic_authority_excludes_textual_false_positives_and_mites() -> None:
    catalog = {
        120: {"name": "D9 Usva Class Stealth Raider", "special": "Radiation Shielding\nStealth Armor"},
        202: {"name": "Nest", "special": "Pod"},
        205: {"name": "Accelerator", "special": "Fueling Station"},
        212: {"name": "Sentry", "special": "Fueling Station"},
        213: {"name": "Red Mite", "special": "Pod"},
        1050: {"name": "Bloodfang", "special": "Stealth Armor"},
    }
    ballistic = _historical_ballistic_hulls(catalog)
    mites = _historical_mite_hulls(catalog)
    assert set(ballistic) == {202, 205, 212}
    assert mites == frozenset({213})


def test_effective_ballistic_topology_is_scoped_to_audited_game_and_raw_shape() -> None:
    raw = _sphere_topology()
    effective = _effective_ballistic_topology(game_id=591478, topology=raw)
    assert (raw.mapwidth, raw.mapheight) == (2150, 2150)
    assert (effective.mapwidth, effective.mapheight) == (2170, 2170)

    other_game = _effective_ballistic_topology(game_id=591479, topology=raw)
    assert other_game is raw

    unexpected_raw = _sphere_topology(width=2170, height=2170)
    assert _effective_ballistic_topology(
        game_id=591478,
        topology=unexpected_raw,
    ) is unexpected_raw

    unstable = _sphere_topology(stable=False)
    assert _effective_ballistic_topology(game_id=591478, topology=unstable) is unstable


def test_previous_mode_comes_from_latest_history_position() -> None:
    topology = _flat_topology()
    assert _previous_mode(
        {"history": [{"x": 0, "y": 0}]},
        origin=(36, 0),
        warp=6,
        topology=topology,
    ) == "normal"
    assert _previous_mode(
        {"history": [{"x": 0, "y": 0}]},
        origin=(54, 0),
        warp=6,
        topology=topology,
    ) == "accelerated"
    assert _previous_mode({}, origin=(54, 0), warp=6, topology=topology) == "launch"


def test_launch_normal_is_strong_but_same_turn_acceleration_is_observed_only() -> None:
    topology = _flat_topology()
    category, strong = _classify_ballistic_formula(
        raw={"heading": 90, "history": []},
        origin=(100, 100),
        observed=(136, 100),
        target=(500, 100),
        warp=6,
        topology=topology,
    )
    assert category == "ballistic_launch_normal"
    assert strong is True

    category, strong = _classify_ballistic_formula(
        raw={"heading": 90, "history": [{"x": 64, "y": 100}]},
        origin=(100, 100),
        observed=(154, 100),
        target=(500, 100),
        warp=6,
        topology=topology,
    )
    assert category == "ballistic_accelerator_transition_observed"
    assert strong is False


def test_accelerated_history_predicts_accelerated_step_strongly() -> None:
    topology = _flat_topology()
    category, strong = _classify_ballistic_formula(
        raw={"heading": 0, "history": [{"x": 100, "y": 46}]},
        origin=(100, 100),
        observed=(100, 154),
        target=(100, 500),
        warp=6,
        topology=topology,
    )
    assert category == "ballistic_accelerated_history_confirmed"
    assert strong is True
