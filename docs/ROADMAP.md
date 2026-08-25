# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-26-cloak-fuel-proration-pending.md`](handoff/2026-08-26-cloak-fuel-proration-pending.md).

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

Fuel v6 independently predicted six exact Nu-proration rows. Production L2 v6 reproduced exactly:

```text
post_mine_strong_residual       2226
fuel_proration_explained           6
post_fuel_proration_residual    2220
```

All Chunnel/Horwasp/mine overlap guards were zero. The v5 -> v6 label-schema bump produced 0/12 L2 cache hits and 12/12 prepared-cache hits. Targeted tests and the full pytest suite were green.

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

One post-v6 transition is attributable end-to-end to Crystal Web Drain feeding Nu fuel proration:

```text
game 360690 / turn 44 / hull 53
one Crystal-owned web
no historical diplomacy immunity
fuel 55 -> 30
movement mass 1274 -> 1249
raw required 45
post-drain required 44
exact Nu-prorated endpoint
```

The keyed raw `.trn` relation-pair / era audit found:

```text
era = pre_2021_classic
relationfrom (Crystal -> target) = -1
web_diplomacy_immune = false
web_drain_allowed = true
exact_case_diplomacy_guard = PASSED
```

Status: **DOCUMENTED + CORPUS_OBSERVED strong evidence; evidence-only**. No production label because support remains one independent game / hull.

## Rejected lead — outbound fuel transfer

Post-v6 runtime audit found only two outbound `transferneutronium` rows globally and none inside the dominant 116-row family:

```text
outbound_fuel_transfer = 2
transfer_target_current_visible = 0
raw_sufficient_to_transfer_insufficient = 0
transfer_causal_exact = 0

target_short_outbound_fuel_transfer = 0
target_short_transfer_causal_exact = 0
```

No further work on this lead absent new evidence.

## Active investigation — standard Cloak fuel -> Nu proration

Planets.nu documents that Cloak occurs before normal movement fuel calculation. Standard Cloak consumes `max(5, floor(hull_mass / 20))` KT Neutronium; the consumed fuel also reduces movement mass. Advanced Cloak consumes zero fuel. A ship already damaged at the start of the turn cannot cloak and does not consume cloak fuel.

This creates a fully local, owner-visible pre-movement fuel delta:

```text
raw fuel sufficient
  -> mission 10 Cloak
  -> standard cloak fuel burn
  -> movement mass reduced by same amount
  -> remaining fuel becomes insufficient
  -> verified Nu waypoint proration
  -> exact short same-line move
```

Active diagnostic:

```text
tools/diagnostics/cloak_fuel_proration_audit.py
```

Strict candidate guards:

```text
mission == 10
hull.can_cloak == true
not Advanced Cloak
raw damage == 0
positive fuel after cloak burn
reachable waypoint
same immutable identity
non-Gravitonic / non-Horwasp
```

The diagnostic compares fuel-only against fuel+mass modelling and includes:

```text
synthetic_cloak_cost_noncloak_mission_exact_control
```

as a specificity control on cloak-capable ships not actually running mission 10.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check and run `cloak_fuel_proration_audit.py`;
3. require `residual_view = movement_post_fuel_proration_residual` and `target_short_forward_rows = 116`;
4. inspect mission-10 coverage within the 116-row family;
5. inspect standard-vs-Advanced-Cloak and damaged exclusions;
6. inspect `raw_sufficient_to_cloak_insufficient` and exact endpoint counts;
7. require synthetic non-Cloak control to remain sparse/zero before treating exact matches as causal;
8. promote nothing from the first pass unless evidence is cross-game / cross-hull;
9. keep production accounting at `2220` throughout this audit.

## Deprioritized / closed leads

- old affordable-whole-LY fuel frontier is correlation evidence only; the Nu rule is waypoint-distance proration;
- outbound submitted fuel transfer is negative for the current dominant family;
- Crystal Web Drain is one fully attributable evidence-only row, not a production classifier;
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

1. run the standard Cloak fuel-proration differential;
2. if Cloak produces specific cross-game exact support, perform an independent global-stage audit before any production change;
3. otherwise close it as evidence-only/rejected and return to the surviving 116-row family;
4. keep all verified intermediate accounting layers immutable as regression controls.
