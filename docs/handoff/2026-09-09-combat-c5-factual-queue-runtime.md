# C5 Host combat — factual queue differential runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains excluded from ordinary promotion.

## Runtime source

User runtime completed on:

```text
31509d2c9e9f4af89f80e5088597452d40f393c1
```

Artifact:

```text
artifacts/combat-c5-factual-queue-selection-20260909-212420
```

All targeted tests passed and both diagnostics completed:

```text
tests rc=0
audit rc=0
residual rc=0
payload_conflicts=0
```

## Main factual-positive queue differential

Population:

```text
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
```

Conditional factual-positive scope:

```text
engagement_eligible: True=1968
phase: standard=1915, priority_intercept=37, unresolved=16
prestandard_kind: normal_priority_intercept=36, reciprocal_priority_intercept=1
side_result: exact=1947, unresolved=19, mismatch=2
```

Strict scope:

```text
engagement_eligible: True=1949, unresolved=19
phase: standard=1895, priority_intercept=37, unresolved=36
prestandard_kind: normal_priority_intercept=36, reciprocal_priority_intercept=1
side_result: exact=1927, unresolved=39, mismatch=2
```

Site-layer phase ordering remains clean:

```text
strict all_phase_resolved_sites=1182
strict fully_resolved_prefix_exact=1182
conditional all_phase_resolved_sites=1202
conditional fully_resolved_prefix_exact=1202
known phase-prefix violations=0
```

Case1 remains reciprocal Priority Intercept with pair/pre-standard attribution known and reciprocal-specific side deliberately unresolved.

Case2 remains exact under Galactic Power forced-left:

```text
621896/T28/VCR67
phase=standard
left=Gorbie62
right=T-Rex38
side exact=true
```

## Exact-target normal PIA fix validated

The pair-selection fix requiring:

```text
interceptor.mission_target_id == considered_target.ship_id
```

passed runtime and removed the three known false PIA side mismatches.

The audit-specific normal PIA count changed from 47 to 36, larger than the first-order estimate of 44. This does **not** justify restoring owner-only PIA binding: primary Planets.nu semantics bind Priority Intercept Attack to the actual Intercept target. The older 37-row linked-PIA population is a different audit scope and is not reopened absent a direct contradiction.

Evidence status for exact pair binding:

```text
PIA target binding text: DOCUMENTED
canonical pair binding: TESTED
factual queue correction: DIFF_VERIFIED
```

## Remaining two side residuals are repeated-pair second passes

The only remaining resolved side mismatches are:

```text
620917/T7/VCR6
621896/T25/VCR52
```

Targeted queue-history diagnostic showed both are the second occurrence of the same pair in the same battle-turn/location.

### 620917/T7

```text
site queue:
VCR5: LEFT ship14 / RIGHT ship13
VCR6: LEFT ship13 / RIGHT ship14
same pair: (13,14)
same_pair_count=2
VCR6 occurrence_index=2
```

T-1 static keys:

```text
ship13: (3,13,0)
ship14: (4,14,0)
```

Thus the first encounter has static higher-priority ship13 on RIGHT; the second encounter flips the same pair.

### 621896/T25

```text
site queue:
VCR49: LEFT ship67 / RIGHT ship34
VCR50: pair (29,34)
VCR51: pair (29,67)
VCR52: LEFT ship34 / RIGHT ship67
same pair: (34,67)
same_pair_count=2
VCR52 occurrence_index=2
```

T-1 static keys:

```text
ship34: (0,999,34)
ship67: (3,67,0)
```

Again the first encounter has static higher-priority ship34 on RIGHT; the second encounter flips the same pair.

## Documentation boundary

Primary Planets.nu documentation establishes:

- stacked ship combat order can shift dynamically;
- each ship can attack each other surviving ship in sequence;
- any two ships can fight each other a maximum of twice.

Secondary classic VGA Planets documentation explicitly describes the second-pass timeout behavior: the first initiator is RIGHT, and if the same pair fights again the opposite ship becomes initiator/RIGHT.

Therefore keep evidence labels distinct:

```text
max two fights per pair / dynamic stack order: DOCUMENTED
these two repeated-pair flips: CORPUS_OBSERVED
universal second-pass flip rule: not yet promoted from only these two rows
```

Do not weaken `standard_battle_priority_key(...)` from these second-pass rows. Static pair-side assignment applies to first/static pass; repeated-pair orientation belongs to mutable queue history.

## Next gate

Committed after this runtime:

```text
tools/diagnostics/combat_host_repeated_pair_side_population_audit.py
tests/test_combat_host_repeated_pair_side_population_audit.py
```

The next gate inventories **all ordinary repeated same-pair ship VCR groups** and checks:

- pair occurrence counts vs documented maximum two;
- stable-owner vs ownership-change/capture groups;
- whether exactly-two stable-owner groups flip RIGHT ship;
- for conservative plain-static groups, whether first RIGHT is the static higher-priority ship and second RIGHT is the opposite/lower-priority ship;
- whether the two former residual groups are ordinary members of the wider pattern.

Only after that population runtime should a reusable mutable queue side rule be promoted.
