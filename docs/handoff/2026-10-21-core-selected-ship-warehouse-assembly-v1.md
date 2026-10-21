# Core shipbuilding V1: explicit warehouse + selected prelimit assembly

Date: 2026-10-21. Base main commit 58408cee409e995e42c8f64c2de325a4b9b03f6a (PR #255, CI #1386 success).

## Documented facts, distinguished from the model

Planets.nu [Building Starships](https://help.planets.nu/building-starship-hulls) describes building a complete hull fitted with all engines and optional selected beams/torpedo launchers. Fighter bays belong to the hull. Individual [hulls](https://help.planets.nu/hull), [engines](https://help.planets.nu/starship-engines), [beams](https://help.planets.nu/beam-weapon-construction) and [launchers](https://help.planets.nu/torpedo-launch-tube-construction) can be constructed and held in starbase warehouse storage for later assembly. A starbase can assemble one starship per turn. The [Host Order Of Shipbuilding](https://help.planets.nu/starbase-host) distinguishes early/prelimit standard construction from post-limit queue/priority mechanisms, with potentially multiple shipbuilding subphases.

The prior PR #255 calculated an all-new ship bill of materials with no warehouse or actual ship. This stage fills the **bounded local standard-assembly** gap, not the real scheduler.

## New typed synthetic model

\`src/planets_lab/sim/standard_ship_warehouse_assembly.py\` introduces:

- \`StandardComponentWarehouse\` (per-base sidecar): four explicit component-ID → count inventories, for hulls, engines, beam weapons and torpedo launchers. Warehouse is **not** added to canonical \`Starbase\` until a full turn snapshot can provide it with adequate provenance.
- \`SelectedBuildSlot\`: exact base planet ID, proposed free ship ID, caller-asserted complete current fleet roster, *explicitly selected* prelimit standard slot, and a 1–999 stated global ship cap. **This does not run or independently authenticate a NuHost build queue.**
- \`assemble_selected_standard_ship(...)\`: exact existing quote validation (rights/tech/slots/catalog), consume available parts from sidecar inventory, purchase only the missing component units from the base's planet, require adequate MC and three minerals, create one conditional ship in a cloned **phase-intermediate** GameState, validate its identical turn number, and return the remaining warehouse plus exact per-kind drawn/purchased ledger.

The installed engines are always the full number required by the hull. The new ship has caller-selected unused ID, owner, hull/engines/weapons, hull crew and intrinsic fighter bays, and starts with zero fuel, ammunition and cargo. No ship is created, materials subtracted or inventory changed for unsupported inputs: no partial result, all-or-nothing.

For a no-inventory standard frigate, the earlier all-new BOM remains the exact bill. If a stock contains an existing hull/engines/weapons, only missing components cost resources. Negative stock, duplicated IDs, phantom catalog entries, unavailable minerals, unsupported tech/license, missing scope/queue selectors, reused ship IDs, ship limit already hit, metadata-defined variants or unknown race-specific crew rules ABSTAIN.

The queue decision is **asserted not independently witnessed**. Correctly computing an ID's absence and global count does **not** establish that NuHost selected this base or the particular proposed ID. The assembled state remains same-turn intermediate, not a complete T→T+1 Host turn. There is no server order receipt and the statuses/flags are unconditionally noncausal.

## Explicit remaining blockers

- A typed **pre-/post-build queue state** for PBQ, PQ, PPQ, PLS and queue priority accounting; actual standard Host order can contain multiple shipbuilding subphases and interacted cloning/combat.
- An independent source for complete per-base component storage and accepted ship build orders, and precise treatment of the game's ship-ID/free-slot policy.
- Scheduling the selected assembly phase alongside starbase technology upgrades, base facilities, movement, combat and planet economy, including correct acquisition and timing of credits/minerals.
- Automatic tech purchase, mixed stored/fresh component acquisition order, refit, repair, cloning, secondary fighter/torpedo production and custom racial/campaign exceptions.

These are neither silently implemented nor implicitly assumed from historical ship appearance.

## Verification / corpus boundaries

Deterministic tests cover all-new pricing, partial storage, full-storage zero-cost assembly, shortage rescued by stocked components, illegal owner/tech/catalog, count/slot/ID limits, invalid queue assertions, unchanged input GameState, unaffected PlayerOrders V1/V2 HMAC schemas and explicitly false Host-verification flags.

No public100 scan or CURRENT change, no fresh32 M2 entity reads, no C5 combat or IntelBoard changes. The separate human-dependent order-attribution experiments remain parked in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).
