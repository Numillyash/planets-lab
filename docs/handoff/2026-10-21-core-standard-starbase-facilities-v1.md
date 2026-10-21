# Core standard starbase facilities — creation, defense and fighters

Date: 2026-10-21. Base commit `832e65f4d44ec0ff8d613bd55338bdfdeff6d2b7` (#253, main CI #1381 success).

## Sources and hard boundaries

The official [Starbases](https://help.planets.nu/starbases) page specifies the **normal** base cost: 900 MegaCredits + 120 KT Duranium + 402 KT Tritanium + 340 KT Molybdenum. Normal maximum starbase defense is **200**, maximum fighters **60**. The [Starbase Defense and Fighters](https://help.planets.nu/starbase-defense-and-fighters) page specifies 10 MegaCredits + 1 KT Duranium per base defense post and 100 MegaCredits + 3 KT Tritanium + 2 KT Molybdenum per base fighter.

These are **not** planetary defense-post costs and do not consume supplies. Nonstandard Shielded Starbases, Mining Stations and campaign/race modifiers are outside this implementation.

## Implemented isolated facility operations

`src/planets_lab/sim/standard_starbase_facilities_phase.py` adds a pure research phase with two explicitly typed, mutually exclusive operations on a given planet per turn:

- `StandardBaseCreateOrder(planet_id)`: only on a currently owned planet without an existing base; debit all four resources atomically and create an ordinary starbase with default tech 1, zero fighters and zero defense.
- `StandardBaseArmOrder(planet_id, defense_target?, fighter_target?)`: only on an already existing base of the same owner; build positive absolute-target increments subject to the documented defense (200) and fighter (60) caps. Reject downgrades, overcaps, unknown inventories and underfunding.

All users in the canonical game roster must have an explicit tuple of base-facility orders, including an explicit empty tuple. Duplicate per-planet orders, accidental owner reassignment, special variants and purchasing a new base *and* arming that same base during the same turn are **not** allowed here.

`src/planets_lab/sim/standard_starbase_facilities_turn.py` composes this phase before or after the existing **unchanged** 14-phase `PlanetaryHostPipeline`. This choice is a **caller-supplied hypothesis**, not the real NuHost Host phase order. No ships, starbase tech upgrade, combat, storms or game metadata/modifiers are admitted in this bounded calculation. Planetary growth, factory supply, taxes and minerals still run through the existing economic implementation.

## Conservation and source integrity

Every facility event must exactly match the explicitly requested base ID, activity, units and mineral/MC prices. The post-turn starbase roster and every base's whole state are compared to expected creation/arming: no silent change in owner, tech or equipment is allowed. All facility costs are then algebraically added back to a **cloned** post-turn planet resource state so that the existing independent PR #251 ledger can reconcile only factory production, tax collection, mining, population effects and other implemented economy phases. Actual returned state is the original complete modeled poststate, not the ledger projection.

Any invalid order, non-standard setting, bad owner/scope, insufficient resource, incompatible base tech or mismatching receipt/state yields `ABSTAIN_STANDARD_STARBASE_FACILITIES_TURN` with **no partial state/events/ledger** exposed. Nothing is added to signed `PlayerOrders` V1/V2 or to the canonical economic phase definition.

The tests include two owners: build one ordinary base while another existing base adds two defense posts and two fighters; verify exact resource deltas and untouched original state, compare facility-before vs facility-after-economy cases, fail-closed broken resource costs, overcaps and tampered events. A tightly funded 899-MC creation illustrates that internally simulated tax production can change a **conditional** funding outcome according to the chosen placement.

## Shipbuilding remains explicitly NOT implemented

[Building Starships](https://help.planets.nu/building-starship-hulls), [Starship Hull Construction](https://help.planets.nu/hull), and the [Starbase Interface](https://help.planets.nu/starbase-commands) describe separate requirements that are **not represented by the existing Starbase dataclass**: hull/engine/beam/torpedo inventory and race availability, exact equipment bills of materials, ship build slots, the ship limit, ship-ID assignment, Priority Points and build queues. In particular a new ship must **not** be conjured solely by subtracting its hull cost. Such functionality needs an explicit storage/queue/eligibility model and a separate opt-in integration contract before claiming even conditional end-to-end shipbuilding.

A next autonomous phase may add an exact static bill-of-materials *quote* using `NuStaticSpecs` and explicit race/tech/queue eligibility, but must ABSTAIN for absent catalogs, queue/limit, equipment or warehouse information. Do not invent ship IDs, fabricate accepted orders or treat an archive appearance as the construction record.

## Evidence and operations

Source pricing is `DOCUMENTED`, synthetic local implementation is `TESTED`. Full Host execution, phase timing, newly built base availability in the same turn, player-signed server-accepted orders and independent `DIFF_VERIFIED` remain unavailable. Those user-driven experiments stay parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).

No public100 rescan, `CURRENT` remains public68, no fresh32 M2 entity sampling, C5/combat, private capture, or IntelBoard changes.
