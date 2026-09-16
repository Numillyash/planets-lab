# C5 directional STANDARD targetability — population runtime

Source branch: `agent/combat-c5-host-phase`

Source HEAD:

```text
23e3b672d4e7c513f348eefd3d0493cc7e21cfef
```

Runtime date: 2026-09-16.

The targeted suite passed (`7 passed`) and the read-only population composition gate completed with every acceptance flag true.

## Supported directional blocks

```text
supported_block_rows=10

sources:
  privateer_rob_ordinary=7
  bird_super_spy_ordinary=1
  bird_super_spy_advanced_historical_control=2

selector impacts:
  blocked_outranking_skip_candidate_fix=6
  blocked_lower_target_no_first_effect=3
  blocked_noninitial_attacker_no_first_effect=1

supported_block_conflicts=0
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
```

The block key is directional:

```text
(game_id, battle_turn, target_ship_id, attacker_ship_id)
```

It means only the attacker's ordinary STANDARD request against that target is suppressed. It is not a symmetric pair blocker and does not suppress the target's own request.

## Initial-selector regression

Baseline remains unchanged before applying the supported overlay:

```text
strict broad:      223/225 first-pair exact; 2 mismatch
strict exact-set:  162/162 first-pair and RIGHT exact

conditional broad:     232/234 first-pair exact; 2 mismatch
conditional exact-set: 169/169 first-pair and RIGHT exact

informative exact-set target-order controls: 15/15 rank1
```

The supported directional overlay repairs every previously known broad mismatch profile:

```text
baseline_mismatch_profiles=4
baseline_mismatch_profiles_fixed=4

privateer_residual_profiles=2
privateer_residual_profiles_fixed=2

bird_residual_profiles=2
bird_residual_profiles_fixed=2

unrelated_baseline_mismatches=0
```

Exact mismatch projection:

```text
360690/T83 strict:      active264 target98 -> factual rank2 target; fixed
360690/T83 conditional: active264 target98 -> factual rank2 target; fixed
511506/T94 strict:      active496 target202 -> factual rank2 target; fixed
511506/T94 conditional: active496 target202 -> factual rank2 target; fixed
```

## Advanced-Cloak eligible control

The previously contradictory factual control remains explicitly preserved:

```text
key=(680435,31,68,26)
population_row_found=True
factual_outcome=pair_vcr
expected_blocked=False
```

This is the mine-hit control already closed by the identity-safe Host message/VCR trace: ship68 hits a mine, reaches damage55 and enters the factual VCR uncloaked.

## Acceptance

All acceptance flags are true:

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

## Evidence boundary

This closes the evidence gate for **directional ordinary-STANDARD targetability composition** over the currently supported cloak states.

It does **not** promote a blanket cloak pair blocker and does not make Host messages or post-Host T state production inputs. Generic Advanced-Cloak dynamic reconstruction still belongs upstream in movement/mine/Glory/Loki/fuel state.

The next implementation step is canonical pair-level wiring in `src/planets_lab/rules/combat/selection.py`: targetability must filter only the opponent's ordinary STANDARD request after pre-standard PIA/C&I classification. Unknown targetability is fail-closed only when an upstream identified potentially-cloaked branch supplies `None`; ordinary callers remain targetable by default.
