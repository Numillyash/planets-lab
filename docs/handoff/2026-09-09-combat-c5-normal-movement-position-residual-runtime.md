# C5 Host combat — normal-movement position residual runtime

Date: 2026-09-09

GitHub is the source of truth. This checkpoint records the bounded residual-attribution runtime that followed the v2 T-1 stationary/normal-movement position differential. Game `591478` remained excluded.

## Runtime source

```text
1d880ca6e0a1e0784f2fae4437c981ce71ac49ed
```

Input position artifact:

```text
artifacts/combat-c5-normal-movement-position-20260909-225503/report.json
```

Residual artifact:

```text
artifacts/combat-c5-normal-movement-position-residual-20260909-231621
```

Runtime status:

```text
targeted tests: 24 passed
tests rc=0
audit rc=0
```

## Residual accounting

```text
mismatch_rows=10
single_exact_context_family=6
unresolved=4
candidate_family_counts={'ion_storm': 6}
candidate_context_counts={'ion_storm_classic:ion_storm_drag': 6}
```

All six attributed rows resolve exactly under the archived authoritative setting:

```text
nuionstorms=False
```

No attributed row required a mine or Tow explanation.

## Exact classic ion-storm rows

```text
360690 / battle turn 114 / ship 238 / owner 2
360690 / battle turn 114 / ship 440 / owner 11
620694 / battle turn 117 / ship 450 / owner 2
620694 / battle turn 128 / ship 146 / owner 10
620694 / battle turn 128 / ship 214 / owner 10
620694 / battle turn 128 / ship 278 / owner 10
```

The T128 triplet is especially strong shape evidence: all three ships share the same ordinary navigation endpoint and receive the same exact classic-storm displacement into the factual combat site.

Evidence status for this bounded residual attribution:

```text
classic/cloudy storm mechanics:         previously DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
six combat-position residual matches:   CORPUS_OBSERVED + DIFF_VERIFIED
storm-aware combat predictor v3:        not yet runtime-tested
```

The residual audit used factual battle coordinates only as comparison targets. The next predictor must compute the storm vector from precombat state/settings without factual T position.

## Four unresolved rows

```text
360690 / battle turn 54  / ship 26  / owner 6 / hull 52
  origin=(2323,1568)
  ordinary prediction=(2384,1532)
  factual site=(1783,1121)
  delta=(-601,-411)

511506 / battle turn 95  / ship 332 / owner 5 / hull 31
  origin=(2716,1999)
  ordinary prediction=(2715,1999)
  factual site=(2716,1999)
  delta=(+1,0)

620694 / battle turn 62  / ship 83  / owner 8 / hull 69
  origin=(1744,1460)
  ordinary prediction=(1783,1437)
  factual site=(1773,1443)
  delta=(-10,+6)

680910 / battle turn 14  / ship 65  / owner 8 / hull 1102
  origin=(2315,1984)
  ordinary prediction=(2312,1921)
  factual site=(2313,1937)
  delta=(+1,+16)
```

For all four:

```text
storm exact context: none
strong DIFF_VERIFIED mine context: none
observed route-equivalent Tow context: none
```

Do not infer a new combat rule from these rows.

The `680910/T14/ship65` hull is the campaign Scorpius Class Carrier (`hull 1102`, tech 6). Its shortened route is a plausible lead for low-tech normal-mine slowdown / short-waypoint scaling, but the target ship has no owner-current post-turn survivor state in this residual report, so the existing strong mine classifier cannot establish the required damage trace. Treat this only as an `INFERRED` research lead until an independent field/route gate confirms or rejects it.

The huge `360690/T54/ship26` displacement is likewise not rounding or a small warp-well residual and must remain unresolved until a separate movement mechanism is independently identified.

## Integration rule

The six exact classic-storm rows may justify adding the already-validated authoritative storm phase to the T-1 position predictor because that vector is computable without factual battle position.

The four unresolved rows must not be patched with factual coordinates. Until their mechanism is known, either:

1. a T-1-visible risk/context guard makes them explicitly `uncovered`, or
2. a separately validated deterministic movement phase predicts them.

After storm-aware integration, rerun the full position audit across all ordinary factual combatants. Previously exact rows must also remain exact; residual-only success is insufficient.
