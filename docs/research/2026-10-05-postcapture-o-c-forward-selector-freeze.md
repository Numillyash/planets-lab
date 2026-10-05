# Post-capture O -> C-forward selector — frozen before open-population evaluation

Date: 2026-10-05

Branch:

```text
research/external-engine-analysis
```

Status:

```text
POST_INDEPENDENT_PREDICTIVE_CANDIDATE_FROZEN_BEFORE_OPEN_EVALUATION
```

This is not a canonical NuHost rule.

## Structural prior

The position classes were frozen before short32 O/C topology was read.

Public36 clean RIGHT captures:

```text
qualified RIGHT:               25
O_AFTER_CAPTOR:                 8
C_BETWEEN:                     17
BEFORE_OR_AT_PRIZE:             0
OTHER_GEOMETRY:                 0
forward covered:               25 / 25
```

Zero-overlap independent short32 topology validation:

```text
qualified RIGHT:                3
O_AFTER_CAPTOR:                 1
C_BETWEEN:                      2
BEFORE_OR_AT_PRIZE:             0
OTHER_GEOMETRY:                 0
forward covered:                3 / 3

status:
PASS_FULL_BRANCH_COVERAGE
```

The independently supported structural prior is therefore:

```text
O = continue forward after the consumed capture-target/captor cursor

if O yields no next pair:

C = scan forward again from immediately after the captured prize's own
    frozen order position
```

## Frozen predictive candidate

Scope for this first selector:

```text
capture side = RIGHT
globally adjacent capture VCR N -> N+1
ship-vs-ship continuation
```

Let the frozen external order be:

```text
order[0 ... n-1]
```

and:

```text
R = index(captured prize)
L = index(captor / capture target)
```

Require:

```text
R < L
```

### Segment O

Scan:

```text
L+1, L+2, ... n-1
```

in order.

The first definitely eligible candidate is predicted.

### Segment C

Only if O is exhausted without a definitely eligible candidate, scan:

```text
R+1, R+2, ... L-1
```

in order.

This bounded C segment is equivalent to a forward restart after R for the
current immutable candidate state because O has already exhausted positions
after L.

The first definitely eligible candidate is predicted.

Positions:

```text
<= R
```

are never reached by this candidate.

## Candidate screening at each position

The scanner may skip a position only when it is independently known not to be
the next pair.

Skip:

```text
ship inactive after elapsed mutable replay
same post-capture owner as prize
pair already occurred twice
candidate does not request combat against prize's new owner
strict directed permission is independently false
production pair composition definitely blocks the pair under both
captured-prize FC bounds
```

Select:

```text
active foreign candidate
pair occurrence count < 2
requests new owner = true
strict permission = true
pair composition definitely eligible and phase-invariant under both:
    1. preserved captured-prize FC
    2. guaranteed-nonmatching fresh symbolic captured-prize FC
```

Fail closed immediately on an earlier order position when any required fact is
unknown:

```text
active/current-owner reconstruction unresolved
request unresolved
strict permission unresolved
pair-composition input unresolved
captured-FC bounds disagree on eligibility or phase
```

This rule prevents the selector from skipping an unknown earlier target merely
because a later factual target is known.

## Pair occurrence state

Pair history is counted from factual elapsed VCRs only through capture VCR N.

Known production boundary:

```text
prior occurrences >= 2 -> pair exhausted
prior occurrences 0 or 1 -> pair may still be selected
```

No pair-occurrence-round priority is used.

## Captured prize order bounds

For pair composition the captured prize uses:

```text
post-capture owner/race transfer
preserved hull
neutral mission / PE
```

Friendly Code is bounded by:

```text
PRESERVED_FC
FRESH_NONMATCHING_SYMBOLIC_FC
```

A pair is definitely eligible only if both bounds agree that it is eligible
with the same phase/prestandard classification.

## Primary and diagnostic permission modes

Primary predictor:

```text
STRICT_PREDICTIVE
```

requires independently proven:

```text
strict_permission = true
```

A secondary diagnostic may report what the same cursor would do if a requesting
candidate with unresolved strict permission were temporarily treated as
permission-anchored:

```text
REQUEST_ANCHORED_DIAGNOSTIC
```

That secondary mode is not predictive evidence and cannot turn an unresolved
primary row into an exact prediction.

## Evaluation boundary

The selector is frozen after the independent topology gate.

The next evaluation may use public36 + now-open short32, but that is an
open-population fitting/differential exercise, not new validation.

Factual N+1 opponent identity is comparator-only.

Factual N+1 LEFT/RIGHT is not used.

The frozen c2ng/THost order key remains EXTERNAL_IMPLEMENTATION evidence; this
selector tests whether the independently supported O/C topology plus current
production eligibility machinery is sufficient on the open corpus.
