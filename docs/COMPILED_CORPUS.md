# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-25-damage-limited-warp-runtime-verification.md`](handoff/2026-08-25-damage-limited-warp-runtime-verification.md)

## Build

L1 movement:

```bash
docker compose run --rm -T lab \
  python -u -m planets_lab.corpus.compiled_movement_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --output-dir validation/corpus/compiled/v1
```

L2 context labels:

```bash
docker compose run --rm -T lab \
  python -u -m planets_lab.corpus.compiled_movement_labels_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --compiled-dir validation/corpus/compiled/v1
```

Generated `validation/corpus/compiled/` is ignored by Git.

## Source state vs generated-data state

Current source on `main`:

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v5
movement residual context:         planets-lab.movement-residual-context-game.v2
                                   planets-lab.movement-residual-context-stats.v2
```

The generated corpus has **not yet** been rebuilt after the post-compile context marker v2 -> v3 change. Therefore the authoritative runtime-verified generated data is still the prior L1 v3 + context-v2 + L2-v5 endpoint with final residual `2236`.

Do not report the expected damage-limited counts as verified before the normal L1/L2 builds complete.

## Layer boundaries

### L0 — raw archives

`/game/loadall` ZIP files are retained unchanged and remain the evidence base.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache containing normalized private-perspective state. It is not a portable dataset format.

### L1 — compiled movement

One flat Parquet row corresponds to one movement-readiness transition. Important fields include factual topology, owner/hull identity, intent, observed/target geometry, warp-well state, gravitonic context, baseline category and external-context category.

Raw topology columns remain factual. Evidence-scoped effective topology never overwrites them.

The L1 external-context stack is ordered and monotonic. Current source semantics:

```text
baseline ordinary movement
  -> owner-visible Tow
  -> Gravitonic movement
  -> initial storm reconstruction
  -> authoritative classic/cloudy storm mode
  -> scoped effective sphere geometry
  -> strict damage-limited warp context
```

Existing explanatory categories are never stolen by later passes.

### Route-equivalent Tow

L1 v3 treats a non-empty set of owner-visible matching Tow towers as movement-route evidence when every match starts with the target and shares its same non-stationary destination. Tower identity may remain ambiguous. This is **TESTED + DIFF_VERIFIED**.

### Scoped sphere geometry

Game `591478` alone has an independently verified effective toroidal period `2170x2170` while raw facts remain `2150x2150`. Never generalize this to `mapwidth+20`.

### Strict damage-limited warp context — source implemented, runtime pending

Module:

```text
src/planets_lab/corpus/movement_damage_context.py
```

Category:

```text
damage_limited_warp_match
```

The strict predicate requires:

```text
still unresolved after previous L1 context
non-Horwasp hull
resolved owner/race
same ship identity after transition
requested warp 1..9
visible onboard supplies < 5 KT
raw-damage max warp < requested warp
exact Host-major/minor endpoint at effective warp
```

Gravitonic distance and scoped effective sphere topology are respected. Repair-bracket-only cases are excluded. No private damage/race/supply values are added to exported Parquet columns; only the derived external-context category/flags change.

The historical symbol `MOVEMENT_STORM_CONTEXT_SCHEMA` is retained because cache metadata already uses `storm_context_schema`. Version 3 now denotes the ordered post-compile stack:

```text
authoritative storm mode
  -> scoped effective sphere geometry
  -> strict damage-limited warp
```

Physical L1 remains `planets-lab.compiled-movement.v3`.

### L2 — compiled context labels

L2 remains:

```text
planets-lab.compiled-movement-context-labels.v5
```

Ordered label stack:

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
```

Strict mine categories:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
```

Historical NuHost evidence selects positive nearest-integer mine damage quanta rather than the documentation's literal round-up wording. Repair-bracket-only mine rows remain evidence-only.

## Cache validity

Movement partition metadata binds cache validity to:

- `compiled_schema`;
- `storm_context_schema`;
- prepared-cache schema;
- game/settings/archive identity;
- raw topology facts.

L2 metadata additionally binds each label partition to the current source movement schema and exact source Parquet SHA-256.

Therefore the pending context-v2 -> v3 semantic marker change should produce:

```text
L1 normal build:
  compiled_cache_hits                0
  compiled_cache_misses             12
  prepared_cache_hits_on_compile    12
  prepared_cache_misses_on_compile   0

following L2 normal build:
  compiled_label_cache_hits           0
  compiled_label_cache_misses        12
  prepared_cache_hits_on_compile     12
  prepared_cache_misses_on_compile    0
```

No manual cache deletion should be required.

## Last runtime-verified 12-game invariants

Current generated L1:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13960
post_external_residual         3934
```

Current generated L2:

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

Verified generic final endpoint:

```text
final_residual_rows  2236
generic_rows          779
generic_games          12
generic_hulls          78
```

## Damage-limited warp independent differential

`tools/diagnostics/damage_limited_warp_residual_audit.py` measured on the verified current endpoint:

```text
generic_non_horwasp_warp1_9_rows  681
target_short_forward_rows          121
raw_damage_limited                  11
raw_damage_limited_endpoint_exact   10
raw_exact_low_supply                10
raw_not_damage_limited_endpoint_exact_control 0
undamaged_endpoint_exact_control              0
```

The 10 exact rows span `9` games, `8` hulls and `6` races. Effective warp values span 1, 3, 4, 5, 6, 7 and 8. Only two exact rows belong to the dominant 121-row short-forward family.

Because all 10 exact rows currently survive to `movement_post_mine_strong_residual`, the independent expected production accounting is:

```text
external_context_explained        13960 -> 13970
post_external_residual             3934 ->  3924
chunnel_explained                  1421 ->  1421
post_chunnel_residual              2513 ->  2503
horwasp_strong_explained            240 ->   240
post_horwasp_strong_residual       2273 ->  2263
mine_strong_explained                37 ->    37
post_mine_strong_residual          2236 ->  2226
label_issues                          0 ->     0
```

Expected generic rows: `779 -> 769`. Expected dominant short-forward family: `121 -> 119`. Generic hull count must be measured after rebuild rather than guessed.

These values are **pre-build predictions**, not runtime invariants yet.

## Closed differentials

### Route-equivalent Tow v3

Global pre-build audit found four multiple visible Tow matches and zero missed single matches. The normal L1/L2 rebuild reproduced the exact predicted `+4/-4` accounting change; post-fix Tow controls are zero. Status: **TESTED + DIFF_VERIFIED**.

### Mine/web v5

Independent diagnostics predicted exactly `18` strict web + `19` strict normal-mine rows. Production closed exactly 37 rows. Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Chunnel v4

Pre-fix audit predicted 34 false residuals and production reproduced the exact predicted Chunnel accounting delta. Status: **TESTED + DIFF_VERIFIED**.

## Current test state

Last fully verified repository state had targeted Tow/compiled/cache tests and the full pytest suite green.

Current source adds:

```text
src/planets_lab/corpus/movement_damage_context.py
tests/test_movement_damage_context.py
```

and post-compile context semantic marker v3. Targeted/full pytest plus normal L1/L2 rebuild verification are pending.
