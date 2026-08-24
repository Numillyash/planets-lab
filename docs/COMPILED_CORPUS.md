# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is a deterministic local derivative and must be rebuildable from cached archives plus manifests.

Current movement/corpus state is summarized in [`handoff/2026-08-24-chunnel-route-equivalent-runtime-verification.md`](handoff/2026-08-24-chunnel-route-equivalent-runtime-verification.md).

## Build

Build the movement dataset with:

```bash
docker compose run --rm -T lab \
  python -u -m planets_lab.corpus.compiled_movement_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --output-dir validation/corpus/compiled/v1
```

Build/refresh context labels with:

```bash
docker compose run --rm -T lab \
  python -u -m planets_lab.corpus.compiled_movement_labels_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --compiled-dir validation/corpus/compiled/v1
```

Generated layout:

```text
validation/corpus/compiled/v1/
  corpus.duckdb
  metadata/
    build.json
    games.parquet
  mechanics/
    movement_transitions/
      game_id=<id>/
        _meta.json
        part-000.parquet
  labels/
    movement_context/
      metadata/
        build.json
      game_id=<id>/
        _meta.json
        part-000.parquet
```

The entire `validation/corpus/compiled/` tree is ignored by Git.

## Layer boundaries

### L0 — raw archives

`/game/loadall` ZIP files are retained unchanged. They are the evidence base used to rebuild every downstream dataset after parser, reconstruction or rules changes.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache. It may contain normalized private-perspective state and large Python object graphs. It is not a portable dataset format.

Current schema:

```text
planets-lab.prepared-game-cache.v1
```

### L1 — compiled movement

The Parquet dataset is flat and SQL/ML friendly. One row corresponds to one movement-readiness transition. Rows preserve readiness separately from mechanic labels.

Current physical/row schema:

```text
planets-lab.compiled-movement.v2
```

Current post-compile external-context semantic schema:

```text
planets-lab.compiled-movement-storm-context.v2
```

The historical symbol name is retained because partition metadata already uses `storm_context_schema`. Version 2 represents the ordered post-compile L1 context stack: authoritative classic/cloudy storm handling followed by evidence-scoped effective sphere geometry on rows that are still unresolved. The separate semantic marker exists because classification behavior can change without changing Parquet columns.

Important L1 data includes:

- game/turn/ship identity;
- raw map-topology facts (`sphere`, dimensions, map shape, stability);
- readiness and privacy-safe issue codes;
- reconstructed owner/hull/geometry fields;
- derived movement intent;
- observed and target geometry;
- warp-well availability;
- gravitonic/tow/storm/effective-sphere context;
- baseline category and residual flag;
- external-context category and residual flag.

Raw topology columns are factual context. Evidence-scoped effective topology never overwrites them.

For historical game `591478`, the production sphere context requires exact game id, `sphere=true`, stable raw topology and raw dimensions exactly `2150x2150` before using the independently validated effective `2170x2170` toroidal period. This is not a global `mapwidth+20` rule.

Classic/cloudy ion-storm selection is driven offline from manifest `settings.nuionstorms`. The compiler fails closed if that setting is missing or not boolean; it does not perform a network lookup during normal compilation.

Private text orders are not exported. Raw fields such as friendly code may be used locally to derive a mechanical category, but the text itself is not a compiled column.

### L2 — compiled context labels

Chunnel and Horwasp classification is stored separately under `labels/movement_context/`. One label row corresponds to one L1 row where `post_external_residual = true`.

Current schema:

```text
planets-lab.compiled-movement-context-labels.v4
```

Version 4 changes Chunnel semantics without changing exported columns. After candidate events are filtered to the same pre-Chunnel position and the same observed destination, any non-empty match set closes the movement as Chunnel. Multiple route-equivalent events no longer become a false residual merely because the initiating event identity is ambiguous. Descriptive role ambiguity is represented as `route_equivalent_multiple_roles` while `chunnel_explained=true` remains authoritative.

This v4 semantic bump intentionally invalidates all old v3 label caches during a normal label build without requiring `--rebuild`.

The compiler may inspect private raw/prepared state locally where a mechanic requires it, but label Parquet exports only derived categories/flags.

Important label fields include:

- `chunnel_category`, `chunnel_match_count`, `chunnel_explained`, `post_chunnel_residual`;
- `horwasp_candidate_kind`;
- `horwasp_category`;
- `horwasp_strong_explained`;
- `horwasp_observed_context_explained`;
- `post_horwasp_strong_residual`.

Weak observed-context Horwasp matches remain evidence only and do not reduce the strong residual.

Each label partition is tied to the source archive and exact source movement Parquet SHA-256 so stale labels cannot survive a changed movement partition.

Standalone Chunnel evaluator semantics are aligned with compiled v4 behavior and use:

```text
planets-lab.movement-chunnel-context-game.v2
planets-lab.movement-chunnel-context-stats.v2
```

## DuckDB catalog

`corpus.duckdb` exposes at least:

- `games`;
- `movement_transitions`;
- `move_most`;
- `movement_residual`;
- `movement_context_labels`;
- `movement_labeled_residual`;
- `movement_post_chunnel_residual`;
- `movement_post_horwasp_strong_residual`.

Useful queries:

```sql
SELECT count(*) FROM move_most;

SELECT hull_id, count(*) AS n
FROM movement_residual
GROUP BY hull_id
ORDER BY n DESC;

SELECT external_context_category, count(*) AS n
FROM move_most
WHERE post_baseline_residual = true
GROUP BY external_context_category
ORDER BY n DESC;

SELECT hull_id, count(*) AS n
FROM movement_post_horwasp_strong_residual
GROUP BY hull_id
ORDER BY n DESC;
```

The catalog contains views over Parquet rather than a second copy of the transition/label tables. Rebuild the catalog if the repository is moved and generated absolute paths become stale.

## Cache validity

Movement partition `_meta.json` records identity/provenance including:

- compiled movement schema;
- prepared-cache schema;
- post-compile movement semantic dependencies such as `storm_context_schema`;
- game ID and settings hash;
- source archive SHA-256;
- raw map-topology facts;
- row/accounting counts;
- Parquet size.

Context-label metadata additionally records the exact source movement Parquet SHA-256 and current label schema.

Bump or add a semantic cache marker whenever classification behavior changes even if columns do not. Do not require users to manually delete caches to make a semantic fix take effect.

## Last runtime-verified 12-game invariants

The following counts are the **pre-v4 runtime baseline**. They remain the last verified values until the route-equivalent Chunnel v4 label build is run and measured.

Movement L1:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13956
post_external_residual         3938
```

Context labels under the prior v3 runtime build:

```text
external_residual_rows             3938
chunnel_explained                  1387
post_chunnel_residual              2551
horwasp_ballistic_candidates        911
horwasp_mite_residual               786
horwasp_strong_explained            240
horwasp_observed_context_explained    0
post_horwasp_strong_residual       2311
label_issues                          0
```

## Route-equivalent Chunnel pre-fix differential

The DB-only audit over the existing v3 label corpus measured:

```text
labeled_rows                         3938
multiple_match_rows                    34
multiple_match_unexplained             34
multiple_match_post_chunnel             34
multiple_match_final_residual            34
multiple_match_warp0_self_waypoint       22
```

All 34 rows had `chunnel_match_count=2` and current category `ambiguous_matching_events`.

Coverage:

```text
by game:
  360690  21
  591478  13

by baseline category:
  warp_zero_external_move  22
  above_nominal            12
```

Expected v4 differential, pending runtime verification:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240  expected unchanged
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

Do not treat these expected values as verified invariants until the normal v4 label build confirms them.

## Scoped sphere categories in L1

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

Raw topology facts for game `591478` remain:

```text
sphere=true
map_width=2150
map_height=2150
map_shape='1'
topology_stable=true
```

## Verified sphere cache behavior

The sphere semantic marker bump invalidated all 12 old movement partitions automatically during a normal build without `--rebuild`:

```text
compiled_cache_hits:             0
compiled_cache_misses:          12
prepared_cache_hits_on_compile: 12
prepared_cache_misses_on_compile: 0
```

The following label build produced:

```text
compiled_label_cache_hits:       11
compiled_label_cache_misses:      1
prepared_cache_hits_on_compile:   1
```

This is consistent with only game `591478` producing a changed source movement partition while rebuilt non-sphere partitions remained hash-compatible with their prior deterministic output.

## Sphere differential closure

Pre-production final-residual diagnostic predicted 442 effective-only closures under the scoped `2170x2170` period. Production L1 closed 512 rows:

```text
post_external_residual    4450 -> 3938  (-512)
post_chunnel_residual     3063 -> 2551  (-512)
```

Seventy of those rows were previously already explained by Horwasp strong labels:

```text
horwasp_strong_explained   310 -> 240  (-70)
```

Therefore the final strong residual changed by exactly the independently predicted amount:

```text
post_horwasp_strong_residual 2753 -> 2311  (-442)
```

Sphere-aware ordinary movement is therefore **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED** for its exact evidence scope.

## Next residual work

The immediate task is not a new mechanic: runtime-verify the Chunnel v4 route-equivalent semantic fix and close its exact 34-row differential. Only after the measured L2 counts are rebaselined should generic residual triage resume.

These counts are evidence/context closure metrics, not global simulator-accuracy percentages.
