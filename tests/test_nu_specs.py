import pytest

from planets_lab.data import NuStaticSpecs, import_static_all


def test_static_specs_project_live_observed_hull_fields() -> None:
    catalog = import_static_all(
        {
            "hulls": [
                {
                    "id": 79,
                    "name": "Golem Class Baseship",
                    "techlevel": 10,
                    "mass": 850,
                    "cargo": 300,
                    "fueltank": 2000,
                    "crew": 1958,
                    "engines": 8,
                    "beams": 6,
                    "launchers": 0,
                    "fighterbays": 10,
                    "cancloak": False,
                    "cost": 990,
                    "duranium": 442,
                    "tritanium": 171,
                    "molybdenum": 32,
                    "parentid": 0,
                    "special": "",
                }
            ],
            "engines": [
                {
                    "id": 9,
                    "name": "Transwarp Drive",
                    "techlevel": 10,
                    "cost": 300,
                    "duranium": 16,
                    "tritanium": 35,
                    "molybdenum": 10,
                    "warp1": 1,
                    "warp2": 1,
                    "warp3": 1,
                    "warp4": 1,
                    "warp5": 1,
                    "warp6": 1,
                    "warp7": 1,
                    "warp8": 1,
                    "warp9": 1,
                }
            ],
            "beams": [
                {
                    "id": 10,
                    "name": "Heavy Phaser",
                    "techlevel": 10,
                    "mass": 4,
                    "damage": 45,
                    "crewkill": 30,
                    "cost": 55,
                    "duranium": 1,
                    "tritanium": 1,
                    "molybdenum": 6,
                }
            ],
            "torpedos": [
                {
                    "id": 10,
                    "fullid": 10,
                    "name": "Mark 8 Photon",
                    "techlevel": 10,
                    "mass": 8,
                    "damage": 100,
                    "crewkill": 60,
                    "combatrange": 30000,
                    "launchercost": 100,
                    "torpedocost": 54,
                    "duranium": 1,
                    "tritanium": 1,
                    "molybdenum": 13,
                }
            ],
        }
    )

    specs = NuStaticSpecs.from_catalog(catalog)

    hull = specs.hulls[79]
    assert hull.mass == 850
    assert hull.engine_count == 8
    assert hull.beam_count == 6
    assert hull.fighter_bay_count == 10
    assert hull.torpedo_launcher_count == 0
    assert hull.munition_kind == "fighters"
    assert hull.cost.megacredits == 990

    engine = specs.engines[9]
    assert engine.fuel_factor(0) == 0
    assert engine.fuel_factor(9) == 1

    beam = specs.beams[10]
    assert beam.mass == 4
    assert beam.damage == 45

    torpedo = specs.torpedoes[10]
    assert torpedo.launcher_cost == 100
    assert torpedo.torpedo_cost == 54
    assert torpedo.full_id == 10


def test_hull_munition_kind_distinguishes_torpedo_and_unarmed_hulls() -> None:
    payload = {
        "hulls": [
            {
                "id": 1,
                "name": "Torpedo Ship",
                "launchers": 4,
                "fighterbays": 0,
            },
            {
                "id": 2,
                "name": "Freighter",
                "launchers": 0,
                "fighterbays": 0,
            },
        ]
    }

    specs = NuStaticSpecs.from_catalog(import_static_all(payload))

    assert specs.hulls[1].munition_kind == "torpedoes"
    assert specs.hulls[2].munition_kind is None


def test_engine_rejects_invalid_warp_lookup() -> None:
    raw_engine = {
        "id": 1,
        "name": "Drive",
        **{f"warp{warp}": warp for warp in range(1, 10)},
    }
    specs = NuStaticSpecs.from_catalog(
        import_static_all({"engines": [raw_engine]})
    )

    with pytest.raises(ValueError, match="0..9"):
        specs.engines[1].fuel_factor(10)
