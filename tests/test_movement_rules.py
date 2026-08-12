import json
from pathlib import Path

import pytest

from planets_lab.rules import max_nominal_distance


def test_standard_nominal_distance_is_warp_squared() -> None:
    assert max_nominal_distance(7) == 49
    assert max_nominal_distance(9) == 81


def test_gravitonic_accelerator_doubles_nominal_distance() -> None:
    assert max_nominal_distance(9, gravitonic=True) == 162


def test_warp_range_is_explicit() -> None:
    with pytest.raises(ValueError):
        max_nominal_distance(10)


def test_golden_warp9_scenario_agrees_with_rule() -> None:
    path = Path("validation/scenarios/movement/normal_warp9_long_waypoint.json")
    scenario = json.loads(path.read_text(encoding="utf-8"))

    assert max_nominal_distance(scenario["input"]["ship"]["warp"]) == scenario["expected"]["max_distance"]
