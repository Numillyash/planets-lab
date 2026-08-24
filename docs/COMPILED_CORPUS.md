# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is a deterministic local derivative and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-24-route-equivalent-tow-verified.md`](handoff/2026-08-24-route-equivalent-tow-verified.md)

## Build

Build/refresh L1 movement data with:

```bash
docker compose run --rm -T lab \
  python -u -m planets_lab.corpus.compiled_movement_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --output-dir validation/corpus/compiled/v1
```

Build/refresh L2 context labels with:

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

## Current verified schema state

Source and generated corpus are now aligned on:

```text
L1 movement:                 planets-lab.compiled-movement.v3
L2 context labels:           planets-lab.compiled-movement-context-labels.v5
prepared cache:              planets-lab.prepared-game-cache.v1
movement residual context:   planets-lab.movement-residual-context-game.v2
                             planets-lab.movement-residual-context-stats.v2
```

The L1 v3 schema has the same physical columns as v2. The version bump is a semantic cache invalidation marker for route-equivalent visible Tow handling.

## Layer boundaries

### L0 — raw archives

`/game/loadall` ZIP files are retained unchanged. They are the evidence base used to rebuild every downstream dataset after parser, reconstruction or rules changes.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache. It may contain normalized private-perspective state and large Python object graphs. It is not a portable dataset format.

### L1 — compiled movement

One flat Parquet row corresponds to one movement-readiness transition. Readiness/facts remain separate from mechanic labels.

Current schema:

```text
planets-lab.compiled-movement.v3
```

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

For historical game `591478`, production sphere context requires exact game id, `sphere=true`, stable raw topology and raw dimensions exactly `2150x2150` before using the independently validated effective `2170x2170` toroidal period. This is not a global `mapwidth+20` rule.

Classic/cloudy ion-storm selection is driven offline from manifest `settings.nuionstorms`. The compiler fails closed if that setting is missing or not boolean.

Private text orders are not exported. Raw fields such as friendly code may be used locally to derive a mechanical category, but the text itself is not a compiled column.

### Route-equivalent Tow semantics in v3

The L1 Tow detector treats a target movement as Tow-supported whenever at least one owner-visible tower satisfies all of:

- Tow mission targets the candidate ship;
- tower and target are colocated before movement;
- tower and target share the same non-stationary observed destination.

If multiple towers satisfy the same route, movement is still explained while tower identity remains ambiguous. Production does not choose an arbitrary winning tower.

The semantic regression is covered in both standalone residual-context evaluation and compiled L1 movement tests.

### L2 — compiled context labels

Chunnel, Horwasp and strict mine/web classification is stored separately under `labels/movement_context/`. One label row corresponds to one L1 row where `post_external_residual = true`.

Current schema:

```text
planets-lab.compiled-movement-context-labels.v5
```

V4 changed Chunnel semantics so multiple route-equivalent observed Chunnel events no longer become false residuals merely because event identity/role is ambiguous.

V5 adds a fail-closed mine/web layer after Horwasp strong labels using strict field-backed corpus evidence.

Strict mine categories:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
```

Historical NuHost corpus evidence selects positive nearest-integer damage quanta:

```text
web:    round_half_up(1000 / (hull_mass + 1))
normal: round_half_up(10000 / (hull_mass + 1))
```

Planets.nu documentation describes mine damage as rounded up. The compatibility layer keeps the empirical NuHost behavior explicit rather than silently rewriting the documentation claim.

Important label fields include:

- `chunnel_category`, `chunnel_match_count`, `chunnel_explained`, `post_chunnel_residual`;
- `horwasp_candidate_kind`, `horwasp_category`;
- `horwasp_strong_explained`, `horwasp_observed_context_explained`;
- `post_horwasp_strong_residual`;
- `mine_category`, `mine_damage_hits`, `mine_slowdown_hits`;
- `mine_strong_explained`, `post_mine_strong_residual`.

No minefield IDs, owners, coordinates or friendly codes are exported by L2.

Weak observed-context Horwasp matches remain evidence only. Repair-bracket-only mine candidates remain evidence only and are not promoted by v5.

## Label layer order

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
```

The pre-mine Horwasp residual remains materialized as a DuckDB view for differential checks.

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

The catalog contains views over Parquet rather than a second copy of transition/label tables.

## Cache validity

Movement partition `_meta.json` records identity/provenance including:

- compiled movement schema;
- prepared-cache schema;
- post-compile semantic markers such as `storm_context_schema`;
- game ID and settings hash;
- source archive SHA-256;
- raw map-topology facts;
- row/accounting counts;
- Parquet size.

Context-label metadata additionally binds each label partition to:

- `label_schema`;
- `source_movement_schema`;
- exact source movement Parquet SHA-256;
- source archive SHA-256;
- prepared-cache schema.

The verified L1 v2 -> v3 semantic migration produced:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

The following unchanged-L2-v5 build correctly invalidated all stale labels from the changed L1 source schema/hash:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

Do not require users to manually delete caches to make semantic fixes take effect.

## Current runtime-verified 12-game invariants

Movement L1 v3:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13960
post_external_residual         3934
```

Context labels v5 over L1 v3:

```text
external_residual_rows             3934
chunnel_explained                  1421
post_chunnel_residual              2513
horwasp_ballistic_candidates        911
horwasp_mite_candidates             786
horwasp_mite_strong_explained         0
horwasp_mite_residual               786
horwasp_strong_explained            240
horwasp_observed_context_explained    0
post_horwasp_strong_residual       2273
mine_strong_explained                37
post_mine_strong_residual          2236
label_issues                          0
```

Strict mine categories remain:

```text
normal_mine_hit_nearest_damage  19
web_mine_hit_nearest_damage     18
```

## Route-equivalent Tow v3 differential closure

Global pre-build audit against all old `3938` external residual rows measured:

```text
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4

multiple-match downstream stage:
post_mine_strong_residual 4
```

Therefore the independently predicted delta was:

```text
external_context_explained       13956 -> 13960
post_external_residual            3938 ->  3934
chunnel_explained                 1421 ->  1421
post_chunnel_residual             2517 ->  2513
horwasp_strong_explained           240 ->   240
post_horwasp_strong_residual      2277 ->  2273
mine_strong_explained               37 ->    37
post_mine_strong_residual         2240 ->  2236
```

The normal L1/L2 rebuild reproduced every count exactly with zero delta:

```text
ACCOUNTING DIFFERENTIAL: EXACT MATCH
```

Post-fix global audit then measured:

```text
external_residual_rows= 3934
any_visible_matching_tower= 0
single_visible_matching_tower= 0
route_equivalent_multiple_visible_towers= 0
```

Status: **TESTED + DIFF_VERIFIED**.

## Previously closed differentials

### Mine/web v5

Independent diagnostics predicted exactly `18` strict web + `19` strict normal-mine rows. Production closed exactly `37` rows. Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Chunnel v4

Pre-fix audit predicted 34 false residuals and production reproduced the exact predicted Chunnel accounting delta. Status: **TESTED + DIFF_VERIFIED**.

## Generic residual rebaseline status

The previous generic clustering is now historical because it was measured before the Tow v3 fix:

```text
final_residual_rows       2240
generic_rows               783
generic_hulls               79
```

The current final endpoint is `2236` rows. Rerun:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

against `movement_post_mine_strong_residual` before choosing the next mechanic family.

## Current test state

For the Tow v3 migration:

```text
targeted regression set: 26 passed
full pytest suite:        green
```

Repository source, schemas and generated corpus are aligned and clean at the verified endpoint.
