# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). New chats should start from [`handoff/2026-09-05-new-chat-context.md`](handoff/2026-09-05-new-chat-context.md); current movement checkpoint is [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**, but movement has reached a subsystem checkpoint. Do not continue unbounded residual hunting unless a residual family blocks a larger Host subsystem or contradicts an already promoted rule.

Runtime-verified movement accounting:

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

Current schemas:

```text
prepared cache:            planets-lab.prepared-game-cache.v1
L1 movement:               planets-lab.compiled-movement.v3
L1 context semantics:      planets-lab.compiled-movement-storm-context.v3
L2 context labels:         planets-lab.compiled-movement-context-labels.v6
```

## Verified movement closures

- ordinary movement / Host major-minor geometry;
- warp-well ordering — `TESTED + DIFF_VERIFIED`;
- route-equivalent owner-visible Tow — `TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multiplicity — `TESTED + DIFF_VERIFIED`;
- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict mine/web interruption v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict Nu waypoint-distance fuel proration v6 — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- short-waypoint normal-mine scaled-floor exact classifier — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; the low-tech slowdown itself is `DOCUMENTED`;
- Red Mite tracking/fallback — research closed absent new evidence.

## Current generic residual landscape

```text
final_residual_rows       2197
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               740
generic_games               12
generic_hulls               75
```

Largest coarse family:

```text
113  warp7-9 <0.5x observed=other same_line_forward
```

Largest detailed member:

```text
89  warp7-9 reachable_other <0.5x observed=other same_line_forward non-gravitonic
```

These residual families remain bounded evidence-mining targets, not a requirement to reach zero residuals before continuing the simulator.

## Short-waypoint normal-mine closure

Production category:

```text
normal_mine_hit_scaled_floor_exact
```

Runtime-verified exact population:

```text
rows = 23
games = 6
hulls = 9
Horwasp rows = 0
```

The classifier is fail-closed: planar only, tech `<7`, hostile normal-field crossing, genuine short waypoint, same-line shortening, direct or exact canonical repair evidence, unique hit model, exact major-axis endpoint. Sphere/unknown topology and ambiguous models remain unresolved.

Full-corpus accounting delta:

```text
mine_strong_explained        37 -> 60
post_mine_strong_residual  2226 -> 2203
post_fuel_proration_residual 2220 -> 2197
```

`511506 / T23 / ship160` is now production-closed with one normal-mine hit plus exact supply repair.

## Evidence-only / rejected broad leads

- Crystal Web Drain — one end-to-end attributable evidence case; no production label because support remains one game/hull.
- outbound submitted fuel transfer — rejected for the dominant family.
- standard Cloak fuel burn — rejected.
- Privateer Rob Ship — rejected for the dominant family.
- Stellar Cartography speed terrain — rejected as a broad explanation; refined inventory found no active Black Hole or wormhole state in the 12-game corpus.

## Immediate next work — cross-repo mechanics inventory and combat integration

The next major step is not another open-ended movement residual investigation.

1. verify merged `main` and record the movement checkpoint;
2. inventory reusable mechanics in both `Numillyash/planets-lab` and `Numillyash/planets-intel`;
3. extract the already-developed Classic combat/VCR mechanics from `planets-intel` into a clean `planets-lab` combat subsystem rather than reimplementing them;
4. preserve license/attribution and existing deterministic/corpus regression evidence;
5. reproduce the existing real-VCR regression corpus from `planets-intel` inside `planets-lab`;
6. then implement the missing Host combat phase around that resolver: engagement eligibility, battle order, left/right assignment, diplomacy/PE/mission interaction, multi-player queues and planet/starbase participation.

The repositories should converge on one canonical pure mechanics implementation; dashboard-specific UI/DB code remains in `planets-intel`.

## Host reconstruction order after combat-core integration

Proceed in this order unless evidence forces a dependency change:

1. **Movement checkpoint** — current subsystem substantially reconstructed; only bounded contradictions/required interactions reopen it.
2. **Combat core extraction + regression parity** — reuse the existing `planets-intel` Classic VCR implementation.
3. **Full Host combat ordering / engagement selection**.
4. **Planet economy + starbases + ship production**.
5. **Minefield lifecycle** — laying, decay, sweep, web drain, visibility, diplomacy/FC interactions and ordering.
6. **General missions + special ship abilities**.
7. **Diplomacy / Safe Passage / alliance / team semantics across all subsystems**.
8. **Race-specific mechanics**, integrated vertically rather than as an isolated final pass.
9. **Observer / visibility / fog-of-war / shared intel** for player-safe agent input.
10. **End-to-end Host-order differential validation** over complete turns.
11. **Training environment and AI** — historical baselines first, then simulator/self-play once the required Host surface is sufficiently complete.

The target is a high-fidelity NuHost-compatible simulator suitable for real-game evaluation and later self-play. Do not shortcut unresolved Host rules merely to begin training sooner.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress.
- **M3 warfare:** partial, but a substantial Classic combat/VCR resolver already exists in `planets-intel` and should be imported rather than rewritten.
- **M4 race mechanics:** partial.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active; movement has reached a subsystem checkpoint.
- **M6 training/AI:** later, after the required simulation/observer surfaces are sufficiently faithful.
