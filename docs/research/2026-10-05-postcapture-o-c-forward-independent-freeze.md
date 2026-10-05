# Post-capture O -> C-forward selector — prospective fresh32 validation freeze

Date: 2026-10-05

Branch:

```text
research/external-engine-analysis
```

Status before fresh32 mechanics read:

```text
PROSPECTIVE_INDEPENDENT_VALIDATION_FROZEN
```

## Frozen selector implementation

The complete RIGHT-capture predictor is frozen at:

```text
d6f80a12c9d6fbf3eaa1d7dfeb1cc39839d147ad
research: add O-C forward open differential runner
```

The freeze guard was added at:

```text
34c76283faf58f605d5c5577071c1aa397866ccf
research: freeze O-C selector implementation
```

Selector-critical paths that must remain byte-identical to the frozen
implementation for this validation:

```text
tools/research/postcapture_o_c_forward_selector.py
tools/research/postcapture_pair_bounds.py
tools/research/probe-postcapture-o-c-forward-open.py
```

## Frozen mechanics candidate

Scope:

```text
capture side = RIGHT
globally adjacent ship-capture VCR N -> N+1
dependency-qualified factual opponent
```

Prediction:

```text
O:
  scan frozen order positions strictly after the capture-target/captor cursor

if O has no definitely eligible pair:

C:
  scan frozen order positions strictly after the captured prize's own
  position and strictly before the consumed captor cursor

select the first definitely eligible pair
```

Eligibility screening remains exactly as frozen before the validation
population is opened:

```text
mutable active membership
current owner identity
request against captured prize's new owner
strict directed diplomacy permission
pair occurrence cap = 2
production pair composition
captured prize mission/PE neutralization
preserved-FC and fresh-nonmatching-FC bounds must agree
fail closed on any earlier unresolved candidate
```

## Prospective population

Canonical main has already acquired a second fresh public population after
the public68/short32 work:

```text
validation/corpus/manifests/public-postindependent-validation-selected.jsonl
validation/corpus/index/public-postindependent-validation-games.jsonl
```

Population boundary recorded on main:

```text
baseline public68 games: 68
fresh selected games:     32
overlap:                    0
combined public100 games: 100
```

Selection used only public listing/loadinfo/settings metadata and archive
compatibility backfill. It did not inspect capture/VCR mechanics outcomes.

This fresh32 population was acquired before the O/C-forward exact selector was
formulated in this research branch.

Therefore it is a prospective independent validation population for the full
selector, provided no fresh32 capture/O-layer outcomes are inspected before
this protocol is frozen.

## Database boundary

The validation must read the fresh32 games from the separately published
public100 compact generation:

```text
generations/corpus-v2compact-public100-*.duckdb
```

Canonical CURRENT must remain on public68 during the gate.

The validator must open public100 through a temporary read-only validation view
or equivalent explicit-generation mechanism. It must not activate public100
before the result is reviewed.

## Prospective artifacts

The gate may create only after this freeze:

```text
fresh32 capture-side harvest, partition=all
fresh32 independent O-layer report
fresh32 O/C-forward selector report
fresh32 independent gate report
```

Factual N+1 opponent identity is comparator-only.

Factual N+1 LEFT/RIGHT is not used by the selector gate.

## Predeclared acceptance

Let:

```text
N = dependency-qualified adjacent capture-on-RIGHT rows
```

Primary exact selector acceptance requires:

```text
N > 0
resolved = N
exact = N
mismatch = 0
unresolved = 0
no_pair = 0
active/order infrastructure unresolved = 0
```

Gate status:

```text
FAILED_MISMATCH
    any primary factual mismatch

INCOMPLETE_UNRESOLVED
    any unresolved/no_pair/infrastructure unresolved row

INSUFFICIENT_NO_COMPARABLE_ROWS
    N = 0

PASS_PARTIAL_BRANCH_COVERAGE
    exact on all N rows, but only O or only C is observed

PASS_FULL_BRANCH_COVERAGE
    exact on all N rows and both O and C branches are observed
```

A PASS_PARTIAL result validates observed rows but is not sufficient to claim
independent coverage of both queue branches.

A PASS_FULL result is the promotion-quality target for this bounded RIGHT-side
next-opponent selector.

## Evidence discipline

If the frozen selector fails, the fresh32 population becomes open and cannot
be reused as independent validation after modifying the selector.

Any post-failure candidate must be labeled post-validation/open-population and
validated on another newly selected zero-overlap population.


## Tracked prospective validator

After the protocol above was frozen, the validator implementation was added:

```text
tools/research/probe-postcapture-o-c-forward-independent.py
tests/test_postcapture_o_c_forward_independent.py
tools/research/run-postcapture-o-c-forward-independent.sh
```

The runner refuses to evaluate unless the selector-critical files remain
byte-identical to the frozen implementation commit.

It also verifies before opening fresh32 mechanics:

```text
public68 baseline count = 68
fresh selected count    = 32
fresh index count       = 32
baseline/fresh overlap  = 0
canonical CURRENT       = frozen public68
public100 source archives = 100
all fresh32 game IDs exist in public100
```

The public100 generation is exposed to the diagnostic tools through a temporary
hard-link validation view under the corpus root. Canonical CURRENT is checked
before and after the run and is never changed.

Fresh32 capture and O-layer artifacts are created only during this prospective
gate. If the gate fails, those outcomes are considered opened and cannot be
reused as independent validation for a modified selector.


## Public100 runtime now available

Canonical main has completed the public100 compact build and published the
immutable prospective-validation generation:

```text
generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb
```

SHA256:

```text
3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c
```

Runtime facts recorded on main:

```text
source archives:     100
source members:      224014
semantic parity:     224014 / 224014 exact
parity failures:     0
database bytes:      28616175616
schema:              planets-lab.corpus-db.v2.compact1
```

Canonical CURRENT remains intentionally on public68:

```text
generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb
```

The prospective O/C-forward runner is now pinned to the exact public100
generation path and SHA256 above. It no longer searches for an arbitrary latest
public100 file.

Main also added explicit-generation readers for the canonical prospective
capture-side workflow. The research selector implementation itself remains
frozen and is still exposed to public100 through the read-only validation view,
so no selector-critical file is changed after the freeze.


## Runtime evidence wrapper

The prospective selector implementation and validation protocol remain frozen.

For the actual runtime, use:

```bash
bash tools/research/run-postcapture-o-c-forward-independent-with-evidence.sh
```

The wrapper publishes:

```text
runtime-logs/postcapture-o-c-forward-independent/<run-id>
```

including the gate log and the bounded fresh32 selector artifacts. The wrapper
does not modify selector-critical files.
