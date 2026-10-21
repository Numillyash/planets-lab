# Classic saved-pointer standard ships × full planet economy

Date: 2026-10-21. Builds on merged PR #259 (pure standard pointer selection) and PR #258 (component-conserving multi-base assembly).

## Executable slice

\`src/planets_lab/sim/classic_standard_pointer_economy_turn.py\` combines:

1. Complete caller-asserted CLASSIC/PBP standard queue state with **known last standard planet pointer**, owner balances all below 21 PBP, no priority pbN, no cloning and exact fleet/base/owner roster.
2. Explicit typed ordinary ship designs, full per-base component warehouses and hull rights for **every queued base**, including designs for bases which may not be selected.
3. Pure #259 circular ascending planet-ID pointer selector. It selects only the bases that fit in remaining hard-limit ship slots; unselected bases retain inventories and are not charged.
4. Deterministic **lowest unused Classic ship ID** assignment in SELECTED POINTER ORDER, not sorted planet order. Actual allocation is a conditional model outcome; input fleet roster and server clock are not independently verified.
5. The existing #256 assembly, reused #257 independent new-component purchase/unit/ship verifier, cloned state per assembly and resource ledger for EVERY step. No partial ship/stocks if a later selected base fails.
6. The unchanged full 14-phase PlanetaryHostPipeline, either before or after the assembly subphase as an **explicit hypothesis**, with a final independent check of every new ship's exact immutable blueprint+crew/cargo and every planet's MC, supplies, surface/ground minerals and structure delta.

The result exposes a final synthetic T+1 GameState, selected starbase and ship IDs in pointer order, next saved standard-pointer candidate, selected per-base component receipts, **all queued bases'** post-warehouse stocks, and per-planet economy ledger. It *never* asserts that actual NuHost uses the chosen relative phase order, accepted the orders, started the Host, or independently provided the queue state.

## What is deliberately not modeled

- All PBP priority builds (including 21+ PBP, pbN or multi-owner priority ranking), cloning, uncertain Middle-stage PBP spending, or a race-to-500 Host first/second build ordering. Both before- and after-economy placements are synthetic.
- PQ/PPQ randomized or proportion-based late slots and PLS individual ship limits.
- Concurrent starbase facility/tech purchase, normal ship movement, transfer, battles and damage; these must be explicitly composed in future core stages.
- Hidden/omitted competing shipbuilding orders. The full-starbase/ship/PBP scope is a **caller assertion**, not a self-authenticating real Host record.

The tests use a *fictional* Classic game with three owned bases, of which one has no ship queued, two competing standard builds, a saved pointer, 8 existing ships and a cap of 10. They verify pointer-order ship IDs and owner assignments, one-slot eligibility with unselected warehouses unchanged, zero-slot no-build, same-turn tax/factory/mineral accounting, full stock vs partial, late-step resource failure ABSTAIN, tampered ship/planet/warehouse controls, and unchanged signed owner schemas.

**Evidence:** documented queue base selection and lowest unused ID, TESTED conditional model state changes, *not* DIFF_VERIFIED. Operator-dependent real accepted orders and NuHost causality remain parked in issue #247. No corpus scan, fresh32 entity records, CURRENT change or C5/IntelBoard modifications.
