"""Documented standard structure construction: bounded, noncausal controls."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from math import isqrt
from pathlib import Path
import sys

import pytest

from planets_lab.sim.standard_structure_build import (
    RESEARCH_STATUS, StructureBuildTargets,
    forecast_standard_structure_build, max_standard_structures,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture


def planet():
    p = fixture().planets[10]
    p.cargo.megacredits = 1000
    p.cargo.supplies = 80
    return p


@pytest.mark.parametrize("clans,expected", [
    (0, (0, 0, 0)),
    (1, (1, 1, 1)),
    (50, (50, 50, 50)),
    (51, (51, 51, 51)),
    (100, (100, 100, 57)),
    (101, (101, 101, 57)),
    (200, (200, 110, 62)),
    (201, (201, 110, 62)),
    (300, (210, 114, 65)),
])
def test_published_clan_caps_round_down_with_integer_sqrt(clans, expected):
    caps = max_standard_structures(clans)
    assert (caps["mines"], caps["factories"], caps["defense_posts"]) == expected


@pytest.mark.parametrize("bad", [None, -1, True, 1.4, "10"])
def test_population_must_be_exact_nonnegative_integer(bad):
    with pytest.raises(ValueError):
        max_standard_structures(bad)


def test_full_funded_three_structure_families_cost_exactly_documented_amounts():
    before = planet()
    preserved = deepcopy(before)
    order = StructureBuildTargets(
        planet_id=10, mines=13, factories=12, defense_posts=1,
    )
    result = forecast_standard_structure_build(
        before, order, standard_rules_asserted=True,
    )
    assert result.supported and result.status == RESEARCH_STATUS
    assert result.resulting_planet is not None
    # 1 defense @10 MC, 2 factories @3 MC, 3 mines @4 MC
    assert result.spent_megacredits == 28
    assert result.spent_supplies == 6
    assert result.resulting_planet.factories == 12
    assert result.resulting_planet.mines == 13
    assert result.resulting_planet.defense_posts == 1
    assert result.resulting_planet.cargo.megacredits == before.cargo.megacredits - 28
    assert result.resulting_planet.cargo.supplies == before.cargo.supplies - 6
    assert result.supplied_structures == (
        ("defense_posts", 1), ("factories", 2), ("mines", 3),
    )
    assert before == preserved
    assert not result.nuhost_execution_verified
    assert not result.host_phase_position_verified


def test_omitted_fields_are_not_interpreted_as_zero_targets():
    p = planet()
    outcome = forecast_standard_structure_build(
        p, StructureBuildTargets(planet_id=10, mines=10),
        standard_rules_asserted=True,
    )
    assert outcome.supported and outcome.spent_supplies == 0
    assert outcome.spent_megacredits == 0
    assert outcome.resulting_planet == p
    assert outcome.supplied_structures == (("mines", 0),)


@pytest.mark.parametrize("modify,targets,reason_fragment", [
    ("none", StructureBuildTargets(planet_id=99, mines=11), "identity"),
    ("none", StructureBuildTargets(planet_id=10), "target"),
    ("none", StructureBuildTargets(planet_id=10, mines=9), "downgrade"),
    ("none", StructureBuildTargets(planet_id=10, factories=101), "cap"),
    ("none", StructureBuildTargets(planet_id=10, defense_posts=58), "cap"),
    ("none", StructureBuildTargets(planet_id=10, mines=True), "target"),
    ("noowner", StructureBuildTargets(planet_id=10, mines=11), "owner"),
    ("badclans", StructureBuildTargets(planet_id=10, mines=11), "population"),
    ("overcap", StructureBuildTargets(planet_id=10, mines=11), "caps"),
    ("no_mc", StructureBuildTargets(planet_id=10, factories=11), "part-funding"),
    ("no_supplies", StructureBuildTargets(planet_id=10, mines=11), "part-funding"),
])
def test_unsupported_or_partially_funded_batches_abstain_without_state(
    modify, targets, reason_fragment,
):
    p = planet()
    if modify == "noowner":
        p.owner_id = None
    elif modify == "badclans":
        p.cargo.clans = -1
    elif modify == "overcap":
        p.mines = 200
    elif modify == "no_mc":
        p.cargo.megacredits = 2
    elif modify == "no_supplies":
        p.cargo.supplies = 0
    preserved = deepcopy(p)
    outcome = forecast_standard_structure_build(
        p, targets, standard_rules_asserted=True,
    )
    assert not outcome.supported
    assert outcome.status == "ABSTAIN_UNSUPPORTED_STRUCTURE_BUILD"
    assert outcome.resulting_planet is None
    assert reason_fragment in (outcome.reason or "")
    assert p == preserved


def test_default_never_infers_standard_rules_or_accepts_unverified_context():
    p = planet()
    result = forecast_standard_structure_build(
        p, StructureBuildTargets(10, mines=11),
    )
    assert not result.supported
    assert result.resulting_planet is None
    assert not result.nuhost_execution_verified
