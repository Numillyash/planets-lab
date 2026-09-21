"""Ship-combat engagement eligibility primitives.

These helpers model narrow documented blockers/overrides around whether a
ship-vs-ship engagement may occur. They do not choose an opponent, assign
left/right sides, or resolve combat.
"""

from __future__ import annotations

from typing import Any

from .order import BIRD_RACE_ID


# Planets.nu documents these three ship Friendly Codes as exceptions to the
# normal exact-matching-FC combat suppression rule. Functionality is
# case-insensitive, while ordinary FC matching itself is case-sensitive.
MATCHING_SHIP_FC_COMBAT_EXCEPTIONS = frozenset({"mkt", "ntp", "lfm"})


def _friendly_code(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def matching_ship_friendly_code_blocks_combat(
    *,
    left_friendly_code: Any,
    right_friendly_code: Any,
    left_race_id: int | None,
    right_race_id: int | None,
    left_harmonic_weapon_modulation_enabled: bool | None,
    right_harmonic_weapon_modulation_enabled: bool | None,
) -> bool | None:
    """Return whether exact matching ship FCs suppress this engagement.

    Planets.nu documents exact, case-sensitive matching Friendly Codes as a
    ship-vs-ship combat blocker, except for MKT/NTP/LFM (case-insensitive as
    special-code functions). Bird Harmonic Weapon Modulation (HWM) overrides
    matching-FC suppression when that advantage is effectively enabled.

    ``False`` means matching-FC suppression does not block the pair; another
    eligibility rule may still block combat. ``True`` means the documented
    matching-FC blocker applies. ``None`` means the FCs match but effective HWM
    state cannot be decided from the supplied race/advantage facts.

    Effective advantage state is an input on purpose. The helper never infers
    Campaign research/activation from race alone.
    """

    left_fc = _friendly_code(left_friendly_code)
    right_fc = _friendly_code(right_friendly_code)
    if left_fc is None or right_fc is None:
        return None

    if left_fc != right_fc:
        return False

    if left_fc.casefold() in MATCHING_SHIP_FC_COMBAT_EXCEPTIONS:
        return False

    sides = (
        (left_race_id, left_harmonic_weapon_modulation_enabled),
        (right_race_id, right_harmonic_weapon_modulation_enabled),
    )

    # Any known active Bird HWM is sufficient to defeat the matching-FC block.
    if any(race_id == BIRD_RACE_ID and enabled is True for race_id, enabled in sides):
        return False

    # A known Bird with unknown effective HWM state can still change the answer.
    if any(race_id == BIRD_RACE_ID and enabled is None for race_id, enabled in sides):
        return None

    # Unknown race with unknown/claimed-active HWM state is also insufficient to
    # establish suppression. Explicit disabled state is enough to rule HWM out.
    if any(
        race_id is None and enabled is not False
        for race_id, enabled in sides
    ):
        return None

    return True


def harmonic_weapon_modulation_applies(
    *,
    bird_race_id: int | None,
    harmonic_weapon_modulation_enabled: bool | None,
    bird_friendly_code: Any,
    opponent_friendly_code: Any,
) -> bool | None:
    """Return whether Bird HWM applies its matching-FC combat effect.

    When enabled, Planets.nu documents HWM as allowing a Bird ship to fight a
    foreign ship with the same Friendly Code and forcing that other ship to
    fight without shields.

    This helper only recognizes the documented trigger. It does not decide
    diplomacy, fuel, target selection, or whether the engagement otherwise
    occurs.
    """

    bird_fc = _friendly_code(bird_friendly_code)
    opponent_fc = _friendly_code(opponent_friendly_code)
    if bird_fc is None or opponent_fc is None:
        return None

    if bird_race_id is not None and bird_race_id != BIRD_RACE_ID:
        return False

    if bird_fc != opponent_fc:
        return False

    if bird_race_id is None:
        return None
    if harmonic_weapon_modulation_enabled is None:
        return None
    return harmonic_weapon_modulation_enabled
