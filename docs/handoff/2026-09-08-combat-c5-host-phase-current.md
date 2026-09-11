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

## Bird ordinary Super Spy blocker — CLOSED at focused boundary

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

Source HEAD `96ce64a1cc3d7da7874f0e9f37dea1333531330c`, 25 targeted tests passed.

```text
baseline_mismatch_examples=4
privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles=2
bird_residual_profiles_projected_fixed=2
unrelated_baseline_mismatches=0
```

All acceptance flags are true. This is structural composition only; canonical targetability remains unwired.

## Bird Super Spy population runtime — hard contradiction gate PASSED

Read:

```text
docs/handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md
```

Source HEAD `2edb1349562d0ed7fc7a6c74a807004e540c46b8`, 17 targeted tests passed.

```text
bird_super_spy_targets_at_factual_sites=30
raw_attack_opportunities=8
conditional_plain_standard_opportunities=8
strict_plain_standard_opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked_factual_pair_regressions=0
```

Hard acceptance all passed:

```text
no_race_conflicts=True
no_payload_conflicts=True
no_blocked_factual_pair_regressions=True
no_decisive_mismatch=True
target_residual_present=True
target_residual_supported=True
```

All three decisive unresolved rows are Advanced Cloak:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

Therefore ordinary Super Spy is supported within scope, while blanket Advanced-Cloak targetability is explicitly not promoted.

## Advanced Cloak visible-context runtime — NO SEPARATOR FOUND

Read:

```text
docs/handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md
```

Source HEAD `838aca3a931d16f7cb46e28350271b34a1cacf8c`, 16 targeted tests passed.

```text
focus_rows=3
expected_blocked_rows=2
expected_eligible_rows=1
stable_t_identity_rows=2
postmove_active_glory_possible_rows=0
postmove_loki_possible_rows=0
t_cloak_false_rows=0
t_cloak_true_rows=2
```

Factual control `680435/T31 ship68`:

```text
start=(1996,2287)
full predicted position=(1984,2266)
position source=normal_move_warp_well
visible mine route risk=None
prior cloak=true, damage0, fuel480
postmove active Glory=[]
postmove Loki=[]
T stable identity=False
```

Skipped `620694/T119 ship26/69`:

```text
start=(1574,1872)
full predicted position=(1590,1837)
position source=normal_move_warp_well
visible mine route risk=None
postmove active Glory at site=False
postmove Loki within 10 ly=False
T stable identities=True
T damage=0
T iscloaked=True for both
```

No visible post-movement Glory/Loki/mine separator exists. A blanket Advanced-Cloak blocker would still regress the factual ship68 pair. Attacker ship26 mission3 is canonical `Kill!`, so ship68 is a valid ordinary-STANDARD negative control rather than a pre-standard mission artifact.

Evidence status:

```text
Advanced Cloak decisive visible-context audit:
  CORPUS_OBSERVED + TESTED

population-wide Advanced Cloak targetability:
  UNRESOLVED
```

## Immediate gate — raw Host events / hidden context

Read:

```text
docs/handoff/2026-09-11-combat-c5-bird-advanced-cloak-event-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_advanced_cloak_event_audit.py
tests/test_combat_host_bird_advanced_cloak_event_audit.py
```

The gate reads raw `.trn` members around the two decisive cases and inventories only tightly scoped mechanical evidence:

```text
680435: T30/T31/T32; ships68/26; site(1984,2266)
620694: T118/T119/T120; ships26/69/74; site(1590,1837)
```

It reports owner3 active advantages/settings/visible minefields, focus-ship timelines, exact-ID/site mechanical messages, sanitized event/report records and matching VCRs.

High-value positive evidence is an explicit mine/web hit, cloak failure, damage/decloak report, Hidden Minefields or related active advantage plus a compatible mechanical report, or another typed event referencing ship68. **Message absence is not proof of no event.**

If the raw-event gate still yields no positive separator, Advanced Cloak stays fail-closed/unresolved. Do not reopen ordinary ship202 or Privateer closures merely because this branch is unresolved.

Only after supported targetability states are population-differential clean should directional targetability be wired into the canonical first STANDARD selector. Then C5 proceeds to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
