"""Pure ship-to-ship battle-sequence carry-over rules.

This module owns only state carried from one resolved ship battle into a later
battle. It does not decide Host engagement eligibility, battle ordering, sides,
or planet/starbase persistence.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CAPTURE_PRIZE_CREW = 10


DYNAMIC_CARRY_FIELDS = ("shield", "damage", "crew", "torpedoes", "fighters")


def _physical_count(raw: Mapping[str, Any], physical_key: str, effective_key: str) -> int:
    value = raw.get(physical_key)
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    value = raw.get(effective_key, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


def functional_weapon_limit(raw: Mapping[str, Any]) -> int:
    """Return the damage-limited number of functional weapon slots.

    Federation crew bonus keeps installed weapons functional despite damage.
    Lizard crew bonus extends the functional threshold to the 150% damage
    envelope. These are explicit simulator inputs, not inferred from race id.
    """

    damage_value = raw.get("damage", 0)
    damage = max(0, damage_value if isinstance(damage_value, int) and not isinstance(damage_value, bool) else 0)
    if bool(raw.get("federation_crew_bonus")):
        return 10
    if bool(raw.get("lizard_crew_bonus")):
        return max(0, min(10, 15 - damage // 10))
    return max(0, min(10, 10 - damage // 10))


def prepare_sequence_ship(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize effective weapon counts for the ship's next engagement."""

    result = deepcopy(dict(raw))
    hull_id = result.get("hull_id", 0)
    if isinstance(hull_id, bool) or not isinstance(hull_id, int) or hull_id <= 0:
        raise ValueError("ship sequence carry-over requires a positive hull_id")

    physical_beams = _physical_count(result, "physical_beam_count", "beam_count")
    physical_launchers = _physical_count(
        result,
        "physical_launcher_count",
        "launcher_count",
    )
    physical_bays = _physical_count(result, "physical_bay_count", "bay_count")
    limit = functional_weapon_limit(result)

    if bool(result.get("federation_crew_bonus")):
        result["beam_count"] = physical_beams
        result["launcher_count"] = physical_launchers
        result["bay_count"] = physical_bays + (3 if physical_bays > 0 else 0)
    else:
        result["beam_count"] = min(physical_beams, limit)
        result["launcher_count"] = min(physical_launchers, limit)
        result["bay_count"] = min(physical_bays, limit)
    return result


def apply_terminal_state(
    target: Mapping[str, Any],
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a copy of ``target`` with dynamic combat state carried forward."""

    result = deepcopy(dict(target))
    for key in DYNAMIC_CARRY_FIELDS:
        value = terminal.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            result[key] = value
    return result


def federation_recover_shields(raw: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    """Apply the explicit Federation between-fight shield recovery candidate.

    Historical Nu VCR chains show a fixed recovery of up to 25 shield points,
    capped by the damage-reduced maximum shield level. The rule is only applied
    when ``federation_crew_bonus`` is explicitly true; historical diagnostics
    must not infer that flag from race id alone.
    """

    result = deepcopy(dict(raw))
    if not bool(result.get("federation_crew_bonus")):
        return result, 0

    shield_value = result.get("shield", 0)
    damage_value = result.get("damage", 0)
    shield = max(0, min(100, shield_value if isinstance(shield_value, int) and not isinstance(shield_value, bool) else 0))
    damage = max(0, damage_value if isinstance(damage_value, int) and not isinstance(damage_value, bool) else 0)
    max_shield = max(0, 100 - damage)
    next_shield = min(max_shield, shield + 25)
    result["shield"] = next_shield
    return result, max(0, next_shield - shield)


def carry_ship_to_next_engagement(
    ship: Mapping[str, Any],
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    """Carry one surviving ship's state into its next explicit engagement."""

    if bool(terminal.get("destroyed") or terminal.get("captured")):
        raise ValueError("defeated ship cannot be carried to another engagement")
    carried = apply_terminal_state(ship, terminal)
    carried, _recovered = federation_recover_shields(carried)
    return prepare_sequence_ship(carried)



def carry_captured_ship_to_next_engagement(
    ship: Mapping[str, Any],
    terminal: Mapping[str, Any],
    *,
    new_owner_id: int,
    new_race_id: int,
    new_federation_crew_bonus: bool,
    new_lizard_crew_bonus: bool,
) -> dict[str, Any]:
    """Carry one combat-captured ship into its next same-turn engagement.

    Evidence-scoped ordering:

    1. apply the deterministic combat terminal vector;
    2. apply any end-of-battle Federation shield recovery using the ship's
       *pre-capture* crew-bonus state;
    3. install the documented 10-person prize crew;
    4. transfer owner/race identity to the captor;
    5. switch race-derived combat bonus flags to the new owner;
    6. recompute effective weapon counts for the next engagement.

    The helper deliberately does not infer the captor.  Queue/orchestration
    callers must supply explicit transfer metadata.
    """

    if terminal.get("captured") is not True or terminal.get("destroyed") is not False:
        raise ValueError("capture carry requires captured=True and destroyed=False")
    for name, value in (
        ("new_owner_id", new_owner_id),
        ("new_race_id", new_race_id),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if not isinstance(new_federation_crew_bonus, bool):
        raise ValueError("new_federation_crew_bonus must be boolean")
    if not isinstance(new_lizard_crew_bonus, bool):
        raise ValueError("new_lizard_crew_bonus must be boolean")

    carried = apply_terminal_state(ship, terminal)
    carried, _recovered = federation_recover_shields(carried)
    carried["crew"] = CAPTURE_PRIZE_CREW
    carried["owner_id"] = new_owner_id
    carried["race_id"] = new_race_id
    carried["federation_crew_bonus"] = new_federation_crew_bonus
    carried["lizard_crew_bonus"] = new_lizard_crew_bonus
    return prepare_sequence_ship(carried)
