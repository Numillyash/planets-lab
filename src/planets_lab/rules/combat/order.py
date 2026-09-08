from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


# Numeric mission mappings established by C5 corpus evidence / existing project
# convention. Keep these constants near the mechanics that consume them rather
# than scattering anonymous IDs through diagnostics and simulation code.
KILL_MISSION_ID = 3
INTERCEPT_MISSION_ID = 7
CLOAK_INTERCEPT_MISSION_ID = 20
BIRD_RACE_ID = 3


class FriendlyCodePriorityKind(str, Enum):
    """How a Friendly Code participates in standard ship combat priority."""

    NUMERIC = "numeric"
    SYMBOLIC = "symbolic"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class FriendlyCodePriority:
    kind: FriendlyCodePriorityKind
    numeric_value: int | None = None
    evidence: str = ""


def classify_battle_friendly_code(value: Any) -> FriendlyCodePriority:
    """Classify the Friendly Code for C5 standard battle ordering.

    Documented NuHost ordering accepts ``001`` through ``999`` as numeric battle
    values. C5 corpus differential additionally established that exact
    three-character signed codes of the form ``+NN`` / ``-NN`` behave as signed
    numeric values. The latter behavior is corpus-observed and diff-verified, but
    is not documented by Planets.nu.

    ``000`` and numeric-looking strings of other lengths remain unsupported here.
    Official documentation describes one/two-digit and ``000`` behavior as
    inconsistent/erratic, so the simulator must fail closed rather than silently
    normalize them. Ordinary symbolic three-character codes participate only via
    mission / Primary Enemy priority groups.
    """

    if not isinstance(value, str):
        return FriendlyCodePriority(
            FriendlyCodePriorityKind.UNSUPPORTED,
            evidence="missing_or_non_string",
        )

    if len(value) == 3 and value.isdigit():
        numeric = int(value)
        if 1 <= numeric <= 999:
            return FriendlyCodePriority(
                FriendlyCodePriorityKind.NUMERIC,
                numeric_value=numeric,
                evidence="documented_001_999",
            )
        return FriendlyCodePriority(
            FriendlyCodePriorityKind.UNSUPPORTED,
            evidence="documented_000_inconsistent",
        )

    if (
        len(value) == 3
        and value[0] in "+-"
        and value[1:].isdigit()
    ):
        return FriendlyCodePriority(
            FriendlyCodePriorityKind.NUMERIC,
            numeric_value=int(value),
            evidence="corpus_signed_three_character",
        )

    if value.isdigit() or (
        value[:1] in {"+", "-"}
        and len(value) > 1
        and value[1:].isdigit()
    ):
        return FriendlyCodePriority(
            FriendlyCodePriorityKind.UNSUPPORTED,
            evidence="noncanonical_numeric_shape",
        )

    return FriendlyCodePriority(
        FriendlyCodePriorityKind.SYMBOLIC,
        evidence="standard_symbolic",
    )


def standard_battle_priority_key(
    *,
    ship_id: int,
    mission: int | None,
    primary_enemy: int | None,
    friendly_code: Any,
) -> tuple[int, int, int] | None:
    """Return the standard post-intercept ship combat priority key.

    Smaller tuples have higher combat priority. This function models only the
    documented standard ordering groups plus the accepted C5 signed-FC parsing.
    It does *not* decide whether two ships are eligible to fight each other.

    ``None`` means the Friendly Code shape is intentionally unsupported and the
    caller must fail closed.
    """

    if isinstance(ship_id, bool) or not isinstance(ship_id, int) or ship_id <= 0:
        raise ValueError("ship_id must be a positive integer")

    fc = classify_battle_friendly_code(friendly_code)
    if fc.kind is FriendlyCodePriorityKind.UNSUPPORTED:
        return None
    if fc.kind is FriendlyCodePriorityKind.NUMERIC:
        assert fc.numeric_value is not None
        return (0, fc.numeric_value, ship_id)

    enemy = primary_enemy if isinstance(primary_enemy, int) and not isinstance(primary_enemy, bool) else 0
    has_pe = enemy > 0
    kill = mission == KILL_MISSION_ID

    if kill and has_pe:
        group = 1
    elif kill:
        group = 2
    elif has_pe:
        group = 3
    else:
        group = 4
    return (group, ship_id, 0)


def orders_request_ship_combat(
    *,
    mission: int | None,
    primary_enemy: int | None,
    opponent_owner_id: int | None,
) -> bool:
    """Return whether Kill!/Primary Enemy orders request hostility.

    This is deliberately narrower than Host engagement eligibility: fuel,
    diplomacy, cloaking, matching Friendly Codes, special abilities and other
    suppressors/overrides are not evaluated here.
    """

    if mission == KILL_MISSION_ID:
        return True
    if (
        isinstance(primary_enemy, int)
        and not isinstance(primary_enemy, bool)
        and primary_enemy > 0
        and isinstance(opponent_owner_id, int)
        and not isinstance(opponent_owner_id, bool)
        and opponent_owner_id > 0
    ):
        return primary_enemy == opponent_owner_id
    return False


def cloak_intercept_order_signature(
    *,
    mission: int | None,
    owner_race_id: int | None,
    mission_target_id: int | None,
    primary_enemy: int | None,
    target_owner_id: int | None,
    hull_can_cloak: bool | None,
) -> bool | None:
    """Recognize the documented Bird Cloak-and-Intercept pre-standard signature.

    ``True`` means an already-observed order has the factual ingredients needed
    for the documented C&I pre-standard target attack: Bird owner, cloak-capable
    hull, mission 20, positive intercept target, and Primary Enemy matching the
    target owner.

    ``False`` means enough state is known and the signature is not present.
    ``None`` means mission 20 is present but a required mechanical fact is
    unknown, so callers must fail closed.

    This does not prove that the C&I advantage is enabled for an arbitrary game
    or player. Historical mission-20 records themselves establish that the order
    existed; future full simulation must model game/player advantage enablement
    separately.
    """

    if mission != CLOAK_INTERCEPT_MISSION_ID:
        return False

    required = (
        owner_race_id,
        mission_target_id,
        primary_enemy,
        target_owner_id,
        hull_can_cloak,
    )
    if any(value is None for value in required):
        return None

    assert mission_target_id is not None
    assert primary_enemy is not None
    assert target_owner_id is not None
    assert hull_can_cloak is not None

    return (
        owner_race_id == BIRD_RACE_ID
        and hull_can_cloak
        and mission_target_id > 0
        and target_owner_id > 0
        and primary_enemy == target_owner_id
    )
