# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is a deterministic local derivative and must be rebuildable from cached archives plus manifests.

Current movement/corpus state is summarized in [`handoff/2026-08-24-mine-context-v5-diff-verified.md`](handoff/2026-08-24-mine-context-v5-diff-verified.md).

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

Chunnel, Horwasp and strict mine/web classification is stored separately under `labels/movement_context/`. One label row corresponds to one L1 row where `post_external_residual = true`.

Current verified schema:

```text
planets-lab.compiled-movement-context-labels.v5
```

Version 4 changed Chunnel semantics without changing exported columns. After candidate events are filtered to the same pre-Chunnel position and the same observed destination, any non-empty match set closes the movement as Chunnel. Multiple route-equivalent events no longer become false residuals merely because event identity or descriptive role is ambiguous.

Version 5 adds a fail-closed mine/web layer after Horwasp strong labels. It uses only corpus-verified strict signatures and keeps the documentation-vs-NuHost rounding distinction explicit.

Chunnel role categories include:

```text
initiator
passenger_same_owner
passenger_other_owner
route_equivalent_multiple_roles
```

Strict mine categories include:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
```

NuHost corpus evidence selects positive nearest-integer damage quanta:

```text
web:    round_half_up(1000 / (hull_mass + 1))
normal: round_half_up(10000 / (hull_mass + 1))
```

The Planets.nu documentation describes mine damage as rounded up. The corpus compatibility layer does not silently replace that statement; v5 records the empirically selected NuHost behavior as a separate compatibility finding.

The compiler may inspect private raw/prepared state locally where a mechanic requires it, but label Parquet exports only derived categories/flags.

Important label fields include:

- `chunnel_category`, `chunnel_match_count`, `chunnel_explained`, `post_chunnel_residual`;
- `horwasp_candidate_kind`;
- `horwasp_category`;
- `horwasp_strong_explained`;
- `horwasp_observed_context_explained`;
- `post_horwasp_strong_residual`;
- `mine_category`;
- `mine_damage_hits`;
- `mine_slowdown_hits`;
- `mine_strong_explained`;
- `post_mine_strong_residual`.

No minefield IDs, owners, coordinates or friendly codes are exported in the label schema. Minefield state is used locally only to establish a derived mechanical classification.

Weak observed-context Horwasp matches remain evidence only and do not reduce the strong residual. Repair-bracket-only mine candidates also remain evidence only and are not promoted by v5.

Each label partition is tied to the source archive and exact source movement Parquet SHA-256 so stale labels cannot survive a changed movement partition.

Standalone Chunnel evaluator semantics remain aligned with compiled v4/v5 behavior and use:

```text
planets-lab.movement-chunnel-context-game.v2
planets-lab.movement-chunnel-context-stats.v2
```

## Label layer order

The current ordered label stack is:

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
```

The pre-mine Horwasp residual remains materialized as a DuckDB view. This is intentional so v5 differential verification can compare the new mine layer against the exact v4 endpoint rather than rewriting prior accounting.

## DuckDB catalog

`corpus.duckdb` exposes at least:

- `games`;
- `movement_transitions`;
- `move_most`;
- `movement_residual`;
- `movement_context_labels`;
- `movement_labeled_residual`;
- `movement_post_chunnel_residual`;
- `movement_post_horwasp_strong_residual`;
- `movement_post_mine_strong_residual`.

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

SELECT mine_category, count(*) AS n
FROM movement_labeled_residual
WHERE mine_strong_explained = true
GROUP BY mine_category
ORDER BY n DESC;

SELECT mine_damage_hits, mine_slowdown_hits, count(*) AS n
FROM movement_labeled_residual
WHERE mine_strong_explained = true
GROUP BY mine_damage_hits, mine_slowdown_hits
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

V5 normal-build cache verification:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

Thus the semantic schema bump invalidated only L2 label partitions and correctly reused all prepared state.

## Current runtime-verified 12-game invariants — v5

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

Context labels under verified v5:

```text
external_residual_rows             3938
chunnel_explained                  1421
post_chunnel_residual              2517
horwasp_ballistic_candidates        911
horwasp_mite_residual               786
horwasp_strong_explained            240
horwasp_observed_context_explained    0
post_horwasp_strong_residual       2277
mine_strong_explained                37
post_mine_strong_residual          2240
label_issues                          0
```

Strict mine categories:

```text
normal_mine_hit_nearest_damage  19
web_mine_hit_nearest_damage     18
```

Damage/slowdown hit distribution:

```text
normal: damage_hits=1, slowdown_hits=1  -> 17
normal: damage_hits=2, slowdown_hits=1  ->  1
normal: damage_hits=2, slowdown_hits=2  ->  1
web:    damage_hits=1                   -> 18
```

All mine overlap guards were zero:

```text
mine_and_chunnel              0
mine_and_horwasp_strong       0
mine_horwasp_hulls            0
mine_not_post_horwasp_source  0
```

## Mine/web v5 differential closure

Independent diagnostics over the verified v4 endpoint measured:

```text
web_nearest_delta_match_after_field        18
normal_nearest_delta_multiple_after_field  19
web_nearest_control_no_after_field          0
normal_nearest_control_no_after_field       0
```

The strict production predicates made those web and normal subsets disjoint. The normal v5 build reproduced the prediction exactly:

```text
post_horwasp_strong_residual  2277  unchanged
mine_strong_explained           37
post_mine_strong_residual     2240
```

Therefore the strict mine/web context layer is `DIFF_VERIFIED`.

Repair-bracket-only rows remain outside v5 until repair reconstruction is independently validated.

## Route-equivalent Chunnel differential closure

The pre-fix DB-only v3 audit measured 34 route-equivalent false residuals, all with `chunnel_match_count=2`. The normal v4 build produced exactly the predicted accounting delta:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

Chunnel v4 remains **TESTED + DIFF_VERIFIED** and is not reopened by v5.

## Current test follow-up

The first v5 targeted/full pytest runs had exactly one failure in `tests/test_movement_chunnel_route_equivalent.py`: a stale assertion still hard-coded the shared compiled label schema as v4. All new mine-context tests passed.

That test-only sentinel was updated in commit `3661f038178bf7fae37496ad23be90e08480ea72` to expect v5 while retaining standalone Chunnel schema v2. A final targeted/full pytest rerun is required for a fully green repository record. No corpus rebuild is required because production code and compiled data are unchanged by the test fix.
