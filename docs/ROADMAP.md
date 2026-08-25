# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-25-web-drain-raw-metadata-discovery.md`](handoff/2026-08-25-web-drain-raw-metadata-discovery.md).

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

## Active investigation — Web Drain raw metadata discovery

The first post-v6 diagnostic found one exact causal-compatible case under a broad enemy-web model. The Crystal-owner-aware rerun preserved that case:

```text
all_enemy_web_at_origin                     79
crystal_owner_web_at_origin                 79
non_crystal_owner_web_at_origin              0
crystal_web_raw_sufficient_to_insufficient   4
crystal_web_drain_causal_exact               1
```

Inside the dominant 116-row family:

```text
crystal_owner_web_at_origin                 61
crystal_web_raw_sufficient_to_insufficient   3
crystal_web_drain_causal_exact               1
```

The exact case remains game `360690`, turn `44`, hull `53`, and is exact only when 25 KT is removed from both available fuel and movement mass. This is strong corpus evidence but still only one game / one hull.

The first diplomacy/game-era inspector found no team metadata, relation records or game-era fields in prepared snapshots. That absence is non-evidence: `mechanics_projection()` intentionally reduces `game` to `{id, turn}`, players to `{id, raceid}`, and settings to a small mechanics-safe subset. The prepared cache therefore cannot answer diplomacy/game-era questions by construction.

The active follow-up is direct privacy-safe discovery in the raw `.trn` members:

```text
tools/diagnostics/web_drain_raw_metadata_discovery.py
```

It reports:

```text
top-level raw payload keys/shapes
safe game metadata related to creation/start/date/year/host
settings keys related to team/relation/alliance/diplomacy/passage
restricted player excerpts for target/web slots
recursive matching paths for the same metadata families
```

Values for names, email, username, savekey, passwords, API keys, secrets, messages and notes are never printed.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check and run `web_drain_raw_metadata_discovery.py`;
3. inspect game `360690` / turn `44` first;
4. identify exact raw JSON paths for game creation/host era and relation/team state, if present;
5. build a narrow deterministic extractor only after those paths are observed;
6. apply the documented Web Drain diplomacy rule appropriate to the actual game era;
7. if raw loadall lacks required metadata, use a separate public game-info source for game era and leave non-observable diplomacy unresolved rather than guessing;
8. do not change L1/L2 schemas or accounting during this follow-up.

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

1. discover raw game-era / diplomacy schema for the four Web Drain candidates;
2. build an extractor only from observed raw paths, without weakening the privacy-safe prepared projection;
3. do not promote a one-row Web Drain label unless era/diplomacy compatibility is attributable;
4. if Web Drain remains evidence-only, return to the post-v6 `116` short-forward family and split it by the next generic documented pre-movement mechanism;
5. keep all verified intermediate accounting layers immutable as regression controls.
