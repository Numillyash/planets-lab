# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-21-movement-corpus-current-state.md`](handoff/2026-08-21-movement-corpus-current-state.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean real NuHost transitions.

Unknown mechanics fail closed rather than being silently guessed. Raw game/settings/topology facts and evidence-scoped effective overrides remain separate.

## Current focus

The active milestone is **M5: historical NuHost corpus + compatibility mining**, with movement as the most mature mechanic family.

Current 12-game movement baseline after the classic-ion-storm integration:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13444
post_external_residual              4450
chunnel_explained                   1387
post_chunnel_residual               3063
horwasp_strong_explained             310
post_horwasp_strong_residual        2753
```

The next active generic gap is **sphere-aware ordinary movement geometry** in game `591478`. The diagnostic-only effective 2170×2170 topology closes 442 current final residual rows, including 394 non-Horwasp rows and 213/235 hull-46 sphere rows. Raw 2150×2150 closes zero of those rows. Production integration is still pending.

## M0 — deterministic skeleton

Status: **substantially complete**.

- canonical full-information `GameState`;
- immutable turn-order contracts;
- deterministic seeded `HostEngine.step()`;
- baseline tests and scenario infrastructure.

## M1 — minimal sandbox

Status: **largely implemented for the movement subset**.

Implemented or partially implemented:

- Planets.nu JSON -> canonical state adapter;
- cargo transfer and colonization primitives;
- ordinary movement, movement mass, fuel use and fuel proration;
- warp wells;
- tow / intercept / HYP movement phases;
- pre-movement repair and damage-limited speed;
- ion-storm displacement;
- minimal planet economy;
- deterministic golden scenarios.

Movement rules should continue to be promoted from M5 differential evidence rather than guessed directly in the simulator.

## M2 — economy and planetary host

Status: **in progress / not current priority**.

Target coverage:

- factories and supplies;
- taxes and happiness;
- natives and growth;
- Cyborg assimilation;
- mining and Trans-Uranium Mutation;
- riots / civil war / Amorphous / Bovinoid behavior;
- starbases and ship construction;
- differential validation for clean planetary transition classes.

## M3 — warfare

Status: **partial**.

Target coverage:

- towing interactions;
- minefields and web mines;
- combat;
- missions;
- fighters / torpedoes;
- ground combat;
- post-combat repair/aftermath.

## M4 — race mechanics

Status: **partial**.

Race-specific behavior belongs in explicit ruleset modules/hooks rather than scattered `if race == ...` conditionals.

Priority families include Privateer gravitonic/rob, Crystal webs, Cyborg chunnel, Fascist pillage/glory, Bird cloak/super-spy, Rebel RGA, Colonial fighter sweep and Horwasp mechanics.

## M5A — historical NuHost corpus

Status: **active; acquisition and movement compilation operational**.

### Corpus foundation

Current corpus:

- 12 recent unique finished games across four configured account histories;
- immutable `/game/loadall` archives cached locally and gitignored;
- deterministic privacy-safe manifests with full `loadinfo.settings`, settings hashes, allowlisted game metadata, minimized player-slot provenance and corpus tier;
- prepared cache for normalized historical snapshots;
- compiled movement Parquet + DuckDB catalog;
- separate context-label layer for Chunnel/Horwasp evidence.

Network policy:

- server corpus network access remains proxy-first via `PLANETSNU_PROXY_URL`;
- production compilation is offline from cached archives/manifests;
- diagnostic direct HTTP is allowed only through an explicit diagnostic CLI option where implemented, never as a silent fallback in the corpus API.

Privacy boundary:

- raw private text/account fields remain only in local raw/prepared evidence;
- manifest game metadata is explicit-allowlist only; the full `loadinfo.game` object is never persisted wholesale;
- compiled datasets export derived mechanical categories, not friendly codes, messages, savekeys, email, etc.

### Current schemas

```text
corpus manifest:
  planets-lab.corpus-game.v2

prepared cache:
  planets-lab.prepared-game-cache.v1

compiled movement:
  planets-lab.compiled-movement.v2

movement storm-context semantics:
  planets-lab.compiled-movement-storm-context.v1

compiled context labels:
  planets-lab.compiled-movement-context-labels.v3
```

Manifest v2 replaces the old v1 behavior that copied `loadinfo.game` wholesale. Existing v1 manifests must be migrated/regenerated before normal corpus loaders accept them. `sanitize_manifest_record()` provides an offline migration path that preserves settings and settings hashes while reapplying the privacy allowlists.

Semantic changes must invalidate affected caches even when the physical Parquet column schema does not change.

### Verified movement progress

The following are closed or production-integrated:

1. ordinary movement baseline / partial Host major-minor geometry;
2. gravitonic movement classification;
3. warp-well capture and corrected warp-well-before-`above_nominal` ordering — `TESTED + DIFF_VERIFIED`;
4. observed tow-target context;
5. Chunnel context layer;
6. Horwasp ballistic strong labels with scoped 2170 topology for game `591478`;
7. scoped Red Mite fallback reconstruction; Red Mite research is closed unless new evidence appears;
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

Classic ion-storm integration produced the verified change:

```text
post_external_residual       6174 -> 4450
final strong residual        4477 -> 2753
hull 79 final residual        495 ->   20
```

### Active movement priority — sphere topology

Evidence-scoped game `591478` effective topology is 2170×2170 despite raw metadata 2150×2150. The current sensitivity audit over `movement_post_horwasp_strong_residual` reports:

```text
sphere final residual rows                 2059
raw 2150 closures                             0
effective 2170 closures                     442
effective 2170 non-Horwasp closures         394
hull 46 sphere rows                          235
hull 46 effective closures                  213
```

This strongly favors a generic ordinary sphere-movement gap over a hull-46-specific mechanic.

Immediate work:

1. integrate the evidence-scoped effective topology into ordinary movement/external-context classification for game `591478`;
2. reuse existing wrapped sample/planet helpers and the existing movement classifier;
3. add regressions for 2170-vs-2150 seam cases;
4. invalidate affected compiled movement semantics without modifying raw topology facts;
5. rebuild movement + labels and measure the exact residual delta;
6. re-rank the remaining final residual after integration;
7. continue with the next high-volume generic mechanic, excluding already-closed Mite research.

### Deprioritized/rejected movement leads

- multi-waypoint queue did not explain the hull-79 cluster in the current corpus;
- fuel-proration signatures exist but are low-volume relative to current generic gaps;
- do not generalize game `591478`'s 2170 period to other games without independent evidence.

## M5B — Nu compatibility matrix

Status: **active through movement differential validation**.

Required outputs:

- mechanic-level `MATCH`, `MISMATCH`, `SKIPPED_AMBIGUOUS`, `UNSUPPORTED` outcomes;
- compatibility grouped by mechanic and settings/ruleset hash;
- explicit ruleset/version splits instead of forcing old games into modern behavior;
- compact permanent regressions for known real-game transitions;
- promotion to `DIFF_VERIFIED` only from clean causally attributable samples.

Movement is the first compatibility family; economy, mines, combat and race mechanics should follow as their corpus classifiers mature.

## M6 — training and AI

Status: **future**.

- scripted baseline agents;
- player-limited observation environment;
- historical imitation/value models;
- parallel self-play;
- policy/value training;
- historical-corpus offline evaluation and pretraining without hidden-information leakage.

## Working order

Unless new evidence changes priorities:

1. finish sphere-aware movement integration and rebaseline the corpus;
2. keep reducing high-volume movement residuals with generic mechanics;
3. promote the stabilized movement subset into simulator/ruleset behavior;
4. expand M5 differential mining into economy/mines/combat/race mechanics;
5. build the broader compatibility matrix;
6. only then treat M6 AI training as a primary workstream.
