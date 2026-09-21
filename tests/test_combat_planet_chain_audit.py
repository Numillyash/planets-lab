from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

from planets_lab.corpus.feature_index import feature_row, write_feature_index
from planets_lab.rules.combat import rebuild_planet_combatant


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_planet_chain_audit.py"
spec = importlib.util.spec_from_file_location("combat_planet_chain_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def _raw_from_planet(combatant: dict[str, object]) -> dict[str, object]:
    return {
        "objectid": 50,
        "name": "Test World",
        "hullid": 0,
        "raceid": combatant.get("race_id"),
        "beamcount": combatant["beam_count"],
        "launchercount": combatant["launcher_count"],
        "baycount": combatant["bay_count"],
        "beamid": combatant["beam_id"],
        "torpedoid": combatant["torpedo_id"],
        "shield": combatant["shield"],
        "damage": combatant["damage"],
        "crew": combatant["crew"],
        "mass": combatant["mass"],
        "fighters": combatant["fighters"],
        "hasstarbase": combatant["has_starbase"],
    }


def test_no_starbase_start_is_inferred_only_from_explicit_false() -> None:
    combatant = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "race_id": 3,
            "has_starbase": False,
            "planet_defense": 65,
        },
        shield=72,
    )
    raw = _raw_from_planet(combatant)
    inferred = audit._infer_no_starbase_start(raw)
    assert inferred is not None
    assert inferred["planet_defense"] == 65
    assert audit._projection_check(inferred, raw)["status"] == "match"

    unknown = dict(raw)
    unknown.pop("hasstarbase")
    assert audit._infer_no_starbase_start(unknown) is None


def test_real_shape_no_starbase_carry_formula_matches_next_vcr_start() -> None:
    first = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "race_id": 3,
            "has_starbase": False,
            "planet_defense": 65,
        }
    )
    next_start = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "race_id": 3,
            "has_starbase": False,
            "planet_defense": 36,
        },
        shield=0,
    )
    transition = audit._transition(
        {
            "game_id": 1,
            "turn": 10,
            "planet_id": 50,
            "position": (1000, 1000),
            "vcr_id": 7,
            "has_starbase": False,
            "start": _raw_from_planet(first),
            "terminal": {
                "shield": 0,
                "damage": 43,
                "fighters": 6,
                "destroyed": False,
                "captured": False,
            },
        },
        {
            "vcr_id": 8,
            "start": _raw_from_planet(next_start),
        },
    )
    assert transition["status"] == "match"
    assert transition["exact_no_starbase"]["status"] == "match"
    assert transition["exact_no_starbase"]["predicted_next_planet_defense"] == 36


def test_starbase_transition_only_asserts_direct_shield_carry() -> None:
    transition = audit._transition(
        {
            "game_id": 1,
            "turn": 10,
            "planet_id": 50,
            "position": (1000, 1000),
            "vcr_id": 7,
            "has_starbase": True,
            "start": {"hasstarbase": True, "mass": 300, "shield": 100},
            "terminal": {
                "shield": 41,
                "damage": 0,
                "fighters": 10,
                "destroyed": False,
                "captured": False,
            },
        },
        {
            "vcr_id": 8,
            "start": {"hasstarbase": True, "mass": 300, "shield": 41},
        },
    )
    assert transition["status"] == "match"
    assert transition["exact_no_starbase"]["status"] == "not_applicable"
    assert transition["shield_carry"]["matches"] is True


def test_scope_keeps_plain_planet_and_starbase_populations_separate() -> None:
    rows = [
        {
            "status": "match",
            "has_starbase": False,
            "gap": 1,
            "shield_carry": {"matches": True},
            "exact_no_starbase": {"status": "match"},
        },
        {
            "status": "match",
            "has_starbase": True,
            "gap": 2,
            "shield_carry": {"matches": True},
            "exact_no_starbase": {"status": "not_applicable"},
        },
    ]
    scope = audit._scope(rows)
    assert scope["transitions"] == 2
    assert scope["base_kind"] == {"no_starbase": 1, "starbase": 1}
    assert scope["shield_carry"] == {"match": 2}
    assert scope["exact_no_starbase"] == {"match": 1, "not_applicable": 1}



def test_scope_selection_is_loaded_from_feature_index(tmp_path: Path) -> None:
    rows = []
    for game_id, sphere, horwasp in (
        (10, False, False),
        (20, True, True),
    ):
        rows.extend(
            [
                feature_row(
                    game_id=game_id,
                    feature="game.status",
                    value=3,
                    known=True,
                    source_kind="fixture",
                    source_location="fixture",
                ),
                feature_row(
                    game_id=game_id,
                    feature="settings.sphere",
                    value=sphere,
                    known=True,
                    source_kind="fixture",
                    source_location="fixture",
                ),
                feature_row(
                    game_id=game_id,
                    feature="population.horwasp_present",
                    value=horwasp,
                    known=True,
                    source_kind="fixture",
                    source_location="fixture",
                ),
            ]
        )

    index = tmp_path / "game_features.parquet"
    write_feature_index(
        rows=rows,
        parquet_path=index,
        database_path=tmp_path / "corpus.duckdb",
    )
    selection = audit._scope_selection(
        argparse.Namespace(
            feature_index=index,
            scope_profile="combat-planar-no-horwasp",
        )
    )

    assert selection is not None
    assert selection["included_game_ids"] == [10]
    assert selection["excluded_game_ids"] == [20]
    assert selection["unknown_game_ids"] == []
