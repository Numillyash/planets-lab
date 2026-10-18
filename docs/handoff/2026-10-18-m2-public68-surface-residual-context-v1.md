# M2: baseline68 mineral surface-residual context, observational V1

Date: 2026-10-18.

## Fixed scientific question

Published evidence from `runtime-logs` identifies, among **13,023** conditionally comparable planet×mineral observations over **136** baseline68 adjacent perspective-turn pairs:

| Status | Count |
|---|---:|
| Both ground and surface match default model | 11,813 |
| Ground matches; only surface residual | **915** |
| Surface matches; only ground residual | 33 |
| Neither matches | 262 |

The immediate task is **NOT** to change the mining rate to explain 915 surface residuals. We must first quantify *which visible covariates* co-occur with the residual classes: own ships at planet coordinates, co-observed cargo changes, starbases explicitly tied to the planet, and changing planetary structures/tax fields.

## Implementation

`src/planets_lab/corpus/m2_surface_residual_context.py` is a pure observational profiler; it is wired into the existing read-only `m2_economy_coverage.py` pass.

For each of the SAME baseline-only previously selected planet pairs and four mineral types, it independently recalculates the current **conditional candidate** default model from T−1, with exactly the original gates: stable mines, valid unchanged density, numeric surface+underground stocks and stable standard race. It classifies each eligible planet×mineral record in **one** of the four disjoint classes above.

Then it counts per-mineral and per-class covariates:

- planet's coordinate pair is explicitly numeric at each time (otherwise abstain);
- owner ship **observed at the same coordinate** before, after, or at both snapshots, and the same own ship ID observed at that site at both snapshots; a missing ship or missing ship array is never proof of no ship activity;
- ship cargo for the relevant mineral both numerically available; whether **exactly one** same-ID co-site ship has an **opposite** cargo delta to the surface model residual. This is only an arithmetic **candidate** for stock exchange, not a shipment order or a proven transaction;
- explicit starbase `planetid` and own `ownerid` matched to the planet before, after, or both (never infer from Starbase ID = Planet ID), plus available technology-field changes; presence is not equivalent to executed construction;
- observed unchanged versus changed planet mines, factories, defenses and two tax-rate fields;
- absolute surface residual magnitude buckets and residual direction;
- source quality/abstentions for missing coordinates, stale ship infoturn, absent ship infoturn, duplicate ship IDs, missing starbase owner or starbase planet link.

Ships missing `infoturn` remain an explicit `OWNER_SHIP_INFOTURN_UNAVAILABLE` limitation. Neither same-location matching nor cargo opposition proves there were no intervening ship actions: these are T−1/T *post-Host* archival snapshots, not authenticated client orders.

The new `surface_residual_context_not_host_verified` aggregate sample section includes no IDs, per-object values, notes, friendly codes or credentials. Game IDs are held only transiently inside the process for **game-level clustering bins**, never emitted. This avoids pretending the 13,023 mineral observations are independent experiment samples.

## Fail-closed invariants

The new classification's four categories are reconciled for **each mineral** against the already present `conditional_mineral_mass_balance_not_host_verified` counts:

    category_both = both_stock_deltas_match_default_model
    ground_only = ground_delta_matches_default_model - category_both
    surface_only = surface_delta_matches_default_mining - category_both
    neither = qualified - ground_exact - surface_exact + category_both

If independent computation differs even once (including denominator mismatch), the diagnostic fails rather than publishing a misleading report. It does **not** mutate the original model rules.

The existing `m2_validate_corpus_aggregate_evidence_v1.py` allows the **new aggregate-count-only** section for publication. It still rejects raw ship data, dictionaries containing arrays, credentials and unexpected root fields.

The corpus guard remains unchanged: explicit public100 generation SHA256, **all 100 games metadata census**, entity reconstruction only for **baseline68**, sealed 32-game heldout untouched, `CURRENT` unchanged.

## One next runtime-evidence run

The source code and synthetic CI tests do **not** have access to the user's 26.65-GiB database. The source-specific 915-class covariates will become *actual measurements* only after a server run. Use the established evidence wrapper directly:

~~~bash
cd /root/projects/planets-lab &&
git fetch origin &&
git switch main &&
git pull --ff-only origin main &&
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-surface-residual-context-v1/report.json \
  bash tools/run-m2-public100-economy-coverage-v1-with-evidence.sh
~~~

This will hash the existing corpus (sequential ~26.65-GiB read), perform only the *same* 136 baseline68 sampled pairs, and automatically publish `gate.log`, `metadata.json` and the **aggregate-only** report to `runtime-logs`.

Before examining new scientific claims, assert the recorded frozen selection SHA256 still equals

`b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f`

and conditional model class totals remain **11813/915/33/262**. The new code refuses a divergence in those totals.

## Subsequent M2 research gates

If the 915 observations are disproportionately associated with candidate opposite ship-cargo deltas, use that finding to prioritize a **separate** authenticated order-input investigation, not to rewrite mineral mining automatically.

If few ships match but starbase/context covariates differ, investigate actual **construction cost/order information** and game-specific abilities. Absence of visible own ships does not exclude other ships, stale contacts or special mechanics.

Next compute *per-game* and *per-window* clustering before confidence intervals or model promotion. Never use sealed heldout games for posthoc tuning. C5, production IntelBoard, combat simulation, existing corpus generations and original source artifacts remain unchanged.
