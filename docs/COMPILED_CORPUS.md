# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is a deterministic local derivative and must be rebuildable from cached archives plus manifests.

Current movement/corpus state is summarized in [`handoff/2026-08-21-movement-corpus-current-state.md`](handoff/2026-08-21-movement-corpus-current-state.md).

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

Current mode-aware storm semantic schema:

```text
planets-lab.compiled-movement-storm-context.v1
```

The separate storm semantic marker exists because external-context behavior can change without changing Parquet columns. Cache validity must therefore include both physical-row and semantic dependencies.

Important L1 data includes:

- game/turn/ship identity;
- raw map-topology facts (`sphere`, dimensions, map shape, stability);
- readiness and privacy-safe issue codes;
- reconstructed owner/hull/geometry fields;
- derived movement intent;
- observed and target geometry;
- warp-well availability;
- gravitonic/tow/storm context;
- baseline category and residual flag;
- external-context category and residual flag.

Raw topology columns are factual context. Evidence-scoped effective topology must not overwrite them.

Classic/cloudy ion-storm selection is driven offline from manifest `settings.nuionstorms`. The compiler fails closed if that setting is missing or not boolean; it does not perform a network lookup during normal compilation.

Private text orders are not exported. Raw fields such as friendly code may be used locally to derive a mechanical category, but the text itself is not a compiled column.

### L2 — compiled context labels

Chunnel and Horwasp classification is stored separately under `labels/movement_context/`. One label row corresponds to one L1 row where `post_external_residual = true`.

Current schema:

```text
planets-lab.compiled-movement-context-labels.v3
```

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
- movement semantic dependencies such as storm-context schema;
- game ID and settings hash;
- source archive SHA-256;
- raw map-topology facts;
- row/accounting counts;
- Parquet size.

Context-label metadata additionally records the exact source movement Parquet SHA-256.

Bump or add a semantic cache marker whenever classification behavior changes even if columns do not. Do not require users to manually delete caches to make a semantic fix take effect.

## Current 12-game invariants

Latest runtime-verified movement build after classic ion-storm mode integration:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13444
post_external_residual         4450
```

Latest runtime-verified context-label accounting:

```text
external_residual_rows             4450
chunnel_explained                  1387
post_chunnel_residual              3063
horwasp_ballistic_candidates       1029
horwasp_mite_residual               786
horwasp_strong_explained            310
horwasp_observed_context_explained    0
post_horwasp_strong_residual       2753
label_issues                          0
```

The classic-storm semantic change was verified through normal cache behavior:

```text
compiled_cache_hits:    0
compiled_cache_misses: 12
prepared_cache_hits:   12
```

The following label build produced five cache hits and seven misses because only changed source movement partitions were invalidated.

## Pending topology rebaseline

The current `2753` final residual is the pre-sphere-integration baseline. Diagnostic evidence for game `591478` shows that using the independently validated effective 2170×2170 wrap period instead of raw 2150×2150 explains 442 of those rows, including 394 non-Horwasp rows and 213/235 hull-46 sphere rows.

That result is **diagnostic only** until integrated into L1 ordinary movement/external-context classification, regression-tested and rebuilt. Do not pre-edit the invariant counts to the expected post-integration values; record the measured runtime result after the production change lands.

These counts are evidence/context closure metrics, not global simulator-accuracy percentages.
