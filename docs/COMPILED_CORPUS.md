# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-25-web-drain-crystal-owner-followup.md`](handoff/2026-08-25-web-drain-crystal-owner-followup.md)

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

## Current verified schema state

Source and generated corpus are aligned on:

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
movement residual context:         planets-lab.movement-residual-context-game.v2
                                   planets-lab.movement-residual-context-stats.v2
standalone Chunnel:                planets-lab.movement-chunnel-context-game.v2
                                   planets-lab.movement-chunnel-context-stats.v2
```

## Layer boundaries

### L0 — raw archives

`/game/loadall` ZIP files remain unchanged and are the evidence base.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache containing normalized private-perspective state. It is not a portable dataset format.

### L1 — compiled movement

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

### L2 — compiled context labels

Current schema:

```text
planets-lab.compiled-movement-context-labels.v6
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
  -> strict Nu fuel-proration
  -> post_fuel_proration_residual
```

Strict categories include:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
fuel_proration_waypoint_match
```

Raw/private state used to derive those labels remains local; exported label rows contain only derived categories/flags and movement keys.

## Cache validity

L1 partition metadata binds validity to compiled schema, post-compile context marker, prepared-cache schema, game/settings/archive identity and topology inputs.

L2 partition metadata binds validity to:

- `label_schema`;
- `source_movement_schema`;
- prepared-cache schema;
- game/settings/archive identity;
- exact source movement Parquet SHA-256.

Fuel v6 changed the L2 label schema itself, so the normal v6 build correctly produced:

```text
compiled_label_cache_hits            0
compiled_label_cache_misses          12
prepared_cache_hits_on_compile       12
prepared_cache_misses_on_compile      0
```

No L1 rebuild was required.

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
fuel_proration_explained              6
post_fuel_proration_residual       2220
label_issues                          0
```

Fuel-proration overlap guards are all zero:

```text
fuel_and_chunnel             0
fuel_and_horwasp_strong      0
fuel_and_mine_strong         0
fuel_not_post_mine_source    0
```

Runtime accounting matched the independent six-row pre-build prediction exactly.

## Current generic final endpoint

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest coarse families:

```text
116  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 43  warp7-9 0.5-1.0x observed=other same_line_forward
```

## Verified recent differentials

### Damage-limited warp

Independent audit predicted 10 strict exact rows; production reproduced the exact 10-row L1/downstream delta. Status: **DOCUMENTED (legacy page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Mine/web hit v5

Independent diagnostics predicted 18 strict web + 19 strict normal-mine rows; production closed exactly 37. Historical NuHost evidence selects positive nearest-integer mine damage quanta over the documentation's literal round-up wording. Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Tow / Chunnel

Both multiplicity fixes reproduced their independent pre-build differentials exactly. Status: **TESTED + DIFF_VERIFIED**.

### Nu fuel proration v6

Competing-rule differential measured:

```text
Nu waypoint-proration exact   6
affordable-frontier exact     3
VGAP3-style exact             0
Nu-only exact                 3
```

A global stage audit found all six only in `post_mine_strong_residual`. L2 v6 then reproduced exactly six `fuel_proration_waypoint_match` rows and `2226 -> 2220`. Status: **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## Active Web Drain follow-up

The first post-v6 broad Web Drain diagnostic found:

```text
raw_proration_exact_control= 0
raw_sufficient_to_web_insufficient= 4
web_drain_fuel_only_endpoint_exact= 0
web_drain_fuel_mass_endpoint_exact= 1
web_drain_causal_exact= 1
synthetic_25_no_web_exact_control= 0
```

The one exact row lies in the 116-row dominant short-forward family and matches only when the drained 25 KT is removed from both available fuel and movement mass.

This remains evidence-only because the first pass counted every enemy web field. Current Planets.nu documentation states that only web minefields owned by a Crystal player produce the 25 KT/field Web Drain, that drain is defined against the post-decay circle, and that current Standard Full Alliance can matter.

Active diagnostic:

```text
tools/diagnostics/web_drain_crystal_owner_followup_audit.py
```

It requires Crystal owner race, treats non-Crystal-owned web fields as a control, and reports all raw-sufficient -> Crystal-web-insufficient candidates. No schema/accounting change is permitted until that follow-up and diplomacy compatibility are resolved.

## Current test state

```text
fuel v6 targeted regression set: 16 passed
full pytest suite:              green
```
