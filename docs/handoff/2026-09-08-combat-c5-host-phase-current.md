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

Hard acceptance all passed. The only decisive unresolved rows were Advanced Cloak:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

## Advanced Cloak visible-context runtime — no visible separator

Read:

```text
docs/handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md
```

Source HEAD `838aca3a931d16f7cb46e28350271b34a1cacf8c`, 16 targeted tests passed.

The full position predictor found no visible post-movement Glory, Loki or candidate-set mine-route separator. Ship68 remained a genuine ordinary-STANDARD negative control; attacker26 mission3 is canonical `Kill!`.

## Advanced Cloak raw-event runtime — MINE-HIT SEPARATOR FOUND

Read:

```text
docs/handoff/2026-09-12-combat-c5-bird-advanced-cloak-raw-event-runtime.md
```

Source HEAD `17dd581be1a2ffc5c99154a24854765e6f839246`, 11 targeted tests passed.

For factual `680435/T31 ship68`, the Bird owner receives an explicit Host message:

```text
RESOLUTE CLASS BATTLECRUISER ID#68 has struck a mine!
Damage is at: 55
(1989,2273)
```

The same ship's factual VCR at `(1984,2266)` starts with:

```text
objectid=68
hullid=31
damage=55
```

Thus the previously unexplained control is directly attributed:

```text
Advanced-Cloak Super Spy ship68
  -> movement mine hit
  -> cloak broken / damage55
  -> ordinary STANDARD combat
```

This matches official Host-order documentation: cloaking requires an undamaged ship, and a cloaked ship hitting a mine during movement becomes uncloaked. Advanced Cloak does not exempt mine-hit decloak.

The skipped `620694/T119 ship26/69` retain stable same-owner/same-hull T identity with `damage=0` and `iscloaked=true`; this is attribution-only positive evidence, not a production input. Raw message absence is not used as proof because IDs collide heavily with unrelated objects in that game.

Evidence status:

```text
Advanced Cloak + mine hit -> uncloaked:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

blanket / fully predictive Advanced-Cloak targetability:
  NOT promoted; dynamic upstream state still matters
```

## Immediate gate — decisive Advanced-Cloak closure

Read:

```text
docs/handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_advanced_cloak_decisive_closure_audit.py
tests/test_combat_host_bird_advanced_cloak_decisive_closure_audit.py
```

Strong acceptance:

```text
factual_mine_decloak_closed=True
blocked_advanced_controls_closed=True
all_decisive_advanced_rows_explained=True
```

Expected counters:

```text
focus_rows=3
factual_rows=1
blocked_rows=2
explicit_target_mine_hit_rows=1
mine_hit_vcr_damage_match_rows=1
blocked_stable_t_cloak_true_rows=2
```

This is evidence closure only. Host messages and T state must never become production inputs. After this passes, resume the combined population-wide directional STANDARD targetability differential using supported Bird ordinary-cloak + DIFF_VERIFIED Privateer states. Dynamic Advanced-Cloak states remain fail-closed unless the precombat movement/mine/Glory/fuel pipeline independently resolves them.

Only after supported targetability states are population-differential clean should directional targetability be wired into the canonical first STANDARD selector. Then C5 proceeds to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
