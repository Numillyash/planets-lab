# C5 Host combat — storm-aware position v3 runtime

GitHub is the source of truth. This checkpoint records the user-run historical differential for the repaired full storm-aware T-1 -> precombat position audit.

## Runtime source

```text
14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c
```

Artifact:

```text
artifacts/combat-c5-position-v3-repaired-20260909-235856
```

Runtime:

```text
tests rc=0
audit rc=0
payload_conflicts=0
storm modes: nuionstorms_false=10, nuionstorms_true=1

ship occurrences:
  factual=3204
  predicted=1810
  exact=1806
  mismatch=4
  uncovered=1383
  normal_move_ion_storm=6

factual pairs:
  total=1986
  exact=678
  mismatch=4
  uncovered=1304

sites:
  total=1220
  all factual pairs position-exact=346
  mismatch sites=4
```

The repaired raw-archive `nuionstorms` resolver restored the complete deterministic population that the first invalid v3 run had accidentally failed closed. All six previously attributed classic-storm residuals are now predicted independently through `normal movement -> ion storm -> warp well`; no new mismatch appeared among the former 1,800 exact v2 rows.

## Remaining four rows

```text
360690/T54/ship26
511506/T95/ship332
620694/T62/ship83
680910/T14/ship65
```

The focused attribution runtime is recorded separately in `2026-09-09-combat-c5-unresolved-movement-context-runtime.md`.

- `620694/T62/ship83`: exact one-hit low-tech scaled-floor endpoint + hostile normal-field crossing + factual VCR-start damage `0 -> 40`, exactly one normal-mine quantum. Specific row attribution: `CORPUS_OBSERVED + DIFF_VERIFIED`.
- `680910/T14/ship65`: exact one-hit low-tech scaled-floor endpoint + battle-turn normal-field crossing + factual VCR-start damage `0 -> 30`, exactly one normal-mine quantum. Specific row attribution: `CORPUS_OBSERVED + DIFF_VERIFIED`; the field is not present in T-1 evidence, so it is attribution-only and not a predictor input.
- `360690/T54/ship26`: bounded unresolved; no exact storm/mine/Tow/route-equivalent Chunnel attribution.
- `511506/T95/ship332`: bounded unresolved; tech 7 and zero VCR-start damage delta reject promotion to the low-tech mine-slowdown explanation despite a degenerate short-waypoint geometric match.

## Evidence boundary

The deterministic covered position layer is now `TESTED + DIFF_VERIFIED` for the audited stationary/ordinary-normal-movement/storm/warp-well scope. It is not a complete movement predictor: Tow, Intercept/C&I, HYP, Chunnel-source stacks, transfer/MKT, fuel-proration and other explicitly unresolved branches remain fail-closed.

The four residual rows are not patched with factual coordinates. Candidate-set v2 must admit only independently predicted site membership and report stochastic/unresolved movement separately.

Next gate: site-conditioned candidate-set v2 using the validated position predictor for all owner-current T-1 ships, with known T-1 foreign mine/web route risk failed closed before pair eligibility is evaluated.
