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
- readiness status and privacy-safe issue codes;
- reconstructed owner/hull/geometry fields;
- derived owner intent class;
- observed and target geometry;
- warp-well availability summary;
- gravitonic/tow/storm context;
- baseline category and residual flag;
- external-context category and residual flag.

Private text orders are not exported. For example, raw `friendlycode` may be used to derive `intent_class = 'hyp'`, but the text itself is not a compiled column.

### Labels remain layered

The baseline and external-context labels in v1 are deterministic reproductions of the existing movement validation stack. Chunnel, Horwasp and later inferred/contextual labels should be added as separate compiled label layers rather than overwriting factual columns.

## DuckDB catalog

`corpus.duckdb` exposes these views:

- `games`;
- `movement_transitions`;
- `move_most`;
- `movement_residual` (post external-context residual).

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
```

The catalog contains views over Parquet rather than a second copy of the transition table. Rebuild the catalog if the repository is moved and its generated absolute paths become stale.

## Cache validity

Each game partition has `_meta.json` containing:

- compiled schema version;
- prepared-cache schema version;
- game ID;
- settings hash;
- source archive SHA-256;
- row/accounting counts;
- Parquet size.

A partition is reused only when those identity/version fields still match. Bump `COMPILED_MOVEMENT_SCHEMA` when compiled-row semantics change.

## Expected current-corpus invariants

For the current 12-game validation manifest, the compiled SQL accounting should reproduce the Python validation stack:

```text
move_most_candidates       227468
baseline_explained         207896
baseline_unresolved         19572
external_context_explained  11699
post_external_residual        7873
```

These are evidence/context closure counts, not simulator accuracy metrics.
