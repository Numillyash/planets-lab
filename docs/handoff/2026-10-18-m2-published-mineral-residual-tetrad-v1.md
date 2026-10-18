# M2: disjoint mining residuals from the published baseline68 aggregate

Date: 2026-10-18.

## Provenance: fetched from GitHub, NO rerun

This analysis uses only the report already published via
runtime evidence. The original 26.65-GiB DuckDB was **not**
reopened, reread or modified in this step.

Published evidence:

- Branch: `runtime-logs`
- Source commit: `d8a548b57a2647a9430a8a17f537ba1960618051`
- Path: `runtime-logs/m2-public100-coverage-existing-v1/20261018T031202Z_d8a548b57a26/artifacts/planetary/m2-public100-mineral-balance-v1/report.json`
- Evidence metadata: `exit_code: 0`, source dirty false
- Database SHA256:
  `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`
- 136 metadata-frozen adjacent archive pairs, baseline68 only;
  heldout32 not inspected. Selection SHA256:
  `b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f`.

## What the existing report identifies precisely

Each of the following 13,023 mineral×planet-pair comparisons has
numeric unchanged mine count, unchanged valid mineral density and
consistent recorded player race. Conditional default mining +
published trans-uranium mutation generates a predicted surface
delta and a separate predicted underground delta. The already
recorded marginal exact counts imply this disjoint 2×2 table:

| Mineral | Qualified | Both exact | Underground only exact, surface residual | Surface only exact, underground residual | Neither exact |
|---|---:|---:|---:|---:|---:|
| Neutronium | 3256 | 2976 | 202 | 7 | 71 |
| Duranium | 3255 | 2955 | 226 | 11 | 63 |
| Tritanium | 3256 | 2943 | 242 | 7 | 64 |
| Molybdenum | 3256 | 2939 | 245 | 8 | 64 |
| **Total** | **13023** | **11813** | **915** | **33** | **262** |

Arithmetic, for each mineral:

    ground_only = ground_exact - both_exact
    surface_only = surface_exact - both_exact
    neither = qualified - ground_exact - surface_exact + both_exact

The four categories are mutually exclusive and sum to the
denominator. No per-game reanalysis or private records are
necessary for this reconciliation.

- Both exact: 11,813 / 13,023 = **90.71%**.
- Among the 1,210 conditional mismatches, 915 (75.62%) have a
  **correct predicted underground delta but a residual surface
  delta**.
- Only 33 (2.73%) match surface but not underground.
- 262 (21.65%) miss both.

The 13,023 measurements are correlated mineral observations
nested in 3,769 planets and 136 perspective-transition pairs
from 68 games; the percentages are **descriptive**, NOT
13,023 independent scientific validation samples or proof
of host algorithm parity.

## Priority and limits

The asymmetry suggests triaging **surface-stock context**
before refitting the mining rate or mutation formula. Plausible
unmeasured contributors include loading/unloading of ships,
production/building expenditure, and special game mechanics.
The reported 915 mismatches DO NOT authenticate any specific
cargo transfer, nor show that the underground formula is
causally correct. Similarly, the 262 joint mismatches cannot
be assigned to mining without independent action witnesses.

Follow-on scientific gates before attributing causes:

1. Keep the sealed 32-game holdout untouched.
2. From baseline68 only, stratify the four disjoint residual
   classes by visible ship presence/position and starbase build
   context at both ends, **as covariates**, not inferred orders.
3. Preserve missing/stale ship or base information as explicit
   abstentions and avoid mixing different players' perspectives.
4. Keep owner-current planet provenance and exact frozen sample;
   only independently authenticated pre-Host TurnOrders plus
   verified next-turn state can upgrade to executed-mechanics
   evidence.
5. Report per-game clustering before any statistical confidence
   statement. Do not posthoc-tune on the 32-game heldout.

## Reproducible computation without corpus access

Reusable pure module:
`src/planets_lab/corpus/m2_mineral_residual_tetrad.py`.

CLI (optional, for a locally existing aggregate report):

~~~bash
python tools/diagnostics/m2_mineral_residual_tetrad_v1.py \
  --input artifacts/planetary/m2-public100-mineral-balance-v1/report.json
~~~

A separate optional `--output` writes a NEW aggregate summary
using exclusive-create mode; existing source evidence is never
overwritten. The module validates pinned corpus and selection
identity, baseline68/heldout32 separation, noncausal flags and
2×2 arithmetic. Synthetic tests pin all four published
per-mineral counts without including any real game IDs,
raw TRNs or HARs.

No new server run required, no new Host rule claimed, no changes
to C5, canonical combat, production IntelBoard, corpus CURRENT
or draft PR #28.
