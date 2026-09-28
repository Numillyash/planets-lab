# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

New chats should start from:

[`handoff/2026-09-05-new-chat-context.md`](handoff/2026-09-05-new-chat-context.md)

Current movement checkpoints:

- [`handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md`](handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md)
- [`handoff/2026-09-09-partial-fuel-historical-gate-verified.md`](handoff/2026-09-09-partial-fuel-historical-gate-verified.md)

External reference/corpus-discovery policy:

- [`handoff/2026-09-27-external-planets-tools-mechanics-reference.md`](handoff/2026-09-27-external-planets-tools-mechanics-reference.md)
- [`research/2026-09-28-engine-core-internet-research-pass.md`](research/2026-09-28-engine-core-internet-research-pass.md)

Third-party tools may propose candidate game ids, message signatures, formulas or
field interpretations, but the compiled corpus accepts evidence only from our
own attributable official Planets.nu acquisition. A game discovered via
T-Continuum Analyser, a replay tool or a plugin catalog must still pass:

```text
external discovery
-> official loadinfo / loadall
-> immutable archive + provenance
-> feature-index classification
-> bounded diagnostic
```

Likewise, a formula seen in an external simulator remains a candidate until a
clean corpus discriminator and local test justify the applicable evidence label.

## Current verified schema state

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
```

Raw `/game/loadall` archives remain unchanged. Prepared projection stays privacy-minimal; raw `.trn` evidence is read directly only by diagnostics that need narrowly scoped historical metadata.

## Game / Host feature index v1

Implemented schema:

```text
planets-lab.game-feature-index.v1
```

The immutable `loadall` ZIP archives remain the evidence source. The feature
index is deterministic compiled selection infrastructure built from:

- the tracked privacy-safe `/game/loadinfo` manifest;
- immutable cached `/game/loadall` archives when locally present;
- existing compiled movement per-game metadata where its semantics already fit.

Default compiled outputs:

```text
validation/corpus/compiled/v1/metadata/game_features.parquet
validation/corpus/compiled/v1/metadata/game_feature_build.json
validation/corpus/compiled/v1/corpus.duckdb -> view game_features
```

The normalized row model is:

```text
schema_version
game_id
feature
value_type
known
bool_value / int_value / double_value / text_value
source_kind
source_location
```

Unknown is explicit and never coerced to a default:

```text
unknown != false
missing != disabled
not present != zero
```

Current tracked manifest coverage is 12 games. Major settings are factual 12/12,
including Sphere, Production Queue, PLS/ship-limit fields, `combatrng`,
Cloak+Intercept, campaign mode, diplomacy limits, cloning and ground-attack
adjustments.

Current explicit UNKNOWN fields include:

```text
engine.host_version
engine.engine_version
game.short_description   # current manifest predates its allowlist
```

The manifest builder now safely allowlists public `shortdescription` for future
refreshes. No Host/engine version is inferred from date/name/configuration.

Archive-derived counters include turn coverage, VCR raw/unique/shape counts,
payload conflicts and relation availability. Missing archives make those
counters UNKNOWN. Partial relation-field coverage makes total relation count
UNKNOWN rather than zero.

Reusable selector API/CLI:

```text
src/planets_lab/corpus/feature_index.py
src/planets_lab/corpus/feature_index_cli.py
```

Named `ordinary-classic` uses an explicit settings-strict Classic rule
signature rather than treating `gametype=2` as Classic. On the current tracked
manifest it selects:

```text
360690
511506
620694
```

and has zero UNKNOWN predicates for that profile.

Existing integration proof consumer:

```text
tools/diagnostics/combat_classic_corpus_parity_audit.py
  --feature-index ...
  --feature-profile ...
```

The `all-indexed` control must preserve its evidence-bearing replay output
exactly.

Reproducible archive-enriched gate:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

GitHub Actions also compiles the actual current 12-game manifest twice without
gitignored archives and byte-compares the Parquet outputs. In that environment
archive-derived rows remain correctly UNKNOWN.

This index is an evidence-selection aid only:

```text
feature-index match
!= mechanic observation
!= discriminator
!= DIFF_VERIFIED
```

Detailed handoff:
`docs/handoff/2026-09-21-corpus-feature-index-v1.md`.

Archive-enriched acceptance runtime:

```text
HEAD      68ed7006732c22273b47a5e915d7c2ed9b4e1f74
archives  12/12
rows      1152
known     1116
unknown   36
parquet   cb72f539775d22726d8d7f225fc7b3deeb8f936312873df12db59340e1dd7735
rebuild   byte/SHA exact
selector  360690, 511506, 620694
combat integration exact=true, mismatches=[]
```

Runtime handoff:
`docs/handoff/2026-09-21-corpus-feature-index-v1-runtime.md`.

Mechanics integration adds a second named profile:

```text
combat-planar-no-horwasp:
  game.status == 3
  settings.sphere == false
  population.horwasp_present == false
```

On the current 12-game corpus it selects 11 games and excludes only the
Sphere/Horwasp game. This deliberately preserves the historical C3/C4 clean
scope while removing ad-hoc game-id checks. It is distinct from the stricter
3-game `ordinary-classic` profile.

Migrated diagnostics:

```text
combat_planet_chain_audit.py
combat_ship_chain_phase_audit.py
combat_ship_chain_cluster_audit.py
```

Runtime continuity gate:

```text
source HEAD                         2b75c9ec079b55e4219f2a64e569b6a5d708e6ae
selected games                      11
excluded games                       1
UNKNOWN selector games               0
C4 selected transitions            103
C3 selected transitions           1169
C3 ship->ship survivor            764/764
C3 adjacent ship->ship            751/751
integration exact                    true
failures                               []
```

Runtime handoff:
`docs/handoff/2026-09-21-combat-feature-scope-selector-runtime.md`.

Shared scope resolver:

```text
src/planets_lab/corpus/feature_scope.py
FeatureScope
load_feature_scope
optional_feature_scope
```

Combat parity, planet-chain, phase and cluster diagnostics now share this one
selector implementation. UNKNOWN is a disjoint fail-closed partition rather than
an alias for known exclusion.


## Current runtime-verified 12-game invariants

The compiled-layer counters remain the last recorded L1/L2 rebuild checkpoint. Later partial-fuel and finite-fuel Tow historical gates read these existing archives/caches without rebuilding L1/L2 and verified narrowly scoped movement rules independently.

L1:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13970
post_external_residual         3924
damage_limited_warp_match       10
```

L2:

```text
external_residual_rows             3924
chunnel_explained                  1421
post_chunnel_residual              2503
horwasp_strong_explained            240
post_horwasp_strong_residual       2263
mine_strong_explained                60
post_mine_strong_residual          2203
fuel_proration_explained              6
post_fuel_proration_residual       2197
label_issues                          0
```

The latest L2 rebuild processed all 12 games with zero failures, all prepared caches hit, and completed in about 102 seconds with `--jobs 2`.

## Partial-fuel historical gate

Server gate candidate:

```text
candidate  f68a31376ff41810d72df0f3fadc165ff55e1017
baseline   1d01bf20c745e84162b6c5ae249e0e81b0ccdc6c
planner    993e76046c3ffaa40acf4b0aa7286d5bd9573480
pytest     371 passed
archives   12 / 12 present
```

Move Most control population:

```text
prefilter_true_partial_rows              32371
true_partial_route                       15560
prefilter_false_positive                  1495
same_integer_cost                        12633
cost_basis_differs                        2927
projected_cost_endpoint_exact             2811
nominal_cost_endpoint_exact               2812
discriminating_endpoint                      1
discriminating_nominal_cost_support          1
discriminating_projected_cost_support        0
```

Intercept baseline -> candidate:

```text
fuel_endpoint_exact                     437 -> 438
fuel_endpoint_differs                    99 -> 99
fuel_limited_discriminating_support       1 -> 2
fuel_limited_discriminating_contradiction 1 -> 1
after_reset_supporting_only               0 -> 1
missing_archive                           0 -> 0
```

Independent discriminators:

- `360690/T164/ship41` Move Most supports continuous nominal one-turn fuel cost and rejects rasterized endpoint-distance cost;
- `620694/T73/ship278` Intercept supports the same nominal-leg basis and reproduces factual `(2742,2070)` with `29/72` fuel proration;
- `620636/T60/ship44` remains an independent proportional finite-fuel Intercept support case.

Targeted confounder checks found no already-modelled mine/storm/damage/Tow/Chunnel explanation for the two supporting limited-fuel Intercept cases. The unchanged `360690/T69/ship391` contradiction remains a snapshot-vs-phase-fuel boundary, not a new candidate regression.

Scoped evidence status:

```text
continuous nominal one-turn fuel basis for true-partial Move Most / Intercept
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Finite-fuel Tow is a separate evidence chain and is not inferred from this promotion.

## Finite-fuel Tow documented reconciliation gate

The finite-fuel Tow evidence chain first isolated strict owner-visible Tow transitions, then bounded warp-well, storm, Chunnel, break-independent-movement and web-context confounders. The final cleaned same-line case is `360690/T41`, tower `425`, target `353`.

Server gate candidate:

```text
candidate  bc3b767330dc23ed09303eed766365fa53877209
source     logs/finite-fuel-tow-same-line-context-resolution-20260911T123937Z-c0f954cf-11500
collected  logs/finite-fuel-tow-documented-reconcile-20260911T160149Z-bc3b7673-29099
stages     all 0/0
```

The towed hull is an Alchemy ship with an exact observed cargo conversion:

```text
supplies          2700 -> 0
minerals total       0 -> 900
mass reduction         1800 KT
```

Three competing models were evaluated against the factual endpoint `(2183,2688)`:

```text
model                         mass KT  fuel required/available  endpoint       exact
pre-Alchemy combined             3963          241 / 124        (2172,2712)     no
post-Alchemy combined            2163          131 / 124        (2183,2688)     yes
post-Alchemy tower-only           333           20 / 124        (2184,2685)     no
```

Gate summary:

```text
cases=1
pre_alchemy_combined_exact=0
post_alchemy_combined_exact=1
post_alchemy_tower_only_exact=0
alchemy_mass_basis_discriminator=1
combined_mass_discriminator=1
```

This is a clean historical discriminator for the documented rule: a successful finite-fuel Tow uses post-Alchemy combined tower+towed movement mass and proportional insufficient-fuel distance. Official Planets.nu documentation independently supplies all three semantics: towed-mass inclusion, mass evaluation after Alchemy, and proportional insufficient-fuel movement.

Scoped evidence status:

```text
base finite-fuel Tow movement
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The promotion is intentionally narrow. `360690/T44` and `360690/T185` remain bounded hostile-web damage context rather than Tow-fuel evidence. Tow contests/chains/cycles, deterministic web/mine hit location, Chunnel/storm interaction ordering, special/campaign behavior and any unimplemented end-to-end Alchemy phase remain separate boundaries.

## Current generic final endpoint

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

Residual clusters are investigation leads only; they are not mechanics without independent evidence.

## Verified / closed recent movement mechanics

- ordinary movement / Host major-minor geometry;
- warp-well ordering — **TESTED + DIFF_VERIFIED**;
- route-equivalent owner-visible Tow — **TESTED + DIFF_VERIFIED**;
- base finite-fuel Tow post-Alchemy combined-mass proportional movement — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Chunnel multiplicity — **TESTED + DIFF_VERIFIED**;
- classic/cloudy ion storms — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- scoped effective sphere topology for game `591478` — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict mine/web interruption v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict damage-limited maximum warp — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict Nu waypoint-distance fuel proration v6 — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- continuous nominal one-turn fuel basis for true-partial normal Move Most / Intercept — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- short-waypoint normal-mine scaled-floor exact classifier — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**; underlying low-tech slowdown itself is **DOCUMENTED**;
- Red Mite tracking/fallback research — closed absent new evidence.

Crystal Web Drain remains one attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition and is not production-labeled.

Rejected broad post-v6 leads for the dominant residual family: outbound fuel transfer, standard Cloak fuel burn, Privateer Rob Ship, and Stellar Cartography speed terrain.

## Short-waypoint normal-mine production closure

Production category:

```text
normal_mine_hit_scaled_floor_exact
```

Runtime-verified population:

```text
rows     = 23
games    = 6
hulls    = 9
Horwasp  = 0
```

By game:

```text
360690  10
511506   4
620694   5
620917   1
621103   2
680910   1
```

All 23 current corpus rows resolve to one damage hit and one slowdown hit.

The empirical planar click penalty used only by the narrow exact production path is:

```text
floor(10 * slowdown_hits * nominal_max_distance / regular_distance)
```

This expression is a corpus-observed classifier relation, not a claim about NuHost source code.

The production path is fail-closed and requires planar topology, hull tech below 7, hostile normal-field crossing, a true short waypoint, same-line shortened movement, direct or exactly reconstructed automatic-repair mine damage, a unique hit model, and an exact predicted Host major-axis endpoint. Sphere/unknown topology and ambiguous hit models are not promoted.

Independent pre-production evidence was:

```text
production planar controls:       15/15 within +/-1 click
strict residual planar resolved:  31/31 within +/-1 click
strict residual exact:            27/31
production-visible equivalence:   23/23 report-backed exact short-waypoint references
misses:                            0
extras:                            0
```

Full-corpus production diff:

```text
mine_strong_explained        37 -> 60
post_mine_strong_residual  2226 -> 2203
fuel_proration_explained      6 -> 6
post_fuel_proration_residual 2220 -> 2197
label_issues                  0 -> 0
```

The original `511506 / T23 / ship160 / hull17` survivor is now production-closed with one mine hit plus exact automatic supply repair (`0 + 76 -> 66 damage`, `53 -> 3 supplies`).

## Current test state

```text
feature index v1 GitHub Actions: 384 passed
feature index 12-game manifest deterministic rebuild: exact Parquet bytes
feature index ordinary-classic selector CLI: passed
movement-mine targeted module: 10 passed
full GitHub Actions pytest:    green on mechanics/test commit
partial-fuel server gate:      371 passed / all stages 0/0
finite-fuel Tow gate:          documented reconciliation all stages 0/0
full 12-game L2 rebuild:       clean / zero failures
final generic clustering:      2197 total / 740 generic / 75 hulls / largest coarse 113
```


## Predictive combat queue consumer

The current predictive ship-queue differential consumes the compiled Feature
Index only through shared `FeatureScope`, using profile
`combat-planar-no-horwasp`.

The selector is population infrastructure only. Factual VCR `N+1` remains
held out from selector input and is used only as the comparator after VCR `N`
terminal replay and active-queue mutation.

Tracked archive-host runner:

```text
tools/run-combat-predictive-queue-gate.sh
```

Generated queue reports remain under `artifacts/` and are not committed.


## Predictive queue runtime checkpoint

Fresh archive-host runtime of `tools/run-combat-predictive-queue-gate.sh` at
`21435cd15c9744e00d958e0e271b9b8a8fd483ad` preserved the shared FeatureScope
partition and the C3/C4 checkpoints.

Held-out next-VCR result:

```text
strict:      22 / 22 exact, 0 mismatch
conditional: 22 / 22 exact, 0 mismatch
capture predecessor exclusions: 7
```

The factual next VCR remains comparator-only. The next unresolved queue boundary
is rebuilding pair candidates after a combat capture changes ownership/race.

## Public validation corpus — first automatic backfill runtime

Published evidence:

```text
runtime-logs/public-validation-corpus/20260928T042502Z_10a08afdde89
source main 10a08afdde89ad98587970d81441caf8b6855567
exit_code 1
```

The first automatic failed-game replacement round improved the compatible
independent public corpus from 22 to 30 indexed games:

```text
selected games              36
indexed games               30
failed games                 6
snapshots               108599
transitions             108110
archive bytes        7987231325
settings hashes              30
```

Eight of the 14 replacement games indexed successfully. Six replacements remain
legacy/binary normalization failures:

```text
43082
68006
78375
138269
190004
190428
```

All six fail on non-UTF-8 `.trn` payload normalization rather than networking.
The published rejection ledger still contains the previous 14 failures because
the runner updates the rejection set at the start of each round from the prior
stats; the next rerun will absorb these six IDs before selecting replacements.

The original bucket target is still not fully reproduced:

```text
target:
  campaign       19
  championship    6
  finite_fuel     9
  sphere          2

after backfill selection:
  campaign       19
  championship    6
  finite_fuel    11

missing:
  sphere          2
```

This bucket-level gap is distinct from the raw setting inventory: the selected
manifest contains games with `settings.sphere=true`, but none occupies the
selector's lower-priority `sphere` bucket after campaign/championship
classification.

Capability metadata remains empty across the selected manifest:

```text
selected player slots                  594
non-empty activeadvantages slots         0
non-empty activehulls slots              0
```

Recovery remains bounded and resumable:

```bash
bash tools/run-public-validation-corpus-with-evidence.sh
```

Do not rediscover the 160-game candidate pool and do not delete immutable local
loadall cache. After the selected corpus stabilizes, proceed to the sealed
discovery-only capture-side harvest before opening held-out games.

Detailed checkpoint:
`docs/handoff/2026-09-28-main-public-corpus-backfill-round1-runtime.md`.

## Public validation corpus — second canonical backfill runtime

Published evidence:

```text
runtime-logs/public-validation-corpus/20260928T164728Z_ec20195891e9
source main ec20195891e937a65897a991c405de88c439b036
exit_code 1
```

The second canonical backfill round started from the 30 compatible games left by
round 1, rejected those six known binary archives, selected six new candidates,
and produced:

```text
selected games              36
indexed games               32
failed games                 4
snapshots               114209
transitions             113698
archive bytes        8455277299
settings hashes              32
```

Successful round-2 replacements:

```text
476380
633855
```

New binary normalization failures:

```text
22158
76301
124766
164693
```

The persisted rejection ledger at the start of this round contains 20 rejected
game ids. On the next backfill pass the four failures above are added from the
fresh stats before any replacement is selected.

The explicit selector bucket target still reports `sphere: 2` missing, while
raw `settings.sphere=true` remains present in selected records classified into
higher-precedence buckets. `activeadvantages` and `activehulls` are still
empty in all selected player slots.

Because discovery successfully probed 159 games, repeated manual one-round
invocations are unnecessary. The acquisition runner now performs up to six
backfill rounds in one invocation by default:

```text
ingest
-> fresh failed_game_ids
-> rejection ledger update
-> replacements from existing candidate pool
-> ingest
-> repeat, bounded by MAX_BACKFILL_ROUNDS
```

Successful immutable archives remain cached and are not redownloaded. The loop
stops on full ingest success, candidate shortfall, fatal backfill error, disabled
auto-backfill, or the configured round cap.

Detailed checkpoint:
`docs/handoff/2026-09-28-main-public-corpus-backfill-round2-runtime.md`.

