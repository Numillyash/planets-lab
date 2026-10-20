# Core standard Host composition — ordinary movement × planetary economy

Date: 2026-10-20. Base commit `b9ec7d4ba2e77b6cced7defe89843a7e2c993b3c`, main CI #1376 success. Live NuHost-dependent experiments remain parked in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

## First executable cross-system standard turn

`src/planets_lab/sim/standard_movement_economy_turn.py` composes **existing** `NormalMovementPhase`, `_ExplicitStructurePhase` and all 14 `PlanetaryHostPipeline` economic phases into one independent research `HostEngine` run. Unlike the earlier planetary-only multiturm test, this executes actual synthesized ordinary ship movement with fuel consumption while structure construction, tax, factory supply and mining run on two owner planets in the **same simulated turn**.

There are two *caller-selected hypothetical* positions for movement relative to the entire structure/economy block, and two positions for structure construction relative to the intact 14 phases. Relative Host timing is NOT independently established. Movement-before and movement-after may produce identical complete states for independent ships/planets. Internal event ordering is not a NuHost observation.

Only a fully declared standard cohort is supported:
- One explicit signed-*by-nobody*, caller-asserted `TurnOrders` entry for every declared player, with **exactly one ordinary navigation order per ship**, including explicit warp-zero no-ops. Every order must name its full integer waypoint and warp; owner and ship existence checked. Missing or duplicate ship orders never become implicit no-ops.
- A separate explicit owner-complete building-target map with no duplicate or foreign planet targets and at least one actual target. V1/V2 HMAC capture schemas and `PlayerOrders` are unchanged and **do not authenticate structure targets**.
- Complete hull and engine specs, known fuel, no unsupported mission/friendly-code, tow, intercept, hyperjump, expanded movement, warp-well, combat equipment, ship damage, cargo transfer, starbase, storms, metadata-driven specials or campaign overrides.
- Fail closed if a ship begins or finishes co-located with a foreign-owned planet, or if ships from different owners co-locate and would need combat/interaction resolution. We do not pretend to settle combat just because a zero-weapon ship moves.
- Every simulated phase result is checked against a **per-planet inventory ledger** from PR #251 (supplies, taxes, construction MC/supplies sold and spent, surface/ground minerals and structure counts) and an independent **per-ship fuel/position ledger**. The latter checks emitted movement/no-op receipts, expected fuel debit, coordinates, unchanged other ship cargo, unchanged equipment and ownership, and exactly one movement receipt per declared ship. Missing or forged receipts cause whole-run `ABSTAIN`.

The function returns complete typed state, phase events, per-planet and per-ship ledgers **only** when every gate passes. Otherwise no partial state, events, or resource balances are exposed.

## Executable coverage inventory: existing components, not a claim of complete Host

| Component | Existing implementation | Composition status in this PR |
|---|---|---|
| Normal reachable ship movement, fuel | `normal_movement_phase.py` | **Supported conditionally** with explicit full-ship orders, no specials |
| 14 implemented planet economic phases | `planetary_host_pipeline.py` | **Supported conditionally** as an intact block |
| Standard structure targets, supply sale | `standard_structure_build.py` | **Supported conditionally** with opt-in pricing/mode |
| Multi-turn planet balance | `planetary_structure_multiturn.py` | **Already local-tested**, separate from ship movement |
| Planet↔ship cargo transfer | `planet_cargo_transfer_phase.py` | **Isolated order-aware research slice**, not admitted into this movement composition |
| Starbase technology upgrades | `starbase_tech_upgrade_phase.py` | **Isolated order-aware research slice**, no full construction/shipbuilding integration |
| Tow, intercept, hyperjump, warp wells | Separate bounded movement phase classes | **ABSTAIN** in this standard movement/economy subset; order interactions not yet composed |
| Combat, mine warfare and special missions | Separate combat/rules diagnostics | **ABSTAIN** in this subset; no complete combat-bearing Host turn |
| Terraform, pillage, rebel assault, campaign Enlighten/Ore Condensing | Omitted by `PlanetaryHostPipeline` | **ABSTAIN / not implemented**, never implicitly considered modeled |

The above is **component coverage**, not validated outcome coverage. No public100 full scan is scheduled; the public100 compact generation remains immutable, `CURRENT` stays public68, fresh32 M2 entities are not read. Standard public68 historical mineral/structure changes are observational data and cannot establish ship, building, or tactical orders.

## Synthetic verification

Two users, two owned planets and two declared ships (one ordinary ten-light-year leg, one warp-zero noop). Four movement/build timing combinations exercise the unchanged 14 phases. Assert consistent fuel usage, immutable input, per-owner planet-building and taxes/mining ledgers, exact equipment/cargo preservation, phase-indistinguishability controls and HMAC schema invariance.

Negative controls cover missing/duplicate/foreign orders, unknown engine, unreachable/fuel-starved waypoint, special missions, ship arms, unauthorized foreign planet arrival, multi-owner co-location, unexpected combat/planetary state mutation, receipt omission, special rule fields, incomplete target rows and starbases. All unsupported cases ABSTAIN with no partially modeled output.

## Next standard mainline work

Introduce **conditional planet ↔ ship cargo transfer at a known orbital site** into this composition, with independent three-location conservation of surface stocks, ship cargo and available planetary construction materials. This is more consequential than extending the existing synthetic phase-identifiability grid. Keep source order provenance explicit, and reject movement/transfer contention until phase and arrival eligibility can be stated without unsupported inference.

External causal evidence requirements remain parked in issue #247.
