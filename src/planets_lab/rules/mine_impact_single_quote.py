"""Pure one-hit normal/web mine damage quote, NOT a movement/Host replay.

https://help.planets.nu/minefields : Mine Impact
- Normal damage percent: ceil(10000 / (hull mass + 1)).
- Web damage percent: ceil(1000 / (hull mass + 1)).
- Per-light-year base hit odds: normal 1%, normal cloaked 0.5%,
  web 5% whether cloaked or not.
- Towed ships cannot be hit by ordinary or web mines.

No random draw, mine position, mine hit actually observed, cumulative damage,
ship destruction threshold, fuel loss, movement stop or Host phase is inferred.
"""
from __future__ import annotations

from dataclasses import dataclass

EVIDENCE = "DOCUMENTED_ONE_MINE_IMPACT_QUOTE_TESTED_CONDITIONAL_NOT_HOST_VERIFIED"
MAX_QUOTED_HULL_MASS_KT = 1_000_000  # calculation guard, NOT Host hull limit


class MineImpactQuoteAbstain(ValueError):
    """Unknown settings/hostile context, special modifiers or invalid hull."""


@dataclass(frozen=True, slots=True)
class SingleMineImpactQuote:
    mine_kind: str
    hull_mass_kt: int
    ship_cloaked: bool
    base_hit_odds_per_ly_numerator: int
    base_hit_odds_per_ly_denominator: int
    exact_damage_numerator: int
    exact_damage_denominator: int
    damage_percent_if_one_hit: int
    damage_rounded_up: bool
    damage_capped_to_100_percent: bool = False
    evidence: str = EVIDENCE
    actual_mine_hit_verified: bool = False
    ship_destroyed_verified: bool = False
    cumulative_damage_calculated: bool = False
    web_fuel_burn_calculated: bool = False
    travel_route_or_movement_calculated: bool = False
    host_orders_accepted_verified: bool = False
    host_phase_order_verified: bool = False
    host_diff_verified: bool = False


def quote_one_documented_mine_impact(
    *,
    mine_kind: str,
    hull_mass_kt: int,
    ship_cloaked: bool,
    ship_under_tow: bool,
    confirmed_enemy_mine_context: bool,
    confirmed_hull_only_mass_without_components_fuel_or_cargo: bool,
    ordinary_standard_impact_settings_confirmed: bool,
    no_custom_or_racial_damage_modifiers_confirmed: bool,
    hypothetical_one_impact_only_confirmed: bool,
) -> SingleMineImpactQuote:
    """Calculate the conditional consequence IF a single mine hit occurs.

    *_confirmed values are external assumptions, not server validation.
    Returned probability is the documented BASE PER-LY value only; it is
    neither integrated over a path nor evidence of a random hit.
    """
    if any(flag is not True for flag in (
        confirmed_enemy_mine_context,
        confirmed_hull_only_mass_without_components_fuel_or_cargo,
        ordinary_standard_impact_settings_confirmed,
        no_custom_or_racial_damage_modifiers_confirmed,
        hypothetical_one_impact_only_confirmed,
    )):
        raise MineImpactQuoteAbstain("unconfirmed ownership/hull/settings/single-hit scope")
    if type(mine_kind) is not str or mine_kind not in ("NORMAL", "WEB"):
        raise MineImpactQuoteAbstain("unknown or untyped mine category")
    if type(ship_cloaked) is not bool or type(ship_under_tow) is not bool:
        raise MineImpactQuoteAbstain("unknown cloak/tow status")
    if ship_under_tow:
        raise MineImpactQuoteAbstain("towed ships cannot be hit by these mine types")
    if (
        type(hull_mass_kt) is not int
        or not 1 <= hull_mass_kt <= MAX_QUOTED_HULL_MASS_KT
    ):
        raise MineImpactQuoteAbstain("invalid or unbounded ship hull-only mass")
    if mine_kind == "NORMAL":
        numerator = 10000
        odds_num, odds_den = (1, 200) if ship_cloaked else (1, 100)
    else:
        numerator = 1000
        odds_num, odds_den = (1, 20)
    denominator = hull_mass_kt + 1
    damage = (numerator + denominator - 1) // denominator
    # The +1 denominator and exact ceil are DOCUMENTED. Never cap raw
    # damage at 100; destruction rules and race advantages are separate.
    return SingleMineImpactQuote(
        mine_kind=mine_kind,
        hull_mass_kt=hull_mass_kt,
        ship_cloaked=ship_cloaked,
        base_hit_odds_per_ly_numerator=odds_num,
        base_hit_odds_per_ly_denominator=odds_den,
        exact_damage_numerator=numerator,
        exact_damage_denominator=denominator,
        damage_percent_if_one_hit=damage,
        damage_rounded_up=(numerator % denominator != 0),
    )
