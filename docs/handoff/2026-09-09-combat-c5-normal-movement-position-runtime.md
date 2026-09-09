# C5 Host combat — T-1 normal-movement position runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains open/draft. Game `591478` remains excluded from ordinary promotion.

## Runtime source

```text
5da7144a9a1c2940b4d6e07c13f88b08274a90af
```

Artifact:

```text
artifacts/combat-c5-normal-movement-position-20260909-225503
```

Targeted tests and historical audit both completed successfully:

```text
tests rc=0
audit rc=0
payload_conflicts=0
archives_considered=11
```

The tested audit schema was:

```text
planets-lab.combat-host-normal-movement-position-audit.v2
```

## Coverage result

Ship occurrences:

```text
factual_ship_occurrences = 3204
position_predicted        = 1810
position_exact            = 1800
position_mismatch         = 10
position_uncovered        = 1383
```

Predicted-source population:

```text
normal_move_warp_well = 874
normal_move           = 765
stationary            = 171
```

Factual pairs:

```text
factual_pairs      = 1986
position_exact     = 677
position_mismatch  = 9
position_uncovered = 1300
```

Sites:

```text
sites                            = 1220
all_factual_pairs_position_exact = 345
has_position_mismatch            = 7
has_position_uncovered           = 869
```

Compared with candidate-set v1, independently position-covered factual pairs increased from `1/1986` to `677/1986` without using factual T ship position as predictor input.

## Explicit uncovered population

The fail-closed first-pass movement boundary remains substantial:

```text
tow_target                     374
intercept_movement             313
tow_attempt                    261
pre_move_mkt_mass_change       238
hyperjump_movement              53
potential_chunnel_source_stack  48
outbound_transfer               47
inbound_transfer                21
cloak_intercept_movement        14
normal_plan_insufficient_fuel   14
owner_current_missing           11
```

These are coverage gaps, not movement contradictions.

## Residual population

Only ten predicted factual ship occurrences disagree with the factual combat site, corresponding to nine factual pairs and seven sites.

```text
360690 / T54  / ship26  owner6  normal_move_warp_well  predicted 2384,1532  factual 1783,1121
360690 / T114 / ship238 owner2  normal_move            predicted 2037,2480  factual 2063,2487
360690 / T114 / ship440 owner11 normal_move_warp_well  predicted 2037,2478  factual 2063,2487
511506 / T95  / ship332 owner5  normal_move            predicted 2715,1999  factual 2716,1999
620694 / T62  / ship83  owner8  normal_move_warp_well  predicted 1783,1437  factual 1773,1443
620694 / T117 / ship450 owner2  normal_move            predicted 1593,1864  factual 1598,1891
620694 / T128 / ship146 owner10 normal_move            predicted 1869,1719  factual 1891,1704
620694 / T128 / ship214 owner10 normal_move            predicted 1869,1719  factual 1891,1704
620694 / T128 / ship278 owner10 normal_move            predicted 1869,1719  factual 1891,1704
680910 / T14  / ship65  owner8  normal_move_warp_well  predicted 2312,1921  factual 2313,1937
```

The repeated common displacement within some battle turns is only a diagnostic lead. It is not by itself evidence for ion storms, Tow, Chunnel, mines or another mechanic.

## Evidence status

```text
position-audit v2 helper/tests:              TESTED
1800 exact factual ship occurrences:         CORPUS_OBSERVED
677 exact factual pairs:                     CORPUS_OBSERVED
10 mismatching ship occurrences:             CORPUS_OBSERVED residuals
stationary/normal position layer generally:  NOT YET promoted as zero-residual DIFF_VERIFIED
```

The large exact population is useful and materially expands candidate-set coverage, but the ten residuals must be either mechanically explained or moved back to an explicit uncovered class before candidate-set v2 treats the corresponding position source as clean.

## Immediate gate

Committed after this runtime:

```text
tools/diagnostics/combat_host_normal_movement_position_residual_audit.py
tests/test_combat_host_normal_movement_position_residual_audit.py
```

The residual audit consumes the exact saved position `report.json` and classifies only its complete mismatch population. It reuses existing movement reconstruction rather than inventing new formulas:

- authoritative archived `nuionstorms` setting when recoverable;
- exact mode-aware ion-storm endpoint classification, including storm/warp-well composition;
- existing strong `DIFF_VERIFIED` mine-hit classifier;
- post-state route-equivalent observed Tow evidence.

Post-turn state and observed Tow routes are attribution-only. They must never become candidate-set predictor inputs.

If a residual is explained by an external/random movement mechanic that cannot be independently predicted from T-1, the correct integration is to make that precombat position source `uncovered`, not to copy the factual endpoint.
