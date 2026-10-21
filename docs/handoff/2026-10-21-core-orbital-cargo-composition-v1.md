# Core M2 — orbital cargo, ordinary movement, construction and economy

Date: 2026-10-21. Base: merged PR #252, source `567ef2b67345fc711c42ad024f1c5d96ce0304eb`, CI #1379 success.

## First integrated cargo-bearing standard turn

`src/planets_lab/sim/standard_orbital_transfer_turn.py` combines existing, **unchanged** `PlanetCargoTransferPhase`, `NormalMovementPhase`, `_ExplicitStructurePhase` and the canonical 14-phase `PlanetaryHostPipeline` under one opt-in `HostEngine`. Exact placements are **conditional hypotheses**: transfer before or after normal movement; the move/transfer block before or after the planetary economy; standard construction before or after the 14 economic phases. None is labeled the real NuHost sequence.

This is deliberately limited to ordinary transfers at a valid orbital site with **the same known planet and ship owner**. The input must contain a nonzero, nonnegative, correctly typed ship-side `PlanetCargoTransferOrder` with a valid direction and planet ID. Every player must have explicit ship orders, with exactly one full normal-move or noop order for each existing ship, plus a complete separate owner-scoped structure-target map. Previous signed V1/V2 schemas remain unchanged, so neither building intents nor client saves are falsely promoted to Host-accepted instructions.

The actual transfer phase enforces orbit, source availability, destination bulk cargo capacity and neutronium tank limits. The composite rejects colonization, foreign-planet transfers, combat/foreign co-location, starbases, storm interactions, special missions, hyperjumps, intercept, tow, partial/prorated routes, warp wells, data omissions, and unknown rule modes. A ship can unload at its departure planet before a move, or load at an owned destination only after arrival; attempting either at an invalid position produces a **whole-turn ABSTAIN** with no partial modeled state.

## Independent three-location inventory check

For each explicitly ordered transfer, a post-execution verifier compares the original typed submitted order with an exactly shaped transfer event (same ship/planet IDs, direction, colonization=false, and exact quantity for all seven cargo fields). It rejects extra, missing or duplicate receipts and unexpected event details. Transfer quantities are then algebraically subtracted from a **cloned** modeled poststate, producing an *audit projection* for the existing independently written:
- Planet economy ledger from PR #251: factory supplies, MC taxes, structure buys/sales, mine extraction, ground mineral mutation and structure changes.
- Ship fuel and navigation ledger from PR #252: motion receipts, fuel consumption, exact coordinates and unchanged ship equipment/other nontransfer cargo.

Transfer conservation is checked on both sides, including ship neutronium fuel affected by movement and planet supplies spent on building. The output returns the actual modeled state, untouched by the projection, plus separate per-transfer receipts and existing planet/ship ledgers. The input game is not mutated. Missing or forged event receipts, or unexplained poststate deltas, produce ABSTAIN, not a partial trajectory.

This is **local self-consistency**, not an independent reference source; corrupt event+state pairs built from the same executable model can still agree. No `DIFF_VERIFIED`, no independent server accepted-order receipt, no actual Host phase order attribution.

## Synthetic integration coverage

Two players, two planets and two freighters: standard ship-to-owned-planet supply unload followed by a 10-LY normal move, ordinary economics and building, across both movement/economy and both construction/economy placements. Arrival-site loading from a new same-owner planet works **only after moving into orbit**. A cargo unload before economy can conditionally finance otherwise unaffordable factory building from available supplies; after economy it cannot. A pre-movement neutronium loading case enables movement that would otherwise fail when the ship has no fuel.

Negative tests cover missing/empty/malformed/foreign transfer orders, insufficient quantities, tank/cargo capacity, bad owner scope, offsite transfer, special missions, unsupported modes and intentionally tampered transfer amount, owner ID, direction, missing/duplicate event, fuel/planet cargo and movement receipts.

## Remaining standard-core work

Explicit controlled **ship/planet cargo exchanges with multiple co-located ships and transfer priority** and zero-order handling may require an independently stated order timing rule. Keep them ABSTAIN until bounded and supported. Starbase construction and ordinary shipbuilding have not yet been composed with the planet economy. Combat-bearing, specialty missions and campaigns stay outside this standard pipeline.

As before: no DuckDB/full-corpus scan, no fresh32 M2 entity reads, no change to `CURRENT` (public68), no C5 combat, no production IntelBoard. User-dependent accepted Host evidence remains parked in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).
