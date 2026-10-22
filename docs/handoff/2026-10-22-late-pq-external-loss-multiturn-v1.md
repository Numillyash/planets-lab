# PR #272 — late PQ bounded multi-turn carry with exact external ship-loss boundary

Date 2026-10-22. New module: `src/planets_lab/sim/late_pq_external_loss_multiturn.py`; tests: `tests/test_late_pq_external_loss_multiturn.py`. This is a **TESTED conditional** multi-turn *model* only, not an authenticated NuHost turn series.

## The missing ship-slot problem

The strictly bounded late PQ #271 model starts with `soft_ship_limit - 1` ships and constructs exactly one caller-selected normal ship, reaching soft cap. A second identical PQ construction is impossible **without freeing a slot**. We MUST NOT silently fabricate Host combat, recycling, unowned ghost conversion, new game phase timing or random selection. Therefore **every subsequent** `LatePQExplicitTurn` requires:

1. A concrete `external_removed_ship_id` of exactly one old ship currently present at the end of the prior fully modeled turn; the ship must be inert (no movement/mission, damage, fighters/ammunition or cargo) to avoid untracked resources.
2. The full `externally_supplied_preturn_state` at the same model turn counter. It must be dataclass-equal to the preceding modeled state with ONLY that ship removed, no other changes to players, planets, resources, starbases, cargo, storms, metadata or fleet. A matching operator-supplied snapshot is a **conditional assertion**, not proof that an independent Host actually removed the ship.
3. A truthy explicit `external_single_inert_ship_loss_asserted` scoped to that transition, plus whole-sequence no-other-effects assumptions.

The first plan must NOT claim any external loss. Input roster must have exactly one vacant soft-cap slot. All transitions run with NO IO and none invoke combat/movement/recycle machinery. These boundary snapshots are **not independently authenticated**.

## Stateful carried inventory and atomic behavior

`LatePQCarry` contains complete `soft_ship_limit`, owner-by-owner PP rows, warehouses of EVERY ordinary starbase (including idle/unselected) and no speculative pointer or RNG state. Each complete `LatePQExplicitTurn` describes one regular queue blueprint/right per real base, externally selected winner, explicitly proposed lowest legal free ship ID and conditional economic placement.

With a valid single-loss boundary the existing #271 full-turn adapter is invoked; it audits exact component BOM, new-ship identity, purchased surface MC/minerals, full 14-phase planet economy and economic events. The next turn's source is the previous final result after the explicitly supplied loss, and its stock is exactly the preceding warehouse-after sidecar; **no phantom replenishment, no silent PP awards or costs**. At every step, preserve old base/player ownership, all unselected warehouse contents, full new ship-ID accounting, player PP and full planetary resource/event balances.

Bounded 2–6 turns, each using a complete queue and separate external selected base; a failure at ANY later step returns `ABSTAIN_MULTITURN_PQ_EXTERNAL_LOSS` without partial state, receipts, warehouses or points. No permit to treat a bare previous result as the next preturn while the fleet remains at soft cap. Synthetic tests cover two turns, an exact one-ship removal and reallocation of its ID, alternating bases, zero-bought-components vs depletion, forgery and missing/extra fleet/planet/PP differences.

## Unsupported / next

Documented PQ random selection does NOT become deterministic just because `selected_planet_id` is given. Nor is an externally asserted removal a NuHost combat/recycle proof or `DIFF_VERIFIED`. Actual server-accepted orders, host phase timing, ship-loss provenance and independent before/after owner snapshots are outstanding in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

A substantive next PR could add a **no-external-loss, one-slot-at-cap terminal** model with full economy and no build or run a cross-mechanic shipyard+cargo/movement composition in a supported subset. Do NOT broaden late PQ RNG to unsupported seeding, PPQ fractional shares/lottery to guessed rounding, nor touch unrelated C5/combat. Preserve `CURRENT` public68, sealed heldout32, public100 untouched, V1/V2 signed PlayerOrders and production IntelBoard.

Per enforcing #262 every next PR must rewrite the whole `docs/CONTINUE_HERE.md` with actual PR number, update `docs/PR_CHANGELOG.md` and meaningful topic docs before exact PR CI success, merge, and confirmed post-merge main CI.
