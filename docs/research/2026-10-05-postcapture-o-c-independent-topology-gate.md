# Post-capture O/C topology — independent short32 gate

Date: 2026-10-05

Branch:

```text
research/external-engine-analysis
```

Status before runtime:

```text
INDEPENDENT_TOPOLOGY_GATE_FROZEN_BEFORE_SHORT32_O_C_READ
```

## Frozen candidate provenance

The O/C topology candidate was frozen before this independent gate at:

```text
7e590cd73690ebf544ff8b7d671747cb6e0ca047
research: freeze postcapture O-C topology candidate
```

The candidate was then fitted structurally on the already-open public36
discovery+heldout population.

Dependency-qualified public36 RIGHT captures currently give:

```text
qualified RIGHT rows:          25
qualified O_AFTER_CAPTOR:       8
qualified C_BETWEEN:           17
qualified BEFORE_OR_AT_PRIZE:   0
qualified forward covered:     25
```

The one unqualified positional exception is the already-known
`597910/T94` intercept-movement fail-closed row and is not used to alter the
candidate.

## Independent population

The independent population already exists on canonical main as the short32
public expansion:

```text
validation/corpus/manifests/public-short-expansion-selected.jsonl
validation/corpus/index/public-short-expansion-games.jsonl
```

Canonical project documentation records:

```text
short32 games:                 32
overlap with original public36: 0
```

The merged O-layer artifact is:

```text
artifacts/public-capture-side/
independent-short32-postheldout-validation.json
```

Important evidence boundary:

The short32 population has already been opened elsewhere for capture-side
LEFT/RIGHT validation. Therefore this is not a globally pristine population.

However:

```text
- short32 was selected independently of the O/C topology candidate;
- it has zero game-id overlap with public36;
- the O/C position classes below were frozen before reading short32 O/C
  topology;
- no short32 O/C position is used to modify the candidate before this gate.
```

Accordingly this gate is labeled:

```text
INDEPENDENT_O_C_TOPOLOGY_VALIDATION
```

with the explicit caveat that the population was previously opened for a
different capture-side question.

## Frozen topology classes

For capture-on-RIGHT rows with reconstructable frozen external order positions:

```text
R = captured prize position
L = capture target / captor position
F = factual N+1 opponent position
```

the frozen classes are:

```text
O_AFTER_CAPTOR
    R < L < F

C_BETWEEN_PRIZE_AND_CAPTOR
    R < F < L

BEFORE_OR_AT_PRIZE
    F <= R

OTHER_GEOMETRY
    any remaining / reversed geometry
```

The forward O/C union is:

```text
O_AFTER_CAPTOR
or
C_BETWEEN_PRIZE_AND_CAPTOR
```

No full selector is fitted in this gate.

## Qualification

The primary gate population is only rows where the independently reconstructed
post-capture factual opponent dependency is fully qualified:

```text
factual opponent active                = true
candidate resolved                     = true
requests captured prize's new owner    = true
strict permission                      = true
```

Movement/site fail-closed rows remain reported but do not count as clean
topology counterexamples.

## Predeclared gate semantics

For dependency-qualified RIGHT rows:

```text
FAILED_COUNTEREXAMPLE
    any BEFORE_OR_AT_PRIZE
    or any OTHER_GEOMETRY

PASS_PARTIAL_BRANCH_COVERAGE
    every qualified row is in forward O/C union,
    but only one of O or C is independently observed

PASS_FULL_BRANCH_COVERAGE
    every qualified row is in forward O/C union,
    and both O_AFTER_CAPTOR and C_BETWEEN_PRIZE_AND_CAPTOR occur
```

An empty qualified population is:

```text
INCOMPLETE_NO_QUALIFIED_ROWS
```

The result must not be relabeled after runtime.

## Authority boundary

The order vector remains the frozen c2ng/THost external comparator and is not
NuHost authority.

A pass supports the structural statement:

```text
dependency-qualified Nu continuations are positionally compatible with
existing-order forward continuation O plus a capture-generated forward scan C
```

It does not establish:

```text
- exact Nu battle-value ordering;
- exact C insertion timing;
- exact C pair eligibility;
- LEFT/RIGHT assignment;
- full mutable queue semantics.
```
