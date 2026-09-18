# C5 mutable membership + second STANDARD queue — runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
87bef989984c909b61e79f86f06fb575cb69c431
```

PR #28 remains open + draft. Game `591478` is excluded from ordinary promotion.

## Regression suite

User runtime:

```text
.......................................... [100%]
```

Covered:

- mutable ship queue;
- mutable-queue corpus adapter;
- repeated-pair side primitive;
- canonical initial STANDARD selector;
- production queue history;
- repeated-pair population adapter;
- second STANDARD production corpus adapter.

## Mutable ship queue ordinary corpus

Diagnostic:

```text
tools/diagnostics/combat_host_mutable_ship_queue_audit.py
```

Runtime:

```text
special_game_591478_excluded=True

archives=11
raw_vcr_observations=15253
unique_vcrs=4394
payload_conflicts=0
replay_supported=4394
ship_appearances=6382
same_location_transitions=1169

survivor_transitions=1146
survivor_membership_exact=1146

captured_predecessor_transitions=23
captured_fail_closed_exact=23

destroyed_predecessor_reappearances=0
production_mutation_errors=0
terminal_flag_unknowns=0
```

Acceptance:

```text
survivor_population_present=True
survivor_membership_exact=True
capture_fail_closed_if_observed=True
destroyed_removal_if_reappearance_observed=True
no_destroyed_predecessor_reappearances=True
no_production_mutation_errors=True
no_terminal_flag_unknowns=True
mutable_ship_queue_transition_gate_passed=True
```

### Interpretation

The earlier red run was a scope error: all 29 destroyed-predecessor reappearances came from isolated game `591478`. After excluding that game, matching the rest of the C5 ordinary corpus, there are no destroyed reappearance contradictions.

Within this bounded ordinary scope:

- replay survivors remain queue-active exactly;
- capture remains intentionally fail-closed and atomic;
- no replay-destroyed predecessor reappears in a later same-location VCR;
- no mutation adapter errors or unknown terminal flags occur.

Status:

```text
ordinary mutable ship membership:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The destruction statement is bounded carefully: the corpus shows no contradiction to removal in the ordinary scope, while the production removal primitive is directly tested. Game `591478` remains a separate identity/lifecycle investigation and is not evidence for ordinary promotion.

## Production second STANDARD occurrence

Diagnostic:

```text
tools/diagnostics/combat_host_second_standard_queue_audit.py
```

Runtime:

```text
comparable_repeated_groups=2
production_second_occurrence_exact=2

baseline:
  archives_considered=11
  special_game_591478_excluded=True
  payload_conflicts=0
  repeated_pair_groups=2
  repeated_pair_vcr_rows=4
  stable_owner_exactly_two_groups=2
  stable_owner_exactly_two_side_flip=2
  plain_static_comparable_groups=2
  plain_static_first_right_exact=2
  plain_static_second_reversed_exact=2
  plain_static_two_pass_exact=2
  max_occurrences=2
  games={620917: 1, 621896: 1}
```

Acceptance:

```text
ordinary_repeated_population_present=True
no_adapter_errors=True
no_production_unresolved=True
production_second_occurrence_exact=True
second_standard_queue_gate_passed=True
```

Production stack:

```text
StandardQueueState
  -> select_next_plain_standard(...)
  -> canonical select_initial_plain_standard(...)
  -> occurrence_index=2
  -> standard_pair_sides_for_occurrence(...)
```

exactly reproduces the second factual orientation for both ordinary repeated-pair controls.

Status:

```text
production occurrence-aware second STANDARD orientation:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Evidence boundary

This runtime closes:

1. ordinary active membership mutation after ship combat;
2. production storage/interpretation of STANDARD pair occurrence history;
3. production second-occurrence LEFT/RIGHT reversal.

It does not yet prove the full next-pair selection across a multi-pair surviving stack. The repeated-pair gate starts from the independently mined repeated-pair population, so pair membership itself is not predicted there.

## Next gate

Build the genuine post-combat queue differential:

```text
independent T-1 candidate reconstruction
        +
factual VCR N only for terminal replay
        -> mutate active membership
        -> preserve occurrence history
        -> independently filter/rebuild surviving candidate pairs
        -> canonical selector
        -> predicted next pair
        -> compare against factual VCR N+1
```

Initial scope must exclude:

- game `591478`;
- capture predecessor;
- unresolved pair decisions;
- non-plain STANDARD/pre-standard queue steps;
- unsupported dynamic targetability/effective-state branches;
- planet combat.

The factual VCR N+1 may be used only as held-out comparison, never as selector input.
