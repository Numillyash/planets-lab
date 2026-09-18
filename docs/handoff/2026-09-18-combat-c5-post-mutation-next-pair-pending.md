# C5 post-mutation next-pair differential — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains isolated.

## Closed prerequisites

Runtime:

```text
docs/handoff/2026-09-18-combat-c5-mutable-and-second-standard-runtime.md
```

Closed ordinary scopes:

```text
mutable ship membership:
  survivor 1146/1146
  capture fail-closed 23/23
  destroyed predecessor reappearances 0
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

production occurrence-aware second STANDARD orientation:
  repeated controls 2/2 exact
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Active diagnostic

```text
tools/diagnostics/combat_host_post_mutation_next_pair_audit.py
```

Test:

```text
tests/test_combat_host_post_mutation_next_pair_audit.py
```

Implementation:

```text
28594aaa4ee159fa32a96ab232f448a46e9fc199
  combat: add post-mutation next-pair differential

d2f266358682cd2bf2d32e6723f13c6ff68330d3
  test: cover post-mutation next-pair differential
```

## Differential construction

The diagnostic deliberately composes existing independently established layers instead of rebuilding them.

Candidate graph:

```text
combat_host_initial_standard_target_audit.py
owner-current T-1
  -> repaired position prediction
  -> independent diplomacy controls
  -> pair decisions
  -> exact-set comparable site
```

Terminal state:

```text
combat_ship_chain_audit.py
factual VCR N
  -> deterministic Classic replay
  -> terminal state for the two participants
```

Production continuation:

```text
candidate graph
  -> select_next_plain_standard(...)
  -> record_standard_queue_step(...)
  -> VCR N terminal
  -> apply_ship_terminal_batch(...)
  -> select_after_ship_mutation(...)
  -> active/inactive pair filter
  -> occurrence history
  -> canonical selector
  -> predicted next pair + LEFT/RIGHT
```

Only then:

```text
predicted next pair/sides
  vs
held-out factual VCR N+1
```

The factual next pair is never passed to the selector.

## Scope

Included:

- ordinary corpus only; game `591478` excluded;
- ship-vs-ship sites;
- at least two factual VCRs at the site;
- exact-set comparable candidate reconstruction;
- resolved plain STANDARD pair decisions;
- deterministic replay-supported predecessor;
- non-capture continuation.

Excluded / fail-closed:

- capture predecessor;
- planet/base combat;
- non-exact candidate sets;
- unresolved/pre-standard candidate rows;
- unsupported replay;
- dynamic pair-decision recomputation after combat.

Important limitation: pair decisions are the same independently reconstructed T-1 projections already used by the DIFF_VERIFIED initial selector. This gate tests whether membership mutation + occurrence state + canonical selector reproduces the next queue step. It does not yet prove that every pair-specific dynamic input is recomputed correctly after each combat.

## Unit controls

The synthetic regression test includes:

1. top target is destroyed in VCR N;
2. every pair touching that ship becomes inactive;
3. production selector chooses the next independent surviving pair;
4. capture predecessor stops continuation fail-closed.

## Runtime

Run:

```bash
cd ~/projects/planets-lab

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

echo "===== HEAD ====="
git rev-parse HEAD
git status --short

echo
echo "===== NEXT-PAIR TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_host_queue.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py \
  tests/test_combat_initial_standard_selector.py \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_sequence.py

echo
echo "===== POST-MUTATION NEXT-PAIR CORPUS ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_post_mutation_next_pair_audit.py \
  --output /workspace/artifacts/combat-host-post-mutation-next-pair.json

echo
echo "===== STATUS ====="
git status --short
```

Acceptance is reported separately for strict and conditional profiles:

```text
multi_vcr_exact_set_population_present=True
next_vcr_transition_population_present=True
all_compared_next_vcr_exact=True
no_nonexcluded_unresolved_sites=True
```

Top-level:

```text
all_profiles_pass=True
```

Do not assume counts before runtime. Inspect mismatch/exclusion populations first.

## If green

Promote the bounded post-mutation next-pair queue composition to `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` within its exact-set static-decision scope.

Then move to dynamic pair-decision recomposition after combat and capture ownership/hostility continuation as separate gates.
