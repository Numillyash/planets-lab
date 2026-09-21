# Combat predictive queue reintegration — selector-backed gate prepared

Date: 2026-09-21

Repository: `Numillyash/planets-lab`

## Source-of-truth inventory

The session started from actual GitHub `main`:

```text
eeaf4440c2cae6d08695b5abe7c95bd525d2c9b3
docs: link next combat engagement handoff
```

GitHub Actions for that HEAD was green.

At that HEAD, `src/planets_lab/rules/combat/` contained only the pairwise replay,
planet carry and ship carry modules. The Host engagement/order primitives named
in historical C5 work were not present in `main`.

The still-existing branch `agent/combat-c5-host-phase` was inspected as a Git
evidence source rather than trusted from chat history. It contains the
productionized C5 order/eligibility/selection/queue code plus its historical
differentials.

## Reintegrated canonical slice

The following evidence-backed C5 primitives have been restored on top of current
`main` without merging the divergent branch wholesale:

```text
order.py
eligibility.py
selection.py
queue.py
host_queue.py
mutable_queue.py
effective_state.py
sequence.py capture continuation
```

This restores the canonical mechanics used by:

- standard Combat Priority;
- PIA / reciprocal PIA / C&I pair classification;
- matching-FC / HWM handling;
- directional STANDARD targetability;
- initial plain-STANDARD selection;
- repeated-pair occurrence handling;
- active queue mutation;
- explicit capture transfer;
- post-mutation next-pair selection.

Experimental later C5 ground-combat / clan-drop work is intentionally not part
of this reintegration block.

## Historical held-out proof recovered from Git

The old C5 branch contains an already completed bounded differential:

```text
independent owner-current T-1 candidate graph
  -> canonical first STANDARD pair
  -> replay factual VCR N only for terminal state
  -> mutate active membership
  -> filter inactive pairs
  -> occurrence-aware canonical selector
  -> predict next pair/sides
  -> compare with factual VCR N+1
```

Factual VCR N+1 was comparator-only.

Historical result for both strict and conditional profiles:

```text
multi_vcr_exact_set_sites = 23
exact sites               = 16
capture-predecessor       = 7 excluded
transitions compared      = 22
next VCR exact            = 22
next VCR mismatch         = 0
```

This historical result is provenance for the recovered code. It is not relabeled
as a fresh runtime on current `main`.

## Shared FeatureScope migration

The recovered historical diagnostics previously built their ordinary population
with a numeric special-game exclusion.

The new gate path instead uses:

```text
FeatureScope
profile = combat-planar-no-horwasp
```

The initial STANDARD target audit and held-out next-pair audit classify archives
through the shared resolver. Excluded, UNKNOWN and unindexed games fail closed.

No new clean selector hardcodes game id `591478`.

## One-command gate

Tracked runner:

```bash
bash tools/run-combat-predictive-queue-gate.sh
```

It deliberately runs in this order:

1. existing `run-combat-feature-scope-gate.sh`;
2. targeted canonical C5 tests;
3. selector-backed held-out next-VCR differential;
4. combined acceptance checker.

The FeatureScope stage is fail-fast. Mechanics diagnostics do not run if shared
scope continuity fails.

Expected combined acceptance includes:

```text
selector_partition_shared=true
selector_partition_disjoint=true
planet_c4_checkpoint_preserved=true
ship_c3_checkpoint_preserved=true
cluster_partition_preserved=true

strict transitions >= 22
strict mismatch = 0
conditional transitions >= 22
conditional mismatch = 0

exact=true
failures=[]
```

## Runtime boundary

GitHub Actions can validate imports, deterministic tests and shell syntax, but
it does not contain the gitignored immutable `loadall` archive ZIPs.

Therefore neither the final post-refactor FeatureScope archive acceptance nor
the fresh selector-backed queue differential is claimed complete until the
tracked runner above executes on the archive host.

If the FeatureScope stage fails, treat it as selector/population plumbing first;
do not modify combat mechanics merely to make the gate green.


## 2026-09-22 archive-host closure

The prepared gate was executed against exact HEAD
`21435cd15c9744e00d958e0e271b9b8a8fd483ad` and passed.

Final combined checker:

```text
exact=true
failures=[]
strict      22/22, mismatch=0
conditional 22/22, mismatch=0
```

FeatureScope continuity also remained exact.

This pending document is superseded for runtime status by:

`docs/handoff/2026-09-22-combat-predictive-queue-runtime.md`.
