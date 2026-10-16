# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

Current durable checkpoints:

- finite-fuel Tow documented reconciliation: [`handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md`](handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md);
- verified partial-fuel historical gate: [`handoff/2026-09-09-partial-fuel-historical-gate-verified.md`](handoff/2026-09-09-partial-fuel-historical-gate-verified.md);
- movement: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md);
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md);
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md);
- planet/starbase sequences: [`handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md`](handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md).
- external client/plugin mechanics references: [`handoff/2026-09-27-external-planets-tools-mechanics-reference.md`](handoff/2026-09-27-external-planets-tools-mechanics-reference.md).
- engine-core internet research pass: [`research/2026-09-28-engine-core-internet-research-pass.md`](research/2026-09-28-engine-core-internet-research-pass.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

External implementations are candidate generators only. Kecupo VCR Sim,
nu-replayer, c2nu, nupilot, McNimble plugins, SitRep, T-Continuum Analyser and
similar projects may identify formulas, edge cases, API fields or public games
worth testing, but they do not create evidence labels by themselves. See the
2026-09-27 external reference catalog for the source-by-source boundary.

## Current focus

**October 16, 2026 priority reset — C5 bounded freeze / M2 active.**
After the V27 archival Chunnel/visibility retrospective, further serial
C5 short-Chunnel and Horwasp residue chasing is PAUSED. The previously
verified ordinary non-capture queue remains bounded at 22/22 held-out
next-VCR comparisons, but complete Host queue, capture O-branch LEFT/RIGHT,
unresolved site arrivals and mixed ship/planet combat remain open and
fail closed. No new universal Host activation rule is promoted.

**Active implementation work is now M2 planetary economy/production
integration and independent historical validation.** Reuse the already
implemented `PlanetaryHostPipeline` instead of restarting formula research.
First operational checkpoint:
`docs/handoff/2026-10-16-c5-bounded-freeze-m2-active.md`
and the 3-turn deterministic `planetary_multiturn_baseline_v1`
runner. That internal baseline has **zero NuHost historical differential
claims**; the next M2 acceptance must explicitly evaluate real
owner-current T-1/T planet snapshots and abstain on unattributable Host
and player-order interactions.

Historical corpus infrastructure **M5** remains available as the
research data foundation, not a reason to block M2 while explaining
individual Chunnel episodes. Production `planets-intel`, main combat
executor, immutable corpus CURRENT, and draft PR #28 remain untouched.


**October 14, 2026 scope decision:** temporarily park Horwasp-specific
postcombat mass, clan losses, fighter-feedback activation and VCR-order
micro-investigations. The evidence is retained as unresolved, not promoted.
Resume the broader ordinary **non-Horwasp C5 Host combat queue** integration,
prioritizing capture/parent-queue continuation and genuinely held-out next-VCR
selection before returning to exotic combat physics. Keep the existing
`combat-planar-no-horwasp` FeatureScope rather than adding ad hoc
per-example exclusions. Full handoff:
[`2026-10-14-horwasp-park-c5-restart.md`](handoff/2026-10-14-horwasp-park-c5-restart.md).

Movement, including the base finite-fuel Tow mass/proration rule, Classic pairwise replay, ordinary ship battle-sequence carry-over, and the attributable ordinary repeated-planet persistence layer now have explicit subsystem checkpoints.

The immediate combat work is the missing **Host combat phase around the resolver**:

- engagement eligibility;
- battle ordering / queues;
- side assignment;
- Priority Intercept / Primary Enemy / mission interaction;
- diplomacy / Safe Passage / alliance effects;
- capture continuation;
- planet/base participation in the full multi-player queue;
- the documented ship-to-planet phase boundary, including between-phase repair.

Do not reopen bounded movement, ordinary ship-sequence, or plain-planet sequence residual hunting unless a contradiction blocks a larger Host subsystem. The base finite-fuel Tow movement rule is closed; Tow contests/chains/cycles and mine/web/Chunnel/storm interaction ordering remain separately scoped and fail closed where unresolved.

The external-tool survey creates a bounded supporting backlog alongside the
combat-order work, without replacing it:

- compare Kecupo VCR Sim and nu-replayer against the existing combat resolver to
  identify concrete disagreements worth historical discrimination;
- mine immutable archive messages using nuWebBounty/nuSweepFC signatures for
  Crystal Web and Safe Passage/mine-scan evidence;
- use c2nu/PMS as parser/API shape cross-checks;
- use T-Continuum Analyser only to discover candidate public games that fill
  explicit Feature Index gaps, then ingest through official Planets.nu sources.

These are opportunistic evidence accelerators, not a new top-level milestone.

The 2026-09-28 engine-core search identified c2ng as the strongest currently
available independent rules implementation and JHOST/JPHost as a high-priority
server-side PHost-derived source-recovery target. These remain REFERENCE ONLY:
use them to enumerate candidate rules and discriminators, never to promote NuHost
mechanics without the normal documentation/corpus/test/differential chain.

## Planning progress snapshot — 2026-09-11

These are approximate planning estimates, **not evidence labels** and not substitutes for differential validation:

- ordinary/Classic movement core: roughly **90%** reconstructed at the rule level; remaining work is dominated by bounded interactions and special/campaign mechanics rather than basic movement geometry/fuel;
- Classic pairwise combat plus ordinary survivor/planet persistence: roughly **75–80%** of the low-level combat state-transition layer; the pairwise resolver is strong, but Host still has to decide who fights whom, in what order, and on which side;
- full Host combat engagement/order layer: roughly **30–35%**; factual VCR replay is mature, predictive queue generation is not yet reconstructed end-to-end;
- overall reverse-engineering understanding of the ordinary Classic core: roughly **60–65%**;
- overall high-fidelity end-to-end Host surface needed before serious self-play: roughly **45–50%**.

The apparent gap between the last two numbers is intentional: several mechanics are understood in isolation but are not yet integrated into a complete Host-order prediction pipeline. Large breadth items still remain after combat ordering: planetary production, complete minefield lifecycle, general missions and special abilities, diplomacy, race-specific rules, observer/visibility semantics and complete-turn differential validation.

## Runtime-verified movement accounting

The recorded compiled-layer counters remain the latest L1/L2 rebuild checkpoint. A later bounded server gate at candidate `f68a31376ff41810d72df0f3fadc165ff55e1017` validated the continuous nominal one-turn fuel basis against the existing 12-game historical corpus without rebuilding L1/L2.

The planner candidate introduced by `993e76046c3ffaa40acf4b0aa7286d5bd9573480` is now scoped:

```text
Move Most + Intercept true-partial normal movement
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Key gate results:

```text
pytest                                      371 passed
Move Most true partial rows                  15560
Move Most differing cost basis                2927
Move Most discriminators                         1
nominal-support discriminators                    1
projected-support discriminators                  0
Intercept fuel-limited support             1 -> 2
Intercept contradictions                   1 -> 1
missing archives                                0
```

The independent discriminators are `360690/T164/ship41` (Move Most) and `620694/T73/ship278` (Intercept). Targeted confounder checks found no already-modelled mine/storm/damage/Tow/Chunnel explanation for the supporting cases.

The separate finite-fuel Tow chain is now also closed for its base movement rule. Runtime candidate `bc3b767330dc23ed09303eed766365fa53877209` produced one cleaned discriminator at `360690/T41`:

```text
pre-Alchemy combined exact       0
post-Alchemy combined exact      1
post-Alchemy tower-only exact    0
Alchemy mass-basis discriminator 1
combined-mass discriminator      1
```

The factual endpoint `(2183,2688)` is reproduced only by post-Alchemy combined tower+towed mass (`2163 KT`) with `124/131` proportional insufficient-fuel movement. Official Nu documentation independently specifies towed-mass inclusion, post-Alchemy movement-mass evaluation and proportional insufficient-fuel distance. Scoped status:

```text
base finite-fuel Tow movement
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

This does not promote unresolved Tow topology or external interaction ordering. Snapshot fuel remains pre-Host evidence and is not automatically movement-phase fuel outside attributable cases. A later `planets-intel` transfer must preserve those boundaries.

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
- base finite-fuel Tow post-Alchemy combined-mass proportional movement — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multiplicity — `TESTED + DIFF_VERIFIED`;
- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict mine/web interruption v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict Nu waypoint-distance fuel proration v6 — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- continuous nominal one-turn fuel basis for true-partial Move Most / Intercept — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
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

## Corpus feature index and historical-game selector — v1 implemented

The M5 corpus now has a deterministic Game / Host Feature Index:

```text
schema: planets-lab.game-feature-index.v1
storage: normalized typed Parquet + DuckDB view game_features
```

Sources remain factual and attributable: tracked `/game/loadinfo` manifests,
immutable `/game/loadall` archives and compatible existing compiled metadata.
Third-party analyzers are discovery/UX references only.

The index preserves strict unknown semantics and per-feature provenance. Current
12-game manifest settings include factual Sphere/topology, Production Queue,
PLS/ship-limit values, combat RNG, Cloak+Intercept, campaign/diplomacy switches,
cloning and relevant race/special flags.

The settings-strict named selector `ordinary-classic` currently selects:

```text
360690
511506
620694
```

It excludes Standard-style, custom/campaign, Sphere and Horwasp populations by
explicit factual predicates and reports every mismatch/UNKNOWN predicate.

One existing diagnostic, Classic combat corpus parity, now accepts optional
feature-index preselection. `all-indexed` is an integration control and must
produce identical evidence-bearing output to the baseline.

Tracked gate:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

The index remains selection infrastructure, not a new evidence label or mechanic
observation.

Detailed state:
`docs/handoff/2026-09-21-corpus-feature-index-v1.md`.

Archive-enriched v1 gate is now runtime-verified on all 12 immutable cached games:

```text
rows=1152
known=1116
unknown=36
deterministic rebuild exact
ordinary-classic=360690,511506,620694
combat parity integration exact=true
```

Runtime:
`docs/handoff/2026-09-21-corpus-feature-index-v1-runtime.md`.


Feature Index is now also being integrated into mechanics diagnostics. A separate
`combat-planar-no-horwasp` profile preserves the historical 11-game C3/C4
scope without hardcoding a special game id. Planet-chain, ship-chain phase and
ship-chain cluster diagnostics now use selector-backed selected/excluded/UNKNOWN
partitions.

Archive continuity gate is now verified exactly:

```text
selector partition shared            true
C3 checkpoint preserved              true
C4 checkpoint preserved              true
cluster partition preserved          true
failures                              []
```

Durable runtime:
`docs/handoff/2026-09-21-combat-feature-scope-selector-runtime.md`.

Combat diagnostics now share `src/planets_lab/corpus/feature_scope.py`; the
selector contract explicitly separates selected, known-excluded and UNKNOWN
games. The continuity gate checks those partitions for overlap in addition to
the historical C3/C4 counters.

## Immediate next work — Host combat phase

Current transition handoff:

`docs/handoff/2026-09-21-new-chat-combat-engagement-order.md`

The first bounded action in the next session is the final archive-host rerun of
`tools/run-combat-feature-scope-gate.sh` against actual GitHub `main`. If the
shared `FeatureScope` path preserves the previously accepted C3/C4 populations
and disjoint selector partitions, close selector plumbing and return immediately
to substantive Host engagement/order reconstruction.

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

1. **Movement checkpoint** — substantially reconstructed, including the base finite-fuel Tow mass/proration rule; reopen only for bounded contradictions/interactions.
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
- **M3 warfare:** materially advanced: ordinary movement including base finite-fuel Tow, Classic pairwise replay, ordinary ship sequences and attributable ordinary repeated-planet persistence are canonical in `planets-lab`; full Host engagement ordering remains open.
- **M4 race mechanics:** partial; Federation shield recovery has scoped differential evidence.
- **M5A historical corpus:** active and operational; deterministic Game / Host Feature Index v1 is implemented for bounded corpus selection.
- **M5B Nu compatibility matrix:** active; movement, base finite-fuel Tow and ordinary Classic combat sequence checkpoints are explicit.
- **M6 training/AI:** later, after required simulation/observer surfaces are sufficiently faithful.


### Active combat gate: selector-backed predictive ship queue

Current integration restores the previously validated C5 canonical primitives
for engagement/order, initial STANDARD selection, occurrence-aware side
assignment, mutable survivor/capture state and post-mutation selection.

The immediate runtime gate is now one command:

```bash
bash tools/run-combat-predictive-queue-gate.sh
```

It must first preserve the shared FeatureScope C3/C4 checkpoints, then reproduce
the historical held-out ordinary queue population with zero next-VCR mismatches.
Do not advance to broader complete-site or mixed planet ownership mechanics if
that gate is not exact.


### Predictive ordinary ship queue — runtime closed

Archive-host runtime at `21435cd15c9744e00d958e0e271b9b8a8fd483ad`
passed the combined shared-scope + held-out queue gate.

For both strict and conditional exact-set profiles:

```text
23 multi-VCR sites
16 exact sites
7 capture-predecessor exclusions
22 compared transitions
22 exact
0 mismatch
```

Shared FeatureScope continuity remained exact with no failures.

Status for the bounded non-capture ordinary plain-STANDARD predictive queue:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Durable runtime:
`docs/handoff/2026-09-22-combat-predictive-queue-runtime.md`.

The immediate residual is post-capture candidate-graph reconstruction after
owner/race transfer; do not reopen the already exact non-capture queue path.


### Active capture residual — LEFT/RIGHT only

The capture path has advanced beyond the earlier reintegration checkpoint.

Closed observed ship-capture layers now include:

```text
capture continuation identity/state       closed
special Tow/Intercept geometry             2 / 2 exact
post-capture candidate graph               8 / 8 exact
post-capture active membership             8 / 8 exact
post-capture pair eligibility/phase        8 / 8 resolved
pair phase                                 8 / 8 STANDARD
captured-FC phase sensitivity              8 / 8 invariant
```

The remaining bounded ship-to-ship capture blocker is post-capture
**LEFT/RIGHT side assignment**. Current independent controls are not universal:

```text
opponent_initiator_right                   7 / 8 exact
neutral captured orders + fresh FC         6 / 8 exact
sticky capture side                        4 / 8 exact
frozen T-1 priority                        4 / 8 exact
neutral orders + preserved FC              4 / 8 exact
```

Do not promote a side rule from the current eight observations. The next primary
mechanics action is to enlarge the independent public archive population, harvest
additional attributable ship-capture continuations, split them into discovery
and held-out validation subsets, and only then freeze/test a side rule.

Current checkpoints:

`docs/handoff/2026-09-28-main-combat-corpus-checkpoint.md`

`docs/handoff/2026-09-28-main-public-corpus-backfill-round1-runtime.md`.

The second canonical automatic backfill runtime increased the compatible public
corpus to 32 / 36 indexed games. Four newly selected replacements remain
legacy/binary `.trn` failures. The acquisition runner now performs bounded
multi-round backfill within one invocation, reusing the existing 159-game
loadinfo candidate pool and immutable archive cache until the target converges,
the candidate supply cannot restore it, or `MAX_BACKFILL_ROUNDS` is reached.
Do not rediscover the candidate pool.

Current corpus runtime:
`docs/handoff/2026-09-28-main-public-corpus-backfill-round2-runtime.md`.

Detailed capture runtime:
`docs/handoff/2026-09-24-combat-capture-runtime.md`.

### Public corpus ingest performance checkpoint

The 2026-09-29 storage/runtime benchmark rejected full extracted-archive caching
as a useful optimization: game 233558 improved only from 1:40.74 to 1:36.61 for
the read+JSON pass while requiring 8.91 GiB extracted from a 0.64 GiB ZIP.
The selected corpus would require about 123.95 GiB block-rounded.

The primary bottleneck was repeated derivation across backfill rounds. Ingest now
reuses compatible previous per-game index records for immutable cached archives,
and the archive normalizer uses one CRC-checking member pass. Full rebuild
remains available with `--no-reuse-index`.

Checkpoint:
`docs/handoff/2026-09-29-public-corpus-ingest-benchmark.md`.

The first full-pipeline reuse validation completed six backfill rounds in 2m52s,
with all 35 successful games served from `index-cache`. Six replacement
archives were independently rejected as legacy/binary and the corpus remained
35 / 36. Since replacement failures are now cheap, the default bounded
`MAX_BACKFILL_ROUNDS` is 24 rather than 6; selection policy itself is
unchanged.

### Public validation corpus stabilized — 36 / 36

Canonical runtime
`runtime-logs/public-validation-corpus/20260929T150456Z_253258f5f870`
closed the acquisition gate on backfill round 15. Game `306971` supplied the
final compatible slot:

```text
games indexed        36 / 36
games failed          0
snapshots        126418
transitions      125862
settings hashes      36
```

Do not continue public-corpus backfill for the active C5 blocker. The immediate
next action is the deterministic **discovery-only** public capture-side harvest;
held-out rows remain sealed until a candidate LEFT/RIGHT rule is frozen.

Checkpoint:
`docs/handoff/2026-09-29-public-corpus-stabilized-runtime.md`.

### Public capture-side discovery: 50 ship continuations

Canonical runtime
`runtime-logs/public-capture-side-discovery/20260929T212837Z_745a7bbe4976`
scanned only the deterministic discovery partition: 20 games scanned, 16
held-out games unscanned.

The discovery population contains 61 post-capture continuations, including 50
ship→ship cases. Factual prize sides are LEFT 37 / RIGHT 13; 46 / 50 are first
occurrences of the prize/opponent pair. The generic opponent-initiator-right
control is only 37 / 50 and sticky capture side is only 22 / 50, so neither is
promoted.

The next discovery pass enriches those same cases with targeted T-1 order/FC
priority context and re-evaluates the earlier C5 priority controls. It reads only
the required owner-perspective T-1 members, not full prepared-game caches.
Held-out remains sealed.

Checkpoint:
`docs/handoff/2026-09-30-public-capture-side-discovery-runtime.md`.

## Corpus DB v1 infrastructure workstream

Branch feature/corpus-db-v1 owns a separate storage migration prototype.

The objective is to retain ZIP/TRN as immutable evidence while mirroring the
same player/perspective/entity semantics into a shared DuckDB generation stored
outside both research checkouts and readable concurrently by both normal and
external-reference containers.

The first gate is game-233558 only: direct mirror, no deltas or semantic dedup.
It must pass full member-level semantic parity and disk/runtime/RSS/concurrent
reader benchmarks before scaling to the 36-game public corpus.

See docs/corpus-db/ARCHITECTURE.md, SHARED_ACCESS.md, WORKSTREAM.md and
NEW_CHAT_START.md.



### Corpus DB v1 prototype implementation checkpoint — 2026-09-30

The dedicated `feature/corpus-db-v1` branch now contains the first direct
ZIP/TRN -> DuckDB implementation for the game-233558 gate. The importer is
member-streaming rather than whole-game snapshot based, preserves full source
semantics through lossless JSON fallback rows, records archive/member provenance,
and refuses publication unless archive integrity plus type-sensitive full-member
round-trip parity are green.

Shared storage is exposed through `PLANETS_CORPUS_DB_ROOT` mounted at
`/corpus-db`; the normal and external research containers use the same
immutable published generation read-only. Tracked runners also measure fresh-
process T-1/T and VCR/site query wall time/RSS and concurrent two-container
reads.

The corrected typed1 game-233558 runtime is now green end-to-end:
6710 / 6710 full semantic parity, native typed entity storage, 3.06 GB DuckDB
from 9.57 GB decoded JSON, bounded indexed queries, and simultaneous read-only
access from both research containers. This is a 74.23% reduction versus the
first 11.87 GB v1 physical layout and removes the per-entity JSON duplication
that caused the earlier regression.

The storage workstream has since advanced through typed1 and compact public36
to the ACTIVE compact public68 backend. Canonical active runtime:

```text
68 archives
169569 / 169569 exact semantic parity
17847300096-byte DuckDB (~16.622 GiB)
no entity_rows
no decoded member fallback blob
no secondary indexes
shared normal/external read PASS
```

The current storage optimization milestone is complete. The guarded CURRENT
switch has activated public68; retain compact public36 as the first rollback.
Further physical improvements are deferred in
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`; do not spend mechanics time on
additional compression unless a documented reopen criterion is met.

Canonical runtime:
`docs/handoff/2026-10-02-corpus-db-compact-public36-runtime.md`.


### Compact CURRENT activation completed — public68 active 2026-10-04

The accepted combined compact public68 generation is now active through
`CURRENT`:

```text
corpus-v2compact-public68-20261004T095236Z-09f71721b77c
169569 / 169569 exact parity
shared normal/external read PASS
```

The previous compact public36 generation remains available as the first
rollback. The corpus DB storage milestone is closed; resume NuHost mechanics on
the new independent population. Deferred storage ideas remain in
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.

Activation checkpoint:
`docs/handoff/2026-10-04-corpus-db-public68-current-activation.md`.

## Public capture side held-out result

The pre-heldout capture-side candidate was frozen at
`cd87f9505472e5e396db28a7d6f7c67c561f9c64` and independently tested against
the sealed public held-out partition.

Result: **FAILED** — 27/29 exact, 1 mismatch, 1 unresolved.

The mismatch is game 476380 turn 223: a reachable captured-LEFT prize flips to
RIGHT. The unresolved row is a same-turn repeated-capture chain in game 257776
turn 230, where the intermediate owner has no valid T-1 source state; mutable
post-capture order state must be carried from the prior capture.

Do not change the old frozen rule and call the gate passed. Any replacement
candidate is held-out-informed and requires a new independent evidence
population before promotion.

See
`docs/handoff/2026-10-03-public-capture-side-heldout-result.md`.

## Post-heldout capture-side candidate

The frozen pre-heldout capture-side rule failed independently at 27/29 exact
with one real mismatch and one repeated-capture unresolved row.

After opening the former held-out population, a new research-only candidate
fits all 60 adjacent rows:

```text
reachable sticky                    20/20
nonreachable neutral/fresh-FC       38/38
second-occurrence reversal           1/1
reachable numeric-opponent override  1/1
                                     -----
                                     60/60
```

This is not validation. The new numeric-opponent and repeated-capture branches
are heldout-informed. Canonical promotion now requires a new independent
population, preferably prospective private game 686764 and/or public games not
present in public36.

See:

`docs/handoff/2026-10-03-postheldout-capture-side-candidate.md`.

### Public68 independent capture-side validation — failed candidate

The frozen post-heldout candidate was independently tested against the new
short32 population after public68 activation.

Independent gate:

```text
short32 games                         32
overlap with public36                  0
adjacent capture continuations        22
candidate exact                       21
candidate mismatch                     1
candidate unresolved                   0

reachable sticky                       9
nonreachable neutral/fresh-FC          6
second-occurrence reversal             1
reachable numeric-opponent override    6

status                       FAILED_MISMATCH
promotion_ready                        false
```

The counterexample is game `341336`, turn `75`, VCR `338 -> 339`:
captured ship `211` remains LEFT against ship `369`, despite opponent
numeric priority `[0, 4, 369]`. The opponent has mission `3` (Kill).

The previous numeric-group-0 override is therefore rejected as universal.

After opening short32, a Kill-sensitive research candidate fits the combined
82 / 82 adjacent rows: reachable numeric group-0 opponents preserve LEFT when
the opponent is Kill, while the two observed numeric LEFT -> RIGHT flips are
non-Kill mission-1 cases. This new candidate is post-independent-informed and
is explicitly NOT canonical.

Implementation:

`tools/diagnostics/combat_public_capture_side_postindependent_candidate.py`

Checkpoint:

`docs/handoff/2026-10-05-public68-capture-side-independent-result.md`.

### Prospective post-independent validation corpus

The replacement Kill-sensitive capture-side candidate is frozen at
`46bcb08c2f0d3f0449b97921edb03ab6647f7d3b`.

The next validation population is a second independent public short corpus that
excludes all 68 games already open in public68. Acquisition is predeclared as:

```text
final turn         80..180
slots               8..16
loadinfo probes       320
selected games         32
baseline games         68
```

Runner:

`tools/run-public-postindependent-validation-acquisition-with-evidence.sh`

The future validation gate must not claim promotion merely from zero mismatches.
It requires fresh independent coverage of both changed numeric-LEFT
discriminators: group-0 Kill and group-0 non-Kill. Missing either yields
`INSUFFICIENT_DISCRIMINATOR_COVERAGE`.

The new games will be built into a separate exact-parity compact generation;
canonical public68 `CURRENT` remains unchanged during validation.

Handoff:

`docs/handoff/2026-10-05-postindependent-validation-acquisition-ready.md`.

### Public100 prospective capture-side validation — failed C proxy

The frozen Kill-sensitive post-independent candidate was tested against the
second fresh 32-game population using the explicit exact-parity public100
generation.

```text
fresh games                         32
adjacent capture rows               20
candidate exact                     19
candidate mismatch                   1
candidate unresolved                 0

fresh numeric Kill LEFT              1
fresh numeric non-Kill LEFT          1

status                  FAILED_MISMATCH
promotion_ready                   false
```

Both numeric Kill/non-Kill discriminators passed. The failure is instead the
first LEFT-oriented O-not-reachable row:

```text
game 597079 T19 VCR17 -> 18
captured ship14
capture LEFT
factual next side RIGHT
identity-anchored order [14, 172, 185]
prize < factual opponent < capture target
```

This demonstrates that the old
`O-not-reachable -> neutral orders + fresh symbolic FC` branch was a proxy.
All earlier such cases were RIGHT -> LEFT, so the proxy never saw the opposite
orientation.

Across the now-open 102 adjacent rows, the minimal structural replacement is:

```text
O reachable:
    retain the existing post-independent O-side rules

O not reachable / capture-created C order:
    prize side = opposite(capture side)
```

The C-order side flip fits 58 / 58 open C rows:

```text
RIGHT -> LEFT  57
LEFT  -> RIGHT  1
```

The complete post-prospective bounded candidate fits 102 / 102 open adjacent
rows but is explicitly NOT canonical because public100 prospective evidence
informed the replacement rule.

Implementation:

`tools/diagnostics/combat_public_capture_side_postprospective_candidate.py`

Checkpoint:

`docs/handoff/2026-10-05-public100-capture-side-prospective-result.md`

Next validation should be controlled rather than another broad random public
corpus. Private game `686764` is the preferred prospective oracle: force a
LEFT capture followed by a C-forward continuation, freeze the candidate first,
and validate the predicted RIGHT side. Private/live data must remain separate
from immutable public100.

Immediate mechanics priority is new prospective/independent discrimination of
numeric group-0 Kill versus non-Kill post-capture side behavior. Do not reuse
public68/short32 as validation for the new candidate.

