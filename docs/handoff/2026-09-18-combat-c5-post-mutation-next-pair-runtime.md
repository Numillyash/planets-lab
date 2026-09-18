# C5 post-mutation next-pair — runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
c3cacd9b1f4dfc45595ee51c11b576f47d01a6aa
```

PR #28 remains open + draft. Game `591478` remains excluded from ordinary promotion.

## Tests

User runtime:

```text
................................ [100%]
```

The targeted queue/mutation/sequence regression suite passed.

## Corpus differential

Diagnostic:

```text
tools/diagnostics/combat_host_post_mutation_next_pair_audit.py
```

Ordinary chain source:

```text
archives=11
raw_vcr_observations=15253
unique_vcrs=4394
payload_conflicts=0
replay_supported=4394
ship_appearances=6382
candidate_ship_turn_chains=797
same_location_transitions=1169
```

Exact-set multi-VCR population, identically for strict and conditional profiles:

```text
multi_vcr_exact_set_sites=23
site_status:exact=16
site_status:excluded=7
excluded:capture_predecessor=7

transitions_compared=22
next_vcr_exact=22
next_vcr_mismatch=0
transitions_with_inactive_filter=22
```

No second-occurrence transition was needed in this population; all 22 compared continuations exercised active-membership filtering after at least one prior participant left the queue.

Acceptance:

```text
strict:
  multi_vcr_exact_set_population_present=True
  next_vcr_transition_population_present=True
  all_compared_next_vcr_exact=True
  no_nonexcluded_unresolved_sites=True

conditional:
  multi_vcr_exact_set_population_present=True
  next_vcr_transition_population_present=True
  all_compared_next_vcr_exact=True
  no_nonexcluded_unresolved_sites=True

all_profiles_pass=True
```

## What this proves

For the bounded exact-set plain-STANDARD population:

```text
independent owner-current T-1 candidate graph
  -> canonical first pair
  -> deterministic terminal replay of VCR N
  -> production active membership mutation
  -> inactive-pair removal
  -> production queue history
  -> canonical next pair
  -> held-out factual VCR N+1
```

reproduces every compared next VCR exactly:

```text
22 / 22
```

Factual VCR N+1 is comparator-only and is not passed to the selector.

Status:

```text
bounded post-mutation ordinary next-pair selection:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Important population shape

All 22 compared transitions report:

```text
transitions_with_inactive_filter=22
```

while no `second_occurrence_predictions` counter appears.

Therefore this runtime specifically validates the common queue transition:

```text
A-B
one prior participant leaves active membership
  -> surviving candidate graph is filtered
  -> next independent pair is selected
```

rather than merely re-testing repeated-pair reversal.

## Remaining boundary

Seven exact-set multi-VCR sites per profile were excluded for:

```text
capture_predecessor
```

Capture is therefore the immediate empirical gap in this same queue population.

A separate generic "dynamic pair-decision recomposition after combat" is not promoted from this runtime: the carried combat vector
`shield/damage/crew/torpedoes/fighters` is not itself an input to the current plain-STANDARD pair-decision primitive. Pair-specific external dynamic facts such as diplomacy, effective cloak/targetability and C&I state remain their own evidence-scoped inputs.

## Next gate

Audit captured-ship continuation over the ordinary same-turn/same-location chains:

- whether captured ship race/ownership attribution changes to the captor;
- whether it remains active in later VCRs;
- how shield/damage/crew/torpedoes/fighters map into its first post-capture VCR;
- whether the next opponent is the captor again or a third ship;
- whether side/order behavior can be explained after ownership transfer.

Do not modify production capture handling until those corpus facts are measured.
