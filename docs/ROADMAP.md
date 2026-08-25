# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-26-web-drain-evidence-closed-transfer-followup.md`](handoff/2026-08-26-web-drain-evidence-closed-transfer-followup.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

## Current focus

Active milestone: **M5 — historical NuHost corpus + compatibility mining**.

Current runtime-verified 12-game movement accounting:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13970
post_external_residual              3924
chunnel_explained                   1421
post_chunnel_residual               2503
horwasp_strong_explained             240
post_horwasp_strong_residual        2263
mine_strong_explained                 37
post_mine_strong_residual           2226
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0
```

Current schemas:

```text
manifest:                  planets-lab.corpus-game.v2
prepared cache:            planets-lab.prepared-game-cache.v1
L1 movement:               planets-lab.compiled-movement.v3
L1 context semantics:      planets-lab.compiled-movement-storm-context.v3
L2 context labels:         planets-lab.compiled-movement-context-labels.v6
residual context:          planets-lab.movement-residual-context-game.v2
                           planets-lab.movement-residual-context-stats.v2
standalone Chunnel:        planets-lab.movement-chunnel-context-game.v2
                           planets-lab.movement-chunnel-context-stats.v2
```

## Verified movement closures

- ordinary movement / Host major-minor geometry;
- warp-well classifier ordering — `TESTED + DIFF_VERIFIED`;
- route-equivalent owner-visible Tow — `TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multiplicity — `TESTED + DIFF_VERIFIED`;
- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- Horwasp ballistic strong context with scoped 2170 topology;
- Red Mite tracking/fallback — research closed absent new evidence;
- strict mine/web interruption v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED (legacy Nu page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict Nu waypoint-distance fuel proration v6 — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

Fuel v6 independently predicted six exact Nu-proration rows and production reproduced exactly:

```text
post_mine_strong_residual       2226
fuel_proration_explained           6
post_fuel_proration_residual    2220
```

## Current generic residual landscape

Broad clustering against `movement_post_fuel_proration_residual`:

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

## Closed evidence-only lead — Crystal Web Drain

The Crystal-owner-aware post-v6 differential found one exact causal-compatible Web Drain case. The exact historical relation-pair / era audit then established:

```text
game 360690 / turn 44 / hull 53
datecreated = 2020-03-03
iscustom = false
relation target->Crystal = -1
relation Crystal->target = -1
era = pre_2021_classic
web_diplomacy_immune = false
web_drain_allowed = true
exact_case_diplomacy_guard = PASSED
```

The endpoint matches only when the documented 25 KT Web Drain is removed from both available fuel and movement mass before Nu waypoint-distance proration.

Status: **DOCUMENTED + CORPUS_OBSERVED strong evidence case; evidence-only, not production-promoted.**

Reason: only one independent game / hull exact case. Do not overfit a production label to it.

## Active investigation — outbound fuel transfer before movement

Planets.nu Host order places own cargo updates and ship-to-foreign-ship transfers before mass check and normal movement. Historical raw ship records expose submitted fields:

```text
transferneutronium
transfertargetid
transfertargettype
```

A submitted outbound fuel transfer can therefore lower both available fuel and movement mass before Move Most and potentially feed the already verified Nu waypoint-proration rule.

Active diagnostic:

```text
tools/diagnostics/outbound_fuel_transfer_proration_audit.py
```

It runs on `movement_post_fuel_proration_residual` and must preserve:

```text
target_short_forward_rows = 116
```

The first pass is attribution-oriented rather than production-oriented. It requires the submitted transfer target to be current-visible and co-located in the sender perspective, reports target-type distribution before assigning numeric semantics, and separately marks receiver fuel-tank capacity as confirmed versus unresolved.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check and run `outbound_fuel_transfer_proration_audit.py`;
3. require `target_short_forward_rows = 116`;
4. inspect `outbound_fuel_transfer` and target-type distribution;
5. inspect current-visible / co-located target coverage;
6. inspect `raw_sufficient_to_transfer_insufficient`;
7. compare `transfer_fuel_only_endpoint_exact` vs `transfer_fuel_mass_endpoint_exact`;
8. treat `transfer_strict_confirmed_exact` as the strongest first-pass evidence subset;
9. do not change production schemas/accounting from a one-off match;
10. keep Web Drain evidence-only and closed absent new independent evidence.

## Deprioritized / closed leads

- old affordable-whole-LY fuel frontier is correlation evidence only; the Nu rule is waypoint-distance proration;
- multi-waypoint queue did not explain the old hull-79 cluster;
- hidden/private-FC Chunnel discovery added no coverage;
- owner-visible Intercept is already excluded from Move Most residuals;
- repair-bracket mine and damage rows remain evidence-only;
- target-origin visible non-Tow co-movement remains evidence only;
- do not generalize game `591478`'s 2170 period;
- do not reopen Red Mite without new evidence;
- hull count alone is not a mechanic identifier.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented for movement subset.
- **M2 economy/planetary Host:** in progress, not current priority.
- **M3 warfare:** partial.
- **M4 race mechanics:** partial.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active through movement differentials.
- **M6 training/AI:** future.

## Working order

Unless new evidence changes priorities:

1. run the outbound fuel-transfer differential;
2. promote nothing unless an attributable cross-game/cross-hull subset survives strict controls;
3. otherwise return to the post-v6 `116` short-forward family and split it by the next generic documented pre-movement mechanism;
4. keep all verified intermediate accounting layers immutable as regression controls.
