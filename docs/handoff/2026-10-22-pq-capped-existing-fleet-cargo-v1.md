# PR #276 — soft-capped PQ waiting with existing-fleet cargo and movement

Date: 2026-10-22. Source: `src/planets_lab/sim/late_pq_capped_existing_fleet_cargo.py`; tests: `tests/test_late_pq_capped_existing_fleet_cargo.py`.

## Bounded executable hypothesis

Before input: canonical complete game with **exactly soft_ship_limit vessels**, all owned planets/2–64 ordinary starbases, complete owned-ship roster. `CappedPQCarry` from #273 includes exact soft cap, PP for every owner and a complete components warehouse inventory for **every** ordinary base. Each of 2–6 consecutive `CappedFleetCargoTurn`s contains a distinct **complete** queue/idle/base/hull-rights declaration (at least two queued contenders), and `TurnOrders` with precisely one caller-explicit `ShipOrder` per existing ship and every owner (no implicit default). One unarmed, ordinary, supported ship is designated moving on that turn; every other ship must receive an explicit **stationary warp-zero/no-transfer no-op** order. Model never allocates a new ship ID, constructs a queued vessel, moves an unlisted ship, updates PP or changes any warehouse. Priority pbN, clone, Mining Stations, combat and special movement are asserted absent.

On each step, the moving ship optionally loads/unloads strictly typed ordinary cargo while orbiting an owned planet **before the move**, then travels exactly one complete nonpartial normal leg; alternatively it travels using existing fuel without a transfer. The only economy ordering choices are `load_move_before_economy` and `economy_before_load_move`. These are **caller hypotheses, not authenticated NuHost phases**. The intact `PlanetaryHostPipeline().phases` runs exactly once per step.

## Independent audit and atomic abstention

- Reuses #273 `_admit` on the complete initial fleet/all per-turn queues, full all-base component inventories, owner PP and unmodeled-actions exclusion.
- Rechecks all ship orders for every turn, exact owner and ship IDs, explicitly stationary other ships, one supported nonspecial ordinary moving hull (armed configuration preserved exactly; encounters forbidden), zero special/unknown orders.
- Uses `PlanetCargoTransferPhase` and `NormalMovementPhase` with the moving ship ID exclusively. Reuses `_audit_transfers_and_undo` for exact submitted transfer ↔ all-field event matching, and projected resource conservation. `_planet_ledgers` reconciles every planet's intact 14-phase economic production/events. `_exact_ship_fuel_ledgers` with an isolated one-ship projection compares measured movement fuel with independent `plan_full_normal_move` using loaded cargo mass. Finally compares the entire moving ship dataclass with its expected source + explicitly transferred cargo − exact movement fuel, and all other ships/owners/base records remain identical.
- Strict roster count stays at cap every turn; no construction receipts and `CappedPQCarry` after is byte-for-byte equal to input PP and warehouses. Any altered ship owner/crew, forged fuel/cargo/economic event, missing owner or ship orders, unfunded transfer, unsupported special hull/route, or extra ship/planet side effect yields **`ABSTAIN_CAPPED_PQ_EXISTING_SHIP_CARGO_CARRY` for the entire 2–6-turn sequence**, with no partial state, transfers or ledgers returned. Caller objects are not mutated.

Synthetic tests exercise alternative economic order on both turns, first-turn own-planet fuel+supplies loading and movement, second-turn further movement using carried fuel, queue changes while waiting, unchanged complete stock/PP and exact 14-phase planet resources, and 30+ failures including forged second-turn output.

## Evidence and next

Evidence level **TESTED conditional**. Passing local Python simulations cannot prove that NuHost accepted these exact ship orders, actually suppressed waiting builds, chose this phase position, or ran the same cargo+movement. This does not change sealed heldout32, public100, `CURRENT` public68, V1/V2 signed PlayerOrders, unrelated C5/combat or production IntelBoard. Independently accepted Host orders and full before/after boundary evidence remain [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

After final exact-head green CI and successful merge/main push CI, next candidate is a **single mixed PQ calendar** that interleaves capped waiting with externally asserted ship-loss and construction turns (#272/#273/#276), only with exact interturn boundary checks and atomic abstention. Another direction is exact ownership-aware multi-ship cargo logistics with physically supported rendezvous and no inferred combat. Document all unknowns rather than fabricating Host data.

Every new PR follows enforced #262: fully rewrite `docs/CONTINUE_HERE.md` with its own PR number, add its own `docs/PR_CHANGELOG.md`, update a substantive handoff/roadmap before running exact-head CI and merge, then check main push CI.
