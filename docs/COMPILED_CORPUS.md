# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-25-fuel-proration-v6-runtime-verification.md`](handoff/2026-08-25-fuel-proration-v6-runtime-verification.md)

## Build commands

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
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
movement residual context:         planets-lab.movement-residual-context-game.v2
                                   planets-lab.movement-residual-context-stats.v2
```

Current generated local corpus is still the last verified **L2 v5** build. It has not yet been rebuilt after the v5 -> v6 fuel-proration label change.

Therefore the authoritative runtime-generated endpoint remains:

```text
post_mine_strong_residual = 2226
```

Do not report the expected post-fuel `2220` as runtime verified until the normal v6 L2 build succeeds.

L1 source and generated L1 data are already aligned and unchanged by the v6 work. **Do not rebuild L1 for this migration.**

## Layer boundaries

### L0 — raw archives

`/game/loadall` ZIP files remain unchanged and are the evidence base.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache containing normalized private-perspective state. It is not a portable dataset format.

### L1 — compiled movement

One flat Parquet row corresponds to one movement-readiness transition. Raw topology, owner/hull identity, intent, observed/target geometry, warp-well state and other factual fields remain separate from inferred/effective context.

Current ordered external-context stack:

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

Verified L1 closures include route-equivalent Tow, authoritative storm mode, evidence-scoped sphere movement and strict damage-limited warp.

Game `591478` alone has independently verified effective toroidal period `2170x2170` while raw facts remain `2150x2150`. Never generalize this to `mapwidth+20`.

### L2 — compiled context labels

Source schema is now:

```text
planets-lab.compiled-movement-context-labels.v6
```

Ordered L2 stack:

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
  -> strict documented Nu fuel proration
  -> post_fuel_proration_residual
```

#### Strict mine/web

Categories:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
```

Historical NuHost evidence selects positive nearest-integer mine damage quanta rather than the documentation's literal round-up wording. Repair-bracket-only mine rows remain evidence-only.

Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED** for the strict 37-row subset.

#### Strict fuel proration — source implemented, runtime pending

Module:

```text
src/planets_lab/corpus/movement_fuel_context.py
```

Category:

```text
fuel_proration_waypoint_match
```

New derived label columns:

```text
fuel_proration_category
fuel_proration_explained
post_fuel_proration_residual
```

New final view:

```text
movement_post_fuel_proration_residual
```

The previous post-mine view remains intact as an intermediate control:

```text
movement_post_mine_strong_residual
```

No raw fuel amount, raw mass or computed fuel requirement is exported in the L2 Parquet. Only derived category/flags are retained.

## Strict fuel predicate

The first production-compatible fuel subset requires:

```text
survives Chunnel + Horwasp strong + mine/web strong
non-Horwasp
non-Gravitonic
warp 1..9
waypoint reachable within ordinary warp^2 distance
same owner/hull/ship identity after transition
race / engine / raw mass / positive fuel / damage resolved
damage does not reduce requested warp
raw mass predicts fuel_required > fuel_available > 0
documented Nu waypoint-distance proration
exact Host major/minor observed x/y endpoint
```

Explicitly excluded:

- partial waypoints beyond normal per-turn range;
- zero-fuel movement;
- Gravitonic movement;
- Horwasp hulls;
- damage-limited requested warp;
- affordable-frontier-only matches;
- VGAP3-style proration;
- mandatory next-turn Warp/waypoint/fuel reset checks.

Historical Time Machine saved turns are not treated as immediate post-Host frames for editable orders/cargo fields. Exact Host `x/y` is the movement outcome used for corpus compatibility matching; same immutable identity is a continuity guard.

## Independent fuel differential evidence

### Competing-rule endpoint differential

`tools/diagnostics/fuel_proration_host_differential_audit.py` measured on the current verified post-mine endpoint:

```text
raw_mass_insufficient_for_waypoint= 19
nu_proration_endpoint_exact= 6
frontier_endpoint_exact= 3
vgap3_endpoint_exact= 0
```

Rule signatures:

```text
('-', '-', '-')           13
('nu', '-', '-')           3
('nu', 'frontier', '-')    3
```

The six Nu exact rows span four hulls and three games. Three are discriminating Nu-only matches; three also match the old affordable-frontier projection. Three of the six belong to the 119-row dominant short-forward family.

### Global downstream-stage audit

`tools/diagnostics/fuel_proration_global_stage_audit.py` scanned the full current L1 residual:

```text
l1_non_horwasp_warp1_9_rows= 1334
reachable_waypoint= 1073
same_identity_after= 861
identity_break_after= 212
raw_damage_limited_excluded= 0
formula_ready= 861
zero_required_fuel= 407
zero_fuel_separate_mechanic= 9
raw_mass_sufficient_for_waypoint= 423
raw_mass_insufficient_for_waypoint= 22
nu_proration_endpoint_exact= 6
nu_only_endpoint_exact= 3
```

Critical partition:

```text
NU EXACT BY DOWNSTREAM STAGE:
post_mine_strong_residual 6

NU-ONLY EXACT BY DOWNSTREAM STAGE:
post_mine_strong_residual 3
```

There are zero exact overlaps with verified Chunnel, Horwasp strong or mine/web strong labels. This is why fuel is placed after mine in L2 rather than added to the early L1 stack.

## Cache validity

### L1

Movement partition metadata binds validity to compiled schema, post-compile context schema, prepared-cache schema, game/settings/archive identity and topology facts.

No L1 schema or semantic marker changed for fuel v6. Existing L1 partitions are authoritative and must be reused.

### L2

L2 metadata binds each label partition to:

- `label_schema`;
- `source_movement_schema`;
- prepared-cache schema;
- game/settings/archive identity;
- exact source movement Parquet SHA-256.

The v5 -> v6 label schema change must invalidate every old v5 label partition on a normal L2 build even though L1 bytes are unchanged.

Expected normal v6 build:

```text
compiled_label_cache_hits            0
compiled_label_cache_misses         12
prepared_cache_hits_on_compile      12
prepared_cache_misses_on_compile     0
```

No manual cache deletion is required.

## Last runtime-verified invariants — generated v5

L1:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13970
post_external_residual         3924
damage_limited_warp_match       10
```

Generated L2 v5:

```text
external_residual_rows             3924
chunnel_explained                  1421
post_chunnel_residual              2503
horwasp_ballistic_candidates        911
horwasp_mite_candidates             786
horwasp_mite_strong_explained         0
horwasp_mite_residual               786
horwasp_strong_explained            240
horwasp_observed_context_explained    0
post_horwasp_strong_residual       2263
mine_strong_explained                37
post_mine_strong_residual          2226
label_issues                          0
```

Last verified generic endpoint:

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

Dominant coarse family:

```text
119 warp7-9 <0.5x observed=other same_line_forward
```

## Independent expected v6 accounting

All six strict-compatible exact fuel rows currently survive in `movement_post_mine_strong_residual` and no exact fuel row overlaps an earlier verified L2 stage.

Expected normal v6 label build:

```text
external_residual_rows             3924
chunnel_explained                  1421
post_chunnel_residual              2503
horwasp_strong_explained            240
post_horwasp_strong_residual       2263
mine_strong_explained                37
post_mine_strong_residual          2226
fuel_proration_explained              6
post_fuel_proration_residual       2220
label_issues                          0
```

Expected broad generic differential:

```text
generic_rows             769 -> 763
dominant short-forward   119 -> 116
```

Closed Mite and known Horwasp counts should remain unchanged. Generic hull count must be measured after build rather than guessed.

## Regression/test state

Last verified repository/corpus state had targeted damage/storm/compiled tests (`27 passed`) and full pytest green.

V6 source adds/changes:

```text
src/planets_lab/corpus/movement_fuel_context.py
src/planets_lab/corpus/compiled_movement_labels.py
src/planets_lab/corpus/compiled_movement_labels_corpus_cli.py
tests/test_movement_fuel_context.py
tests/test_compiled_movement_labels.py
tests/test_movement_chunnel_route_equivalent.py
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Runtime verification is pending. Do not mark fuel v6 `TESTED + DIFF_VERIFIED` until targeted/full tests and the normal L2 build reproduce the six-row prediction exactly.

## Closed differentials

### Damage-limited warp

Production reproduced the independent ten-row prediction exactly and changed final residual `2236 -> 2226`. Status: **DOCUMENTED (legacy Nu help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Tow v3

Global differential predicted four rows; production reproduced the exact `+4/-4` accounting delta. Status: **TESTED + DIFF_VERIFIED**.

### Mine/web v5

Independent diagnostics predicted exactly `18` strict web + `19` strict normal-mine rows; production closed exactly 37. Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Chunnel v4

Pre-fix diagnostic predicted 34 false residuals and production reproduced the exact accounting delta. Status: **TESTED + DIFF_VERIFIED**.
