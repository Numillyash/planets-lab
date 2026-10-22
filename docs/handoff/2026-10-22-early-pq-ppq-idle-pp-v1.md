# Unthrottled early PQ/PPQ — ordinary ships and selected idle starbase PP (PR #268)

Date: 2026-10-22. Sources: [Production Queue](https://help.planets.nu/queue-pq) and [Planetary Production Queue](https://help.planets.nu/queue-ppq), differentiated from the late priority builds added in [#266](https://github.com/Numillyash/planets-lab/pull/266)–[#267](https://github.com/Numillyash/planets-lab/pull/267).

## Documented behavior and bounded scope

In both PQ and PPQ's completely unthrottled **Early** mode, ordinary starbases that have a normal build queued can build without spending Priority Points. A *selected* ordinary starbase with no queued ship can instead receive **2 default Priority Points**. PQ excludes Mining Stations from selection. PPQ's early mode is also all eligible bases when there are enough slots; other custom PP earnings and early-queue transitions require extra state.

`src/planets_lab/sim/early_pq_ppq_idle_pp_turn.py` requires a complete roster of **every** ordinary build-capable starbase in the modeled game, including explicitly idle ones. It supports at least one ordinary queued ship and at least one idle base, at least two bases total; all ordinary bases are caller-asserted selected; no priority `pbN` codes, clone orders, custom PP rates, queued special base actions or ship movement/combat. This is confined to a conservative **post-build fleet strictly below 90%** of the configured soft ship limit.

The caller provides complete per-base warehouse inventories (INCLUDING idle), build specs and hull eligibility for queued bases, current ship roster and all player PP balances. Every built ship's **set** of asserted IDs must be exactly the first N free legal IDs 1..999. **Assignment of those IDs to particular bases remains a caller assertion**, since the actual queue order can be randomized; sorting local code by planet ID is NOT NuHost selection.

### Execution

- Simultaneously admit every ordinary queued build in the all-slots-available interval and use existing audited per-base hull/engine/weapons BOM and warehouse deductions.
- Credit **exactly +2 PP for each selected idle** base, to its actual owner. Ordinary shipbuilding does not consume PP in this bounded early mode. Other PP awards, including combat, recycling and inactive selected bases in later queues, are absent.
- Execute the unchanged full 14-phase planetary economy before or after these operations as a **declared conditional hypothesis**, never proven NuHost placement.
- Independently check every new ship's final hull, engine, equipment, owner, position and crew; verify previous ships/bases unchanged, purchased components vs stocks, all planet mining/taxes/factory effects, and per-owner PP credits against initial complete balances.
- ABSTAIN the entire turn on missing/duplicate idle base, source stock, invalid component, non-lowest ship IDs, ship cap contention, nondefault PP rate or unknown influence; no partial ships, PPs, receipts or state returned.

### Evidence and boundaries

`TESTED` model consistency only. Real PP earnings, randomized PQ/PPQ starbase selection, actual order contents, Host timestamp, accepted IDs and independent pre/post owner states are NOT authenticated; [issue #247](https://github.com/Numillyash/planets-lab/issues/247) tracks those investigations. PQ late random queue and PPQ late planet-share regular allocation remain separate, unimplemented.

Tests: two owners, two simultaneously queued bases, one idle base earning +2PP, alternate one queued plus two idle earning +2PP each owner, fully stocked ship paid with 0 MC, income-funded after-economy build, **permuted base-to-ID assignment as declared input**, low-ID set enforcement, negatives and forged economic/ship state. No public100 rebuild, heldout32, CURRENT(public68), C5 combat/IntelBoard or V1/V2 owner schema changes. Per-PR handoff, changelog and docs remain mandatory under #262.
