# C5 Host combat — repeated-pair side population runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains excluded from ordinary promotion.

## Population runtime source

```text
692bde1fb4aad4b8e50801253a2294c01a0206ba
```

User runtime completed with:

```text
TARGETED TESTS: passed
tests rc=0
audit rc=0
payload_conflicts=0
invalid_owner_vcr_rows=0
```

Artifact:

```text
artifacts/combat-c5-repeated-pair-side-20260909-215615/
```

## Population result

Across all 11 ordinary archives, excluding special game `591478`, the entire repeated same-pair ship-vs-ship population is only two groups / four VCRs:

```text
repeated_pair_groups=2
repeated_pair_vcr_rows=4
occurrence_count={'2': 2}
max_occurrences=2
stable_owner_groups=2
stable_owner_exactly_two_groups=2
stable_owner_exactly_two_side_flip=2
plain_static_comparable_groups=2
plain_static_first_right_exact=2
plain_static_second_reversed_exact=2
plain_static_two_pass_exact=2
target_residual_groups=2
```

No counter-population exists:

```text
over_documented_max_two_groups=0
owner_change_groups=0
stable_owner_exactly_two_same_orientation=0
plain_static_first_right_mismatch=0
plain_static_second_reversed_mismatch=0
plain_static_two_pass_mismatch=0
```

Keys absent from the emitted summary are zero-count `Counter` members.

## The two repeated-pair groups

### 620917 / battle turn 7 / pair 13,14

```text
T-1 priority:
  ship13 -> (3, 13, 0)
  ship14 -> (4, 14, 0)

VCR5: LEFT14 RIGHT13
VCR6: LEFT13 RIGHT14
```

Owner-current T-1 state aligns with both factual owners. No exact pair Intercept/C&I order and no Galactic Power candidate exists.

### 621896 / battle turn 25 / pair 34,67

```text
T-1 priority:
  ship34 -> (0, 999, 34)
  ship67 -> (3, 67, 0)

VCR49: LEFT67 RIGHT34
VCR52: LEFT34 RIGHT67
```

The site has intervening VCR50/VCR51 against ship29, but the repeated pair itself appears exactly twice. Owner-current T-1 state aligns with both factual owners. No exact pair Intercept/C&I order and no Galactic Power candidate exists.

## Scoped conclusion

The two former factual queue side residuals are not contradictions to static standard battle priority. They are the entire ordinary repeated-pair population and both show the same queue-history pattern:

```text
first occurrence RIGHT  = static higher-priority ship
second occurrence RIGHT = the opposite ship
```

Evidence status for the **plain ordinary standard repeated-pair scope**:

```text
maximum two fights / dynamic stacked queue: DOCUMENTED
factual repeated-pair population:            CORPUS_OBSERVED
second-pass side reversal pattern:           CORPUS_OBSERVED + DIFF_VERIFIED
exact second-pass reversal as primary text:  NOT PROMOTED AS DOCUMENTED
```

The exact reversal is consistent with secondary classic Host descriptions, but current project evidence policy reserves `DOCUMENTED` for primary Planets.nu documentation.

Do not change `standard_battle_priority_key(...)`.

## Canonical queue primitive — TESTED

```text
src/planets_lab/rules/combat/queue.py
tests/test_combat_queue.py
```

Public helper:

```text
standard_pair_sides_for_occurrence(...)
```

Scope and behavior:

- the caller must already have selected the same ordinary STANDARD pair for an occurrence;
- occurrence 1 preserves the first-pass resolved LEFT/RIGHT sides;
- occurrence 2 reverses them;
- occurrence >2 fails closed (`None`);
- the helper does **not** decide whether a second combat occurs;
- PIA, reciprocal PIA, C&I, Galactic Power, capture/reinsertion and target selection remain outside this helper.

User implementation runtime source:

```text
de824ab4ecc0bc8cd32784ce4d3df9021eddd71b
```

Artifact:

```text
artifacts/combat-c5-queue-primitive-20260909-221345
```

Result:

```text
QUEUE PRIMITIVE TESTS
.................................................................... [100%]
tests rc=0
```

Therefore the queue primitive is `TESTED`. This label applies to the implementation; the historical second-pass reversal remains `CORPUS_OBSERVED + DIFF_VERIFIED` in the bounded scope above.

## Next gate

Proceed to the candidate-set differential:

```text
docs/handoff/2026-09-09-combat-c5-candidate-set-pending.md
```

The next gate must not use factual VCR presence as a positive pair-eligibility oracle. It starts with a conservative site-conditioned T-1 stationary subset, preserves movement/fuel/diplomacy unknowns, and compares canonical `eligible / blocked / unresolved` decisions against the held-out factual pair set before mutable target selection is implemented.

Do not reopen static standard priority, matching-FC, Galactic Power or reciprocal-PIA gates absent contradiction.
