# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable source-of-truth layer.
Compiled data is a deterministic local derivative and must be rebuildable from those archives.

## Movement corpus v1

Build the current movement dataset with:

```bash
docker compose run --rm -T --interactive=false lab \
  python -m planets_lab.corpus.compiled_movement_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --output-dir validation/corpus/compiled/v1
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

### L0 raw archives

The `/loadall` ZIP files are retained unchanged. They are the evidence base used to rebuild every downstream dataset after parser, reconstruction or rules changes.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache. It may contain normalized private-perspective state and large Python object graphs. It is not a portable dataset format.

### L1 compiled movement rows

The Parquet dataset is flat and SQL/ML friendly. One row corresponds to one movement-readiness transition. Rows preserve readiness separately from mechanic labels.

Important columns include:

- game/turn/ship identity;
- stable map-topology facts (`sphere`, dimensions, map shape);
- readiness status and privacy-safe issue codes;
- reconstructed owner/hull/geometry fields;
- derived owner intent class;
- observed and target geometry;
- warp-well availability summary;
- gravitonic/tow/storm context;
- baseline category and residual flag;
- external-context category and residual flag.

Topology is factual context in v1. It does not silently change the existing baseline labels; sphere-aware explanatory labels remain a separate mechanics/validation layer.

Private text orders are not exported. For example, raw `friendlycode` may be used to derive `intent_class = 'hyp'`, but the text itself is not a compiled column.

### L2 compiled context labels

Chunnel and Horwasp classification is stored separately under `labels/movement_context/`. One label row corresponds to one L1 movement row where `post_external_residual = true`.

Build or refresh this layer with:

```bash
docker compose run --rm -T --interactive=false lab \
  python -u -m planets_lab.corpus.compiled_movement_labels_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --compiled-dir validation/corpus/compiled/v1
```

The compiler deliberately uses private raw/prepared state only locally when a mechanic requires it. Chunnel detection may inspect a numeric friendly code and Horwasp classification may inspect heading/history, but none of those raw private fields are exported. The label Parquet contains only derived categories and closure flags.

The source set is not recomputed from Python baseline logic. It is read directly from the existing movement Parquet rows with `post_external_residual = true`, so the L2 layer is anchored to the exact L1 residual set.

Important label fields include:

- `chunnel_category`, `chunnel_match_count`, `chunnel_explained` and `post_chunnel_residual`;
- `horwasp_candidate_kind` (`ballistic` or `mite` where applicable);
- `horwasp_category`;
- `horwasp_strong_explained`;
- `horwasp_observed_context_explained` for weaker same-transition evidence;
- `post_horwasp_strong_residual`.

Weak observed-context Horwasp matches are retained as evidence but do not reduce the strong residual count.

Each label partition is tied to both the source archive SHA-256 and the exact source movement Parquet SHA-256. A changed movement partition therefore cannot be silently accepted with labels compiled from an older row set.

## DuckDB catalog

`corpus.duckdb` exposes the base views:

- `games`;
- `movement_transitions`;
- `move_most`;
- `movement_residual` (post external-context residual).

After the movement-context label layer is built it additionally exposes:

- `movement_context_labels`;
- `movement_labeled_residual`;
- `movement_post_chunnel_residual`;
- `movement_post_horwasp_strong_residual`.

Example queries:

```sql
SELECT count(*) FROM move_most;

SELECT hull_id, count(*) AS n
FROM movement_residual
GROUP BY hull_id
ORDER BY n DESC;

SELECT baseline_category, count(*) AS n
FROM move_most
GROUP BY baseline_category
ORDER BY n DESC;

SELECT game_id, sphere, map_width, map_height, map_shape
FROM games
ORDER BY game_id;

SELECT horwasp_category, count(*) AS n
FROM movement_labeled_residual
WHERE horwasp_category IS NOT NULL
GROUP BY horwasp_category
ORDER BY n DESC;

SELECT hull_id, count(*) AS n
FROM movement_post_horwasp_strong_residual
GROUP BY hull_id
ORDER BY n DESC;
```

The catalog contains views over Parquet rather than a second copy of the transition or label tables. Rebuild the catalog if the repository is moved and its generated absolute paths become stale.

## Cache validity

Each movement game partition has `_meta.json` containing:

- compiled schema version;
- prepared-cache schema version;
- game ID;
- settings hash;
- source archive SHA-256;
- map-topology facts;
- row/accounting counts;
- Parquet size.

Each context-label game partition additionally records the source movement Parquet SHA-256. A label partition is reused only when the archive identity, settings, prepared schema, movement schema and exact movement Parquet all still match.

Bump `COMPILED_MOVEMENT_SCHEMA` when compiled-row semantics change. Bump `COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA` when Chunnel/Horwasp label semantics or exported label fields change.

## Expected current-corpus invariants

For the current 12-game validation manifest, the compiled SQL accounting should reproduce the Python validation stack:

```text
move_most_candidates       227468
baseline_explained         207896
baseline_unresolved         19572
external_context_explained 11699
post_external_residual        7873
```

The context-label layer should then preserve the current strong-evidence accounting:

```text
external_residual_rows          7873
chunnel_explained               1387
post_chunnel_residual           6486
horwasp_strong_explained         234
post_horwasp_strong_residual    6252
```

These are evidence/context closure counts, not simulator accuracy metrics.
