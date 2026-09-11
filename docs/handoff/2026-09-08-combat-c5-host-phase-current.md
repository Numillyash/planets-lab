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
- `T` is post-Host/postcombat and may reuse Ship IDs;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

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

Original broad mismatch sites:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

## Privateer Rob ordinary cloak — CLOSED

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

Status:

```text
Privateer Rob ordinary-cloak directional STANDARD targetability:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The helper remains in `src/planets_lab/rules/combat/effective_state.py`; canonical targetability is not yet wired.

## Bird ordinary Super Spy — scoped closure

Focused ship202 runtime remains clean:

```text
Bird race3 / Red Wind / mission9 Super Spy
damage=0
fuel=37, ordinary reference cost=5
reference normal move remaining fuel=29
prior iscloaked=true
ion storm=False
planet ion pulse=False
Loki=False
active Glory=False
documented_effective_cloak_supported=True
```

Matched factual ship332 has prior `iscloaked=true` but mission2 and actually fights. Raw archived cloak is therefore rejected as a blanket blocker.

Status:

```text
focused Bird ordinary Super Spy targetability:
  DOCUMENTED + CORPUS_OBSERVED + TESTED
```

## Bird population checkpoint

Runtime:

```text
docs/handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md
```

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

All hard contradiction checks passed. The three decisive unresolved rows were Advanced Cloak:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

## Advanced Cloak decisive rows — HISTORICALLY CLOSED

Raw-event runtime:

```text
docs/handoff/2026-09-12-combat-c5-bird-advanced-cloak-raw-event-runtime.md
```

Decisive closure runtime:

```text
docs/handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md
```

Source runtime HEAD:

```text
a3412e419b156296d08fac946eb63ff1d09799e4
```

Targeted tests: 14 passed.

Closure summary:

```text
focus_rows=3
factual_rows=1
blocked_rows=2
explicit_target_mine_hit_rows=1
mine_hit_vcr_damage_match_rows=1
blocked_stable_t_cloak_true_rows=2
```

Acceptance:

```text
factual_mine_decloak_closed=True
blocked_advanced_controls_closed=True
all_decisive_advanced_rows_explained=True
```

Factual `680435/T31 ship68` has an identity-safe Host mine-hit message with damage55, and the same `objectid=68` enters the factual VCR with damage55. This closes the apparent counterexample as:

```text
prior Advanced Cloak
  -> movement mine hit
  -> damage55 / decloak
  -> ordinary STANDARD combat
```

Official mechanics document mine-hit decloak for cloaked ships; Advanced Cloak does not exempt this path.

Skipped `620694/T119 ship26/69` retain stable same-owner/same-hull T identities with `damage=0` and `iscloaked=true`. This is attribution-only evidence, never a production input.

Evidence boundary:

```text
Advanced Cloak + mine-hit decloak:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

fully predictive generic Advanced-Cloak state resolver:
  NOT promoted
```

Dynamic cloak state must ultimately come from reconstructed movement/mine/Glory/Loki/fuel phases, not Host messages or T state.

## Immediate gate — population directional STANDARD targetability

Read:

```text
docs/handoff/2026-09-12-combat-c5-directional-targetability-population-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_directional_targetability_audit.py
tests/test_combat_host_initial_standard_directional_targetability_audit.py
```

The gate composes only supported directional blocks over the unchanged initial STANDARD baseline:

- Privateer Rob ordinary-cloak helper=True rows;
- Bird ordinary Super Spy `candidate_blocked=True` rows;
- the two historically closed Advanced-Cloak blocked controls;
- ship68 mine-hit row as an explicit eligible control only.

Every block is directional:

```text
(game_id, battle_turn, target_ship_id, attacker_ship_id)
```

It must not become symmetric pair eligibility and must not remove the cloaked target's own attack request.

Strong acceptance:

```text
privateer_gate_clean=True
bird_population_gate_clean=True
advanced_decisive_closure_clean=True
no_supported_block_conflicts=True
no_supported_blocked_factual_pairs=True
no_potential_first_selector_regressions=True
strict_and_conditional_exact_set_controls_preserved=True
all_baseline_mismatch_profiles_fixed=True
privateer_residual_all_profiles_fixed=True
bird_residual_all_profiles_fixed=True
no_unrelated_baseline_mismatches=True
advanced_mine_hit_eligible_control_preserved=True
directional_targetability_population_gate_passed=True
```

Expected broad projection remains:

```text
baseline mismatch profiles=4
privateer fixed=2/2
bird fixed=2/2
unrelated=0
```

Only after this gate passes should directional targetability be wired into the canonical ordinary STANDARD selection boundary. Pre-standard C&I/PIA must remain untouched. Unknown states fail closed.

After canonical targetability wiring, C5 proceeds to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct.
