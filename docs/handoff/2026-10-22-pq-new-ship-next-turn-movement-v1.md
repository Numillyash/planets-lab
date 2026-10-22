# PR #275 — PQ ship construction on turn T, cargo and normal move on T+1

Date 2026-10-22. Research code `src/planets_lab/sim/late_pq_new_ship_next_turn_move.py`; tests `tests/test_late_pq_new_ship_next_turn_move.py`.

## Difference versus PR #274

PR #274 explores a strictly **hypothetical same-turn** post-assembly load and movement subphase. This PR deliberately provides a more conservative executable alternative: **two separately advanced modeled turn counters**, no movement by the new ship on its build turn. Turn T invokes the already bounded and independently synthetic-tested #271 late PQ one-slot ordinary selected ship, BOM, all-base stock/PP and complete 14-phase economy. This reaches the ordinary PQ soft cap. The next complete model step T+1 uses explicit orders ONLY for the newly built ship to load fuel and other ordinary cargo from its own building planet and execute one normal full-length flight, with a complete second **14-phase planetary economy**. All waiting ordinary queue orders build nothing while at soft cap; no pbN, mining stations, clone or external fleet/planet effects permitted.

## Reused ledgers

- On both conditional build/economy placements: #271 proves model exact new-ship identity, warehouse/BOM surface debits, untouched existing ships and PP ledger.
- On the next modeled turn the existing `PlanetCargoTransferPhase` and `NormalMovementPhase` execute in one `HostEngine` step with the intact `PlanetaryHostPipeline().phases`, either **load/move before planetary** or **planetary before load/move** (explicit unverified order hypotheses).
- The existing orbital transfer receipt auditor `_audit_transfers_and_undo` checks submitted ship-to-planet relationship and all typed cargo fields, then subtracts only transfer deltas from a detached final projection. `_planet_ledgers` independently checks this projection against full economic events. The normal ship fuel auditor `_exact_ship_fuel_ledgers` runs on the newly moving ship's one-ship projection, and independent `plan_full_normal_move` requires full reachability and predicts exact movement fuel/coordinates.
- All old ships and ship IDs, all bases/owners, external metadata and storms remain unchanged; carry PP/warehouses is the unchanged #271 sidecar. Full model turn increases **by exactly two**, no arbitrary interturn changes. Any missing/forged events, fuel or material shortfall, encounter, foreign planet, custom order or unsupported movement causes an atomic `ABSTAIN_PQ_NEW_SHIP_NEXT_TURN`, with no intermediate output disclosed.

## Evidence boundaries

This is a **TESTED conditional** synthetic composition, not independently authenticated NuHost Host execution or proof that actual NuHost permits this ordering. The new ship is not activated until next model turn; nevertheless phase timing inside that next turn is caller-selected and no real accepted orders or real Host boundary evidence is present. No special hulls, warp wells, tow/intercept, partial fuel, arbitrary ship actions, real priority build, PPQ fractional quota/lottery or combat is modeled. Do not interpret modeled local API `HostEngine` as host parity. User-dependent independent evidence remains blocked by [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

Tests should cover both build placements × both next-turn economic placements, accurate owner PP/warehouse carry, fuel burn and post-load supplies, omission/invalid input and adversarial event/result mutations. CI and actual merge result MUST be checked live on exact final head before declaring success.

Next: integrate conditional multi-turn waiting-at-cap PQ (#273) with ship movement and cargo after explicit source boundary; or extend to owner-verified orders and independent NuHost snapshots when available. Each later PR must update full continuation, PR changelog and relevant docs and verify PR/main CI. Keep public68 `CURRENT` unchanged, public100 untouched, heldout32 sealed, signed V1/V2 PlayerOrders, unrelated C5/combat and IntelBoard production intact.
