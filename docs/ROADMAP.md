# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

Current durable checkpoints:

- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md) — two ordinary non-PIA side residuals inspected; symmetric T-1 diplomacy rejects the asymmetry hypothesis; causality open, next gate is narrow source-state/VCR context for the same two cases;

- movement: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md);
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md);
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md);
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

Movement, Classic pairwise replay, ordinary ship battle-sequence carry-over, and the attributable ordinary repeated-planet persistence layer now have explicit subsystem checkpoints.

The immediate combat work is the missing **Host combat phase around the resolver**:

- engagement eligibility;
- battle ordering / queues;
- side assignment;
- Priority Intercept / Primary Enemy / mission interaction;
- diplomacy / Safe Passage / alliance effects;
- capture continuation;
- planet/base participation in the full multi-player queue;
- the documented ship-to-planet phase boundary, including between-phase repair.

Do not reopen bounded movement, ordinary ship-sequence, or plain-planet sequence residual hunting unless a contradiction blocks a larger Host subsystem.

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
post_mine_strong_residual           2203
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

Current generic movement residual landscape:

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

These remain bounded evidence-mining targets, not a requirement to reach zero residuals before continuing the simulator.

## Combat integration checkpoint

### C1 — Classic resolver extraction

Completed:

- imported the deterministic Classic VCR resolver into `rules/combat`;
- preserved c2ng/PCC2 BSD attribution;
- kept dashboard DB/API/UI dependencies out of the canonical mechanics layer;
- added independent unit tests.

### C2 — Nu adapter and historical replay coverage

Current historical corpus:

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

Battle-shape population from C2:

```text
ship_vs_planet  3719
ship_vs_ship    2750
```

Raw `combatrng` is available in factual RST for all processed turn members; no inferred settings manifest is needed.

C2 evidence status:

```text
CORPUS_OBSERVED + TESTED
```

C2 alone is replay coverage, not an independent terminal-state proof.

### C3 — ordinary ship battle sequences

C3 compares deterministic terminal state from factual VCR N against factual start state in the next same-turn/same-location appearance of the same ship.

Final corpus sanity:

```text
raw_vcr_observations      22256
unique_vcrs                6469
replay_supported           6469
ship_appearances           9219
candidate_ship_turn_chains 1015
same_location_transitions  1485
metadata_conflicts            0
```

Phase distribution:

```text
ship_vs_ship -> ship_vs_ship      938
ship_vs_ship -> ship_vs_planet    544
ship_vs_planet -> ship_vs_planet    3
```

Strong ordinary same-phase survivor oracle:

```text
ship_vs_ship -> ship_vs_ship
transitions  764
match        764
mismatch       0
```

Per-field:

```text
damage      764 / 764 exact
crew        764 / 764 exact
torpedoes   764 / 764 exact
fighters    764 / 764 exact
shield      764 / 764 exact-carry or scoped Federation recovery
```

Strongest globally adjacent subset:

```text
VCR gap = 1
transitions  751
match        751
mismatch       0
```

This promotes ordinary Classic ship battle sequence carry-over to:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Federation recovery closure

Historical race-1 chains reject the imported `25% of missing shields` interpretation. The current corpus supports:

```text
next_shield = min(100 - damage, shield + 25)
```

Across 48 race-1 transitions:

```text
exact/both             28
federation_candidate   20
shield mismatch          0
```

Scoped evidence status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Exact-zero shield crew correction

C3 exposed a port mismatch against upstream c2ng `HostAlgorithm::hit()`: a hit that takes positive shields exactly to zero does not apply crew damage on that same hit. Correcting Nu replay ordering removed all 20 crew-only mismatches from the strict ordinary ship-to-ship survivor subset.

### Capture and special-game boundary

Across the full C3 chain population:

```text
terminal survived    1431
terminal captured      25
terminal destroyed     29
```

All 25 captured reappearances change owner. True `destroyed -> reappeared` transitions are confined to special/campaign/Horwasp-heavy game `591478`, so they are not generalized into ordinary Classic carry-over.

### Ship-to-planet phase boundary

Ordinary `ship_vs_ship -> ship_vs_planet` transitions retain eight damage-only mismatches after C3 cleanup:

```text
transitions                  397
match                        374
reappearance_after_capture    15
mismatch                       8
problem signature         damage
```

This boundary has a separate Host repair step and is not a strict same-phase carry oracle. Do not patch the Classic pairwise resolver to force these rows closed.

### C4 — ordinary planet/starbase battle sequences

C4 compares replay terminal planet/base state from factual VCR N against the factual start state of the same planet in VCR N+1.

Corpus population:

```text
raw_vcr_observations               22256
unique_vcrs                         6469
replay_supported                    6469
planet_appearances                  3719
candidate_same_turn_planet_chains    110
same_location_transitions            136
```

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

#### Plain-planet exact carry

For factual `hasstarbase=false`, C4 infers candidate persistent DP as:

```text
planet_defense = combat_mass - 100
```

The inferred state must reproduce the factual first VCR before it is accepted into the carry oracle.

Final ordinary no-starbase result after correcting native planet beam-tech rounding:

```text
transitions                      11
exact next-state match           10
start reconstruction mismatch     1
next-state mismatch               0
shield carry match               11 / 11
```

The ten comparable rows reproduce the entire next factual combatant. Supported carry includes proportional DP damage, generated planetary fighter losses reducing DP, drained shield persistence and re-derived combat state.

Evidence status for the supported ordinary plain-planet path:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The sole remaining non-comparable ordinary row has zero active beams and differs only in inactive `beamid` metadata (`0` vs `1`); it is not promoted as a combat mismatch and the strict audit is left unchanged.

#### Native planet beam tech

The first C4 gate showed six ordinary rows whose only mismatch was factual `beamid = imported_value + 1`. The corpus supports nearest-integer native beam tech:

```text
ROUND(SQRT(DP / 2))
```

with tech clamped to the supported 1..10 range for positive DP. Threshold regressions are covered by tests.

#### Starbase shield persistence

All ordinary repeated starbase defenders preserve terminal shield into the next factual VCR:

```text
92 / 92 exact
```

Evidence status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

This does **not** promote hidden post-hull-damage starbase defense state.

#### Starbase fail-closed boundary

A surviving starbase with non-zero planet hull damage remains fail-closed because factual VCR state does not uniquely expose the resulting persistent:

```text
starbase defense
starbase beam tech
starbase accumulated damage
```

The zero-hull-damage starbase carry helper is `TESTED`; the hidden damaged-base branch remains unresolved.

#### Special game 591478

Game `591478` remains separated from ordinary promotion:

```text
transitions                    33
match                          17
not_comparable                  9
mismatch                        4
reappearance_after_defeat       3
shield match                   28
shield mismatch                 2
```

Do not generalize these special/campaign/Horwasp residuals into ordinary Classic planet rules.

## Immediate next work — Host combat phase

Proceed in this order:

1. reconstruct full factual combat queues by turn/location from ordered VCRs;
2. determine engagement eligibility and opponent selection for ordinary Classic cases;
3. reconstruct side assignment / left-right rules separately from pairwise resolution;
4. integrate Priority Intercept / Primary Enemy / mission semantics only where IDs and behavior are established;
5. incorporate diplomacy, Safe Passage and alliance/team effects;
6. model capture continuation in the same Host phase rather than as a pairwise resolver property;
7. place the documented ship-to-planet repair boundary between ship and planet combat phases;
8. integrate planet/base participation using the C4 persistence layer while keeping hidden damaged-starbase state fail-closed;
9. keep game `591478` and other special/campaign mechanics separately labeled until attributable.

The next goal is not merely to replay an already supplied VCR. It is to predict the **set, order and sides of VCRs Host will generate** from the factual co-located game state.

## Host reconstruction order after combat sequence checkpoints

Proceed in this order unless evidence forces a dependency change:

1. **Movement checkpoint** — substantially reconstructed; reopen only for bounded contradictions/interactions.
2. **Classic pairwise combat C1/C2** — extracted and complete for current replay corpus.
3. **Ordinary ship battle sequences C3** — `DIFF_VERIFIED` on clean same-phase historical chains.
4. **Planet/starbase sequences C4** — attributable ordinary plain-planet carry and starbase shield persistence checkpointed; hidden damaged-starbase state remains fail-closed.
5. **Full Host combat ordering / engagement selection** — current immediate focus: eligibility, queues, side assignment, PE/mission/diplomacy and capture continuation.
6. **Planet economy + starbases + ship production**.
7. **Minefield lifecycle** — laying, decay, sweep, web drain, visibility, diplomacy/FC interactions and ordering.
8. **General missions + special ship abilities**.
9. **Diplomacy / Safe Passage / alliance / team semantics across all subsystems**.
10. **Race-specific mechanics**, integrated vertically rather than as an isolated final pass.
11. **Observer / visibility / fog-of-war / shared intel** for player-safe agent input.
12. **End-to-end Host-order differential validation** over complete turns.
13. **Training environment and AI** — historical baselines first, then simulator/self-play once the required Host surface is sufficiently complete.

The target remains a high-fidelity NuHost-compatible simulator suitable for real-game evaluation and later self-play. Do not shortcut unresolved Host rules merely to begin training sooner.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress.
- **M3 warfare:** materially advanced: Classic pairwise replay, ordinary ship sequences and attributable ordinary repeated-planet persistence are canonical in `planets-lab`; full Host engagement ordering remains open.
- **M4 race mechanics:** partial; Federation shield recovery has scoped differential evidence.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active; movement and ordinary Classic combat sequence checkpoints are explicit.
- **M6 training/AI:** later, after required simulation/observer surfaces are sufficiently faithful.
