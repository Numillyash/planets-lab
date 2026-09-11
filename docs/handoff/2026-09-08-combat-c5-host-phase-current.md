# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

Progress overview: `docs/handoff/2026-09-11-reverse-progress-assessment.md`.

Planning estimate only: combat mechanics knowledge C1-C5 ~70-80%; independently reconstructed ordinary ship-combat candidate coverage ~20-25%; whole NuHost roadmap ~40-50%.

## Stable C5 layers

Do not reopen absent a direct contradiction:

- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- direct ordinary STANDARD priority: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I attacker: 7/7 RIGHT;
- scoped Galactic Power Case2, reciprocal PIA and matching-FC closures;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- owner-current `T-1` is the precombat order/state source;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

`T` is post-Host/postcombat. Same Ship ID at T is not automatically the same physical ship because construction may reuse a freed ID.

## Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383
  factual pairs exact=678 mismatch=4 unresolved=1304

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

No candidate-covered factual pair is conditionally hard-blocked.

## Initial STANDARD selector checkpoint

```text
conditional exact-set: 169/169 first pair exact; 169/169 RIGHT exact
strict exact-set:      162/162 first pair exact; 162/162 RIGHT exact
informative exact-set target-order controls: 15/15 rank1
```

Supported selector when the eligible set is correct:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

The two original broad initial mismatches were:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Both now have independent evidence-scoped directional targetability explanations.

## Privateer Rob blocker — CLOSED at scoped targetability boundary

Evidence-scoped state:

```text
Privateer race5 + mission9 Rob + ordinary cloak-capable hull:
  prior false                         -> not effectively cloaked
  prior true + fuel <= reference cost -> not effectively cloaked
  prior true + fuel >  reference cost -> effectively cloaked
  advanced cloak                      -> unresolved / fail closed
```

Queue-decisive differential:

```text
opportunities=16
decisive_rows=8
decisive_match=8
decisive_mismatch=0
decisive_unresolved=0
```

Selector-impact differential:

```text
overlay_rows=16
overlay_blocked=7
overlay_eligible=9
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
privateer_residual_profiles_projected_fixed=2/2
bird_residual_profiles_overlay_affected=0/2
```

Evidence status:

```text
Privateer Rob ordinary-cloak targetability:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

universal Rob fuel-consumption causality:
  REJECTED

raw prior iscloaked as blanket blocker:
  REJECTED
```

The helper remains at `src/planets_lab/rules/combat/effective_state.py`, but targetability is not yet wired into canonical selection.

## Bird Super Spy blocker — CLOSED at focused targetability boundary

Focused runtime source `6cf47de46fadcbe1619c6a6eee5731d51866c12e`, 21 targeted tests passed.

Ship202:

```text
Bird race3 / Red Wind / mission9 Super Spy
damage=0
fuel=37, ordinary reference cost=5
reference normal move: fuel_used=8, remaining=29
prior iscloaked=true
ion storm=False
planet Super-Spy Ion Pulse=False
Loki=False
active Glory=False
documented_effective_cloak_supported=True
```

Matched factual ship332 has prior `iscloaked=true` but mission2, is outside Super Spy scope and actually fights. Raw archived cloak therefore remains rejected as a generic blocker.

Evidence status:

```text
focused Bird Super Spy ordinary-cloak targetability blocker:
  DOCUMENTED + CORPUS_OBSERVED + TESTED
```

## Combined structural blocker projection — PASSED

Runtime:

```text
docs/handoff/2026-09-11-combat-c5-initial-standard-combined-blocker-projection-runtime.md
```

Source HEAD:

```text
96ce64a1cc3d7da7874f0e9f37dea1333531330c
```

Targeted tests: 25 passed.

Baseline remains exactly four mismatch profile rows, two per historical site. Combined projection result:

```text
baseline_mismatch_examples=4
privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles=2
bird_residual_profiles_projected_fixed=2
unrelated_baseline_mismatches=0
```

All acceptance flags are true:

```text
privateer_gate_still_clean=True
bird_context_gate_clean=True
privateer_residual_all_profiles_projected_fixed=True
bird_residual_all_profiles_projected_fixed=True
no_unrelated_baseline_mismatches=True
all_original_broad_mismatches_projected_fixed=True
```

This closes the structural composition of the two independently established blockers, but does **not** yet prove a corpus-wide Bird rule or justify canonical targetability wiring.

## Immediate gate — Bird Super Spy population opportunity differential

Read:

```text
docs/handoff/2026-09-11-combat-c5-bird-super-spy-population-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_attack_opportunity_audit.py
tests/test_combat_host_bird_super_spy_attack_opportunity_audit.py
```

It scans all ordinary historical archives except game `591478`, reconstructing hostile one-way plain-STANDARD opportunities against Bird race3 / mission9 Super Spy / cloak-capable targets through the same position-v3, candidate-set-v2, diplomacy and canonical pair-decision layers used elsewhere.

The documented effective-cloak candidate remains conservative: ordinary cloak only, damage/fuel/reference movement resolved, prior archived cloak positive, and T-1 ion storm / possible planet Ion Pulse / Loki / active Glory contexts clear. Advanced and unresolved states remain unresolved.

Queue-decisive labels are only:

```text
initial_pair_vcr                       -> expected eligible
initial_skip_target_outranks_factual  -> expected blocked
```

Strong acceptance:

```text
no_race_conflicts=True
no_payload_conflicts=True
no_blocked_factual_pair_regressions=True
no_decisive_mismatch=True
target_residual_present=True
target_residual_supported=True
```

`decisive_unresolved>0` is not itself a contradiction because the candidate deliberately fails closed; every unresolved decisive row must be inspected before generic promotion.

If this population gate is clean enough, next compose supported Bird states with the DIFF_VERIFIED Privateer overlay and rerun a population-wide directional STANDARD targetability differential over the full initial selector baseline. Require all previously exact selectors to stay exact, zero factual-pair/first-selector regressions, and both historical residuals fixed.

Only then wire targetability into the canonical first STANDARD selector. After that C5 moves to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
