# New chat context — NuHost reconstruction

GitHub `main` is the only source of truth for project state. Do not reconstruct current state from an old ChatGPT conversation.

Read first:

1. [`2026-09-07-movement-checkpoint-scaled-mine-closed.md`](2026-09-07-movement-checkpoint-scaled-mine-closed.md)
2. [`../ROADMAP.md`](../ROADMAP.md)
3. [`../COMPILED_CORPUS.md`](../COMPILED_CORPUS.md)
4. [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
5. [`../WORKFLOW.md`](../WORKFLOW.md)

The older `2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md` handoff is historical only; its active investigation has been completed and production-integrated.

## Operating rules

1. GitHub `main` is source of truth.
2. Before changing code, fetch/pull current `main`, inspect HEAD and dirty state, and read the files above.
3. Raw historical archives, prepared caches and compiled corpus databases are local/gitignored.
4. Do not weaken privacy-safe corpus projections merely to make diagnostics convenient. Raw `.trn` inspection must remain explicit and narrowly scoped.
5. Unknown mechanics fail closed. Separate `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED`, and `DIFF_VERIFIED` evidence.
6. Do not promote a production mechanic from a single attributable transition.
7. After meaningful mechanics changes, update durable state in ROADMAP / COMPILED_CORPUS / handoff as appropriate.
8. Do not rebuild L1/L2 unless compiled semantics actually changed.
9. Prefer bounded differential questions over open-ended residual hunting.
10. Preserve one canonical pure mechanics implementation where `planets-lab` and `planets-intel` overlap.

## Runtime-verified movement checkpoint

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
mine_strong_explained                 60
post_mine_strong_residual           2203
fuel_proration_explained               6
post_fuel_proration_residual        2197
label_issues                           0
```

Generic endpoint:

```text
final_residual_rows       2197
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               740
generic_games               12
generic_hulls               75
```

Largest coarse generic family:

```text
113  warp7-9 <0.5x observed=other same_line_forward
```

Current schemas:

```text
prepared cache:       planets-lab.prepared-game-cache.v1
L1 movement:          planets-lab.compiled-movement.v3
L1 context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:    planets-lab.compiled-movement-context-labels.v6
```

## Important movement closures

Production-verified closures include:

- ordinary movement / Host major-minor geometry;
- warp-well ordering;
- route-equivalent owner-visible Tow;
- route-equivalent Chunnel multiplicity;
- classic/cloudy ion storms;
- scoped effective sphere topology for game `591478`;
- strict mine/web interruption;
- strict damage-limited maximum warp;
- strict Nu waypoint-distance fuel proration;
- short-waypoint normal-mine scaled-floor exact classification.

Red Mite tracking/fallback research is closed absent contradictory evidence.

### Scaled normal-mine production result

Category:

```text
normal_mine_hit_scaled_floor_exact
```

Runtime population:

```text
23 rows
6 games
9 hulls
0 Horwasp rows
```

The classifier remains planar/exact/fail-closed. The empirical scaled-floor expression is `CORPUS_OBSERVED`, not documented NuHost source semantics.

The original target `511506 / T23 / ship160` is closed as one normal-mine hit plus exact automatic supply repair.

## Next active work

Do not continue the old normal-mine survivor investigation.

After confirming current GitHub `main` HEAD, proceed with the roadmap's next major block:

1. cross-repo mechanics inventory (`planets-lab` + `Numillyash/planets-intel`);
2. extract the existing Classic combat/VCR core from `planets-intel` into a clean reusable `planets-lab` combat subsystem;
3. reproduce the existing VCR/chain regression evidence;
4. implement the missing Host combat orchestration around that resolver;
5. continue through economy/starbases/production, mine lifecycle, missions/abilities, diplomacy/alliances, race mechanics, observer/visibility, and complete Host-order differential validation.

The objective is a high-fidelity NuHost-compatible simulator suitable for later player-safe AI training and self-play. Do not substitute an approximate shortcut simulator simply to start ML earlier.

## Git state

The SHA written in any handoff is only a historical checkpoint. Always query actual GitHub `main` before work; later documentation/merge commits advance it.
