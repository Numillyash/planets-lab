# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Initial-target fuel residual runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md).
- Initial-target cloak residual runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md).
- Privateer Rob cloak population runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md).
- Privateer Rob VCR control runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-vcr-control-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-vcr-control-runtime.md).
- Active Privateer Rob attack-opportunity gate: [`handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-pending.md`](handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-pending.md).
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

Combat C1-C4 are checkpointed. C5 is the immediate focus: reconstruct Host engagement selection around the deterministic resolver rather than merely replaying supplied VCRs.

Stable C5 layers include:

```text
pair selection                         TESTED
factual queue phase ordering           CORPUS_OBSERVED + DIFF_VERIFIED
normal Priority Intercept scope        DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
reciprocal PIA pair attribution        DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
Galactic Power scoped forced-left      DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
matching-FC positive exceptions        DOCUMENTED + TESTED + CORPUS_OBSERVED
plain STANDARD repeated-pair reversal  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Repaired precombat position checkpoint

Runtime source `14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c`:

```text
payload_conflicts=0
storm modes: false=10 true=1
ship occurrences: factual=3204 predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs: total=1986 exact=678 mismatch=4 unresolved=1304
sites: total=1220 fully position-exact=346 mismatch sites=4
```

Six previously attributable classic ion-storm residuals are now exact through independent `normal movement -> ion storm -> warp well` prediction. Two remaining rows are DIFF_VERIFIED stochastic normal-mine hits and two remain bounded unresolved. No factual coordinate is injected into the predictor.

### Candidate-set v2 checkpoint

Runtime source `c804575f4275f4454dbb282d9fcfc99fad0700d6`:

```text
tests rc=0
audit rc=0
payload_conflicts=0
factual unique pairs=1986
candidate-covered factual pairs=428
candidate-uncovered factual pairs=1558
candidate pairs=1092
strict factual: eligible=420 unresolved=8 blocked=0
conditional factual: eligible=427 unresolved=1 blocked=0
conditional eligible nonfactual=331
all factual positions covered sites=242
conditional factual subset of eligible=236
conditional eligible exactly factual=171
```

No candidate-covered factual pair is conditionally hard-blocked. Candidate-set v2 therefore gives a broad positive differential for canonical pair eligibility.

### Initial plain-STANDARD target-order checkpoint

Runtime source `d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3`:

```text
conditional exact-set: sites=169 first_pair_exact=169 first_right_exact=169
strict exact-set:      sites=162 first_pair_exact=162 first_right_exact=162
exact-set informative target-order sites: 15/15 target rank 1
```

Strongly supported when the eligible set is correct:

```text
first active ship = highest standard Combat Priority ship having an eligible target
first target      = highest-priority eligible target for that active ship
```

Only two broad-scope mismatches remain:

```text
360690/T83: active264; extra target98; factual target190
511506/T94: active496; extra target202; factual target332
```

Both already choose the correct active ship. Do not invert target ordering.

### Residual blocker checkpoints

Fuel runtime source `55ad7c5799f52d8bc703f3247cf7ed179dbb18f9` rejected post-movement zero fuel for both extra targets.

Cloak runtime source `3d3b8d91f3ff281b0563a0f7112fadbe86222f2b` split the residuals:

```text
511506/T94 ship202:
  Bird race3 + Red Wind + mission9 Super Spy
  T-1/T persistent raw cloak control
  => strong scoped effective-cloak candidate

360690/T83 ship98:
  Privateer race5 + Meteor + mission9/Rob + PE0
  T-1/T persistent raw cloak control
  => raw state persistence, semantics unresolved
```

Factual `511506/T94/ship332` has T-1 `iscloaked=true`, current mission2 and enters VCR728, so raw T-1 cloak is not a blanket blocker.

### Privateer Rob population and VCR controls

Population runtime source `e0b7f9ac91f99e8006546b80ec4a940ab21e2a6e`:

```text
candidate_rows=2223
stable_identity=2174
stable_vcr_participant=2
stable_no_vcr=2172
before_cloak_true=1433
true_to_true=1378
false_to_true=693
false_to_false=68
true_to_false=35
stable_before_cloaked_pe_zero_no_vcr=1394
stable_true_to_true_pe_zero_no_vcr=1360
stable_before_cloaked_pe_zero_vcr=0
stable_true_to_true_pe_zero_vcr=0
payload_conflicts=0
```

VCR control extraction source `6ef2c9344b1544a7e60952db50e1d942e352e53e` found that both stable VCR participants had their own nonzero PE:

```text
511506/T15 ship89:  PE=6,  true_to_true, VCR7 vs owner6
511506/T22 ship157: PE=11, true_to_true, VCR25 vs owner11
```

These are not PE0 hostile-targetability counterexamples. They show only that a persistent raw-cloak Rob ship can still fight when its own PE requests combat.

The Privateer mission9 archive cloak persistence is `CORPUS_OBSERVED + TESTED`; combat-effective targetability remains unpromoted. Current Planets.nu Host documentation keeps Cloak and Rob as separate Host steps, so mission9 itself is not promoted as a cloak-generating rule.

### Immediate combat work

Run:

```text
tools/diagnostics/combat_host_privateer_rob_attack_opportunity_audit.py
```

with regression:

```text
tests/test_combat_host_privateer_rob_attack_opportunity_audit.py
```

The gate requires an ordinary factual battle site, a Privateer race5 mission9 cloak-capable PE0 target, independently reconstructed target/opponent positions, a hostile opponent whose Kill!/PE requests combat against the Privateer owner, and a canonical conditional plain-STANDARD pair decision.

Interpret outcomes:

```text
pair_vcr
attacker_fought_other
target_fought_other
both_fought_other
neither_vcr
```

Known residual must appear as `360690/T83 target98 attacker264 -> attacker_fought_other` before any cloak rule is added.

Inspect outcome distribution by prior archive cloak state. Any `prior cloak=true + PE0 + pair_vcr` is a direct counterexample to a blanket raw-bit blocker. Strong positive blocker evidence is `prior cloak=true + attacker_fought_other + target skipped`, especially in strict diplomacy scope.

Do not modify `selection.py`, STANDARD priority or target order before this gate is reviewed.

After initial blocker closure:

1. add canonical initial target selector;
2. implement mutable target selection with survivor/destruction state;
3. compose the already-closed second-pass orientation;
4. model capture continuation;
5. place the documented ship-to-planet repair boundary between ship and planet phases;
6. integrate planet/base participation using the C4 persistence layer;
7. keep game `591478` and special/campaign mechanics separately labeled.

The next goal remains prediction of the **set, order and sides of VCRs Host will generate** from reconstructed precombat state, with unresolved movement and queue state explicit.

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

Verified movement closures include ordinary major/minor geometry, warp-well ordering, route-equivalent Tow and Chunnel, classic/cloudy ion storms, scoped sphere topology, strict mine/web interruption, damage-limited maximum warp, strict Nu waypoint fuel proration, and short-waypoint normal-mine scaled-floor compatibility. Generic movement residuals remain bounded evidence-mining targets, not a requirement to reach zero residuals before continuing the Host simulator.

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

Current active stage. Pair mechanics and a broad candidate-set layer are reconstructed. Immediate missing layers are:

- final initial-target candidate blocker closure;
- canonical first target selection;
- mutable target selection and queue mutation;
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
