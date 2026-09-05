# planets-lab

Deterministic Planets.nu simulation, reverse-engineering and AI research environment.

## Current movement/corpus state

The active workstream is historical NuHost movement compatibility mining across 12 finished games.

Runtime-verified accounting:

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

Current generic endpoint:

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest surviving coarse family:

```text
116  warp7-9 <0.5x observed=other same_line_forward
```

Verified recent production closures include route-equivalent Tow/Chunnel, classic/cloudy ion storms, scoped sphere geometry, strict mine/web hit context, strict damage-limited warp, and strict Nu waypoint-distance fuel proration v6.

Crystal Web Drain remains one fully attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition. Outbound submitted fuel transfer, standard Cloak fuel burn, Privateer Rob Ship and Stellar Cartography speed terrain are rejected as broad explanations for the dominant 116-row family.

The normal-mine slowdown exposure pass found 10 route-exposed target rows and only two with deficits near the documented `10 * N` pattern. The hull-tech gate then rejected one immediately:

```text
game 360690 / turn 155 / hull 23 -> tech 10 -> slowdown impossible
game 511506 / turn 23  / hull 17 -> tech 6  -> survives gate
```

The sole surviving candidate has:

```text
hull mass = 130
normal-mine corpus damage quantum = 76
before damage/supplies = 0 / 53
after damage/supplies  = 66 / 3 (supplies observational)
```

One 76% mine hit followed by automatic post-movement supply repair of 10% predicts exactly `66%` damage and `3` supplies from the submitted before-state. Two damage hits do not match that repair trace. The active question is therefore one-hit mine attribution plus the remaining movement-distance discrepancy, not a blind two-hit `20 ly` interpretation.

Active diagnostic:

```text
tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py
```

It checks exact post-decay intersected fields, turn-specific Safe Passage/team state, exposed minefield Friendly Codes, ship/field FC matching, route intervals and one-hit vs two-hit repair predictions for `game 511506 / turn 23 / ship 160` only. Unknown FC state fails closed; no production label is allowed from this single transition.

Current schemas:

```text
L1 physical movement:       planets-lab.compiled-movement.v3
L1 context semantics:       planets-lab.compiled-movement-storm-context.v3
L2 context labels:          planets-lab.compiled-movement-context-labels.v6
```

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/handoff/2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md`](docs/handoff/2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md)
- [`docs/COMPILED_CORPUS.md`](docs/COMPILED_CORPUS.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

GitHub `main` is the source of truth. Raw historical archives, prepared caches and compiled datasets remain local/gitignored; Git contains privacy-safe manifests, code, schemas and reproducible summaries.
