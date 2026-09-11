# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

Progress overview: `docs/handoff/2026-09-11-reverse-progress-assessment.md`.

Planning estimate only (not evidence): combat mechanics knowledge C1-C5 ~70-80%; independently reconstructed ordinary ship-combat candidate coverage ~20-25%; whole NuHost roadmap ~40-50%.

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

`T` is post-Host/postcombat. Same Ship ID at T is not automatically the same physical ship because later construction may reuse a freed ID.

## Position / candidate checkpoint

Position v3:

```text
factual ship occurrences=3204
predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs exact=678 mismatch=4 unresolved=1304
```

Candidate-set v2:

```text
factual unique pairs=1986
candidate-covered=428
conditional factual eligible=427 unresolved=1 blocked=0
strict factual eligible=420 unresolved=8 blocked=0
```

No candidate-covered factual pair is conditionally hard-blocked.

## Initial STANDARD target-order checkpoint

```text
conditional exact-set: 169/169 first pair exact; 169/169 RIGHT exact
strict exact-set:      162/162 first pair exact; 162/162 RIGHT exact
informative exact-set target-order controls: 15/15 rank1
```

Strongly supported when the eligible set is correct:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

The two original broad initial residuals are:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Bird `511506/T94/ship202` remains a separate Super Spy/effective-cloak residual.

## Privateer Rob effective-cloak closure path

Read in order:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-effective-cloak-threshold-runtime.md
```

### Initial-decision controls

Three clean missing-state rows:

```text
360690/T57 ship46  vs attacker146
360690/T57 ship280 vs attacker146
360690/T83 ship98  vs attacker264
```

All are Privateer race5 / Meteor hull46 / mission9 Rob / PE0 / prior `iscloaked=true`, and each strictly outranks the factual first target for the same initial attacker.

The clean fought prior-true control is:

```text
620694/T64 ship118 vs attacker134
fuel=5
```

### Fuel-state population

```text
stable prior-true rows=1413
exact_reference_debit=545
zero_debit=90
other_debit=778
true_to_true=1378
true_to_false=35
threshold above=1399
threshold equals=3
threshold below=11
```

The broad exact-reference-debit correlation is real but not causal proof.

### Clean attribution runtime

Runtime source `16f9253b92f7e48f7f2179f9c3b704469de4128a`, tests/audit rc0.

Conservative stationary/no-visible-fuel-mutation subset:

```text
rows=12
exact_reference_debit=2
zero_debit=7
other_debit=3
all 12 true_to_true
```

Therefore reject the simple universal rule `Rob Ship consumes ordinary cloak reference fuel`.

The low-fuel controls are much stronger:

```text
ordinary-cloak prior-true rows with fuel <= reference cost:
  13/13 true_to_false

sole threshold true_to_true row:
  advanced-cloak hull29, fuel acquisition confounded
```

No ordinary threshold row has archived T-1 ion/Loki/active-Glory exposure in this diagnostic.

### Effective-cloak threshold differential

Runtime source `37ea8fc3a68be3b18737f6a71a2a09bb36226ad5`, tests 5 passed, audit rc0.

Candidate:

```text
Privateer race5 + mission9 Rob + ordinary cloak-capable hull:

prior false                              -> not effectively cloaked
prior true + fuel <= reference cost      -> not effectively cloaked
prior true + fuel >  reference cost      -> effectively cloaked
advanced cloak                           -> unresolved / fail closed
```

Queue-decisive result:

```text
opportunities=16
decisive_rows=8
decisive_match=8
decisive_mismatch=0
decisive_unresolved=0

expected blocked -> candidate blocked: 3/3
expected eligible -> candidate eligible: 5/5
```

The three skipped Meteors are all blocked. The five factual initial-pair controls remain eligible. Crucially:

```text
620694/T64 ship118:
  prior=true
  fuel == reference cost == 5
  candidate effective cloak=false
  factual initial pair exists
  archived transition true_to_false
```

This resolves the previous apparent contradiction without a ship-specific exception.

Evidence status:

```text
Privateer Rob ordinary-cloak threshold state:
  CORPUS_OBSERVED + TESTED

universal Rob fuel-consumption causality:
  REJECTED

raw prior iscloaked as direct blocker:
  REJECTED

advanced-cloak threshold:
  UNRESOLVED

Bird Super Spy effective cloak:
  UNRESOLVED
```

## Effective-state helper

A fail-closed helper now exists at:

```text
src/planets_lab/rules/combat/effective_state.py
```

`privateer_rob_ordinary_cloak_state(...)` encodes only the evidence scope above. Other races/missions, advanced cloak, unresolved cloak type or unresolved fuel/reference inputs return `None`.

The helper is **not wired into `selection.py` or `queue.py` yet**.

## Immediate gate — selector impact differential

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_selector_impact_audit.py
tests/test_combat_effective_state.py
tests/test_combat_host_privateer_rob_selector_impact_audit.py
```

It reruns the unchanged full initial-STANDARD baseline and projects the helper over all 16 independently reconstructed Rob plain-STANDARD opportunities.

Acceptance boundary:

1. no effectively-cloaked overlay row may be a factual pair;
2. no effectively-cloaked overlay row may be a factual initial pair;
3. potential first-selector regression rows must be zero;
4. the Privateer `360690/T83/ship98` baseline mismatch must be projected fixed for every comparable profile;
5. Bird `511506/T94/ship202` must remain present and untouched;
6. baseline exact-set evidence must not be contradicted;
7. advanced/unresolved state fails closed.

If this passes, Privateer ship98 blocker state is closed strongly enough to consider canonical candidate/selector integration. Bird ship202 remains the separate blocker investigation before declaring the broad initial selector fully closed.

Later C5 work: close Bird ship202; promote canonical first selector; compose mutable survivor/destruction state; second-pass orientation in the mutable queue; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
