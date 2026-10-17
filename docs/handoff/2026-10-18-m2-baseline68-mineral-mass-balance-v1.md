# M2 baseline68: mineral mass-balance against default mining/mutation candidate

Date 2026-10-18. Evidence: second actual public100 server run,
same frozen 136 baseline68 adjacent T−1/T perspective pairs and
3,769 same-owner owner-current planet pairs. Selection SHA256:
b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f.

## Observational motivation

Actual archival net-stock directions:

| Mineral | Surface increased | Underground decreased | Underground unchanged with surface increase |
|---|---:|---:|---:|
| Neutronium | 3448 | 510 | 2793 |
| Duranium | 3411 | 461 | 2801 |
| Tritanium | 3408 | 491 | 2739 |
| Molybdenum | 3432 | 414 | 2835 |

A rise in surface minerals with no change underground does not
prove unexplained generation. The existing MineralMiningPhase
reduces underground amount while adding to surface stock.
The separate TransUraniumMutationPhase increases underground
amount. Their combination can leave ground stock unchanged
and still increase surface cargo. This is a hypothesis, NOT
confirmation for the observed 2,700–2,800 cases per mineral.
Transfers, ship actions, ore condensation, campaign abilities,
and unobserved Host phases can all contribute.

The actual tax statistics also disambiguate tax and happiness:
ColonistTaxRate changed in 153 pairs (88 down/65 up);
NativeTaxRate in 177 (78 down/99 up);
NativeHappyPoints in 578 (157 down/421 up).
Because the groups overlap, adding those counts to estimate
unique tax orders would be invalid.

## Conditional arithmetic, fail-closed gates

For an independently qualified owner-current planet pair, for
each mineral with nonnegative numeric T−1/T stocks:

    ground_delta = ground_T - ground_Tminus1
    surface_delta = surface_T - surface_Tminus1
    total_delta = ground_delta + surface_delta

Require explicitly recorded, unchanged valid mineral densities
0..100 to compare total_delta with the published standard
trans-uranium mutation formula (rate=5). This arithmetic is a
NET observational comparison, not a Host execution witness.

The stricter candidate model requires a valid same-player race
identity in both archives (1..11), observed numeric and unchanged
mines, and stable density. Use T−1 mines/density/underground amount,
the project's existing INFERRED integer mining rule, published
race modifier and assumed 100% output modifier:

    expected_ground_delta = mutation - mining
    expected_surface_delta = mining

Count exact/mismatched individual ground and surface deltas,
joint exact candidates, and specifically those puzzling cases
with ground unchanged / surface increased. Count all abstentions
for missing/changed mines, density or race.

Binned aggregates report surface-increase magnitudes and absolute
residual against the default mutation-only mass balance. NO
game IDs, player IDs, per-planet mineral quantities, raw notes,
credentials or inferred orders are emitted.

Even two exact delta matches do NOT independently establish
the NuHost mechanism: unseen player orders or other phases
may cancel out. No Host-order execution status is promoted.

## Implementation and safety

New src/planets_lab/corpus/m2_mineral_balance.py adds pure,
offline hypothesis profiling. The already integrated
m2_economy_coverage.py accumulates the new results under
conditional_mineral_mass_balance_not_host_verified.
Synthetic tests validate a balanced case (five mines at 40%
density, 2 mined + 2 trans-uranium replenishment), an
unexplained larger surface gain, stale-owner rejection and
missing or changing input abstentions.

Same explicit SHA256-pinned immutable public100 source.
Metadata census of all 100 games, entity sampling ONLY from
the authorized baseline68. The sealed 32-game heldout stays
untouched. No new database, no CURRENT mutation, no alteration
of canonical mining formulas, C5, production or draft PR #28.

## One follow-up server command

From existing server checkout after the PR is merged:

    cd /root/projects/planets-lab &&
    git fetch origin &&
    git switch main &&
    git pull --ff-only origin main &&
    M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-mineral-balance-v1/report.json bash tools/run-m2-public100-economy-coverage-v1.sh

The prior report is not overwritten. Verify the frozen metadata
selection SHA256 above remains unchanged. Interpret results
as conditional client/archival observations, not independently
verified Host mining execution.
