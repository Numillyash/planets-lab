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

Original broad initial mismatches:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

## Privateer Rob blocker — CLOSED at scoped targetability boundary

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-effective-cloak-threshold-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md
```

Three clean blocker controls:

```text
360690/T57 ship46  vs attacker146
360690/T57 ship280 vs attacker146
360690/T83 ship98  vs attacker264
```

Clean fought threshold control:

```text
620694/T64 ship118 vs attacker134
prior iscloaked=true
fuel == reference cost == 5
factual initial pair exists
archived transition true_to_false
```

The broad exact-reference fuel-debit signal was real but the clean attribution subset rejected universal `Rob Ship consumes ordinary cloak fuel` causality:

```text
clean stationary/no-visible-fuel-mutation rows=12
exact_reference_debit=2
zero_debit=7
other_debit=3
```

The low-fuel transition was much cleaner:

```text
ordinary-cloak prior-true rows with fuel <= reference cost:
  13/13 true_to_false
```

Evidence-scoped Privateer state:

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
expected blocked -> candidate blocked: 3/3
expected eligible -> candidate eligible: 5/5
```

Selector-impact runtime source `5bfdecfc090357cd7f38fa69f9cb05d2c6aee611`, 15 targeted tests passed:

```text
overlay_rows=16
overlay_blocked=7
overlay_eligible=9
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles=2
bird_residual_profiles_overlay_affected=0
```

All acceptance flags are true.

Evidence status:

```text
Privateer Rob ordinary-cloak targetability state:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

universal Rob fuel-consumption causality:
  REJECTED

raw prior iscloaked as blanket blocker:
  REJECTED

advanced-cloak Privateer branch:
  UNRESOLVED
```

Helper:

```text
src/planets_lab/rules/combat/effective_state.py
```

Important: this evidence establishes a **directional ordinary-STANDARD targetability effect**, not a symmetric pair-combat ban. Do not wire `effective_cloak=True` into `_base_engagement` as a blanket pair blocker. A cloaked ship may have its own attack request and pre-standard phases have separate semantics.

## Remaining original blocker — Bird Super Spy ship202

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md
docs/handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-pending.md
```

Residual:

```text
game 511506 / T94
active 496 owner5/race5 Bloodfang
extra  202 owner3/race3 Red Wind, mission9
factual 332 owner3/race3 Resolute, mission2
```

Existing archive/static facts for ship202:

```text
Bird race3
cloak-capable Red Wind
mission9 Super Spy
T-1 iscloaked=true
T-1 fuel=37
ordinary cloak reference cost=5
T same owner/hull and iscloaked=true
```

Matched negative control ship332:

```text
Bird Resolute, cloak-capable
mission2, not Super Spy
T-1 iscloaked=true
factual VCR with ship496 occurs
```

This independently rejects raw `T-1 iscloaked=true` as a generic blocker.

Official Planets.nu documentation provides a direct rule basis:

- Super Spy: Bird ships on Super Spy which can cloak attempt to cloak normally; inadequate fuel means cloak does not occur while Super Spy continues.
- Cloak: cloaked ships are protected from enemy attack; ordinary cloak consumes the normal hull-mass-based reference fuel; damage prevents initiating or maintaining cloak; Advanced Cloak has separate fuel semantics.

Sources:

```text
https://help.planets.nu/mis-super-spy
https://help.planets.nu/mis-cloak
```

## Immediate gate — Bird Super Spy dynamic context

Diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_cloak_context_audit.py
tests/test_combat_host_bird_super_spy_cloak_context_audit.py
```

The diagnostic is deliberately stricter than the documentation. It only reports the focused ship202 candidate supported when all of these resolve:

```text
Bird race3
mission9 Super Spy
cloak-capable ordinary-cloak hull
damage=0
prior archived iscloaked=true
fuel > reference cost
reference normal movement resolved
reference remaining fuel > reference cost
T-1 ion context clear
T-1 Loki exposure clear
no co-located active POP/TRG Glory device
```

T state remains attribution-only.

Acceptance:

```text
extra_ship_documented_effective_cloak_supported=True
factual_ship_documented_effective_cloak_supported=False
raw_prior_cloak_control_separates=True
race_conflicts=0
```

If this passes, promote the Bird blocker only at the focused ordinary-STANDARD targetability boundary as `DOCUMENTED + CORPUS_OBSERVED + TESTED`, then project ship202 removal over both baseline profiles. After both original broad blockers are closed, introduce a generic directional STANDARD targetability composition and rerun the full initial selector differential before promoting the canonical first selector.

If Bird fails or is unresolved, follow the specific reported movement/damage/ion/Loki/Glory factor rather than special-casing ship202.

Later C5 work after broad initial-blocker closure: canonical first selector; mutable survivor/destruction state; second-pass orientation in the mutable queue; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.