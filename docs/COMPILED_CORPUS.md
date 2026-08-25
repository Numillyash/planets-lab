# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-26-rob-ship-exposure-pending.md`](handoff/2026-08-26-rob-ship-exposure-pending.md)

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

`/game/loadall` ZIP files remain unchanged and are the evidence base. Raw `.trn` members contain richer historical metadata than the privacy-safe prepared projection; diagnostics needing game-era/diplomacy provenance read only narrowly required raw fields.

### Prepared cache

`validation/corpus/cache/prepared-v1/*.pickle` is a trusted local performance cache. `mechanics_projection()` intentionally reduces `game`, players and settings to mechanics-safe subsets.

### L1 — compiled movement

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

Strict categories:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
fuel_proration_waypoint_match
```

## Cache validity

L1 partition validity binds schema/context marker, prepared-cache schema, archive/settings identity and topology inputs. L2 binds label schema, source movement schema, prepared-cache schema, archive/settings identity and exact source movement Parquet SHA-256.

Fuel v6 changed the L2 schema and correctly produced:

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

L2:

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

Fuel-proration overlap guards remain zero.

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

Independent diagnostics predicted 18 strict web + 19 strict normal-mine rows; production closed exactly 37. Status: **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

### Route-equivalent Tow / Chunnel

Both multiplicity fixes reproduced independent pre-build differentials exactly. Status: **TESTED + DIFF_VERIFIED**.

### Nu fuel proration v6

```text
Nu waypoint-proration exact   6
affordable-frontier exact     3
VGAP3-style exact             0
Nu-only exact                 3
```

All six were isolated to the prior `post_mine_strong_residual`; production reproduced `2226 -> 2220`. Status: **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## Web Drain evidence-only closure

One Crystal Web Drain row (`game 360690`, turn 44, hull 53) is attributable end-to-end, including Crystal ownership, pre-2021 game era, exact relation pair, lack of diplomacy immunity, 25 KT fuel/mass reduction, and exact Nu-prorated endpoint. Status: **DOCUMENTED + CORPUS_OBSERVED strong evidence-only**; no production label because support remains one game/hull.

## Rejected post-v6 leads

### Outbound fuel transfer

```text
outbound_fuel_transfer = 2
transfer_target_current_visible = 0
raw_sufficient_to_transfer_insufficient = 0
transfer_causal_exact = 0
target_short_outbound_fuel_transfer = 0
```

### Standard Cloak fuel burn

```text
target_short_forward_rows = 116
target_short_cloak_capable_hull = 6
target_short_standard_cloak_hull = 2
target_short_cloak_mission = 0
target_short_standard_cloak_fuel_burn_candidate = 0
target_short_cloak_causal_exact = 0
```

Globally, the eight relevant mission-10 residual rows were on hulls without static cloak capability. No standard Cloak fuel-burn candidate survived.

## Active Rob Ship exposure follow-up

Planets.nu documents Privateer `Rob Ship` in the early Mission-9 Host block before all movement. The first pass intentionally measures exposure only, before implementing exact robber/target ordering, diplomacy immunity, Host-phase cloak state, Protofield interaction or the 1% failure chance.

Active diagnostic:

```text
tools/diagnostics/rob_ship_exposure_audit.py
```

A `rob_exposure_candidate` requires a co-located owner-record Privateer ship with mission 9, beams, positive fuel and free fuel-tank capacity. Important counters:

```text
privateer_mission9_at_origin
rob_exposure_candidate
rob_exposure_static_noncloak_victim
rob_exposure_positive_victim_fuel

target_short_privateer_mission9_at_origin
target_short_rob_exposure_candidate
target_short_rob_exposure_static_noncloak_victim
```

If target-family exposure is zero, Rob Ship is rejected immediately. If nonzero, a second-pass exact robbery-order/diplomacy audit is justified. No schema/accounting change is permitted during the exposure pass.

## Current test state

```text
fuel v6 targeted regression set: 16 passed
full pytest suite:              green
```
