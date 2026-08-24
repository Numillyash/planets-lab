from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def route_equivalent_chunnel_category(
    matches: Sequence[Any],
    *,
    ship_id: int,
    owner_id: int,
) -> str | None:
    """Classify a non-empty set of already route-equivalent Chunnel events.

    Callers must first filter events to the same candidate pre-Chunnel position
    and the same observed destination. Multiple such events are mechanically
    equivalent for movement closure: any one of them explains the displacement.
    Only the descriptive role can remain ambiguous when different matching
    events assign different roles to the same ship.
    """

    if not matches:
        return None

    roles: set[str] = set()
    for event in matches:
        if ship_id == int(event.initiator_ship_id):
            roles.add("initiator")
        elif owner_id == int(event.owner_id):
            roles.add("passenger_same_owner")
        else:
            roles.add("passenger_other_owner")

    if len(roles) == 1:
        return next(iter(roles))
    return "route_equivalent_multiple_roles"
