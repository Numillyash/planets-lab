# C5 directional STANDARD targetability — canonical pair wiring runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
606971df33aad68d6e1c2a998e24288bed49e538
```

This checkpoint validates the pair-level production input added by:

```text
1386966ff1a4674140b4ba5404602b8e94d535d8  combat: wire directional STANDARD targetability
c4701ebae04568fb74755ebf6c41c3c9bf159d2f  test: cover directional STANDARD targetability
```

## Runtime

Targeted canonical suite:

```text
tests/test_combat_selection.py
tests/test_combat_standard_targetability.py
tests/test_combat_host_initial_standard_directional_targetability_audit.py

................................ [100%]
```

Population regression was then rerun through:

```text
tools/diagnostics/combat_host_initial_standard_directional_targetability_audit.py
```

Summary:

```text
supported_block_rows=10
supported_block_sources:
  privateer_rob_ordinary=7
  bird_super_spy_ordinary=1
  bird_super_spy_advanced_historical_control=2

selector impacts:
  blocked_lower_target_no_first_effect=3
  blocked_noninitial_attacker_no_first_effect=1
  blocked_outranking_skip_candidate_fix=6

supported_block_conflicts=0
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0

baseline_mismatch_profiles=4
baseline_mismatch_profiles_fixed=4
privateer_residual_profiles=2
privateer_residual_profiles_fixed=2
bird_residual_profiles=2
bird_residual_profiles_fixed=2
unrelated_baseline_mismatches=0
```

Baseline exact-set controls remained unchanged:

```text
strict:      162/162 first pair exact, 162/162 RIGHT exact
conditional: 169/169 first pair exact, 169/169 RIGHT exact
```

Every population acceptance flag was `True`, including:

```text
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

Broad mismatch projection remained exactly the expected four profiles:

```text
360690/T83 strict:      active264 target98 -> projected fixed
360690/T83 conditional: active264 target98 -> projected fixed
511506/T94 strict:      active496 target202 -> projected fixed
511506/T94 conditional: active496 target202 -> projected fixed
```

Advanced eligible control remained preserved:

```text
680435/T31 target68 <- attacker26
closure=explicit_mine_hit_matches_positive_vcr_damage
factual_outcome=pair_vcr
expected_blocked=False
```

## Promoted production boundary

`ShipCombatSideInput.standard_targetable_by_opponent` is now a tested canonical pair-composition input for ordinary STANDARD combat.

Semantics remain directional:

```text
False: suppress only opponent -> this ship ordinary STANDARD request
True:  request may proceed normally
None:  unresolved; fail closed if no independently surviving STANDARD direction exists
```

Pre-standard PIA/C&I are evaluated before this filter and remain untouched. A target which cannot be attacked in one direction retains its own attack request. `has_fuel=False` is not used as a cloak substitute.

Evidence status:

```text
canonical directional ordinary-STANDARD pair input:
  TESTED

population composition over supported historical targetability rows:
  TESTED; Privateer scoped branch additionally DIFF_VERIFIED
```

## Boundary not yet promoted

This runtime does **not** prove a mutable stack/queue implementation. At this checkpoint production still lacked a first-pair stack selector. Effective cloak reconstruction also remains upstream and evidence-scoped; historical Advanced-Cloak T/messages are not production inputs.

The next gate is therefore a bounded initial plain-STANDARD stack selector which consumes already-composed pair decisions and reproduces the established active-then-target ordering before mutable combat state is introduced.
