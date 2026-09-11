# Intel combat formula historical recheck runtime — 2026-09-11

This checkpoint records the completed bounded recheck of two stale `planets-intel` Battle Planner formulas directly against the cached historical `/game/loadall` corpus.

## Runtime

```text
candidate  3e101d6303de29998bebdc067bce55050405a016
branch     agent/intel-combat-formula-recheck
archives   12
collected  logs/intel-combat-formula-recheck-20260911T170242Z-3e101d63-12209
stages     inputs/tooling/corpus-recheck/summary all 0/0
result     all_assertions_pass=true
```

The gate compares the exact formulas then present in `planets-intel` with the corrected `planets-lab` candidates; it is not a self-consistency test of the lab implementation.

## Federation between-fight shield recovery

Old IntelBoard candidate:

```text
25% of missing shields
```

Corpus-verified rule:

```text
next_shield = min(100 - damage, shield + 25)
```

Runtime population:

```text
comparable                     48
corrected_exact                48
old_intel_exact                38
old_intel_mismatch             10
corrected_only_discriminator   10
observed_recovery_rows         20
old-only counterexamples        0
```

Representative corrected-only historical discriminators include:

```text
620694 T65  ship343  84 -> factual 100   old 88   corrected 100
620694 T67  ship34   80 -> factual 100   old 85   corrected 100
620694 T107 ship306  36 -> factual 61    old 52   corrected 61
620694 T108 ship212  40 -> factual 65    old 55   corrected 65
620694 T108 ship212  65 -> factual 90    old 74   corrected 90
622476 T17  ship59   79 -> factual 100   old 84   corrected 100
```

The corrected rule matches every comparable race-1 transition. The old IntelBoard formula has ten factual counterexamples and no old-only support.

Evidence status remains:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Native planet beam tech

Old IntelBoard candidate:

```text
TRUNC/FLOOR-like SQRT(DP / 2)
```

Corpus-verified ordinary rule:

```text
ROUND(SQRT(DP / 2))
```

using nearest-integer rounding and tech clamped to 1..10 for positive defense-post counts.

Special/campaign/Horwasp-heavy game `591478` is excluded from this promotion.

Runtime population:

```text
comparable                     1036
corrected_exact                1036
old_intel_exact                 712
old_intel_mismatch              324
corrected_only_discriminator    324
old-only counterexamples          0
payload_conflicts                 0
unique_vcrs                    6469
```

Representative corrected-only rows include:

```text
DP   5 -> factual beam 2   old 1
DP   7 -> factual beam 2   old 1
DP  15 -> factual beam 3   old 2
DP  30 -> factual beam 4   old 3
DP  49 -> factual beam 5   old 4
DP  67 -> factual beam 6   old 5
DP  86 -> factual beam 7   old 6
DP 148 -> factual beam 9   old 8
```

The corrected rule is exact on all 1036 comparable ordinary rows; the old IntelBoard mapping fails on 324 and has no old-only counterexample.

Evidence status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Cross-repository consequence

The runtime gate establishes that these were real `planets-intel` formula defects, not merely differences in interpretation between repositories. The corresponding IntelBoard production-code correction is tracked separately in `Numillyash/planets-intel`; this lab checkpoint remains the historical evidence source.

No new Host combat-order, side-assignment, damaged-starbase persistence, or special/campaign mechanic is promoted by this gate.
