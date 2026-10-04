# Post-capture occurrence-round candidates

Date: 2026-10-04

Branch:

```text
research/external-engine-analysis
```

Status:

```text
DISCOVERY_DERIVED_CANDIDATES_FROZEN_BEFORE_FULL_QUALIFIED_POPULATION_TEST
```

Authority:

```text
CORPUS_OBSERVED residual shape + INFERRED candidate
```

This note freezes the next bounded candidates before testing them across the
complete dependency-qualified discovery population.  It is not independent
validation because the candidates were derived from two discovery residuals.

Held-out is not used.

## Residuals that motivate the candidates

The static post-capture strict requester ranking is exact on 13/15 currently
dependency-qualified adjacent discovery rows.

The only two rank>1 residuals are:

```text
486109 / T55 / VCR 191 -> 192
prize=450
static rank1=198
factual rank2=467

486109 / T88 / VCR 518 -> 519
prize=296
static rank1=214
factual rank2=454
```

Both rows share the same history discriminator:

```text
prior occurrences(prize, static-rank1) = 1
prior occurrences(prize, factual-rank2) = 0
```

Detailed histories:

```text
T55:
  VCR189  198 vs 448
  VCR190  198 vs 450   <- rank1/prize first occurrence
  VCR191  448 vs 450   <- capture
  VCR192  factual next is 467 vs 450

T88:
  VCR515  214 vs 412
  VCR516  213 vs 214
  VCR517  214 vs 296   <- rank1/prize first occurrence
  VCR518  296 vs 374   <- capture
  VCR519  factual next is 454 vs 296
```

The factual rank2 attacker had no earlier VCR appearance in either residual,
while the static rank1 attacker had already appeared multiple times.

These two facts create two competing explanations which must be separated.

## Candidate A — pair-occurrence round

Prefer a fresh ship pair over a second occurrence before applying ordinary
static priority.

For every strict attacker candidate against the captured prize:

```text
pair_count = number of factual occurrences of
             unordered {prize, attacker}
             through the capture VCR

if pair_count >= 2:
    pair is exhausted
else:
    candidate key = (pair_count, static_priority)
```

Select the lexicographically smallest key.

Therefore:

```text
all occurrence-1 pairs (prior count 0)
precede
all occurrence-2 pairs (prior count 1)
```

Within one occurrence round, ordinary Nu static priority remains unchanged.

This candidate is compatible with the existing documented/project boundary
that one ship pair may fight at most twice and with the already verified
second-occurrence side reversal.  It changes pair selection order, not the
pair cap or side-reversal rule.

## Candidate B — attacker freshness

The two motivating rows also permit a broader ship-level explanation.

For every strict attacker candidate:

```text
attacker_appearances = number of VCRs containing that attacker
                       through the capture VCR
```

Two frozen variants are tested:

```text
B1 fresh-attacker boolean:
   key = (attacker_appearances > 0, static_priority)

B2 attacker appearance count:
   key = (attacker_appearances, static_priority)
```

These deliberately compete with Candidate A.  If a row exists where an attacker
has fought previously but has never fought the prize, pair-round and
attacker-freshness can diverge.

## Baseline

The current static candidate remains:

```text
key = static_priority
```

It is known to produce:

```text
13 / 15 exact
2 / 15 rank>1 residuals
```

## Required discovery comparison

The next probe must reconstruct every adjacent discovery capture through the
capture VCR and, only for rows where the factual opponent dependency is
qualified, compare:

```text
STATIC_PRIORITY
PAIR_OCCURRENCE_ROUND
FRESH_ATTACKER_BOOLEAN
ATTACKER_APPEARANCE_COUNT
```

Inputs allowed before prediction:

```text
- T-1 independently reconstructed candidate/order state
- elapsed factual VCR history through capture VCR N
- replayed terminal/mutation state through VCR N
```

Forbidden prediction input:

```text
- factual N+1 side
- factual N+1 pair when choosing among candidates
- held-out partition
```

The factual N+1 opponent identity is comparator-only.

## Interpretation boundary

Even a 15/15 fit would be discovery fitting evidence, not validation, because
the occurrence-round candidate was derived from two rows in that population.

A successful pair-round fit would justify a new frozen candidate for future
independent evidence:

```text
post-capture mutable recomposition
-> strict eligible attackers
-> lowest pair-occurrence round
-> static priority within the round
```

It would not by itself establish LEFT/RIGHT behavior.
