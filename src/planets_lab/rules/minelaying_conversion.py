"""Standard starship torpedo-to-mine conversion *quote*, not field placement.

Official sources:
  https://help.planets.nu/minefields
  https://help.planets.nu/friendly-codes

Yields, mdN/md0/MDA limits, and Robot 4x bonus are DOCUMENTED.
Actual Host mine-laying/merging/splitting, geometry, interference, friendly
code order, ship mission acceptance, and phase ordering remain UNVERIFIED.

This module never mutates the ship's inventory, constructs a MinefieldState,
consumes a field ID or chooses/expands an existing field. The result is an
explicitly UNALLOCATED mine-unit *proposal* to compose only after relevant
Host-phase/placement evidence becomes available.
"""
from __future__ import annotations

from dataclasses import dataclass

# Exact names of documented standard torpedo families. These are NOT Nu
# dynamic component IDs, and must never be mapped onto client hull/weapon
# IDs without independent game-spec provenance.
STANDARD_TORPEDO_MINE_YIELDS: dict[str, int] = {
    "mark_1_photon": 1,
    "proton_torp": 4,
    "mark_2_photon": 9,
    "gamma_bomb": 16,
    "mark_3_photon": 25,
    "mark_4_photon": 36,
    "mark_5_photon": 49,
    "mark_6_photon": 64,
    "mark_7_photon": 81,
    "mark_8_photon": 100,
    "quantum": 121,
}
STANDARD_MAX_RADII = frozenset((100, 150))
MAX_QUOTED_TORPEDOES = 10000
EVIDENCE = "DOCUMENTED_CONVERSION_AND_TESTED_CONDITIONAL_NOT_HOST_ACCEPTED"


class MineLayingQuoteAbstain(ValueError):
    """Unsupported, insufficiently witnessed or ambiguous conversion input."""


@dataclass(frozen=True, slots=True)
class MineLayingQuote:
    torpedo_family: str
    mission: str
    drop_code: str
    torpedoes_before: int
    torpedoes_converted: int
    torpedoes_remaining: int
    base_mine_units_per_torpedo: int
    asserted_robot_laying_multiplier: int
    unallocated_mine_units: int
    single_empty_standard_field_capacity: int
    unallocated_units_exceed_single_field_capacity: bool
    uses_web_mine_units: bool
    evidence: str = EVIDENCE
    field_created_or_expanded: bool = False
    minefield_allocation_verified: bool = False
    host_mission_accepted_verified: bool = False
    host_phase_order_verified: bool = False
    host_causal_verified: bool = False


def _drop_count(torpedoes_held: int, drop_code: str) -> int:
    # mdN uses ten times the decimal N, except md0 means 100.
    if drop_code in ("ALL", "MDA"):
        return torpedoes_held
    if len(drop_code) == 3 and drop_code[:2] == "MD" and drop_code[2] in "0123456789":
        limit = 100 if drop_code[2] == "0" else 10 * int(drop_code[2])
        return min(torpedoes_held, limit)
    raise MineLayingQuoteAbstain("ambiguous or unsupported mine-drop control")


def quote_standard_starship_minelaying(
    *,
    torpedo_family: str,
    torpedoes_held: int,
    drop_code: str,
    mission: str,
    standard_torpedo_catalog_confirmed: bool,
    ordinary_no_custom_modifiers_confirmed: bool,
    mission_and_tubes_eligible_confirmed: bool,
    web_permission_confirmed: bool,
    robot_fourfold_bonus_confirmed: bool,
    robot_field_owner_is_self_confirmed: bool,
    max_radius: int = 150,
) -> MineLayingQuote:
    """Quote an isolated torpedo inventory change and *unallocated* mine units.

    All confirmation flags are **conditional caller preconditions**, not
    independently proven server orders. False/unknown is an ABSTAIN unless
    a flag is deliberately inapplicable (web permission for a normal field;
    Robot owner identity when no Robot bonus is asserted).
    """
    if (
        standard_torpedo_catalog_confirmed is not True
        or ordinary_no_custom_modifiers_confirmed is not True
        or mission_and_tubes_eligible_confirmed is not True
    ):
        raise MineLayingQuoteAbstain("standard torpedo catalog/mission/rules unverified")
    if type(torpedo_family) is not str or torpedo_family not in STANDARD_TORPEDO_MINE_YIELDS:
        raise MineLayingQuoteAbstain("unknown standard torpedo family")
    if type(torpedoes_held) is not int or not 0 <= torpedoes_held <= MAX_QUOTED_TORPEDOES:
        raise MineLayingQuoteAbstain("unbounded or untyped ammunition quantity")
    if type(drop_code) is not str:
        raise MineLayingQuoteAbstain("untyped mine-drop control")
    if mission not in ("LAY_MINES", "LAY_WEB_MINES") or type(mission) is not str:
        raise MineLayingQuoteAbstain("unrecognized mission")
    if type(max_radius) is not int or max_radius not in STANDARD_MAX_RADII:
        raise MineLayingQuoteAbstain("custom/dense/unknown max field radius")
    if (
        type(web_permission_confirmed) is not bool
        or type(robot_fourfold_bonus_confirmed) is not bool
        or type(robot_field_owner_is_self_confirmed) is not bool
    ):
        raise MineLayingQuoteAbstain("ambiguous race ownership or web permission")
    web = mission == "LAY_WEB_MINES"
    if web and web_permission_confirmed is not True:
        raise MineLayingQuoteAbstain("web minelaying permission not confirmed")
    if robot_fourfold_bonus_confirmed and (
        web or robot_field_owner_is_self_confirmed is not True
    ):
        # Official rules exclude the 4x bonus when laying mines for
        # another player using miN, and ordinary Robots cannot be
        # silently promoted to Crystal web mine layers.
        raise MineLayingQuoteAbstain("Robot 4x bonus not applicable to asserted owner/mission")

    spent = _drop_count(torpedoes_held, drop_code)
    base_yield = STANDARD_TORPEDO_MINE_YIELDS[torpedo_family]
    multiplier = 4 if robot_fourfold_bonus_confirmed else 1
    unallocated = spent * base_yield * multiplier
    remaining = torpedoes_held - spent
    if remaining < 0 or remaining + spent != torpedoes_held:
        raise MineLayingQuoteAbstain("ammunition conservation failure")
    cap = max_radius * max_radius
    return MineLayingQuote(
        torpedo_family=torpedo_family,
        mission=mission,
        drop_code=drop_code,
        torpedoes_before=torpedoes_held,
        torpedoes_converted=spent,
        torpedoes_remaining=remaining,
        base_mine_units_per_torpedo=base_yield,
        asserted_robot_laying_multiplier=multiplier,
        unallocated_mine_units=unallocated,
        single_empty_standard_field_capacity=cap,
        unallocated_units_exceed_single_field_capacity=unallocated > cap,
        uses_web_mine_units=web,
    )
