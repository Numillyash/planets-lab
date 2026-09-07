# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

Current durable checkpoints:

- movement: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md);
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md);
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md).

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

Movement has reached a subsystem checkpoint. Classic pairwise combat and ordinary ship battle-sequence carry-over have now also reached explicit compatibility checkpoints. The immediate work is **C4 planet/starbase battle sequences**, followed by the missing Host combat phase around the resolver: engagement eligibility, battle order, side assignment, diplomacy/PE/mission interaction, multi-player queues, and planet/starbase participation.

Do not reopen bounded movement or ordinary ship-sequence residual hunting unless a contradiction blocks a larger Host subsystem.

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

This boundary has a separate Host repair step and is not a strict same-phase carry oracle. The eight damage rows move to C4/Host-phase reconstruction; do not patch the Classic pairwise resolver to force them closed.

## Immediate next work — C4 planet/starbase sequences

Proceed in this order:

1. reconstruct consecutive ship-vs-planet/starbase battles at the same planet in factual VCR order;
2. distinguish plain planet defense from starbase defense;
3. determine which planet/base combat state persists between attackers and which state resets;
4. verify ship state entering the planet phase, including documented between-phase repair;
5. preserve fail-closed handling for surviving damaged bases when exact persistent defense split is not recoverable;
6. compare simulated planet/base terminal state against the next factual planet VCR wherever an independent oracle exists;
7. keep game `591478` special mechanics separately labeled;
8. only after C4 move to Host engagement eligibility/order/side assignment and diplomacy/PE/mission interaction.

## Host reconstruction order after combat sequence checkpoints

Proceed in this order unless evidence forces a dependency change:

1. **Movement checkpoint** — substantially reconstructed; reopen only for bounded contradictions/interactions.
2. **Classic pairwise combat C1/C2** — extracted and complete for current replay corpus.
3. **Ordinary ship battle sequences C3** — `DIFF_VERIFIED` on clean same-phase historical chains.
4. **Planet/starbase sequences C4** — current immediate focus.
5. **Full Host combat ordering / engagement selection** — eligibility, queues, side assignment, PE/mission/diplomacy and capture continuation.
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
- **M3 warfare:** materially advanced: Classic pairwise replay and ordinary ship sequence carry-over are now canonical in `planets-lab`; planet/base sequencing and Host engagement order remain open.
- **M4 race mechanics:** partial; Federation shield recovery now has scoped differential evidence.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active; movement and ordinary ship combat sequences have explicit subsystem checkpoints.
- **M6 training/AI:** later, after required simulation/observer surfaces are sufficiently faithful.
