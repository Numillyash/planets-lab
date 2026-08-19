import pytest

from planets_lab.corpus.compiled_movement_corpus_cli import _manifest_nuionstorms
from planets_lab.corpus.movement_residual_context import StormRecord
from planets_lab.corpus.movement_storm_context import storm_expected_category_for_mode
from planets_lab.validation.movement_geometry import MovementSample


def _sample() -> MovementSample:
    return MovementSample(
        turn=10,
        ship_id=1,
        x=190,
        y=100,
        target_x=190,
        target_y=100,
        warp=0,
        next_x=217,
        next_y=100,
        hull_id=3,
    )


def _storm() -> StormRecord:
    return StormRecord(
        id=1,
        x=100.0,
        y=100.0,
        radius=100.0,
        voltage=200.0,
        warp=6,
        heading=90.0,
        parent_id=0,
    )


def test_classic_constant_voltage_explains_edge_drag() -> None:
    category, status = storm_expected_category_for_mode(
        _sample(),
        storms=(_storm(),),
        planets=(),
        nuionstorms=False,
    )
    assert category == "ion_storm_drag"
    assert status == "resolved_drag"


def test_cloudy_voltage_attenuation_does_not_explain_same_edge_drag() -> None:
    category, status = storm_expected_category_for_mode(
        _sample(),
        storms=(_storm(),),
        planets=(),
        nuionstorms=True,
    )
    assert category is None
    assert status == "not_affected"


def test_unknown_storm_mode_fails_closed() -> None:
    category, status = storm_expected_category_for_mode(
        _sample(),
        storms=(_storm(),),
        planets=(),
        nuionstorms=None,
    )
    assert category is None
    assert status == "storm_mode_unknown"


def test_manifest_storm_mode_requires_authoritative_boolean() -> None:
    assert _manifest_nuionstorms({"settings": {"nuionstorms": False}}) is False
    assert _manifest_nuionstorms({"settings": {"nuionstorms": True}}) is True
    with pytest.raises(ValueError, match="settings.nuionstorms"):
        _manifest_nuionstorms({"settings": {}})
