from planets_lab.corpus.movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _movement_category,
)
from planets_lab.corpus.movement_sphere_context import (
    MOVEMENT_EFFECTIVE_TOPOLOGY_SCHEMA,
    effective_sphere_category,
    effective_sphere_topology,
)
from planets_lab.corpus.movement_topology_diagnostics import (
    MapTopologyEvidence,
    _wrapped_planets_near,
    sphere_adjusted_sample,
)
from planets_lab.validation.movement_geometry import MovementSample


def _sphere_topology(*, width: int = 2150, height: int = 2150, stable: bool = True) -> MapTopologyEvidence:
    return MapTopologyEvidence(
        sphere=True,
        mapwidth=width,
        mapheight=height,
        mapshape=1,
        first_member="first.trn",
        last_member="last.trn",
        stable=stable,
        first_candidates={},
        last_candidates={},
    )


def _seam_sample() -> MovementSample:
    # Under the audited 2170 period the wrapped target is (2270, 1100) and
    # Host major/minor movement at warp 9 lands at (2204, 1049), stored as x=34.
    # Under raw 2150 geometry both target and observed images differ, so the
    # same transition remains unresolved.
    return MovementSample(
        turn=10,
        ship_id=46,
        x=2140,
        y=1000,
        target_x=100,
        target_y=1100,
        warp=9,
        next_x=34,
        next_y=1049,
        hull_id=46,
    )


def test_effective_topology_is_exactly_scoped_and_preserves_raw_fact_object() -> None:
    raw = _sphere_topology()
    effective = effective_sphere_topology(game_id=591478, topology=raw)

    assert MOVEMENT_EFFECTIVE_TOPOLOGY_SCHEMA.endswith(".v1")
    assert (raw.mapwidth, raw.mapheight) == (2150, 2150)
    assert (effective.mapwidth, effective.mapheight) == (2170, 2170)
    assert effective is not raw

    assert effective_sphere_topology(game_id=591479, topology=raw) is raw
    assert effective_sphere_topology(
        game_id=591478,
        topology=_sphere_topology(width=2170, height=2170),
    ).mapwidth == 2170
    unstable = _sphere_topology(stable=False)
    assert effective_sphere_topology(game_id=591478, topology=unstable) is unstable


def test_2170_seam_geometry_closes_transition_that_raw_2150_does_not() -> None:
    sample = _seam_sample()
    raw = _sphere_topology()

    raw_adjusted = sphere_adjusted_sample(sample, width=2150, height=2150)
    raw_planets = _wrapped_planets_near(
        (sample.x, sample.y),
        (),
        width=2150,
        height=2150,
    )
    raw_category = _movement_category(raw_adjusted, planets=raw_planets)
    assert raw_category not in GEOMETRY_EXPLAINED_CATEGORIES

    category = effective_sphere_category(
        sample,
        game_id=591478,
        topology=raw,
        planets=(),
    )
    assert category == "effective_sphere_partial_host_major_minor"


def test_same_transition_fails_closed_outside_audited_scope() -> None:
    assert effective_sphere_category(
        _seam_sample(),
        game_id=591479,
        topology=_sphere_topology(),
        planets=(),
    ) is None
