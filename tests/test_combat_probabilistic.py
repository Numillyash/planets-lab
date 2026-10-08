from __future__ import annotations

from copy import deepcopy

import pytest

from planets_lab.rules.combat import probabilistic as prob
from planets_lab.rules.combat.classic import ReplayUnsupported


def _ship(ship_id: int, *, bays: int = 0, race: int = 5) -> dict:
    return {
        "objectid": ship_id,
        "hullid": 70 if bays else 89,
        "raceid": race,
        "beamcount": 5,
        "launchercount": 0 if bays else 2,
        "baycount": bays,
        "beamid": 1,
        "torpedoid": 0 if bays else 3,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "torpedos": 0 if bays else 20,
        "fighters": 20 if bays else 0,
        "beamkillbonus": 1,
        "beamchargerate": 1,
        "torpchargerate": 1,
        "torpmisspercent": 35,
        "crewdefensepercent": 0,
    }


def _payload(*, carrier: bool = True) -> dict:
    return {
        "leftownerid": 5,
        "rightownerid": 10,
        "battletype": 1,
        "left": _ship(184, bays=10 if carrier else 0),
        "right": _ship(140),
    }


def test_ensemble_weights_two_mass_branches_and_two_seeds(monkeypatch) -> None:
    observed_calls = []

    def fake_replay(payload, *, beams, torpedoes, settings):
        observed_calls.append((payload["seed"], payload["right"]["mass"]))
        lose_right = payload["right"]["mass"] == 510
        return {
            "result": ["right_destroyed" if lose_right else "left_destroyed"],
            "left": {
                "destroyed": not lose_right, "captured": False,
                "survived": lose_right, "shield": 80,
                "damage": 20, "crew": 90, "torpedoes": 15, "fighters": 0,
            },
            "right": {
                "destroyed": lose_right, "captured": False,
                "survived": not lose_right, "shield": 40,
                "damage": 60, "crew": 50, "torpedoes": 5, "fighters": 0,
            },
        }

    monkeypatch.setattr(prob, "replay_nuhost_from_nu_catalog", fake_replay)
    payload = _payload()
    frozen = deepcopy(payload)
    report = prob.evaluate_conditional_classic(
        payload, beams=(), torpedoes=(), settings={"combatrng": 0},
        left_hull_mass=980, right_hull_mass=150,
        assumed_no_other_mass_modifiers=True, seed_values=(1, 2),
    )
    assert payload == frozen
    assert sorted(observed_calls) == [(1, 150), (1, 510), (2, 150), (2, 510)]
    assert report["scenario_count"] == 4
    assert report["total_probability"] == 1.0
    assert report["carrier_eligible"] is True
    assert report["outcome_probabilities"] == {
        "left_destroyed": 0.4, "right_destroyed": 0.6,
    }
    assert report["sides"]["right"]["probabilities"]["destroyed"] == 0.6
    assert report["sides"]["right"]["expected_terminal"]["damage"] == 60.0


def test_noncarrier_has_one_mass_branch(monkeypatch) -> None:
    def fake_replay(payload, **kw):
        return {
            "result": ["timeout"],
            "left": {
                "destroyed": False, "captured": False, "survived": True,
                "shield": 100, "damage": 0, "crew": 100,
                "torpedoes": 20, "fighters": 0,
            },
            "right": {
                "destroyed": False, "captured": False, "survived": True,
                "shield": 100, "damage": 0, "crew": 100,
                "torpedoes": 20, "fighters": 0,
            },
        }
    monkeypatch.setattr(prob, "replay_nuhost_from_nu_catalog", fake_replay)
    report=prob.evaluate_conditional_classic(
        _payload(carrier=False), beams=(), torpedoes=(),
        settings={"combatrng": 0}, left_hull_mass=150, right_hull_mass=150,
        assumed_no_other_mass_modifiers=True, seed_values=(1, 2),
    )
    assert report["scenario_count"] == 2
    assert report["mass_scenarios"] == [
        {"right_mass": 150, "assumed_probability": 1.0, "branch": "no_bonus"}
    ]
    assert report["outcome_probabilities"]["timeout"] == 1.0


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(seed=27),
    lambda p: p["left"].update(mass=980),
    lambda p: p["right"].update(mass=510),
    lambda p: p["right"].pop("crew"),
])
def test_factual_seed_mass_or_unknown_effective_field_rejected(mutation) -> None:
    p = _payload()
    mutation(p)
    with pytest.raises(ReplayUnsupported):
        prob.evaluate_conditional_classic(
            p, beams=(), torpedoes=(), settings={"combatrng": 0},
            left_hull_mass=980, right_hull_mass=150,
            assumed_no_other_mass_modifiers=True, seed_values=(1, 2),
        )


def test_ambiguous_mass_and_invalid_seed_grid_fail_closed() -> None:
    kwargs = dict(
        beams=(), torpedoes=(), settings={"combatrng": 0},
        left_hull_mass=980, right_hull_mass=150,
    )
    with pytest.raises(ReplayUnsupported, match="assumption required"):
        prob.evaluate_conditional_classic(
            _payload(), assumed_no_other_mass_modifiers=False,
            seed_values=(1, 2), **kwargs,
        )
    for seeds in ((), (1, 1), (0, 1), (119,), (True,)):
        with pytest.raises(ReplayUnsupported, match="seed ensemble"):
            prob.evaluate_conditional_classic(
                _payload(), assumed_no_other_mass_modifiers=True,
                seed_values=seeds, **kwargs,
            )


def test_default_grid_is_exactly_118_distinct_start_seeds() -> None:
    assert prob.CLASSIC_START_SEEDS == tuple(range(1, 119))


def test_horwasp_mass_must_be_independently_reconstructed() -> None:
    payload = _payload()
    payload["right"]["raceid"] = 12
    with pytest.raises(ReplayUnsupported, match="Horwasp clan-dependent"):
        prob.evaluate_conditional_classic(
            payload, beams=(), torpedoes=(), settings={"combatrng": 0},
            left_hull_mass=980, right_hull_mass=145,
            assumed_no_other_mass_modifiers=True, seed_values=(1, 2),
        )


def test_federation_threshold_crossing_is_not_silently_classic() -> None:
    payload = _payload()
    payload["right"]["raceid"] = 1
    with pytest.raises(ReplayUnsupported, match="Federation-adjusted"):
        prob.evaluate_conditional_classic(
            payload, beams=(), torpedoes=(), settings={"combatrng": 0},
            left_hull_mass=980, right_hull_mass=120,
            assumed_no_other_mass_modifiers=True, seed_values=(1, 2),
        )
