import pytest

from planets_lab.data import NuStaticDataError, import_static_all


def test_import_static_all_indexes_documented_collections_losslessly() -> None:
    payload = {
        "hulls": [
            {"id": 1, "name": "Scout", "mass": 75, "custom": {"x": 1}},
            {"id": "2", "name": "Destroyer", "mass": 90},
        ],
        "beams": [{"id": 4, "name": "Positron"}],
        "engines": [{"id": 9, "name": "Transwarp"}],
        "torpedos": [{"id": 5, "name": "Mark 3"}],
        "races": [{"id": 1, "name": "Federation"}],
        "advantages": [{"id": 12, "name": "Example"}],
        "levels": [{"id": 1, "name": "Midshipman"}],
    }

    catalog = import_static_all(payload)

    assert catalog.hulls[1]["mass"] == 75
    assert catalog.hulls[2]["name"] == "Destroyer"
    assert catalog.beams[4]["name"] == "Positron"
    assert catalog.engines[9]["name"] == "Transwarp"
    assert catalog.torpedoes[5]["name"] == "Mark 3"
    assert catalog.races[1]["name"] == "Federation"
    assert catalog.advantages[12]["name"] == "Example"
    assert catalog.extra_collections["levels"][0]["name"] == "Midshipman"

    payload["hulls"][0]["custom"]["x"] = 999
    assert catalog.hulls[1]["custom"]["x"] == 1


def test_import_static_all_keeps_default_ids_separate_from_all_sets() -> None:
    catalog = import_static_all(
        {
            "hulls": [{"id": 1, "name": "default"}],
            "hullsall": [{"id": 1001, "name": "campaign"}],
            "torpedos": [{"id": 1, "name": "default"}],
            "torpedosall": [
                {"id": 1, "fullid": 1001, "name": "campaign-a"},
                {"id": 1, "fullid": 2001, "name": "campaign-b"},
            ],
        }
    )

    assert set(catalog.hulls) == {1}
    assert catalog.hulls_all[0]["id"] == 1001
    assert set(catalog.torpedoes) == {1}
    assert len(catalog.torpedoes_all) == 2
    assert catalog.torpedoes_all[0]["fullid"] == 1001


def test_import_static_all_rejects_duplicate_ids() -> None:
    with pytest.raises(NuStaticDataError, match="duplicate id 1"):
        import_static_all({"hulls": [{"id": 1}, {"id": 1}]})


def test_import_static_all_rejects_non_list_collection() -> None:
    with pytest.raises(NuStaticDataError, match="hulls must be a list"):
        import_static_all({"hulls": {"id": 1}})
