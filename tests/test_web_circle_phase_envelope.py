"""Conservative pre/post web envelope parity and source type adversarial tests."""
from dataclasses import FrozenInstanceError
from math import isqrt

import pytest

from planets_lab.rules.minefield_placement_candidate import Point
from planets_lab.rules.web_circle_phase_envelope import (
    EVIDENCE, PRE_DECAY, POST_DECAY,
    INSIDE_CONFIRMED, EDGE_ABSTAIN, OUTSIDE_CONFIRMED,
    WebCircleGeometryAbstain, classify_web_circle_envelope,
)


def classify(*, xy=Point(0,0), center=Point(0,0), units=100, phase=PRE_DECAY, **overrides):
    kwargs=dict(
        ship_position=xy, field_center=center,
        field_mine_units=units, phase=phase,
        exact_integer_positions_and_phase_confirmed=True,
        standard_field_no_custom_geometry_confirmed=True,
    )
    kwargs.update(overrides)
    return classify_web_circle_envelope(**kwargs)


@pytest.mark.parametrize("phase", [PRE_DECAY, POST_DECAY])
def test_integer_radius_and_explicit_phase_are_preserved(phase):
    r=classify(xy=Point(10,0),phase=phase)
    assert r.phase==phase
    assert r.radius_integer_ly==10
    assert r.conservative_outer_guard_radius_ly==12
    assert r.distance_squared==100
    assert r.classification==INSIDE_CONFIRMED
    assert r.evidence==EVIDENCE
    assert not r.exact_web_cell_raster_verified
    assert not r.actual_host_selection_verified
    assert not r.host_diff_verified


@pytest.mark.parametrize("phase", [PRE_DECAY, POST_DECAY])
def test_clear_inside_near_edge_and_clear_outside(phase):
    assert classify(xy=Point(0,0),phase=phase).classification==INSIDE_CONFIRMED
    assert classify(xy=Point(9,4),phase=phase).classification==INSIDE_CONFIRMED
    assert classify(xy=Point(11,0),phase=phase).classification==EDGE_ABSTAIN
    assert classify(xy=Point(8,7),phase=phase).classification==EDGE_ABSTAIN
    assert classify(xy=Point(12,0),phase=phase).classification==OUTSIDE_CONFIRMED
    assert classify(xy=Point(13,0),phase=phase).classification==OUTSIDE_CONFIRMED


def test_legacy_web_sweep_and_web_drain_decision_windows_are_unchanged():
    # Exhaustive lattice parity across multiple field sizes, both phases.
    for units in (1,2,9,99,100,101,22500):
        radius=isqrt(units)
        for x in range(-35,36):
            for y in range(-35,36):
                dist2=x*x+y*y
                old=(
                    INSIDE_CONFIRMED if dist2 <= radius*radius
                    else EDGE_ABSTAIN if dist2 < (radius+2)**2
                    else OUTSIDE_CONFIRMED
                )
                for phase in (PRE_DECAY,POST_DECAY):
                    r=classify(xy=Point(x,y),units=units,phase=phase)
                    assert r.classification==old
                    assert r.distance_squared==dist2


def test_distance_calculations_use_absolute_coordinates_symmetrically():
    origin=Point(400,-200)
    for x,y in ((10,0),(-10,0),(0,10),(0,-10),(11,0),(-11,0)):
        result=classify(center=origin,xy=Point(origin.x+x,origin.y+y))
        expected=INSIDE_CONFIRMED if x*x+y*y<=100 else EDGE_ABSTAIN
        assert result.classification==expected


def test_typed_immutability():
    a=classify()
    assert a==classify()
    with pytest.raises(FrozenInstanceError):
        a.classification=OUTSIDE_CONFIRMED


@pytest.mark.parametrize("bad",[
    {"phase":"UNKNOWN"},
    {"phase":"pre_decay"},
    {"phase":None},
    {"phase":True},
    {"xy":(0,0)},
    {"xy":Point(True,0)},
    {"xy":Point(1_000_001,0)},
    {"center":(0,0)},
    {"center":Point(0,False)},
    {"center":Point(0,-1_000_001)},
    {"units":0},
    {"units":True},
    {"units":1.0},
    {"units":-1},
    {"units":22501},
    {"units":"100"},
    {"exact_integer_positions_and_phase_confirmed":False},
    {"exact_integer_positions_and_phase_confirmed":1},
    {"standard_field_no_custom_geometry_confirmed":False},
    {"standard_field_no_custom_geometry_confirmed":None},
])
def test_fail_closed_unknown_phase_or_wrong_provenance(bad):
    with pytest.raises(WebCircleGeometryAbstain):
        classify(**bad)


def test_callers_keep_pre_sweep_and_post_drain_phase_distinct():
    source=classify(phase=PRE_DECAY)
    target=classify(phase=POST_DECAY)
    assert source.classification==target.classification
    assert source.phase != target.phase
    # A phase difference is metadata; same inputs must not imply same
    # phase-observed Host event or a real Host order.
    assert source.actual_host_selection_verified is False
    assert target.actual_host_selection_verified is False
