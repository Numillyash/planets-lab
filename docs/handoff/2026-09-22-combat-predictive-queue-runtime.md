# Combat predictive queue — archive-host runtime

Date: 2026-09-22

Repository: `Numillyash/planets-lab`

Runtime source HEAD:

```text
21435cd15c9744e00d958e0e271b9b8a8fd483ad
```

Command:

```bash
git checkout main
git pull --ff-only origin main
bash tools/run-combat-predictive-queue-gate.sh
```

The checkout was clean/current and the tracked gate completed successfully.

## FeatureScope acceptance

Compiled Game Feature Index rebuild:

```text
games=12
rows=1152
known_rows=1116
unknown_rows=36
missing_archives=[]
parquet_sha256=cb72f539775d22726d8d7f225fc7b3deeb8f936312873df12db59340e1dd7735
```

Scope:

```text
profile=combat-planar-no-horwasp
included games=11
excluded games=[591478]
unknown games=[]
```

Shared selector continuity:

```text
selector_partition_shared=true
selector_partition_disjoint=true
planet_c4_checkpoint_preserved=true
ship_c3_checkpoint_preserved=true
cluster_partition_preserved=true
exact=true
failures=[]
```

The refactor therefore preserves the already accepted C3/C4 historical
populations under the shared `FeatureScope` resolver.

## Predictive ship queue differential

The held-out next-VCR diagnostic now runs against the same shared FeatureScope.

Both strict and conditional profiles produced:

```text
multi_vcr_exact_set_sites=23
site_status:exact=16
site_status:excluded=7
excluded:capture_predecessor=7

transitions_compared=22
next_vcr_exact=22
next_vcr_mismatch=0
transitions_with_inactive_filter=22
```

Acceptance:

```text
multi_vcr_exact_set_population_present=true
next_vcr_transition_population_present=true
all_compared_next_vcr_exact=true
no_nonexcluded_unresolved_sites=true
all_profiles_pass=true
```

Combined integration checker:

```text
strict transitions=22
strict exact=22
strict mismatch=0

conditional transitions=22
conditional exact=22
conditional mismatch=0

exact=true
failures=[]
```

## Evidence boundary

The proof is intentionally bounded:

1. owner-current T-1 state reconstructs the initial candidate graph;
2. the canonical plain-STANDARD selector chooses the first pair;
3. deterministic replay of factual VCR N supplies only terminal combat state;
4. production queue mutation removes destroyed ships / carries survivors;
5. occurrence history and active membership feed the canonical next selector;
6. factual VCR N+1 remains held out until comparison.

The seven excluded exact-set sites all stop for one declared reason:

```text
capture_predecessor
```

No non-capture unresolved site remains in this population.

This promotes the current bounded predictive ordinary ship queue to:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

within `combat-planar-no-horwasp` and the exact-set plain-STANDARD scope.

## Next mechanics boundary

Capture is now the immediate residual inside the same predictive queue proof.

Production already contains explicit capture transfer / prize-crew carry
primitives, but the predictive held-out selector deliberately did not rebuild
the pair graph after owner/race mutation.

The next gate should therefore test:

```text
factual VCR N capture terminal
  -> explicit owner/race transfer
  -> captured ship stays active
  -> rebuild post-capture pair candidates under new ownership
  -> ordinary opponent-side attack/defense semantics
  -> canonical next-pair selection
  -> held-out factual VCR N+1
```

Do not retain the captured ship's old mission/Primary Enemy merely to close the
corpus. Historical C5 evidence already showed that every observed immediate
post-capture continuation has an independently attributable opponent-side
initiator.
