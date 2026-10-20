# Core M2 structure construction × existing economy: explicit conditional turn

Date: 2026-10-20. Depends on merged #249 (`a6c700f01aa446a9a516b7be2ad6014202ebac61`), which added standard-priority construction with partial funding and explicit supply-to-MC exchange.

## What is now integrated

`src/planets_lab/sim/planetary_structure_turn_slice.py` inserts the new structure purchase phase **only into an opt-in research HostEngine**, either immediately **before** or **after** the unchanged `PlanetaryHostPipeline` of 14 economy phases. It requires explicit caller assertions about standard rules and complete building targets, a tuple (including an explicit empty tuple) for **every declared player**, exactly owned planets, and no duplicate planet target. There is no silent inference of zero orders from a missing owner.

For this initial bounded slice, ship, starbase, ion-storm or known `no_supplies` contexts ABSTAIN, rather than pretending to simulate their interactions. Only the separate `StructureBuildTargets` records are used: no edits to `PlayerOrders` or V1/V2 HMAC envelope schemas, and no automatic conversion of client-side targets into server-accepted Host orders.

The structure phase applies partial purchases using already tested standard priority and sale accounting, returns explicit conditional events, and lets the **real existing** factory, mining, taxes, population and society code run under both declared timings. HostEngine owns the usual state clone and turn increment. No Canonical Host phase/order source is modified.

## Discrimination test

With one artificial owned planet, 10 factories and a target of 11:
- `structures_before_planetary` buys the eleventh factory before FactorySupplyPhase. The economy produces 11 supplies from factories during that simulated turn.
- `structures_after_planetary` keeps 10 factories during FactorySupplyPhase, producing 10 supplies, then buys the extra factory. The two full conditional final states differ by **one** supply when all other explicit inputs are held constant.

A second case has 0 initial MC and supplies; the existing economy first produces supplies, so the AFTER placement can conditionally afford one factory through 1:1 supply conversion, while the BEFORE placement cannot. These are **model discriminators only**, not evidence that any real Host used one ordering. Other mechanics may remain unmodeled.

The tests also verify two-run determinism, complete input immutability, no special game or unowned targets, duplicate/missing-player rejection, noncausal flags and unchanged 14-phase `PlanetaryHostPipeline`.

## Scientific/operational constraints

Source is `TESTED` and independently documented priority/cost rules are `DOCUMENTED`. No matching NuHost accepted orders or independent Host clock exists, so `DIFF_VERIFIED` remains false and human-dependent experiments stay parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).

No database access, no corpus scan/rebuild, no fresh32 M2 entity read, no `CURRENT` changes, no C5/combat, no production IntelBoard. Keep public100 immutable (SHA256 `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`). Frozen baseline68/136-pair observational statistics remain evidence of net differences, not performed construction orders.

## Next standard-core stage

After this integration: add a small multi-turn deterministic standard planetary scenario with explicit targets across multiple owner planets, stable phase ledger and no hidden special rules. Only then expand family-specific observed coverage where a predeclared novel metric cannot be recovered from previously published aggregates. Do not create a new owner-signature schema unless genuinely required by a separate, later independent Host study.
