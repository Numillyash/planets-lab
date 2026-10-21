# Classic/PBP standard build subphase — bounded pointer selector

Date: 2026-10-21. Based on PR #258 early/unthrottled multi-base common queue, main commit \`4248ad180a99cd4f5c1f35c22e5340d0a4974539\`.

Official Planets.nu [Priority Build Points](https://help.planets.nu/queue-pbp) and [Host Order Of Shipbuilding](https://help.planets.nu/starbase-host) distinguish **priority builds** from **standard builds**. Priority subphases select high-PBP owners and may account for pbN codes. Standard subphase (when fewer ships than hard limit) traverses starbases in ascending planet-ID order and remembers the last STANDARD build across phases/turns. Clones/advanced cloning, previous pointer, priority subphase and before/after combat windows are separate sources of order and cannot be silently reconstructed here. Classic uses hard ship IDs up to the configured limit.

## This stage actually implements

\`src/planets_lab/sim/classic_standard_queue_pointer.py\` is a pure, deterministic, *standard-only* base selector, **not** a complete Classic queue solver and **not** a ship-building API. It requires:

- A complete caller-asserted base roster, including explicitly idle bases and each owner's known PBP balance. All PBP balances must be **below 21**. This conservative gate excludes priority-eligible players, mid-stage PBP consumption and priority pbN ordering. It cannot independently verify the roster or balances.
- A known saved last-standard-built pointer in [0,500], hard ship limit, exact current fleet count and strict assertions that priority effects are already handled, no clones, no other build effects and base/owner lists are complete. A missing pointer **ABSTAINS**, never defaults to planet 001.
- Ordinary build/no-build status on each base. Any pbN code or cloning action ABSTAINS.

Given S available ship slots, walk the 001–500 circular planet ID ring starting **after** the saved pointer, skipping idle/absent bases, select at most S queued bases, and return the final selected base as the updated pointer. When no build occurs, preserve the original pointer. The result does not allocate ship IDs, spend PBP, deduct resources, execute actual assembly or establish Host order timing.

The tests cover wraparound, arbitrary pointers, skipped idle bases, one-/two-slot contention, next-phase pointer carry, fully exhausted ship limit and the complete negative scope. A dishonest caller claiming a partial list is complete cannot be detected from that same list; this is intentionally recorded as a provenance limit rather than presented as verification.

## Next integration step

Take the exact selected subset from this pure selector and compose it with **existing** per-base warehouse ship assembly and independent #257 material/ship auditor; reject any ship-ID collision, unaccounted competing base or wrong roster and keep all outcomes model-conditional. Then add the 14-phase economy and explicit before/after conditional placement. This step is responsible for actually exercising resource contention in a limited Classic phase; it may not copy a queue pointer into the canonical GameState as a Host fact.

Priority builds (PBP >=21), pp spending, pbN priority, clones and pre/post combat phases remain deferred until typed authenticated queue state and independently validated formulas exist; see [#247](https://github.com/Numillyash/planets-lab/issues/247) for user-dependent causal evidence.

No corpus reads, heldout32 entity use, CURRENT change, C5/combat or IntelBoard changes. No signed PlayerOrders V1/V2 schema changes.
