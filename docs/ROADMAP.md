# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Active C5 runtime gate: [`handoff/2026-09-10-combat-c5-initial-standard-target-pending.md`](handoff/2026-09-10-combat-c5-initial-standard-target-pending.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Repaired storm-aware precombat position runtime: [`handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md`](handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md).
- movement: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md).
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md).
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md).
- planet/starbase sequences: [`handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md`](handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**.

Combat C1-C4 are checkpointed. C5 is the current immediate focus: reconstruct the Host phase around the deterministic resolver rather than merely replaying already supplied VCRs.

Stable C5 layers already include:

```text
pair selection                         TESTED
factual queue phase ordering           CORPUS_OBSERVED + DIFF_VERIFIED
normal Priority Intercept scope        DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
reciprocal PIA pair attribution        DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
Galactic Power scoped forced-left      DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
matching-FC positive exceptions        DOCUMENTED + TESTED + CORPUS_OBSERVED
plain STANDARD repeated-pair reversal  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
candidate-set v2 positive differential CORPUS_OBSERVED + DIFF_VERIFIED (covered scope)
```

The repaired T-1 -> precombat position differential has the following ordinary runtime population:

```text
source=14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c
payload_conflicts=0
storm modes: false=10 true=1

ship occurrences:
  factual=3204
  predicted=1810
  exact=1806
  mismatch=4
  uncovered=1383

factual pairs:
  total=1986
  exact=678
  mismatch=4
  uncovered=1304

sites:
  total=1220
  fully position-exact=346
  mismatch sites=4
```

All six previously attributable classic ion-storm residuals are exact through independent `normal movement -> ion storm -> warp well` prediction. Two of the four remaining rows are specific stochastic normal-mine hits with `CORPUS_OBSERVED + DIFF_VERIFIED` attribution; two remain bounded unresolved. No factual coordinate is injected into the predictor.

Candidate-set v2 then expanded the independent combat-candidate population:

```text
source=c804575f4275f4454dbb282d9fcfc99fad0700d6
tests rc=0
audit rc=0
payload_conflicts=0

factual unique pairs=1986
candidate-covered factual pairs=428
candidate-uncovered factual pairs=1558
candidate pairs=1092

strict factual:      eligible=420 unresolved=8 blocked=0
conditional factual: eligible=427 unresolved=1 blocked=0
conditional eligible nonfactual=331

all factual positions covered sites=242
conditional factual subset of eligible=236
conditional eligible exactly factual=171
```

No candidate-covered factual pair is conditionally hard-blocked. The single conditional factual unresolved row is a fuel-state coverage gap. Extra eligible nonfactual pairs are now the expected input to target-list / survivor-mutation reconstruction rather than evidence against pair eligibility.

### Immediate combat work

Proceed in this order:

1. run `tools/diagnostics/combat_host_initial_standard_target_audit.py` over the 11 ordinary archives;
2. evaluate the first plain-STANDARD VCR only on position-covered/resolved sites, before any combat outcome mutation;
3. compare the documented/inferred selector `highest-priority active -> highest-priority eligible target` against the factual first VCR;
4. report the exact-candidate-set control separately from the broader `factual ⊆ eligible` population and compare against the low-priority-target control;
5. investigate every first-pair/right mismatch before adding a canonical target selector;
6. if the first-selection rule is coherent, implement the narrow canonical selector and then compose mutable survivor/destruction state;
7. integrate the already closed second-pass repeated-pair orientation when both ships survive to the later active-ship pass;
8. then model capture continuation inside the same Host phase;
9. place the documented ship-to-planet repair boundary between ship and planet phases;
10. integrate planet/base participation using the C4 persistence layer;
11. keep game `591478` and special/campaign mechanics separately labeled.

Candidate-set v2 remains site-conditioned: factual VCR supplies the site coordinate and held-out pair set, but not per-ship position or positive eligibility. Visible T-1 foreign normal/web mine crossings fail closed because hit occurrence is stochastic.

The next goal is to predict the **set, order and sides of VCRs Host will generate** from reconstructed precombat state, with unresolved movement and queue state explicit.

## Runtime-verified movement accounting

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
post_mine_strong_residual          2203
fuel_proration_explained               6
post_fuel_proration_residual        2197
label_issues                           0
```

Current movement schemas:

```text
prepared cache:            planets-lab.prepared-game-cache.v1
L1 movement:               planets-lab.compiled-movement.v3
L1 context semantics:      planets-lab.compiled-movement-storm-context.v3
L2 context labels:         planets-lab.compiled-movement-context-labels.v6
```

Verified movement closures include ordinary major/minor geometry, warp-well ordering, route-equivalent Tow and Chunnel, classic/cloudy ion storms, scoped sphere topology, strict mine/web interruption, damage-limited maximum warp, strict Nu waypoint fuel proration, and short-waypoint normal-mine scaled-floor compatibility. See the movement handoffs for evidence boundaries.

Generic movement residuals remain bounded evidence-mining targets, not a requirement to reach zero residuals before continuing the Host simulator.

## Combat integration checkpoints

### C1 — Classic resolver extraction

Completed: deterministic Classic VCR resolver imported into `rules/combat`, with independent unit tests and no dashboard/API coupling.

### C2 — Nu adapter and historical replay coverage

```text
archives                   12
raw_vcr_observations     22256
unique_vcrs               6469
replay_supported          6469
replay_unsupported           0
payload_conflicts            0
replay_result_conflicts      0
malformed_members            0
```

C2 status: `CORPUS_OBSERVED + TESTED`. Replay coverage is not by itself independent terminal-state proof.

### C3 — ordinary ship battle sequences

Strong ordinary same-phase survivor oracle:

```text
ship_vs_ship -> ship_vs_ship
transitions  764
match        764
mismatch       0
```

Ordinary sequence carry-over is `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`. Federation recovery and exact-zero shield crew ordering have separate closed checkpoints. Capture reappearance changes owner as expected; special game `591478` remains isolated.

### C4 — ordinary planet/starbase battle sequences

Ordinary population excluding game `591478`:

```text
transitions             103
match                   102
not_comparable            1
mismatch                  0
starbase                  92
no_starbase               11
shield carry match       103 / 103
```

Comparable plain-planet carry and starbase shield persistence are `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`. Hidden damaged-starbase state remains fail-closed.

### C5 — Host engagement/ordering around the resolver

Current active stage. Pair mechanics and a broad covered candidate-set differential are reconstructed; the immediate missing layers are:

- initial standard target-list ordering;
- mutable survivor/destruction queue mutation;
- capture continuation;
- ship-to-planet repair/phase boundary;
- planet/base participation in the full multi-player queue.

Do not reopen closed C5 sub-gates merely to fit residuals unless a new contradiction directly requires it.

## Host reconstruction order

Proceed in this order unless evidence forces a dependency change:

1. Movement checkpoint — substantially reconstructed; reopen only for bounded contradictions/interactions.
2. Classic pairwise combat C1/C2.
3. Ordinary ship battle sequences C3.
4. Planet/starbase sequences C4.
5. Full Host combat ordering / engagement selection C5 — current immediate focus.
6. Planet economy + starbases + ship production.
7. Minefield lifecycle.
8. General missions + special ship abilities.
9. Diplomacy / Safe Passage / alliance / team semantics across all subsystems.
10. Race-specific mechanics integrated vertically.
11. Observer / visibility / fog-of-war / shared intel.
12. End-to-end Host-order differential validation over complete turns.
13. Training environment and AI after simulator/observer fidelity is sufficient.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress.
- **M3 warfare:** materially advanced; full Host engagement ordering remains open.
- **M4 race mechanics:** partial; Federation recovery and scoped Galactic Power have differential evidence.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active.
- **M6 training/AI:** later, after required simulation/observer surfaces are sufficiently faithful.

The target remains a high-fidelity NuHost-compatible simulator suitable for real-game evaluation and later self-play. Do not shortcut unresolved Host rules merely to begin training sooner.