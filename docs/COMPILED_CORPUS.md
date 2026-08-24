# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is a deterministic local derivative and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-24-route-equivalent-tow-runtime-verification.md`](handoff/2026-08-24-route-equivalent-tow-runtime-verification.md)

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

## State terminology

Keep code/schema state separate from runtime-verified generated data.

At the current `main`:

```text
implemented L1 schema:       planets-lab.compiled-movement.v3
implemented L2 label schema: planets-lab.compiled-movement-context-labels.v5
```

However, until the route-equivalent Tow rebuild is executed, the **last runtime-verified generated corpus** remains the earlier L1 v2 + L2 v5 dataset whose final residual is `2240`.

Do not report the pending v3 accounting as verified before the normal L1/L2 rebuild and differential comparison complete.

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

One flat Parquet row corresponds to one movement-readiness transition. Readiness/facts remain separate from mechanic labels.

Implemented physical/row schema on `main`:

```text
planets-lab.compiled-movement.v3
```

V3 has the same physical columns as v2. The bump is semantic and exists to invalidate stale movement partitions after correcting route-equivalent visible Tow handling.

The Tow detector now treats any non-empty set of owner-visible matching Tow towers as movement-route evidence when every counted tower:

- targets the same candidate ship with Tow;
- is colocated with that target before movement;
- shares the target's same non-stationary observed destination.

Multiple matching towers preserve identity ambiguity. The detector stores the complete tuple of matching tower IDs internally and never chooses an arbitrary Tow winner. Only the derived fact that the target movement is Tow-supported is exported into L1.

Standalone movement-residual-context schemas are now:

```text
planets-lab.movement-residual-context-game.v2
planets-lab.movement-residual-context-stats.v2
```

Current post-compile external-context semantic schema remains:

```text
planets-lab.compiled-movement-storm-context.v2
```

The historical symbol name is retained because partition metadata already uses `storm_context_schema`. Version 2 represents the ordered post-compile context stack: authoritative classic/cloudy storm handling followed by evidence-scoped effective sphere geometry on still-unresolved rows.

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

Classic/cloudy ion-storm selection is driven offline from manifest `settings.nuionstorms`. The compiler fails closed if that setting is missing or not boolean.

Private text orders are not exported. Raw fields such as friendly code may be used locally to derive a mechanical category, but the text itself is not a compiled column.

### L2 — compiled context labels

Chunnel, Horwasp and strict mine/web classification is stored separately under `labels/movement_context/`. One label row corresponds to one L1 row where `post_external_residual = true`.

Implemented and runtime-verified label schema:

```text
planets-lab.compiled-movement-context-labels.v5
```

V4 changed Chunnel semantics so multiple route-equivalent observed Chunnel events no longer become false residuals merely because event identity/role is ambiguous.

V5 adds a fail-closed mine/web layer after Horwasp strong labels. It uses only strict field-backed corpus evidence.

Chunnel role categories include:

```text
initiator
passenger_same_owner
passenger_other_owner
route_equivalent_multiple_roles
```

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

Therefore the L1 v2 -> v3 semantic bump automatically invalidates old v5 labels after the movement partitions are rebuilt, even though the label predicates/schema themselves remain v5.

Do not require users to manually delete caches to make a semantic fix take effect.

Expected cache behavior for the pending Tow migration:

```text
L1 normal build:
  compiled cache hits              0 / 12
  prepared cache hits             12 / 12

following L2 normal build:
  compiled-label cache hits        0 / 12
  prepared cache hits             12 / 12
```

The exact CLI field names are recorded from runtime; these ratios are the semantic invariant.

## Last runtime-verified 12-game invariants — pre-Tow v3 rebuild

These are the authoritative generated-data counts until the pending route-equivalent Tow rebuild completes.

Movement L1 (verified v2 data):

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13956
post_external_residual         3938
```

Context labels (verified v5 data over that L1):

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

All mine overlap guards were zero.

## Verified post-v5 generic rebaseline

The broad clustering against `movement_post_mine_strong_residual` produced:

```text
final_residual_rows       2240
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               783
generic_games               12
generic_hulls               79
```

Largest surviving coarse families included:

```text
121  warp7-9 <0.5x     observed=other same_line_forward
 97  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 48  warp7-9 0.5-1.0x observed=other same_line_forward
 46  warp7-9 >3.0x     observed=other oblique
```

## Route-equivalent Tow differential — pending runtime closure

Focused target-origin audit found:

```text
candidate_rows                              226
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4
```

Each of those four rows has exactly two owner-visible Tow towers sharing the target's origin and observed destination. They span four games and four hulls and remain in the old final residual.

Those four rows establish the defect, but they are only a lower bound because the focused audit filtered to target-at-origin candidates.

Before rebuilding L1, run:

```text
tools/diagnostics/tow_route_equivalent_global_differential_audit.py
```

It scans all old `movement_labeled_residual` rows and partitions every multiple visible Tow match by current downstream stage. Its output defines the expected accounting delta.

Critical negative control:

```text
single_visible_matching_tower = 0
```

If the global total is exactly the four known final-residual rows, the conditional expected endpoint is:

```text
external_context_explained  13960
post_external_residual       3934
chunnel_explained            1421
post_chunnel_residual        2513
horwasp_strong_explained      240
post_horwasp_strong_residual 2273
mine_strong_explained          37
post_mine_strong_residual     2236
```

Do not promote those numbers to runtime invariants until the global audit and normal L1/L2 builds reproduce them.

## Previously closed differentials

### Mine/web v5

Independent diagnostics predicted exactly `18` strict web + `19` strict normal-mine rows. Production closed exactly `37` rows:

```text
post_horwasp_strong_residual  2277
mine_strong_explained           37
post_mine_strong_residual     2240
```

Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Chunnel v4

Pre-fix audit predicted 34 false residuals. Production reproduced exactly:

```text
chunnel_explained             1387 -> 1421
post_chunnel_residual         2551 -> 2517
horwasp_strong_explained       240 ->  240
post_horwasp_strong_residual  2311 -> 2277
```

Status: **TESTED + DIFF_VERIFIED**.

## Current test state

Before the Tow v3 source change, the repository-wide test suite was fully green after the mine-v5 schema-sentinel correction.

The new Tow regression and compiled-movement v3 change are now implemented but still require the targeted/full pytest run recorded in the current handoff before the new repository state is marked tested.
