# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-26-normal-mine-slowdown-exposure-pending.md`](handoff/2026-08-26-normal-mine-slowdown-exposure-pending.md)

## Current verified schema state

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
```

Raw `/game/loadall` archives remain unchanged. Prepared projection stays privacy-minimal; raw `.trn` evidence is read directly only by diagnostics that need narrowly scoped historical metadata or feature schema.

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
horwasp_strong_explained            240
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

Largest coarse family:

```text
116  warp7-9 <0.5x observed=other same_line_forward
```

## Verified / closed recent mechanics

- damage-limited warp — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict mine/web hit v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Tow / Chunnel — **TESTED + DIFF_VERIFIED**;
- Nu waypoint-distance fuel proration v6 — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- Crystal Web Drain — one end-to-end attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition.

## Rejected post-v6 broad leads

```text
outbound fuel transfer:
  target_short_outbound_fuel_transfer = 0

standard Cloak fuel burn:
  target_short_cloak_mission = 0

Privateer Rob Ship:
  target_short_rob_exposure_candidate = 0
```

### Stellar Cartography speed terrain

The first raw feature inventory was invalid because its local ratio bucket produced 126 rather than the authoritative 116 target rows and because it counted empty lists / zero settings as active features. The refined inventory corrected both issues.

Verified refined population:

```text
target_short_forward_rows = 116
```

Movement-relevant active counts:

```text
blackholes active_turns = 0
blackholes target_active_turns = 0
settings.blackholes active_turns = 0
wormholes active_turns = 0
wormholes target_active_turns = 0
settings.maxwormholes active_turns = 0
```

Nebula/debris state is active on only seven target turns total and is not documented as a generic normal-movement speed limiter. Terrain-speed is rejected as a broad explanation for the current dominant family.

## Active normal-mine slowdown exposure follow-up

Planets.nu documents that normal mine impacts slow ships with hull tech below 7 by 10 light-years per hit when more than 10 light-years remain. Hull tech 7+ is not slowed.

Strict mine/web v5 already covers attributable hit/damage rows. The complementary hypothesis is repair-hidden slowdown:

```text
normal mine hit
  -> 10 ly slowdown per hit on low-tech hull
  -> observed short same-line movement
  -> later repair / snapshot semantics remove visible damage evidence
```

Active diagnostic:

```text
tools/diagnostics/normal_mine_slowdown_exposure_audit.py
```

The first pass is intentionally an upper-bound exposure/geometry audit. It currently does **not** filter historical diplomacy, reconstruct hull tech, infer mine-hit RNG or infer repair. It reports:

```text
normal_mine_route_exposure
normal_mine_multi_field_route_exposure
positive_planned_distance_deficit
deficit_near_10n

target_short_normal_mine_route_exposure
target_short_normal_mine_multi_field_route_exposure
target_short_positive_planned_distance_deficit
target_short_deficit_near_10n
```

Only material overlap between route exposure and `10*N` deficit geometry justifies a second stricter pass.

No schema/cache/accounting change is permitted during this exposure audit.

## Current test state

```text
fuel v6 targeted regression set: 16 passed
full pytest suite:              green
```
