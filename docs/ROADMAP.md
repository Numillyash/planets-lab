# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob attack-opportunity runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md).
- Privateer Rob initial-decision runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md).
- Privateer Rob initial cloak-context runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-runtime.md).
- Privateer Rob cloak/fuel-state population runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md).
- Active Rob cloak/fuel attribution gate: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-pending.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-pending.md).
- Repaired storm-aware precombat position runtime: [`handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md`](handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md).
- movement checkpoint: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md).
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md).
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md).
- planet/starbase sequences: [`handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md`](handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

## Engineering progress estimate

These are planning estimates, **not mechanics evidence** and not percentages derived from test count. Keep mechanics understanding separate from end-to-end historical coverage.

```text
combat mechanics reconstruction (C1-C5 knowledge):     ~70-80%
ordinary ship-combat independent end-to-end coverage:  ~20-25%
movement ordinary-core reconstruction:                  ~80-90%
whole NuHost reverse across the roadmap:                ~40-50%
```

The apparently large gap between combat knowledge and end-to-end coverage is expected. Candidate-set v2 independently covers only `428 / 1986 = 21.6%` factual ship-vs-ship pairs, while the candidate-covered eligibility model itself has zero conditionally hard-blocked factual pairs. Position v3 similarly predicts 1810/3204 factual ship occurrences, with 1806 exact and only 4 mismatches. In other words, deterministic rules are increasingly well constrained, but many special/stochastic precombat states still fail closed.

Whole-NuHost progress is lower because economy/starbase production, minefield lifecycle, general missions/special abilities, race mechanics, cross-subsystem diplomacy, observer/visibility and full-turn end-to-end validation remain substantial work. See `docs/handoff/2026-09-11-reverse-progress-assessment.md` for the detailed basis.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**.

Combat C1-C4 are checkpointed. C5 is immediate: reconstruct the Host phase around the deterministic resolver rather than merely replaying supplied VCRs.

Stable C5 layers include pair composition, factual phase ordering, normal/reciprocal Priority Intercept attribution, scoped Galactic Power, matching-FC exceptions, repaired precombat positions, candidate-set v2, repeated-pair side reversal and clean first-target ordering. Closed gates are not reopened absent direct contradiction.

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

Do not invert target ordering.

### Residual blocker state

The two original broad initial residuals remain:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Bird ship202 remains a separate Super Spy/effective-cloak branch. Privateer ship98 is narrowed through Rob controls.

Initial-decision runtime isolated three clean first-decision missing-state residuals:

```text
360690/T57 ship46
360690/T57 ship280
360690/T83 ship98
```

Matched same-site prior-false Meteors are actually fought by the same attackers. The only clean prior-true initial fought control is `620694/T64/ship118` with T-1 fuel `5 KT`.

Focused cloak-context runtime source `fe9f1575b81d7ea4c922426c8f56d689dbd66ef3` rejected damage / normal-movement fuel / Loki as the ship118 discriminator.

Population fuel-state runtime source `cf52a264c31418a8247987a64332c54e50e07a91` is complete:

```text
stable prior-true rows=1413
exact_reference_debit=545
zero_debit=90
other_debit=778

same_position=718
position_changed=695

true_to_true=1378
true_to_false=35

threshold above reference cost=1399
threshold equals reference cost=3
threshold below reference cost=11
```

The exact ordinary-cloak-reference debit is strongly structured:

```text
545 / 1413 = 38.6% overall
541 / 545 = 99.3% exact-debit rows are true_to_true
same-position damage0 PE0 no-VCR bucket:
  515 exact / 112 other / 86 zero
  exact share=72.2%
```

The three clean skipped Meteors remain exact 5-KT observations:

```text
ship46:  58 -> 53
ship280:  9 -> 4
ship98:  45 -> 40
```

Ship118 starts at exactly the 5-KT Meteor reference cost, so a hypothetical same debit would exhaust it. That debit is still **not observed** because T identity is unstable after its factual battle.

Evidence status:

```text
large structured exact-reference-debit population:
  CORPUS_OBSERVED + TESTED

Rob Ship cloak-fuel mechanic / mission9 effective cloak:
  NOT PROMOTED
```

### Immediate combat work

The first cloak/fuel attribution runtime attempt on source `180429508419581cf5082bb5363e1b8c528dd14f` is **invalid** as mechanics evidence: pytest collection failed with `ModuleNotFoundError: No module named 'tools'` (`tests rc=2`, `audit rc=99`). The test imports have been repaired using the established `tools/diagnostics` path convention. Rerun the gate on the repaired HEAD before interpreting any attribution result.

Proceed in this order:

1. rerun `tools/diagnostics/combat_host_privateer_rob_cloak_fuel_attribution_audit.py` and its targeted tests on the repaired HEAD;
2. inspect the cleaner subset requiring damage0, effective Warp0, unchanged T position, no submitted inbound/outbound transfer and no foreign owner-current ship at the T-1 Rob origin;
3. compare exact/zero/other debit in that clean subset;
4. inspect all 14 stable low-fuel controls: 3 rows with `fuel==reference_cost` and 11 with `fuel<reference_cost`;
5. require their fuel transition, `true_to_true/true_to_false`, VCR state and T-1 ion/Loki/Glory context to be reported explicitly;
6. if clean exact-reference debit remains dominant and low-fuel controls show a coherent threshold transition, define an evidence-scoped effective-state helper and rerun the initial-target differential before touching canonical pair selection;
7. if clean attribution or low-fuel controls contradict the threshold model, reject the 5-KT explanation rather than special-case ship118;
8. keep Bird Super Spy ship202 separate from Privateer Rob ship98;
9. no `selection.py`, `queue.py`, target-order, STANDARD priority or Friendly Code parser change until the effective state closes;
10. after initial blocker closure, promote the canonical first selector and rerun candidate/target differentials;
11. compose mutable survivor/destruction state, second-pass orientation and capture continuation;
12. place ship-to-planet repair boundary and integrate planet/base participation;
13. keep game `591478` separate.

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
13. Training environment and AI after simulator/observer surfaces are sufficiently faithful.

## Wider milestones

Planning estimates only:

```text
M0 deterministic skeleton:          ~90%+
M1 minimal sandbox/infrastructure: ~80-90%
M2 economy/planetary Host:         ~35-50%
M3 warfare overall:                ~65-75%
M4 race-specific mechanics:        ~35-50%
M5A historical corpus pipeline:    ~75-85%
M5B Nu compatibility/differential: ~60-75%
M6 training/AI:                    intentionally later
```

`M3 warfare` is lower than the combat-only estimate because complete minefield lifecycle and several special/race interactions are not yet integrated end-to-end.

Do not shortcut unresolved Host rules merely to begin training sooner.
