from __future__ import annotations


SUPPLIES_PER_DAMAGE_POINT = 5
LIZARD_RACE_ID = 2


def repair_damage_with_supplies(*, damage: int, supplies: int) -> tuple[int, int, int]:
    """Return (remaining_damage, remaining_supplies, repaired_damage).

    Planets.nu automatically spends 5 KT supplies per 1 percentage point of
    starship damage during the Host repair step. Only complete 5-KT groups can
    repair damage.
    """

    if damage < 0:
        raise ValueError("damage must be non-negative")
    if supplies < 0:
        raise ValueError("supplies must be non-negative")

    repaired = min(damage, supplies // SUPPLIES_PER_DAMAGE_POINT)
    return (
        damage - repaired,
        supplies - repaired * SUPPLIES_PER_DAMAGE_POINT,
        repaired,
    )


def damage_warp_limit(*, damage: int, lizard_crew: bool = False) -> int:
    """Return the maximum warp permitted by current starship damage.

    For ordinary crews, 0-19% damage permits Warp 9 and each additional 10%
    band reduces the limit by one until 100% damage. Lizard crews retain Warp 9
    through 69% and then lose one warp factor per 10% band through 150%.
    """

    if damage < 0:
        raise ValueError("damage must be non-negative")

    if lizard_crew:
        if damage > 150:
            return 0
        return max(0, min(9, 15 - damage // 10))

    if damage >= 100:
        return 0
    return max(1, min(9, 10 - damage // 10))


def effective_warp(*, ordered_warp: int, damage: int, lizard_crew: bool = False) -> int:
    if not 0 <= ordered_warp <= 9:
        raise ValueError("ordered_warp must be between 0 and 9")
    return min(ordered_warp, damage_warp_limit(damage=damage, lizard_crew=lizard_crew))
