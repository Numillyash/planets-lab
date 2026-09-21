# Combat feature-scope selector migration — archive runtime verified

Date: 2026-09-21

Repository: `Numillyash/planets-lab`
Branch: `main`

Runtime source HEAD:

```text
2b75c9ec079b55e4219f2a64e569b6a5d708e6ae
```

Command:

```bash
bash tools/run-combat-feature-scope-gate.sh
```

Full runtime log:

```text
artifacts/combat-feature-scope-v1/gate.log
```

## Acceptance result

The selector-backed combat scope migration passed exactly.

```json
{
  "checks": {
    "cluster_partition_preserved": true,
    "planet_c4_checkpoint_preserved": true,
    "selector_partition_shared": true,
    "ship_c3_checkpoint_preserved": true
  },
  "exact": true,
  "failures": [],
  "profile": "combat-planar-no-horwasp",
  "schema": "planets-lab.combat-feature-scope-integration-check.v1"
}
```

This runtime changes no mechanics evidence labels. It verifies that replacing the
old ad-hoc game-id partition with factual Feature Index predicates preserves the
existing historical C3/C4 populations and results.

## Feature index rebuilt from immutable corpus

```text
games                 12
rows                  1152
known_rows            1116
unknown_rows          36
missing_archives      []
parquet_sha256        cb72f539775d22726d8d7f225fc7b3deeb8f936312873df12db59340e1dd7735
```

The Parquet SHA matches the previously accepted Feature Index v1 archive build.

## Scope selector

Profile:

```text
combat-planar-no-horwasp
```

Predicates:

```text
game.status == 3
settings.sphere == false
population.horwasp_present == false
```

Included 11 games:

```text
360690
511506
620636
620694
620917
621103
621253
621896
622476
680435
680910
```

Excluded:

```text
591478
```

The exclusion is factual:

```text
settings.sphere = true
population.horwasp_present = true
```

UNKNOWN selector predicates:

```text
none
```

No diagnostic in this migrated block needs to special-case the numeric game id
to construct the clean scope.

## C4 planet-chain continuity

Full factual population remains:

```text
archives                         12
raw_vcr_observations          22256
unique_vcrs                    6469
payload_conflicts                 0
replay_supported               6469
planet_appearances             3719
candidate_same_turn_planet_chains 110
same_location_transitions       136
```

Selector-backed clean scope:

```text
profile_selected_all:
  transitions       103
  match             102
  not_comparable      1
  mismatch            0

  starbase            92
  no_starbase         11
  shield carry       103/103
```

No-starbase exact path remains:

```text
transitions                       11
exact carry match                 10
start reconstruction mismatch      1
next-state exact mismatch          0
shield carry                      11/11
```

Starbase shield persistence remains:

```text
92/92 exact
```

Excluded scope is the former special population:

```text
transitions                    33
match                          17
not_comparable                  9
mismatch                        4
reappearance_after_defeat       3
shield match                   28
shield mismatch                 2
```

## C3 ship-chain continuity

Full factual chain population remains:

```text
same_location_transitions  1485
ship_vs_ship->ship_vs_ship  938
ship_vs_ship->ship_vs_planet 544
ship_vs_planet->ship_vs_planet 3

survived   1431
destroyed    29
captured     25
```

All 25 captured reappearances still change owner.

Selector-backed clean scope:

```text
profile_selected_all:
  transitions                    1169
  match                          1138
  reappearance_after_capture       23
  mismatch                          8
```

Strict same-phase survivor oracle:

```text
profile_selected_ship_vs_ship_survivors:
  transitions 764
  match       764
  mismatch      0
```

Strongest globally adjacent subset:

```text
profile_selected_ship_vs_ship_survivors_gap1:
  transitions 751
  match       751
  mismatch      0
```

Ship-to-planet boundary remains:

```text
transitions                    397
match                          374
reappearance_after_capture      15
mismatch                         8
problem signature           damage
```

The eight damage-only phase-boundary residuals are unchanged.

Excluded scope:

```text
transitions                    316
match                           81
mismatch                       204
reappearance_after_destroyed    29
reappearance_after_capture       2
```

All true destroyed reappearances therefore remain outside the selected clean
scope without using a hardcoded game id.

## Cluster continuity

```text
profile_selected same-location transitions = 1169
profile_excluded same-location transitions = 316
profile_unknown transitions                = 0
```

Race-1 Federation shield accounting remains unchanged:

```text
transitions               48
match                     48
both                       28
federation_candidate      20
shield mismatches           0
```

## Evidence boundary

This runtime validates population-selection equivalence only.

Existing mechanics statuses remain exactly as before:

```text
ordinary same-phase ship carry:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

Federation between-fight +25 shield recovery:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

plain-planet repeated engagement carry:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

starbase shield persistence:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

No new mechanic is promoted from a selector match.

## Result

The first mechanics workstream migrated to Feature Index scoping is closed:

```text
hardcoded game-id scope removed
factual profile predicates used
UNKNOWN fails closed
C3 checkpoint preserved exactly
C4 checkpoint preserved exactly
cluster partition preserved exactly
mechanics conclusions unchanged
```


## Shared scope API follow-up

After the successful archive runtime, selector plumbing was consolidated into:

```text
src/planets_lab/corpus/feature_scope.py
```

API:

```text
FeatureScope
load_feature_scope(...)
optional_feature_scope(...)
```

`FeatureScope` owns:

- index/profile metadata;
- selected game IDs;
- known-mismatch excluded game IDs;
- UNKNOWN game IDs;
- per-game classification;
- JSON-safe report metadata.

Partitions are explicitly disjoint:

```text
selected ∩ excluded = empty
selected ∩ unknown  = empty
excluded ∩ unknown  = empty
```

An unindexed game classifies separately as `unindexed` and is never silently
treated as selected.

The following combat diagnostics now consume the shared resolver:

```text
combat_classic_corpus_parity_audit.py
combat_planet_chain_audit.py
combat_ship_chain_phase_audit.py
combat_ship_chain_cluster_audit.py
```

The base `combat_ship_chain_audit.py` does not construct a special-game clean
scope and therefore does not need selector plumbing.

The continuity checker now gates both historical C3/C4 counts and disjoint scope
partitions.

Full GitHub Actions after the shared resolver refactor reached:

```text
390 passed
```

A final archive-host rerun of `tools/run-combat-feature-scope-gate.sh` is the
runtime acceptance for the refactored shared path.
