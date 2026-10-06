# Fresh32 prospective O/C-forward selector result — C branch independently exact

Date: 2026-10-06

## Runtime

Runtime evidence:

    runtime-logs/postcapture-o-c-forward-independent/
    20261006T024237Z_bbc0b467ae0a

Research source:

    bbc0b467ae0ab9ef107b7877a4970a05f04fb059

Canonical main source:

    fe709f92f4e082ed8b36a3f13b3df784a157da3e

Frozen selector implementation:

    d6f80a12c9d6fbf3eaa1d7dfeb1cc39839d147ad

Frozen validation protocol:

    16b5a10e6bda7ebd8e98e1cee3a8ca16508727de

The selector-critical files remained byte-identical to the frozen
implementation.

## Population boundary

    public68 baseline games      68
    fresh games                  32
    fresh index games            32
    public68/fresh overlap        0

The exact public100 generation was used through a read-only validation view:

    generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb

SHA256:

    3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

Canonical CURRENT remained on public68 throughout the gate.

## Result

Fresh32 capture harvest:

    ship capture continuations   43
    globally adjacent rows       20

Dependency-qualified RIGHT-capture rows accepted by the frozen full selector:

    qualified                     6
    resolved                      6
    exact                         6
    mismatch                      0
    unresolved                    0
    no_pair                       0
    active replay unresolved      0
    order unresolved              0

Observed selector branches:

    O                             0
    C                             6

Gate status:

    PASS_PARTIAL_BRANCH_COVERAGE

The result is partial only because the fresh population did not contain a
qualified O-branch row. It is not partial because of any selector mismatch or
unresolved dependency.

## Six independently exact C-forward rows

    game 326221 T40  V268  ->269  prize155 captor145 factual303
        order [155, 303, 145]
        R=0 F=1 L=2
        predicted303 exact

    game 326221 T161 V1584 ->1585 prize2 captor297 factual128
        order [2, 128, 297]
        R=0 F=1 L=2
        predicted128 exact

    game 347358 T52  V176  ->177  prize351 captor432 factual361
        order [104, 351, 361, 432, 460, 2, 310]
        R=1 F=2 L=3
        predicted361 exact

    game 400330 T141 V592  ->593  prize140 captor184 factual170
        R=3 F=4 L=8
        predicted170 exact

    game 400330 T141 V594  ->595  prize170 captor184 factual382
        R=4 F=5 L=8
        predicted382 exact

    game 497195 T18  V8    ->9    prize98 captor60 factual243
        order [98, 243, 60]
        R=0 F=1 L=2
        predicted243 exact

Every factual opponent satisfied the frozen positive dependency boundary:

    active = true
    candidate resolved = true
    requests captured prize's new owner = true
    strict directed permission = true

The request-anchored diagnostic was identical to the strict primary selector on
all six rows.

## Promotion boundary

The following bounded statement now has prospective independent evidence:

    For a dependency-qualified capture-on-RIGHT row where O is exhausted and
    the frozen selector reaches C, scan forward after the captured prize's
    frozen order position (bounded before the consumed captor position) and
    choose the first definitely eligible candidate under the frozen screening
    rules.

Observed independent C coverage:

    6 / 6 exact

The complete O->C selector is not yet fully independently validated because the
fresh population supplied no qualified O row.

Do not relabel the whole selector PASS_FULL_BRANCH_COVERAGE.

## Next orchestration boundary

Do not acquire another broad random corpus merely to obtain an O example.

The more valuable next step is integration with the already verified ordinary
post-mutation queue:

    factual VCR N terminal
      -> atomic active-set / survivor / capture mutation
      -> if N captured a prize:
             frozen O->C continuation selector
         else:
             production ordinary STANDARD post-mutation selector
      -> held-out factual VCR N+1

A particularly valuable open integration chain is:

    game 400330, turn 141, site (1674, 2363)

    V592  ship184 captures ship140
      -> C predicts V593 prize140 vs ship170

    V593  prize140 continuation completes
      -> ordinary mutable queue resumes

    V594  ship184 captures ship170
      -> C predicts V595 prize170 vs ship382

This chain crosses:

    capture mutation
    C-forward selection
    ordinary queue resumption
    second capture mutation
    second C-forward selection

The research composition layer is:

    tools/research/postcapture_site_transition_executor.py

It deliberately fails closed if a capture cursor is exhausted instead of
guessing how Host resumes the parent/global queue. That resumption boundary is
the next orchestration question.


## Research-branch CI note

PR #119 was intentionally based on `research/external-engine-analysis`, not
`main`, because the external evidence branch contains frozen reverse-
engineering history that should not be rebased or bulk-merged merely to satisfy
modern production-branch tests.

The current PR head CI result is:

```text
613 passed
3 failed
```

All newly added mutable-site executor tests pass.

The three remaining failures are inherited branch drift unrelated to this
change:

```text
test_o_layer_wrapper_is_main_guarded_and_discovery_only
    old external branch lacks the later main discovery evidence wrapper

test_discovery_wrapper_is_main_guarded_and_heldout_sealed
    old external branch lacks the later main discovery evidence wrapper

test_public_harvest_requests_progress_output
    old external capture continuation diagnostic predates the later main
    progress-output contract
```

The real integration runner deliberately executes against the current canonical
`main` checkout mounted as `/workspace`, while importing only the frozen
research cursor and new composition layer from `/research`. Therefore the
three inherited external-branch failures are not runtime dependencies of the
site-transition gate.

Do not merge the hundreds of divergent main commits into the frozen external
evidence branch solely to turn this historical branch's global pytest green.
