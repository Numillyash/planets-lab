# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` remains the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-25-fuel-proration-host-differential-pending.md`](handoff/2026-08-25-fuel-proration-host-differential-pending.md)

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

## Current verified schema state

Source and generated corpus are aligned on:

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v5
movement residual context:         planets-lab.movement-residual-context-game.v2
                                   planets-lab.movement-residual-context-stats.v2
```

Physical L1 v3 columns are unchanged by the damage-context work. `storm-context.v3` is the semantic cache marker for the ordered post-compile L1 stack.

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

#### Route-equivalent Tow

L1 v3 treats a non-empty set of owner-visible matching Tow towers as route evidence when each match starts colocated with the target and shares its same non-stationary observed destination. Tower identity may remain ambiguous. Status: **TESTED + DIFF_VERIFIED**.

#### Scoped sphere geometry

Game `591478` alone has independently verified effective toroidal period `2170x2170` while raw facts remain `2150x2150`. Never generalize this to `mapwidth+20`.

#### Strict damage-limited warp

Module:

```text
src/planets_lab/corpus/movement_damage_context.py
```

Category:

```text
damage_limited_warp_match
```

Strict predicate:

```text
still unresolved after previous L1 context
non-Horwasp hull
resolved owner/race
same ship identity after transition
requested warp 1..9
visible onboard supplies < 5 KT
raw-damage maximum warp < requested warp
exact Host-major/minor endpoint at effective warp
```

Gravitonic distance and scoped effective sphere topology are respected. Repair-bracket-only cases are excluded. Private damage/race/supply values are not added to exported Parquet columns; only the derived category/flags change.

Status: **DOCUMENTED (legacy Nu help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### L2 — compiled context labels

Current schema:

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

L1 movement partition metadata binds cache validity to:

- `compiled_schema`;
- `storm_context_schema`;
- prepared-cache schema;
- game/settings/archive identity;
- raw topology facts.

L2 metadata binds each label partition to:

- `label_schema`;
- `source_movement_schema`;
- prepared-cache schema;
- game/settings/archive identity;
- exact source movement Parquet SHA-256.

Damage context migration to `storm-context.v3` produced:

```text
L1 normal build:
  compiled_cache_hits                0
  compiled_cache_misses             12
  prepared_cache_hits_on_compile    12
  prepared_cache_misses_on_compile   0
```

L2 normal build produced:

```text
compiled_label_cache_hits           3
compiled_label_cache_misses         9
prepared_cache_hits_on_compile      9
prepared_cache_misses_on_compile    0
```

This is correct. Physical source movement schema remained v3. Three rebuilt L1 partitions were byte-identical because no row in those games changed under the new damage pass, so their exact source Parquet SHA-256 stayed valid and the old L2 labels were safely reused. The other nine source hashes changed and correctly missed.

Do not force L2 cache misses when source bytes and source schema are unchanged. No manual cache deletion should be required.

## Current runtime-verified 12-game invariants

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

L2 over current L1:

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

Current generic final endpoint:

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

Main coarse signatures:

```text
119  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 45  warp7-9 0.5-1.0x observed=other same_line_forward
```

## Damage-limited warp differential closure

Independent pre-build audit measured:

```text
raw_damage_limited                  11
raw_damage_limited_endpoint_exact   10
raw_exact_low_supply                10
raw_not_damage_limited_endpoint_exact_control  0
undamaged_endpoint_exact_control               0
```

The 10 exact rows spanned 9 games, 8 hulls, 6 races and effective warps 1, 3, 4, 5, 6, 7 and 8. Production reproduced exactly the expected 10-row delta:

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

Runtime result:

```text
ACCOUNTING DIFFERENTIAL: EXACT MATCH
```

Post-build damage audit found zero remaining exact production-eligible rows. Generic rebaseline reproduced `779 -> 769` and dominant short-forward `121 -> 119`; measured generic hulls are 76.

## Fuel diagnostics

### Historical affordable-frontier audit

`tools/diagnostics/generic_fuel_limited_residual_audit.py` now defaults to the current final view. Current-endpoint rerun measured:

```text
residual_view= movement_post_mine_strong_residual
generic_non_horwasp_warp1_9_rows= 671

target_short_forward_rows= 119
target_short_gravitonic_excluded= 15
target_short_non_gravitonic= 104
target_short_fuel_geometry_candidate= 97
target_short_same_identity_after= 96
target_short_identity_break_after= 1
target_short_formula_ready= 97

target_short_insufficient_for_regular= 6
target_short_formula_brackets_observed= 5
target_short_affordable_frontier_match= 3
target_short_depleted_after= 22
target_short_strong_fuel_limit_signature= 3
```

Across the wider non-Gravitonic short-same-line population, the historical criterion still reports:

```text
strong_fuel_limit_signature= 7
```

across six hulls and four games.

These seven rows are **correlation evidence only**. The old strongest criterion uses proximity to the maximum affordable whole-light-year frontier, but that is not the documented Planets.nu insufficient-fuel proration rule.

### Documented Nu fuel-proration differential

Planets.nu documents:

```text
actual distance = waypoint distance * fuel available / fuel required
```

and explicitly gives a 60-ly / 12-KT / 11-KT example that travels 55 ly even though 11 KT could otherwise afford 59 ly. The Nu/VGAP3 differences documentation states that VGAP3 instead uses a `warp^2 * fuel / fuel_required` maximum-distance rule.

The repository already implements the documented building blocks:

```text
src/planets_lab/rules/fuel.py
src/planets_lab/rules/proration.py
src/planets_lab/sim/normal_movement.py
```

New exact differential:

```text
tools/diagnostics/fuel_proration_host_differential_audit.py
```

It compares exact Host-major/minor endpoints for:

1. documented Nu waypoint-distance proration;
2. historical affordable-whole-LY frontier;
3. VGAP3-style max-distance ratio.

The first causal pass is intentionally limited to positive-fuel, reachable-waypoint, non-Gravitonic, same-identity rows. Partial waypoints, zero-fuel movement and Gravitonic cases are excluded.

The strongest Nu evidence additionally requires the documented out-of-fuel post-state:

```text
fuel_after = 0
warp_after = 0
waypoint_after = observed current position
```

No production fuel category exists yet. Promotion requires exact endpoint discrimination plus post-reset and cross-game support.

## Closed differentials

### Route-equivalent Tow v3

Global pre-build audit found four multiple visible Tow matches and zero missed single matches. Production reproduced the exact `+4/-4` accounting delta; post-fix Tow controls are zero. Status: **TESTED + DIFF_VERIFIED**.

### Mine/web v5

Independent diagnostics predicted exactly `18` strict web + `19` strict normal-mine rows. Production closed exactly 37 rows. Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Chunnel v4

Pre-fix audit predicted 34 false residuals and production reproduced the exact Chunnel accounting delta. Status: **TESTED + DIFF_VERIFIED**.

## Current test state

```text
targeted damage/storm/compiled regression set: 27 passed
full pytest suite:                         green
```

Repository source, schemas/semantic markers and generated corpus are aligned at the verified `2226` endpoint. The new fuel-proration differential is diagnostic-only and does not alter compiled schemas or accounting.
