# C5 Host combat — directional STANDARD targetability population gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Why this gate exists

The three previously decisive-unresolved Bird Advanced Cloak rows are now historically explained:

```text
680435/T31 ship68  -> explicit mine hit, damage55, same damage in factual VCR
620694/T119 ship26 -> stable T same owner/hull, damage0, iscloaked=true
620694/T119 ship69 -> stable T same owner/hull, damage0, iscloaked=true
```

Runtime:

```text
docs/handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md
```

This removes the apparent contradiction without claiming a universal predictive Advanced-Cloak resolver.

## Active diagnostic

```text
tools/diagnostics/combat_host_initial_standard_directional_targetability_audit.py
tests/test_combat_host_initial_standard_directional_targetability_audit.py
```

The diagnostic composes four evidence surfaces over the unchanged initial STANDARD baseline:

1. Privateer Rob ordinary-cloak helper rows with `effective_cloak=True`;
2. Bird ordinary Super Spy rows with documented/corpus-supported `candidate_blocked=True`;
3. the two historically closed Advanced-Cloak blocked controls;
4. the mine-hit ship68 row as an explicit eligible control only.

It does not use Host messages or T state as future production inputs.

## Directionality

Every supported block is keyed as:

```text
(game_id, battle_turn, target_ship_id, attacker_ship_id)
```

Only that attack direction is removed. The target's own combat request remains untouched. This is not a symmetric pair blocker and does not modify pre-standard C&I/PIA logic.

## Exact-set preservation

The unchanged baseline currently has:

```text
strict exact-set:      162/162 first pair exact, 162/162 RIGHT exact
conditional exact-set: 169/169 first pair exact, 169/169 RIGHT exact
```

For an exact-set site, predicted eligible pairs already equal factual pairs. Therefore any supported targetability block at such a site would necessarily remove a factual pair. The composition gate requires zero supported blocked factual pairs and zero potential first-selector regressions; under those conditions the existing exact-set controls remain exact without replaying Host-message evidence as state input.

## Broad mismatch projection

The unchanged baseline has exactly four broad mismatch rows:

```text
360690/T83 strict      predicted target98 active264
360690/T83 conditional predicted target98 active264
511506/T94 strict      predicted target202 active496
511506/T94 conditional predicted target202 active496
```

A mismatch is counted repaired only when the exact supported directional block matches the predicted `(target, active)` direction, the factual target is rank2 for the same active ship, and factual RIGHT equals predicted active.

Expected result:

```text
baseline_mismatch_profiles=4
baseline_mismatch_profiles_fixed=4
privateer_residual_profiles=2 fixed=2
bird_residual_profiles=2 fixed=2
unrelated_baseline_mismatches=0
```

## Acceptance

All must be true:

```text
privateer_gate_clean
bird_population_gate_clean
advanced_decisive_closure_clean
no_supported_block_conflicts
no_supported_blocked_factual_pairs
no_potential_first_selector_regressions
strict_and_conditional_exact_set_controls_preserved
all_baseline_mismatch_profiles_fixed
privateer_residual_all_profiles_fixed
bird_residual_all_profiles_fixed
no_unrelated_baseline_mismatches
advanced_mine_hit_eligible_control_preserved
directional_targetability_population_gate_passed
```

## Evidence boundary

This is the final population composition gate before canonical directional targetability wiring. It does **not** claim that all Advanced Cloak state is reconstructable from T-1 today. Dynamic state reconstruction remains outside pure pair composition and must ultimately consume reconstructed movement/mine/Glory/Loki/fuel facts, not Host outputs.
