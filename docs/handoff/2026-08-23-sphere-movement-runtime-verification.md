# Sphere-aware ordinary movement — runtime verification handoff

Date: 2026-08-23

Repository: `Numillyash/planets-lab`

Status: **sphere-aware ordinary movement is runtime verified; next task is generic post-sphere residual triage.**

This is the current movement/corpus handoff. It supersedes the sphere-integration status in `2026-08-21-movement-corpus-current-state.md`.

## Runtime-verified corpus state

Current schemas:

```text
corpus manifest:
  planets-lab.corpus-game.v2

prepared cache:
  planets-lab.prepared-game-cache.v1

compiled movement:
  planets-lab.compiled-movement.v2

post-compile external-context semantics:
  planets-lab.compiled-movement-storm-context.v2

compiled context labels:
  planets-lab.compiled-movement-context-labels.v3
```

Current 12-game accounting:

```text
transition_rows                       254046
geometry_ready                        247816
move_most_candidates                  227468
baseline_explained                    209574
baseline_unresolved                    17894
external_context_explained             13956
post_external_residual                  3938

chunnel_explained                       1387
post_chunnel_residual                    2551
horwasp_ballistic_candidates              911
horwasp_mite_residual                      786
horwasp_strong_explained                   240
horwasp_observed_context_explained           0
post_horwasp_strong_residual              2311
label_issues                                 0
```

## Sphere integration result

Pre-production diagnostic over the old final residual predicted:

```text
final residual rows                         2753
sphere rows                                 2059
raw 2150 closures                              0
effective 2170 closures                      442
effective 2170 non-Horwasp closures          394
hull 46 sphere rows                           235
hull 46 effective closures                   213
```

Production implementation:

```text
src/planets_lab/corpus/movement_sphere_context.py
tests/test_movement_sphere_context.py
```

Evidence scope is exact and fail-closed:

- game id must be `591478`;
- raw archive topology must be stable;
- `sphere=True`;
- raw dimensions must be exactly `2150x2150`;
- effective movement period is `2170x2170` only inside that scope;
- this must never be generalized as `mapwidth + 20`.

Raw compiled topology facts remain unchanged. Runtime query after the production rebuild returned:

```text
(591478, True, 2150, 2150, '1', True)
```

The production pass is monotonic:

1. raw baseline classification;
2. existing tow / gravitonic / authoritative storm context;
3. effective sphere geometry only for rows still `post_external_residual=true`;
4. L2 Chunnel;
5. L2 Horwasp.

Existing explanatory categories are therefore not stolen or renamed.

## Tests

Targeted runtime suite:

```text
19 passed
```

The full pytest suite also completed green at 100%.

## Cache invalidation verification

The post-compile semantic marker changed from:

```text
planets-lab.compiled-movement-storm-context.v1
```

to:

```text
planets-lab.compiled-movement-storm-context.v2
```

A normal L1 build without `--rebuild` produced:

```text
compiled_cache_hits:                0
compiled_cache_misses:             12
prepared_cache_hits_on_compile:    12
prepared_cache_misses_on_compile:   0
```

So semantic invalidation worked automatically while all prepared caches were reused.

The following L2 build produced:

```text
compiled_label_cache_hits:          11
compiled_label_cache_misses:         1
prepared_cache_hits_on_compile:      1
prepared_cache_misses_on_compile:    0
```

Only game `591478` required label recompilation, consistent with only that movement source partition changing semantically/content-wise.

## L1 effective sphere categories

Runtime distribution:

```text
effective_sphere_partial_host_major_minor                    212
effective_sphere_gravitonic_reachable_warp_well_match        105
effective_sphere_gravitonic_reachable_exact                   61
effective_sphere_gravitonic_partial_host_major_minor          58
effective_sphere_reachable_warp_well_match                    40
effective_sphere_reachable_exact                              34
effective_sphere_partial_host_major_minor_warp_well_match      2
-----------------------------------------------------------------
effective_sphere_total                                       512
```

L1 therefore changed:

```text
post_external_residual 4450 -> 3938  (-512)
```

Chunnel count stayed exactly stable at `1387`, so:

```text
post_chunnel_residual 3063 -> 2551  (-512)
```

Horwasp strong count changed:

```text
310 -> 240  (-70)
```

Those 70 rows are overlap: production sphere geometry now explains them earlier at L1 even though old L2 Horwasp strong could also explain them. Therefore the final strong residual falls by:

```text
512 - 70 = 442
```

and runtime gives exactly:

```text
post_horwasp_strong_residual 2753 -> 2311
```

This exactly matches the independent pre-production final-residual diagnostic.

Sphere-aware ordinary movement for this evidence scope is now:

**CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## Closed / do not reopen without new evidence

- warp-well classifier ordering — `TESTED + DIFF_VERIFIED`;
- Red Mite tracking/fallback — research closed, remaining hull-213 rows fail closed;
- scoped Horwasp ballistic 2170 topology — `TESTED + DIFF_VERIFIED`;
- classic ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped ordinary sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- multi-waypoint hypothesis for old hull-79 cluster — rejected;
- hull 79 is not an active target after classic-storm closure;
- fuel proration is real but low-volume and deprioritized.

## Current final residual ranking

Largest rows after sphere integration:

```text
hull 213   786 / 1 game   # closed Red Mite cluster; ignore for priority
hull 210   293 / 1 game   # Horwasp-heavy
hull 202   170 / 1 game   # Horwasp-heavy
hull 207    82 / 1 game   # Horwasp-heavy
hull 23     78 / 3 games
hull 52     59 / 4 games
hull 56     55 / 4 games
hull 17     51 / 9 games
hull 46     50 / 4 games
hull 208    48 / 1 game   # Horwasp-heavy
hull 94     43 / 3 games
hull 29     36 / 5 games
hull 22     25 / 5 games
hull 16     24 / 6 games
hull 31     22 / 6 games
```

Do not interpret hull ranking as mechanic identity. The next investigation must look for shared cross-hull/cross-game signatures.

## Immediate priorities

1. Add a generic post-sphere residual clustering diagnostic over `movement_post_horwasp_strong_residual`.
2. Explicitly exclude/flag closed Red Mite hull 213 and known Horwasp hulls `201-213` from the generic ranking view.
3. Group remaining rows by:
   - game count and hull count;
   - warp zero vs nonzero;
   - observed displacement vector and repeated vectors;
   - observed distance vs nominal movement distance;
   - target distance / target-is-origin / target-direction relationship;
   - repeated signatures shared by different hull IDs.
4. Start from the multi-game populations around hulls `23, 52, 56, 17, 46, 94, 29`, but promote only a generic mechanic if the signature actually crosses hulls/games.
5. Keep one-off race/hull explanations below generic high-volume mechanics unless evidence forces otherwise.
6. After the next material commit, update current state/roadmap in the same development cycle.

## Implementation commits for sphere integration

```text
e4a1a46  Add scoped sphere movement context
ab6c5ac  Cover scoped sphere movement context
237f7f3  Wire sphere context from compiled row facts
0ea9abc  Apply scoped sphere context after storm resolution
6d8b390  Record sphere integration pending runtime verification
```

## Working rules

- GitHub `main` is source of truth.
- Preserve raw facts and evidence-scoped effective context separately.
- Never infer a global topology rule from one historical game.
- Prefer generic cross-game mechanics over hull-specific overfitting.
- Generated raw/cache/compiled data remains local; privacy-safe compact manifests, code, schemas and summaries belong in Git.
