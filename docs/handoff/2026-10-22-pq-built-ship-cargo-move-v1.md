# PR #274 — late PQ: new ship, own-planet cargo load, fully fuelled normal move

Date: 2026-10-22. Code: `src/planets_lab/sim/late_pq_built_ship_cargo_move.py`; tests: `tests/test_late_pq_built_ship_cargo_move.py`.

## Composition

The supported #271 late PQ full-turn builder handles exactly one remaining ordinary soft-cap slot; externally selected winning queued base among 2+ contenders, the lowest free ship ID, complete all-base warehouses/owner PP, independently typed ship BOM, and fully reconciled 14-phase planetary economy (build before or after planetary, caller hypothesis). On that **one modeled after-economy GameState**, the new module applies two **caller-selected subphases** directly and sequentially, without a second HostEngine.step, economic block, or extra turn counter increment:

1. Complete typed `PlanetCargoTransferOrder` from the owning build planet to the **newly assembled empty ship**, including neutronium fuel and optional supported cargo. Uses unchanged `PlanetCargoTransferPhase` and checks a one-to-one detailed transfer receipt, whole `GameState` equality with independently calculated planet-stock debit/ship-stock credit.
2. A **fully reachable nonpartial** ordinary `NormalMovementPhase` leg of that same selected new ship, after loading its own fuel. Uses exact `plan_full_normal_move` fuel prediction; checks movement receipt source/destination/fuel, expected waypoints and warp, complete ship and planet state equality, and no encounters at endpoints.

No older ship moves/transfers, all unrelated inventories and owners remain identical; owner PP/warehouses are inherited unchanged from the trusted conditional #271 stage. The transfer consumes only planetary on-hand amounts *after* the documented model economic block and the assembled ship's component purchases; avoids an imaginary duplicate economy turn. All other stage permutations and unsourced Host timing are explicitly excluded.

## Evidence boundary / restrictions

The phase sequence `build+economy → orbital load → normal movement` is an **explicit scenario hypothesis, NOT an inferred actual NuHost order**. The real Host might require the new ship to wait a turn before movement or might schedule cargo differently. Its inclusion here means local executable conditional consistency **TESTED**, not server accepted orders, Host execution or `DIFF_VERIFIED`. Actual Host subphase sequence, new-ship immediate operability, and independently witnessed loading remain unknown. No random PQ selection, mining stations, priority pbN, special engines, warped wells, tow/intercept/hyperjump, combat, partial/fuel-limited navigation, unowned transfers, foreign planets or any other ship orders. Such cases atomically `ABSTAIN_PQ_BUILT_SHIP_CARGO_MOVE` with state/receipts/PP withheld and untouched inputs.

Synthetic tests exercise both alternative build/economy placements, loaded fuel and supplies, mass/fuel accounting, complete previous-turn identity, invalid queue/transfer/warp/budget/hull boundaries, and tampered event or inventory evidence. All host evidence flags remain false.

## Next

1. Verify PR #274 exact final SHA pytest CI and post-merge push main CI before claiming success; no security/validator waivers.
2. Extend the bounded composition in a **separate PR** to cargo transfer to already existing ships in a staged boundary after shipyard, or a multi-turn interval with new ship movement on its **next** turn. Strongly prefer the next-turn case if immediate action cannot be independently confirmed; never claim real Host order.
3. Future shared pipeline requires independent Host timing/order and complete before/after owner snapshots; issue #247. Do not touch sealed heldout32, public100, `CURRENT` public68, unrelated C5/combat, IntelBoard production, signed V1/V2 `PlayerOrders`.

Each next PR requires completely refreshed `docs/CONTINUE_HERE.md` with its own actual PR number, own `docs/PR_CHANGELOG.md` entry and meaningful handoff/roadmap, exact-green PR CI, merge and confirmed post-merge main CI.
