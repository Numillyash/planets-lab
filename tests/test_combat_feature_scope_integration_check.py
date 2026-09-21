from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = (
    Path(__file__).parents[1]
    / "tools"
    / "diagnostics"
    / "combat_feature_scope_integration_check.py"
)
spec = importlib.util.spec_from_file_location(
    "combat_feature_scope_integration_check",
    TOOL,
)
assert spec is not None and spec.loader is not None
check_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_tool)


def _selection() -> dict[str, object]:
    return {
        "profile": "combat-planar-no-horwasp",
        "predicate_count": 3,
        "included_game_ids": list(range(1, 12)),
        "excluded_game_ids": [12],
        "unknown_game_ids": [],
    }


def test_checkpoint_continuity_accepts_expected_c3_c4_populations() -> None:
    planet = {
        "scope_selection": _selection(),
        "scopes": {
            "profile_selected_all": {
                "transitions": 103,
                "status": {"match": 102, "not_comparable": 1},
                "base_kind": {"starbase": 92, "no_starbase": 11},
                "shield_carry": {"match": 103},
            }
        },
    }
    phase = {
        "scope_selection": _selection(),
        "scopes": {
            "profile_selected_all": {
                "transitions": 1169,
                "status": {
                    "match": 1138,
                    "reappearance_after_capture": 23,
                    "mismatch": 8,
                },
            },
            "profile_selected_ship_vs_ship_survivors": {
                "transitions": 764,
                "status": {"match": 764},
            },
            "profile_selected_ship_vs_ship_survivors_gap1": {
                "transitions": 751,
                "status": {"match": 751},
            },
            "profile_selected_ship_to_planet_boundary": {
                "transitions": 397,
                "status": {
                    "match": 374,
                    "reappearance_after_capture": 15,
                    "mismatch": 8,
                },
            },
        },
    }
    cluster = {
        "scope_selection": _selection(),
        "scopes": {
            "profile_selected": {
                "status": {"same_location_transitions": 1169}
            },
            "profile_excluded": {
                "status": {"same_location_transitions": 316}
            },
        },
    }

    report = check_tool.check(planet, phase, cluster)

    assert report["exact"] is True
    assert report["failures"] == []
    assert report["checks"] == {
        "selector_partition_shared": True,
        "selector_partition_disjoint": True,
        "planet_c4_checkpoint_preserved": True,
        "ship_c3_checkpoint_preserved": True,
        "cluster_partition_preserved": True,
    }


def test_checkpoint_continuity_fails_on_population_drift() -> None:
    planet = {
        "scope_selection": _selection(),
        "scopes": {
            "profile_selected_all": {
                "transitions": 102,
                "status": {"match": 102, "not_comparable": 1},
                "base_kind": {"starbase": 92, "no_starbase": 11},
                "shield_carry": {"match": 103},
            }
        },
    }
    phase = {
        "scope_selection": _selection(),
        "scopes": {
            "profile_selected_all": {
                "transitions": 1169,
                "status": {
                    "match": 1138,
                    "reappearance_after_capture": 23,
                    "mismatch": 8,
                },
            },
            "profile_selected_ship_vs_ship_survivors": {
                "transitions": 764,
                "status": {"match": 764},
            },
            "profile_selected_ship_vs_ship_survivors_gap1": {
                "transitions": 751,
                "status": {"match": 751},
            },
            "profile_selected_ship_to_planet_boundary": {
                "transitions": 397,
                "status": {
                    "match": 374,
                    "reappearance_after_capture": 15,
                    "mismatch": 8,
                },
            },
        },
    }
    cluster = {
        "scope_selection": _selection(),
        "scopes": {
            "profile_selected": {
                "status": {"same_location_transitions": 1169}
            },
            "profile_excluded": {
                "status": {"same_location_transitions": 316}
            },
        },
    }

    report = check_tool.check(planet, phase, cluster)

    assert report["exact"] is False
    assert any(item.startswith("planet.transitions:") for item in report["failures"])
