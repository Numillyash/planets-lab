from planets_lab.corpus.movement_damage_context import (
    DAMAGE_LIMITED_WARP_CATEGORY,
    damage_limited_warp_match,
    max_warp_from_damage,
)
from planets_lab.validation.movement_geometry import MovementSample


def _sample(*, warp: int, next_x: int, next_y: int = 0, gravitonic: bool = False) -> MovementSample:
    return MovementSample(
        turn=10,
        ship_id=1,
        x=0,
        y=0,
        target_x=200,
        target_y=0,
        warp=warp,
        next_x=next_x,
        next_y=next_y,
        hull_id=17,
        gravitonic=gravitonic,
    )


def test_standard_damage_table_maximum_warp() -> None:
    assert max_warp_from_damage(0, 1) == 9
    assert max_warp_from_damage(19, 1) == 9
    assert max_warp_from_damage(20, 1) == 8
    assert max_warp_from_damage(38, 1) == 7
    assert max_warp_from_damage(40, 1) == 6
    assert max_warp_from_damage(56, 1) == 5
    assert max_warp_from_damage(65, 1) == 4
    assert max_warp_from_damage(76, 1) == 3
    assert max_warp_from_damage(89, 1) == 2
    assert max_warp_from_damage(96, 1) == 1
    assert max_warp_from_damage(100, 1) is None


def test_lizard_damage_table_maximum_warp() -> None:
    assert max_warp_from_damage(0, 2) == 9
    assert max_warp_from_damage(69, 2) == 9
    assert max_warp_from_damage(70, 2) == 8
    assert max_warp_from_damage(99, 2) == 6
    assert max_warp_from_damage(100, 2) == 5
    assert max_warp_from_damage(140, 2) == 1
    assert max_warp_from_damage(150, 2) == 0
    assert max_warp_from_damage(151, 2) is None


def test_strict_damage_limit_requires_exact_endpoint_and_low_supplies() -> None:
    # Standard-race damage 38% limits Warp 9 to Warp 7 -> 49 ly.
    sample = _sample(warp=9, next_x=49)
    assert damage_limited_warp_match(sample, race_id=1, damage=38, supplies=0) == 7
    assert damage_limited_warp_match(sample, race_id=1, damage=38, supplies=4) == 7

    # Current cargo capable of even 1% repair is deliberately not promoted.
    assert damage_limited_warp_match(sample, race_id=1, damage=38, supplies=5) is None

    # Same damage, wrong endpoint: correlation alone is insufficient.
    wrong = _sample(warp=9, next_x=48)
    assert damage_limited_warp_match(wrong, race_id=1, damage=38, supplies=0) is None

    # Undamaged / not-limited ships are negative controls.
    assert damage_limited_warp_match(sample, race_id=1, damage=0, supplies=0) is None


def test_gravitonic_damage_limit_uses_effective_warp_distance() -> None:
    # Gravitonic Warp 7 movement has a 98 ly nominal limit.
    sample = _sample(warp=9, next_x=98, gravitonic=True)
    assert damage_limited_warp_match(sample, race_id=1, damage=38, supplies=0) == 7


def test_category_name_is_stable() -> None:
    assert DAMAGE_LIMITED_WARP_CATEGORY == "damage_limited_warp_match"
