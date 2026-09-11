# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob attack-opportunity runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md).
- Active initial-decision gate: [`handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-pending.md`](handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-pending.md).
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

Combat C1-C4 are checkpointed. C5 is the immediate focus: reconstruct the Host phase around the deterministic resolver rather than merely replaying supplied VCRs.

Stable C5 layers include pair composition, factual phase ordering, normal/reciprocal Priority Intercept attribution, scoped Galactic Power, matching-FC exceptions, repaired precombat positions, candidate-set v2, and plain STANDARD repeated-pair reversal. Closed gates are not reopened absent direct contradiction.

### Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383
  factual pairs exact=678 mismatch=4 unresolved=1304

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

### Initial target-order checkpoint

```text
conditional exact-set: 169/169 first pair exact
strict exact-set:      162/162 first pair exact
informative exact-set target-order controls: 15/15 rank1
```

When the eligible set is correct, evidence strongly supports:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Only two broad initial residuals remain:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Do not invert target ordering.

### Residual blocker state

Fuel is rejected for both residuals. Bird ship202 remains a strong scoped Super Spy/effective-cloak candidate. Privateer ship98 required separate investigation.

Privateer race5 mission9/Rob raw-cloak population shows large archive `iscloaked` persistence but raw prior cloak is not a combat oracle.

Latest site-conditioned attack-opportunity runtime source `bab8689c18d894399448543d3362f1cec288f5b4`:

```text
strict/conditional plain-STANDARD opportunities=16
prior true:  attacker_fought_other=8, pair_vcr=2
prior false: pair_vcr=5, neither_vcr=1
payload_conflicts=0
```

The two `true:pair_vcr` rows reject both a blanket raw-cloak blocker and a scoped `Privateer Rob + prior iscloaked` blocker. The eight skipped targets cannot yet be classified as protected because the attacker may simply have fought a different higher-priority target first and then left the mutable queue.

### Immediate combat work

Proceed in this order:

1. run `tools/diagnostics/combat_host_privateer_rob_initial_decision_audit.py`;
2. classify the 16 Rob attack opportunities by factual VCR position and canonical target priority;
3. treat `initial_skip_target_outranks_factual` as the strongest clean missing-blocker shape because no prior combat can have mutated that site queue;
4. confirm the known `360690/T83/ship98` residual remains in that scope;
5. classify the two prior-true `pair_vcr` controls as initial vs later before interpreting raw cloak state;
6. do not infer targetability from later-attacker skips until survivor/destruction replay is composed;
7. for clean initial residuals only, audit documented current-Host effective-cloak/decloak context (mission, fuel, damage, Loki, ion/mine/glory and special cloak type) rather than copying archive `iscloaked`;
8. keep Bird Super Spy ship202 separate from Privateer Rob ship98;
9. after initial blocker closure, promote the canonical first selector and rerun candidate/target differentials;
10. implement mutable survivor/destruction state, then compose closed second-pass orientation and capture continuation;
11. place ship-to-planet repair boundary and integrate planet/base participation;
12. keep game `591478` separate.

The target remains prediction of the **set, order and sides of VCRs Host will generate** from reconstructed precombat state.

## Wider Host reconstruction order

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

Do not shortcut unresolved Host rules merely to begin training sooner.
