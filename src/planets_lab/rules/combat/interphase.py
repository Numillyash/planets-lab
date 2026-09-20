"""Inter-phase Host repair primitives used around combat phases.

The ordinary supply-repair rule is documented by Planets.nu and independently
visible in historical ship->planet VCR transitions:

- five KT of supplies repair one percentage point of ship damage;
- all usable supplies are consumed automatically;
- repair does not restore crew or recharge shields;
- Host performs a Mass check / repair / MKT step after ship-vs-ship combat and
  before ship-vs-planet/base combat.

MKT torpedo construction is intentionally not implemented here yet. It needs a
separate resource/catalog boundary and is not required by the currently
observed ship->planet transition population.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .sequence import prepare_sequence_ship


SUPPLIES_PER_DAMAGE_POINT = 5


def repair_ship_with_supplies(
    raw: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    """Apply one automatic ordinary supply-repair opportunity.

    Returns (next_state, repaired_damage_points).

    The helper consumes exactly five KT of supplies per repaired damage point,
    caps repair at current damage, preserves shields/crew/ammunition, and
    recomputes damage-limited functional weapon counts for the following combat
    engagement.

    damage and supplies must be explicit non-negative integers. A valid
    positive hull_id is required because functional weapon counts are rebuilt
    for the post-repair state.
    """

    result = deepcopy(dict(raw))

    for name in ("damage", "supplies"):
        value = result.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")

    damage = int(result["damage"])
    supplies = int(result["supplies"])

    repaired = min(damage, supplies // SUPPLIES_PER_DAMAGE_POINT)
    result["damage"] = damage - repaired
    result["supplies"] = supplies - repaired * SUPPLIES_PER_DAMAGE_POINT

    return prepare_sequence_ship(result), repaired
