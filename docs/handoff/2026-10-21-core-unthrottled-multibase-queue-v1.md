# Core: complete early/unthrottled multi-starbase shipbuilding queue

Date: 2026-10-21. Follows merged #257 (selected one-base assembly + complete planetary economy).

## Authoritative documented queue rules and conservative intersection

See official [Build Queues](https://help.planets.nu/queue), [Priority Build Points (Classic)](https://help.planets.nu/queue-pbp), [Production Queue](https://help.planets.nu/queue-pq), [Planetary Production Queue](https://help.planets.nu/queue-ppq), [Ship Limit](https://help.planets.nu/ship-limit) and [Host Order Of Shipbuilding](https://help.planets.nu/starbase-host).

- Classic PBP: in the **early** regime, before a game approaches 90% of its hard ship cap, all bases with standard queued builds can build without spending PBPs; near-limit middle and late phases use PBP and an evolving round-robin/planet-ID queue pointer.
- PQ: an unthrottled early window selects enough bases to complete all queued standard builds, but throttled selection after the limit is randomized and priority-based. A base selected without a queued ship can earn PP, which is not modeled here.
- PPQ: before the limit restricts building, bases with standard queued ships can build without spending PP (excluding optional priority-code effects); in the late/contested regime, ownership proportions, PP and RB/PB queue assignments matter. Other sources sometimes describe the limit as hard or soft; the bounded common early window does **not** resolve that disagreement or simulate past the threshold.
- PLS: individual limits driven by planet holdings are a separate queue family, **excluded** from this module.

**Safety restriction**: permit only a *full roster* of at least two ordinary starbases, all with explicit regular shipbuilding orders and warehouses, and conservative **post-build fleet count STRICTLY under 90%** of a caller-specified global limit (10–999). No priority friendly codes, no cloned ships, no unqueued bases, no contested slots, no auto-tech, no PP changes, no random candidate selection and no missing competing starbases. These are **caller assertions, not independently accepted Host data**.

## Implemented executable subset

\`src/planets_lab/sim/standard_unthrottled_multibase_queue.py\` takes:
- \`queue_mode\`: \`CLASSIC_PBP\`, \`PRODUCTION_PQ\`, or \`PLANETARY_PPQ\`, each **only in the common unthrottled interval**. The enum does not claim implementation of any mode's near-limit or late queue.
- \`queue: dict[int, CompleteBaseBuild]\`: an **exhaustive**, one-entry-per-existing-base list. Every entry includes a complete \`StandardShipBlueprint\`, \`StandardComponentWarehouse\`, caller-authored \`SelectedBuildSlot\` with explicitly unused proposed ship ID and full-roster assertion, and explicitly race-eligible hull IDs.
- \`placement\`: all ship assembly before or after the intact 14-phase standard planetary economy, as a *hypothesis*, not real Host timing.

All bases are admitted simultaneously in the safe regime. They are processed in ascending planet ID solely for **deterministic local execution**, not because the real Host's priority, random distribution or round-robin pointer has been inferred. Each base has independent warehouse/planet material availability, and the routine calls the existing #256 assembler once for every base, accounting for a global ship cap/ship IDs.

Each step is checked with the independent #257 unit/price/ship auditor using a **detached adjacent-turn copy**; the real assembly stays a phase-intermediate state. The audit must reconstruct the preceding entire GameState (except the detached +1 turn number), proving the local action changed **only** that base's authorized stock, planet materials and one new ship. A forged receipt, extra/duplicated ship, unexpected warehouse component, unaffordable request, or an unmodeled source mutation fails the entire batch. No base's successful intermediate ship or inventory is exposed on ABSTAIN.

After all admissible builds, the existing 14-phase economy executes (or executed before the batch). An economy-only projection removes *only* the known newly built ships and restores *only* the purchased MC/minerals for each base. The existing planet ledger checks factory supplies, tax income, mining/ground stock, population and structure differences for **all planets and owners**. A missing event or post-state mismatch fails closed.

The output includes a final modeled T+1 GameState, per-base BOM/warehouse/new-ship receipts and per-planet economic ledgers, plus immutable false flags for independently verified queue ordering, PP, ship ID allocation, stock, Host execution, phase placement and Host parity.

## Synthetic regression coverage

Two owners, two bases, two ships in one turn, across 3 queue families × 2 hypothetical placements; different stored/new component mixes, shortfall at one base after another succeeded (full-batch ABSTAIN), tax- and Federation-mining-funded after-economy builds. Negative and tampering cases include competing/missing/phantom bases, duplicate IDs, hard Classic ID cap, 90% boundary, missing complete-roster or no-priority assertions, unsupported PLS/late queue, missing catalog components, wrong owner, new-ship/warehouse/price corruption and altered/missing mining/tax events.

## Remaining work and limits

This result is **TESTED conditional consistency**, not a full queue solver:
1. Classic PBP **middle/late** round-robin pointer, player balances, pbN priority and pre-/post-combat build passes.
2. PQ/PPQ **throttled and late** queue allocation, random seed and player build-rights, RB and PB codes, awarded PPs, and custom modifiers.
3. Explicit PLS per-player ship caps and special scenarios.
4. Binding authenticated server orders, storage and assignment of ship IDs, plus actual Host time boundary, before any **DIFF_VERIFIED** claim.
5. Full integration with starbase defense/tech purchases, movement, transfer and combat (the dedicated primary-corpus mainline stages).

Nothing scans public100/fresh32 M2 entities, mutates \`CURRENT\` (public68), changes canonical \`PlayerOrders\` HMAC V1/V2, or alters IntelBoard/C5. External Host witness experiments remain parked in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).
