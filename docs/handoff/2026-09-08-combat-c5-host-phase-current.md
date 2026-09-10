# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

This is the compact current pointer; dated handoffs contain full evidence and runtime details.

## Stable C5 layers

- corpus: 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts;
- owner-current `T-1` is the precombat order/state source; `T` is post-Host/postcombat state, and same Ship ID at T is not automatically the same physical ship because later construction can reuse open IDs;
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

Read `docs/handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`.

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

No candidate-covered factual pair is conditionally hard-blocked.

## Initial plain STANDARD target-order runtime

Read `docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`.

Runtime source `d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3`:

```text
conditional exact-set: sites=169 first_pair_exact=169 first_right_exact=169
strict exact-set:      sites=162 first_pair_exact=162 first_right_exact=162
exact-set informative target-order sites: 15/15 target rank 1
```

This strongly supports, conditional on a correct eligible set:

```text
first active ship = highest standard Combat Priority ship having an eligible target
first target      = highest-priority eligible target for that active ship
```

Only two broad residuals remain, both with the correct active ship and factual target already eligible:

```text
360690/T83: active264; reconstructed extra target98; factual target190
511506/T94: active496; reconstructed extra target202; factual target332
```

Do not invert target ordering from these rows.

## Fuel residual — rejected

Read `docs/handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md`.

Runtime source `55ad7c5799f52d8bc703f3247cf7ed179dbb18f9`:

```text
extra target98 postmove fuel=45
extra target202 postmove fuel=29
zero-fuel extras=0
```

Post-movement zero fuel explains neither residual.

## Cloak residual runtime — partial closure

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md
```

Runtime source `3d3b8d91f3ff281b0563a0f7112fadbe86222f2b`, tests/audit rc0, payload conflicts0.

`511506/T94/ship202` is a clean scoped Bird Super Spy clue:

```text
owner3 resolves race3
hull47 Red Wind can cloak
mission9
T-1 iscloaked=true
T-1 fuel37 >= ordinary 5 kt reference
T same owner/hull and iscloaked=true
```

This strongly supports a missing effective-cloak blocker for pair `[202,496]`, but no generic current-host cloak implementation is promoted yet.

`360690/T83/ship98` is different:

```text
owner5 resolves race5 Privateer
hull46 Meteor can cloak
mission9 (Privateer race-specific mission, not Bird Super Spy)
T-1 iscloaked=true, fuel45
T same owner/hull and iscloaked=true
```

Factual target ship190 has the same owner/race/hull/mission9 but T-1 fuel4, below the ordinary 5 kt cloak reference, `T-1 iscloaked=false`, and fights/captures as observed.

Crucially factual target `511506/T94/ship332` also has `T-1 iscloaked=true` yet current mission2 and VCR728 occurs. Therefore **raw T-1 `iscloaked` is rejected as a blanket combat blocker**.

## Immediate gate — Privateer Rob cloak-state population

Read:

```text
docs/handoff/2026-09-10-combat-c5-privateer-rob-cloak-population-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_cloak_population_audit.py
tests/test_combat_host_privateer_rob_cloak_population_audit.py
```

It inventories ordinary archive-resolved race5 + mission9 + cloak-capable hull rows across consecutive archive turns. T-state is attribution-only. Same Ship ID is not sufficient: owner, hull/equipment and available build-turn identity must align before a cloak transition is treated as the same physical ship.

Key population questions:

```text
stable true_to_true / true_to_false / false_to_true / false_to_false
stable_before_cloaked_pe_zero_vcr
stable_true_to_true_pe_zero_vcr
exact target row 360690 T82->T83 ship98
```

A stable prior-cloaked + PE0 + VCR row is a direct counterexample to treating the previous raw cloak bit as combat protection in that Host. Systematic true->true persistence without VCR would support state persistence/timing semantics but still would not alone prove combat-step effective cloak.

No `selection.py` or target-order change is allowed until this population gate is reviewed.

Later C5 work remains: close the last initial candidate blocker, add canonical initial selector, mutable survivor/destruction state, second-pass composition, capture continuation, ship-to-planet repair boundary, then planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
