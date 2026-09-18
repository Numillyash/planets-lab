# C5 ordinary STANDARD queue composition — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 must remain open + draft. Game `591478` is excluded from ordinary promotion.

## Preconditions

Already closed:

- pair composition / plain STANDARD priority;
- canonical initial plain-STANDARD selector;
- ordinary Privateer/Bird directional targetability in supported scopes;
- repeated-pair second occurrence side reversal;
- C3 survivor carry primitive;
- atomic mutable ship membership primitive.

The first mutable membership runtime exposed a scope bug in the diagnostic: it included isolated game `591478`. The repaired diagnostic excludes that archive before population accounting.

## New production queue-history layer

Module:

```text
src/planets_lab/rules/combat/host_queue.py
```

API:

```python
StandardQueueState
StandardQueueStepResult
select_next_plain_standard(...)
select_after_ship_mutation(...)
record_standard_queue_step(...)
```

Implementation:

```text
6ea1388201b92b080c8c1798d370311125de7db7
  combat: add ordinary STANDARD queue history

dc473c4ed24d1bf119c1d08e3da8298d38806bc4
  test: cover ordinary STANDARD queue history

9b9cda93935f9ecedfb33e77dc268ab276b4fd40
  combat: export STANDARD queue orchestration
```

## Semantics

The queue layer does not recompute pair mechanics.

Caller supplies freshly composed `InitialStandardPairInput` rows for the current state.

The layer:

1. removes candidate pairs touching inactive ships;
2. removes pairs that already fought `STANDARD_PAIR_MAX_OCCURRENCES == 2`;
3. invokes the already-tested `select_initial_plain_standard(...)`;
4. interprets pair occurrence history;
5. uses canonical first-pass LEFT/RIGHT for occurrence 1;
6. requires recorded first-pass sides and applies the DIFF_VERIFIED reversal for occurrence 2;
7. fails closed if occurrence history or first-pass side history is incomplete/conflicting.

`select_after_ship_mutation(...)` only accepts a resolved `ShipQueueMutationResult`. Pair inputs remain a separate argument so stale pre-mutation pair decisions cannot be reused implicitly.

## Production unit coverage

```text
tests/test_combat_host_queue.py
```

Covers:

- first occurrence -> history record -> second occurrence reversal;
- exhausted pair removal before canonical selection;
- missing first-pass side history fail-closed;
- post-mutation removal of pairs touching destroyed ships;
- unresolved capture mutation stops queue selection;
- stale occurrence record rejection.

## Corpus occurrence composition gate

Diagnostic:

```text
tools/diagnostics/combat_host_second_standard_queue_audit.py
```

Test:

```text
tests/test_combat_host_second_standard_queue_audit.py
```

Implementation:

```text
f39711503ba1fae827a378935813598ab528a661
  combat: add second STANDARD queue composition gate

28ba9a0b8d499ef845a22f3af1848ea185c5728d
  test: cover second STANDARD queue corpus adapter
```

The diagnostic reuses the existing repeated-pair population, which already excludes game `591478`.

It only evaluates:

```text
stable owners
exactly two occurrences
plain static comparable
```

For each such group it reconstructs the ordinary pair decision from T-1 order fields, seeds production history with factual first-pass sides and occurrence count 1, and asks the production queue layer for occurrence 2.

Required acceptance:

```text
ordinary_repeated_population_present=True
no_adapter_errors=True
no_production_unresolved=True
production_second_occurrence_exact=True
second_standard_queue_gate_passed=True
```

Expected population from the previously verified repeated-pair audit:

```text
comparable repeated groups=2
production second occurrence exact=2
mismatch=0
```

Evidence boundary: this proves production occurrence-history composition and second-pass orientation on the existing repeated-pair controls. It does NOT yet prove full post-mutation next-pair selection among a multi-pair surviving stack, because factual repeated-pair membership still selects the population.

## Required runtime sequence

Run:

```bash
docker compose run --rm lab pytest -q \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_host_mutable_ship_queue_audit.py \
  tests/test_combat_queue.py \
  tests/test_combat_initial_standard_selector.py \
  tests/test_combat_host_queue.py \
  tests/test_combat_host_repeated_pair_side_population_audit.py \
  tests/test_combat_host_second_standard_queue_audit.py

docker compose run --rm lab python \
  tools/diagnostics/combat_host_mutable_ship_queue_audit.py \
  --output /workspace/artifacts/combat-host-mutable-ship-queue.json

docker compose run --rm lab python \
  tools/diagnostics/combat_host_second_standard_queue_audit.py \
  --output /workspace/artifacts/combat-host-second-standard-queue.json
```

If both gates pass, promote:

- ordinary mutable membership gate within the 11-game scope;
- production occurrence-aware second STANDARD orientation.

Then the next gate is the real multi-pair composition problem: after each replay terminal, independently rebuild current eligible pairs for the surviving active set and compare the canonical next-pair selection against factual VCR N+1.
