# PR #277 — exact-boundary mixed late PQ calendar

Date: 2026-10-22. `src/planets_lab/sim/late_pq_mixed_calendar.py`; `tests/test_late_pq_mixed_calendar.py`.

## Problem and staged solution

Earlier bounded models establish different isolated **conditional** late PQ windows: at-cap regular builds wait (#273); one **externally asserted** empty/inert ship loss can create a single vacant soft-cap slot (#272); one ordinary queued starbase selected by the caller can build a ship with exact BOM/warehouses/PP/14-phase economy (#271); existing ships can execute cargo/movement while the rebuilt fleet remains at soft cap (#276). A unified calendar must not invent a loss, a host-selected base, a hidden queue replacement, an undocumented PP increase, a resource refill, or an extra planet economic phase.

`simulate_mixed_late_pq_wait_loss_build_fleet_calendar` composes:

1. `2–8` consecutive at-soft-cap no-build planetary economic turns using #273 with complete ordinary queues and full owner PP/warehouse rosters; whole fleet, all player/base identities and all sidecars must remain exact.
2. An operator-provided `LatePQExplicitTurn` with a complete `externally_supplied_preturn_state` **equal to the immediately preceding modeled outcome EXCEPT for deletion of precisely one known, inert cargo/ammo-empty ship**, checked using #272's strict `_check_preturn_external_loss`. The loss must be caller asserted and is **NOT a NuHost combat/recycle simulation**.
3. The declared normal build candidate set must equal the previous no-build waiting queue entry at EVERY starbase, including queued/idle flag, blueprint and eligible hull rights — the external loss alone cannot fabricate new queued orders. Using the current carried warehouses/PP, #271 must build exactly one externally selected candidate with **the lowest unused ship ID**; verify exact new ship, full all-planet 14-phase event/resource ledgers and unchanged owner PP. The per-base component warehouse rollover must cover the same complete base set.
4. `2–6` capped-fleet turns from #276 with complete ordinary waiting queues, all-owner explicit ship orders, one supported full-leg mover per turn, optional own-planet cargo transfer and full second-stage 14-phase economy. Source is exactly the #271 after-build canonical state; PP/warehouse sidecar is exactly the audited build result. No new ship IDs or queue builds while at soft cap.

The final modeled turn equals starting turn + number of no-build waits + ONE rebuild turn + number of fleet logistics turns. Every stage must be fully supported, and any failure anywhere returns **`ABSTAIN_MIXED_LATE_PQ_WAIT_LOSS_BUILD_FLEET` without partial receipts, intermediate GameStates, PP or warehouses**.

## Evidence and tests

All snapshots, orders, queue intentions and timing are **caller-provided hypotheses**. A caller's complete matching preturn snapshot is not proof that the actual NuHost executed a ship loss or accepted a specific build, and local synthetic tests are only `TESTED conditional`, NEVER `DIFF_VERIFIED`. The API does not infer or run combat/recycling, Host RNG/selection, ship priority, cloning, Mining Stations, fractional PPQ lottery, unsupported movement, or custom planetary economy.

Synthetic tests cover a full `2 wait → exact empty ship loss → 1 rebuild → 2 logistics` sequence, late PQ alternative economic placement, queue and complete warehouse carry, owner PP, ship-ID reuse, fuel/cargo, and 25+ adversarial negative cases (tampered full preturn snapshot, unexpected planet mutation or extra ship, loss of a non-inert ship, changed queue, missing owner, unbalanced downstream stage). Unknown requirements trigger one atomic ABSTAIN.

## Next

Complete PR #277 exact-head CI, fix issues without relaxing guards, merge and verify post-merge main CI. Then extend mixed calendar to multiple separate externally validated loss/rebuild cycles only after boundary invariants are fully described, or independently validate actual Host timing/accepted orders through [issue #247](https://github.com/Numillyash/planets-lab/issues/247). No sealed heldout32, public100 rebuild, `CURRENT` changes, unrelated C5/combat, IntelBoard production or signed V1/V2 `PlayerOrders`.

Every PR **must** update its entire `docs/CONTINUE_HERE.md`, own `docs/PR_CHANGELOG.md` and meaningful handoff/roadmap inside that same PR before the exact CI and merge.
