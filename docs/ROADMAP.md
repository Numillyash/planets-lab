# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-23-sphere-movement-runtime-verification.md`](handoff/2026-08-23-sphere-movement-runtime-verification.md).

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

Current 12-game movement baseline after scoped sphere-topology integration:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13956
post_external_residual              3938
chunnel_explained                   1387
post_chunnel_residual               2551
horwasp_strong_explained             240
post_horwasp_strong_residual        2311
```

The privacy-safe 12-game manifest is tracked at `validation/corpus/manifests/accounts-recent-finished.jsonl` under schema `planets-lab.corpus-game.v2`; manifest privacy cleanup is closed.

The scoped sphere-topology integration for game `591478` is now **TESTED + DIFF_VERIFIED**. Raw topology remains `2150x2150`; effective `2170x2170` closes 512 L1 rows. Seventy of those rows were already strong Horwasp closures in the old L2 stack, so the final residual falls by exactly the pre-production diagnostic prediction of 442 rows: `2753 -> 2311`.

The next active task is **generic post-sphere residual triage**. A DB-only diagnostic is now implemented at `tools/diagnostics/post_sphere_generic_residual_clustering_audit.py`; its runtime output is the next required evidence. It prioritizes cross-game/cross-hull signatures rather than another hull-specific rule and excludes known Horwasp hull IDs `201-213` from the generic population by default.

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
- privacy-safe v2 manifest tracked in Git at `validation/corpus/manifests/accounts-recent-finished.jsonl`;
- immutable `/game/loadall` archives cached locally and gitignored;
- deterministic manifests with full `loadinfo.settings`, settings hashes, allowlisted game metadata, minimized player-slot provenance and corpus tier;
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

post-compile external-context semantics:
  planets-lab.compiled-movement-storm-context.v2

compiled context labels:
  planets-lab.compiled-movement-context-labels.v3
```

Manifest v2 replaces the old v1 behavior that copied `loadinfo.game` wholesale. Existing v1 manifests must be migrated/regenerated before normal corpus loaders accept them. `sanitize_manifest_record()` provides an offline migration path that preserves settings and settings hashes while reapplying the privacy allowlists. The current 12-game v2 manifest passed targeted privacy/corpus tests and a recursive forbidden-field check before being committed.

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
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. evidence-scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

Classic ion-storm integration produced the verified change:

```text
post_external_residual       6174 -> 4450
final strong residual        4477 -> 2753
hull 79 final residual        495 ->   20
```

Scoped sphere integration then produced:

```text
post_external_residual       4450 -> 3938  (-512)
post_chunnel_residual        3063 -> 2551  (-512)
horwasp_strong_explained      310 ->  240  (-70 overlap)
final strong residual        2753 -> 2311  (-442)
```

Runtime preserved raw game `591478` topology facts as `(sphere=True, map_width=2150, map_height=2150, map_shape='1', topology_stable=True)`.

### Next movement priority — generic residual triage

Do not choose the next mechanic from hull count alone. The implemented diagnostic:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

reads only the compiled DuckDB and groups `movement_post_horwasp_strong_residual` by generic cross-game signatures. It reports:

- generic hull/game counts after excluding hull IDs `201-213` by default;
- baseline, warp, distance and observed/nominal-ratio distributions;
- waypoint/target relationship and observed-vector direction relative to target;
- exact displacement vectors shared across hulls/games;
- sign/axis-normalized canonical displacement shapes;
- detailed and coarse mechanic signatures shared by multiple hulls/games;
- signature breakdowns for the leading multi-game hull populations.

Initial candidate population after excluding closed Mite and known Horwasp-heavy clusters:

```text
hull 23   78 rows / 3 games
hull 52   59 rows / 4 games
hull 56   55 rows / 4 games
hull 17   51 rows / 9 games
hull 46   50 rows / 4 games
hull 94   43 rows / 3 games
hull 29   36 rows / 5 games
```

Immediate work:

1. run `post_sphere_generic_residual_clustering_audit.py` on the current `2311`-row final residual and preserve the complete output;
2. identify clusters with multiple hulls and multiple games before inspecting raw/private context;
3. only then add a focused second-pass diagnostic for the strongest shared signature;
4. separately flag known Horwasp hulls `201-213` and closed Mite `213` so they do not dominate generic ranking;
5. only promote a production rule when evidence is cross-sample and fail-closed;
6. keep current runtime invariants synchronized after every material commit.

### Deprioritized/rejected movement leads

- multi-waypoint queue did not explain the hull-79 cluster in the current corpus;
- fuel-proration signatures exist but are low-volume relative to current generic gaps;
- do not generalize game `591478`'s 2170 period to other games without independent evidence;
- do not reopen Red Mite research without new evidence.

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

1. run the generic post-sphere clustering audit and choose the strongest cross-game/cross-hull signature;
2. keep reducing movement residuals with cross-game mechanics rather than hull-specific overfit;
3. promote the stabilized movement subset into simulator/ruleset behavior;
4. expand M5 differential mining into economy/mines/combat/race mechanics;
5. build the broader compatibility matrix;
6. only then treat M6 AI training as a primary workstream.
