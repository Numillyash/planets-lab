# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

This is the compact current pointer; dated handoffs contain full evidence and runtime details.

## Stable C5 layers

- corpus: 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts;
- owner-current `T-1` is the precombat order/state source; `T` ship state is postcombat;
- mission 3 = Kill!, mission 7 = Intercept, mission 20 = Bird Cloak and Intercept, raw `enemy` = Primary Enemy;
- direct isolated ordinary STANDARD relation: 413/413 higher static priority on RIGHT;
- normal PIA linked population: 37/37 before regular combat and 37/37 attacker RIGHT;
- isolated C&I factual attacker: 7/7 RIGHT;
- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- plain STANDARD repeated-pair second-pass reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; static priority remains unchanged.

Do not reopen Galactic Power Case2, reciprocal PIA, matching-FC, diplomacy, physical-stack or repeated-pair gates absent a direct contradiction. Do not weaken Friendly Code parsing or standard Combat Priority to fit queue residuals.

## Position checkpoint

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
docs/handoff/2026-09-09-combat-c5-unresolved-movement-context-runtime.md
```

Repaired storm-aware v3 runtime source `14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c`:

```text
ship occurrences: factual=3204 predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs:     total=1986 exact=678 mismatch=4 unresolved=1304
sites:             total=1220 fully position-exact=346 mismatch sites=4
payload_conflicts=0
storm modes: false=10 true=1
```

Six classic-ion-storm residuals are independently exact. Two remaining rows are DIFF_VERIFIED stochastic normal-mine hits and two remain bounded unresolved; no factual endpoint is injected into the predictor.

## Candidate-set v2 — runtime complete

Read:

```text
docs/handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md
```

Runtime source `c804575f4275f4454dbb282d9fcfc99fad0700d6`:

```text
factual unique pairs=1986
candidate-covered factual pairs=428
candidate-uncovered factual pairs=1558
candidate pairs=1092
strict factual:      eligible=420 unresolved=8 blocked=0
conditional factual: eligible=427 unresolved=1 blocked=0
conditional eligible nonfactual=331
all factual positions covered sites=242
conditional factual subset of eligible=236
conditional eligible exactly factual=171
payload_conflicts=0
```

No candidate-covered factual pair is conditionally hard-blocked. The single conditional factual unresolved pair is `360690/T140 [198,458]` with `left_fuel_unknown`.

## Initial plain STANDARD target-order runtime

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md
```

Runtime source `d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3`:

```text
conditional exact-set: sites=169 first_pair_exact=169 first_right_exact=169
strict exact-set:      sites=162 first_pair_exact=162 first_right_exact=162
exact-set informative target-order sites: 15/15 target rank 1
```

This strongly supports, conditional on a correct eligible candidate set:

```text
first active ship = highest standard Combat Priority ship having an eligible target
first target      = highest-priority eligible target for that active ship
```

Broad scope has only two residuals, identical in strict/conditional:

```text
360690/T83: active 264; reconstructed extra target 98; factual target 190
511506/T94: active 496; reconstructed extra target 202; factual target 332
```

In both cases the active ship is correct and the factual pair is already eligible; the mismatch exists only because one extra nonfactual candidate pair survives. Do **not** invert target ordering from these rows.

## Immediate gate — post-movement fuel on the two extra targets

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-residual-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_target_residual_audit.py
tests/test_combat_host_initial_standard_target_residual_audit.py
```

Current candidate inputs derive `has_fuel` from positive T-1 neutronium. That is intentionally conservative for earlier positive gates but can be wrong after movement: an arriving ship may spend its final fuel and therefore be unable to combat.

The focused audit reconstructs normal-movement fuel for active, extra-target and factual-target ships at the two residual sites using the existing canonical movement planner. It reports `fuel_required`, `fuel_used` and `postmove_fuel`. T state is attribution/control only.

If both extra targets independently resolve to `postmove_fuel=0`, treat the two broad target-order residuals as missing post-movement-fuel blockers. Then integrate safe reconstructed fuel into candidate inputs and rerun candidate-set v2 + initial-target differential before promoting any canonical selector. If either does not, investigate another blocker; do not change standard Combat Priority or target ordering.

Later C5 work remains: canonical initial selector after evidence closure, mutable survivor/destruction state, second-pass composition, capture continuation, ship-to-planet repair boundary, then planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.