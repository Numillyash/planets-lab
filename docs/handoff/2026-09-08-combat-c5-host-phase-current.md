# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

This is the compact current pointer; dated handoffs contain the evidence and runtime details.

## Stable C5 facts

- established corpus: 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts;
- ordinary Host ordering: ship combat precedes planet combat;
- owner-current `T-1` is the precombat order/state source for battle turn `T`; factual `T` ship state is postcombat;
- mission 3 = Kill!, mission 7 = Intercept, mission 20 = Bird Cloak and Intercept, raw `enemy` = Primary Enemy;
- direct isolated ordinary standard relation: 413/413 higher static priority on RIGHT after documented special branches;
- ordinary normal PIA linked population: 37/37 before regular combat and 37/37 attacker RIGHT;
- isolated C&I factual attacker: 7/7 RIGHT.

## Closed combat gates — do not reopen absent contradiction

Read before touching pair/queue semantics:

```text
docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md
docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md
docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md
docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md
docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md
docs/handoff/2026-09-09-combat-c5-factual-queue-runtime.md
docs/handoff/2026-09-09-combat-c5-repeated-pair-side-runtime.md
```

Former standard-side residuals remain closed for distinct reasons:

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Standard Galactic Power forced-left Evil-Empire Gorbie
```

Do not weaken standard priority, Friendly Code parsing, Intercept semantics or diplomacy to fit them.

## Canonical pair / repeated-pair layers

```text
src/planets_lab/rules/combat/selection.py
```

Deterministic pair composition is `TESTED`.

```text
src/planets_lab/rules/combat/queue.py
standard_pair_sides_for_occurrence(...)
```

User runtime on `de824ab4ecc0bc8cd32784ce4d3df9021eddd71b` passed. The entire ordinary repeated-pair population is exactly two groups/four VCRs; both show first RIGHT = static higher priority, second RIGHT = opposite ship. Scoped reversal is `CORPUS_OBSERVED + DIFF_VERIFIED`; static priority remains unchanged.

## Factual-positive queue differential — closed

Runtime source `31509d2c9e9f4af89f80e5088597452d40f393c1`:

```text
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
payload_conflicts=0
known phase-prefix violations=0
```

Exact-target normal PIA binding is runtime validated. Existing VCR presence was a positive oracle in this gate, so this is not candidate-set prediction.

## Candidate-set v1 — closed as coverage-limited

Read:

```text
docs/handoff/2026-09-09-combat-c5-candidate-set-v1-runtime.md
```

Runtime source `1ef175f77419970b244c5d69df2863a06390ab6c`:

```text
factual_unique_pairs=1986
candidate_pairs=107
factual_pairs_candidate_covered=1
factual_pairs_movement_uncovered=1985
```

The single covered factual pair was eligible. Warp-0-only position scope was clean but unusably narrow, so movement-derived precombat position became the dependency.

## Storm-aware T-1 -> precombat position — runtime checkpoint

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
docs/handoff/2026-09-09-combat-c5-unresolved-movement-context-runtime.md
```

Repaired v3 runtime source:

```text
14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c
```

Artifact:

```text
artifacts/combat-c5-position-v3-repaired-20260909-235856
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
storm modes: false=10 true=1

ship occurrences:
  factual=3204
  predicted=1810
  exact=1806
  mismatch=4
  uncovered=1383

factual pairs:
  total=1986
  exact=678
  mismatch=4
  uncovered=1304

sites:
  total=1220
  all factual pairs position-exact=346
  mismatch sites=4
```

All six previously attributable classic-storm residuals are now independently exact through:

```text
normal navigation -> ion-storm drag -> warp-well snapping
```

No new mismatch appeared among the former 1,800 exact v2 occurrences.

The four remaining rows are bounded:

```text
360690/T54/ship26    -> unresolved
511506/T95/ship332   -> unresolved
620694/T62/ship83    -> one stochastic normal-mine hit, DIFF_VERIFIED attribution
680910/T14/ship65    -> one stochastic normal-mine hit, DIFF_VERIFIED attribution
```

For ship65 the matching minefield is visible only in battle-turn evidence, so it is attribution-only and never a T-1 predictor input. No row is patched with factual coordinates.

## Immediate gate — candidate-set v2

Read:

```text
docs/handoff/2026-09-10-combat-c5-candidate-set-v2-pending.md
```

New diagnostic:

```text
tools/diagnostics/combat_host_candidate_set_v2_audit.py
tests/test_combat_host_candidate_set_v2_audit.py
```

Schema:

```text
planets-lab.combat-host-candidate-set-audit.v2
```

V2 remains site-conditioned, not a full-turn site predictor. For each factual ordinary battle site it independently predicts every owner-current T-1 ship position with the repaired v3 layer, admits only ships predicted at that site, forms all cross-owner physical pairs, and then evaluates canonical pair eligibility.

Visible T-1 foreign normal/web mine route crossings fail closed as position unresolved because hit occurrence is stochastic. This is a risk gate, not a claim that a mine hit happened. Special/unresolved movement branches remain excluded.

Strict diplomacy remains leave-pair-out; conditional diplomacy is only an upper-bound composition profile. `eligible_nonfactual` is not a queue failure until mutable target selection is reconstructed.

### Required next runtime

Run the targeted position/combat/candidate tests and full candidate-set v2 audit over the 11 ordinary archives.

Advance only if:

- tests rc=0;
- audit rc=0;
- payload_conflicts=0;
- factual candidate coverage is materially larger than v1's `1/1986`;
- no candidate-covered factual pair is conditionally hard-blocked, or every such row is individually explained;
- movement uncertainty remains explicit.

If coherent, checkpoint candidate-set v2 and move next to mutable target-list / queue mutation on fully position-covered sites. Capture continuation and the ship-to-planet repair boundary remain later work.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
