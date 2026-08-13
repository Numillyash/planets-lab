from planets_lab.data import import_loadturn


def test_loadturn_preserves_mission_targets_for_movement_resolution() -> None:
    state = import_loadturn(
        {
            "rst": {
                "game": {"id": 1, "turn": 2},
                "planets": [],
                "ships": [
                    {
                        "id": 10,
                        "ownerid": 1,
                        "hullid": 16,
                        "x": 100,
                        "y": 100,
                        "mission": 6,
                        "mission1target": 22,
                        "mission2target": 33,
                    }
                ],
                "starbases": [],
            }
        }
    )

    ship = state.ships[10]
    assert ship.mission == "6"
    assert ship.mission1_target_id == 22
    assert ship.mission2_target_id == 33
