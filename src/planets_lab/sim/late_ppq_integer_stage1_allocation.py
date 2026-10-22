"""Late PPQ regular subphase: uniquely determined integer-share Stage 1.

Documented PPQ allocates max(10, missing soft-cap slots) regular places
after the priority subphase. Stage 1 guarantees each owner its integral
share of currently *owned* planets. Whenever EVERY owner's exact share
is integral, guaranteed slots exhaust the pool: no Stage 2/3 lottery is
needed. This bounded selector resolves per-owner RB1..RB9 / hull-mass
ordering only when the selected base SET is unique (no cutoff ties).

No ship is created, no PP or resources change, and no real NuHost RNG,
ship-ID assignment, accepted orders, phase order or Host outcome is
claimed. Missing full planet/base/queue context => atomic ABSTAIN.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from planets_lab.core import GameState

STATUS = "CONDITIONAL_LATE_PPQ_INTEGRAL_STAGE1_REGULAR_SELECTION_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class PPQRegularBase:
    planet_id: int
    queued: bool
    hull_mass_kt: int | None = None
    rb_code: str | None = None


@dataclass(frozen=True, slots=True)
class PPQStage1Context:
    soft_ship_limit: int
    all_bases: tuple[PPQRegularBase, ...]
    full_planet_fleet_and_base_roster_asserted: bool = False
    complete_queued_hulls_rb_codes_and_eligible_bases_asserted: bool = False
    no_mining_stations_priorities_clones_or_other_host_actions_asserted: bool = False
    regular_subphase_after_priorities_asserted: bool = False
    default_ppq_stage1_owned_planet_share_rule_asserted: bool = False


@dataclass(frozen=True, slots=True)
class PPQStage1Quote:
    status: str
    allocated_regular_slots: int = 0
    owned_planet_counts: tuple[tuple[int, int], ...] = ()
    guaranteed_slots_by_owner: tuple[tuple[int, int], ...] = ()
    selected_base_ids_by_owner: tuple[tuple[int, tuple[int, ...]], ...] = ()
    lowest_available_ship_id_pool: tuple[int, ...] = ()
    reason: str | None = None
    server_selection_verified: bool = False
    server_ship_id_assignment_verified: bool = False
    server_accepted_orders_verified: bool = False
    nuhost_stage_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def _order_key(row: PPQRegularBase) -> tuple[int, int]:
    if row.rb_code is not None:
        return (0, int(row.rb_code[-1]))
    assert row.hull_mass_kt is not None
    return (1, -row.hull_mass_kt)


def quote_integral_ppq_regular_stage1(
    before: GameState, context: PPQStage1Context,
) -> PPQStage1Quote:
    """Quote ONLY the deterministic Stage-1 integer-share selection set.

    No rounding conventions or random lottery are guessed. RB cutoff ties
    abstain even when a local sort could assign a deterministic order.
    """
    def abstain(reason: str) -> PPQStage1Quote:
        return PPQStage1Quote("ABSTAIN_LATE_PPQ_REGULAR_STAGE1", reason=reason)

    if (
        type(before) is not GameState or type(context) is not PPQStage1Context
        or type(context.soft_ship_limit) is not int
        or not 10 <= context.soft_ship_limit < 999
        or type(context.all_bases) is not tuple
        or context.full_planet_fleet_and_base_roster_asserted is not True
        or context.complete_queued_hulls_rb_codes_and_eligible_bases_asserted is not True
        or context.no_mining_stations_priorities_clones_or_other_host_actions_asserted is not True
        or context.regular_subphase_after_priorities_asserted is not True
        or context.default_ppq_stage1_owned_planet_share_rule_asserted is not True
    ):
        return abstain("incomplete default PPQ Stage-1 contract")

    try:
        before.validate()
        if (
            before.metadata or before.ion_storms or not before.players
            or not before.planets or not before.starbases
            or len(before.starbases) != len(context.all_bases)
            or len(before.starbases) > 128
            or any(type(sid) is not int or not 1 <= sid <= 999
                   or type(ship.id) is not int or ship.id != sid
                   for sid, ship in before.ships.items())
            or len(before.ships) >= context.soft_ship_limit
        ):
            return abstain("incomplete roster, custom state, or no late regular opening")
        gap = context.soft_ship_limit - len(before.ships)
        slots = max(10, gap)
        if (
            slots > 64 or len(before.ships) + slots > 999
            or sum(1 for row in context.all_bases
                   if type(row) is PPQRegularBase and row.queued is True) <= gap
        ):
            return abstain("early unthrottled phase or unsupported regular slot count")

        owners: dict[int, int] = {pid: 0 for pid in before.players}
        for planet in before.planets.values():
            if planet.owner_id is not None:
                if type(planet.owner_id) is not int or planet.owner_id not in owners:
                    return abstain("unknown planet owner")
                owners[planet.owner_id] += 1
        total_owned = sum(owners.values())
        if total_owned == 0:
            return abstain("no owned planets: cannot determine PPQ share")

        guaranteed: dict[int, int] = {}
        for owner, count in owners.items():
            whole, remainder = divmod(slots * count, total_owned)
            if remainder:
                return abstain("nonintegral share requires PPQ Stage-2/3 lottery")
            guaranteed[owner] = whole
        if sum(guaranteed.values()) != slots:
            return abstain("unaccounted guaranteed regular slots")

        seen: set[int] = set()
        candidates: dict[int, list[PPQRegularBase]] = {
            owner: [] for owner in before.players
        }
        for row in context.all_bases:
            if (
                type(row) is not PPQRegularBase
                or type(row.planet_id) is not int
                or row.planet_id not in before.starbases
                or row.planet_id in seen
                or type(row.queued) is not bool
            ):
                return abstain("missing or duplicate ordinary starbase entry")
            seen.add(row.planet_id)
            base = before.starbases[row.planet_id]
            planet = before.planets[row.planet_id]
            if (
                base.owner_id != planet.owner_id
                or base.owner_id not in candidates
            ):
                return abstain("planet/starbase ownership disagreement")
            if row.queued:
                if (
                    type(row.hull_mass_kt) is not int
                    or not 1 <= row.hull_mass_kt <= 1000000
                    or (row.rb_code is not None and (
                        type(row.rb_code) is not str
                        or re.fullmatch(r"(?i:rb)[1-9]", row.rb_code) is None
                    ))
                ):
                    return abstain("incomplete hull mass or invalid RB code")
                candidates[base.owner_id].append(row)
            elif row.hull_mass_kt is not None or row.rb_code is not None:
                return abstain("nonqueued base has an unmodeled regular order")
        if seen != set(before.starbases):
            return abstain("incomplete build-capable starbase roster")
        if any(
            ship.warp != 0 or ship.damage != 0 or ship.mission is not None
            or ship.mission1_target_id is not None
            or ship.mission2_target_id is not None
            for ship in before.ships.values()
        ):
            return abstain("unmodeled fleet orders or combat")

        selected: list[tuple[int, tuple[int, ...]]] = []
        for owner in sorted(guaranteed):
            quota = guaranteed[owner]
            ranked = sorted(candidates[owner],
                            key=lambda row: (_order_key(row), row.planet_id))
            if len(ranked) < quota:
                return abstain("owner cannot fill its guaranteed allocation")
            if 0 < quota < len(ranked) and (
                _order_key(ranked[quota - 1]) == _order_key(ranked[quota])
            ):
                return abstain("random RB/hull tie crosses owner selection cutoff")
            selected.append((owner, tuple(sorted(row.planet_id
                                                  for row in ranked[:quota]))))
        if sum(len(bases) for _, bases in selected) != slots:
            return abstain("allocated and selected slot count mismatch")
        free_ids = tuple(sid for sid in range(1, 1000)
                         if sid not in before.ships)[:slots]
        if len(free_ids) != slots:
            return abstain("insufficient legal ship IDs")
        return PPQStage1Quote(
            STATUS, allocated_regular_slots=slots,
            owned_planet_counts=tuple(sorted(owners.items())),
            guaranteed_slots_by_owner=tuple(sorted(guaranteed.items())),
            selected_base_ids_by_owner=tuple(selected),
            lowest_available_ship_id_pool=free_ids,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("invalid or incomplete late PPQ owned-planet/queue state")
