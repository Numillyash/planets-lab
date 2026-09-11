# Finite-fuel Tow passenger-Chunnel resolution runtime — 2026-09-11

GitHub is the source of truth. This handoff records completed server runtime evidence only. It does not promote a simulator rule or a finite-fuel Tow fuel formula.

## Runtime source

Server checkout candidate:

```text
23321c359db92772b54507e48a534cee8fbaf389
```

Completed gate:

```text
logs/finite-fuel-tow-passenger-chunnel-resolution-20260910T203118Z-23321c35-26120
```

All stages completed `0/0`.

Source population was the exact nine-row post-classic-storm finite-fuel Tow residual after the bounded classic multi-root audit and first passenger-Chunnel context pass.

## Closed accounting

```text
post_classic_storm_input=9
cases=9
resolution_target_rows=3
background_no_chunnel_rows=6
geometry_warpwell_rows=6
geometry_warpwell_ambiguous_rows=0
stable_observed_chunnel_warpwell_route_rows=2
changed_catalog_rows=1
exact_turn_catalog_resolved_rows=1
exact_turn_catalog_missing_rows=0
exact_turn_catalog_conflict_rows=0
exact_turn_observed_chunnel_warpwell_route_rows=0
exact_turn_structural_origin_rows=0
rows_with_tow_pair_structural_role=1
rows_with_tow_pair_numeric_fc_structural_role=0
refined_observed_chunnel_route_warpwell_exact=2
refined_tow_pair_numeric_fc_structural_chunnel=0
refined_tow_pair_structural_chunnel=0
refined_exact_turn_catalog_no_chunnel_lead=1
```

## Two route-equivalent Chunnel exclusions

### 511506 / T34 / tower 188 / Tow target 136

```text
Tow direct geometry=(2530,1331)
ordinary eligible-planet warp well=(2530,1334)
factual destination=(2606,1425)
observed Chunnel 200 -> 155
observed pre-Chunnel position=(2530,1334)
```

After ordinary warp-well normalization, the Tow route is exactly route-equivalent to an independently reconstructed same-turn Chunnel event. This is strong external-relocation evidence for evidence-mining exclusion; it does not identify which ship was carried by Chunnel.

Tow target `136` is itself a structural Chunnel-initiator hull at the Tow origin and reaches the same factual destination as stationary target-ability ship `155`, but its factual friendly code is the nonnumeric string `mkt`. Therefore the direct structural pair is not promoted to a proven Chunnel event.

### 511506 / T39 / tower 17 / Tow target 321

```text
Tow direct geometry=(2578,1467)
ordinary eligible-planet warp well=(2576,1469)
factual destination=(2514,1772)
observed Chunnel 200 -> 384
observed pre-Chunnel position=(2576,1469)
```

This also becomes exact route equivalence only after ordinary warp-well normalization. It is therefore removed from the Tow fuel inference population as attributable external Chunnel context.

## Exact-turn catalog resolution

For `620694/T126` the archive-wide Chunnel ability catalog changed, but the exact archive-turn consensus resolved cleanly:

```text
exact_turn_ability_sets=(((), (), ()),)
```

There are no Chunnel initiator/target/self abilities in that exact turn payload, no exact-turn Chunnel route event, and no exact-turn structural pair. The row is therefore refined to:

```text
exact_turn_catalog_no_chunnel_lead
```

This closes the catalog uncertainty for this turn only.

## Remaining population

After removing the two exact route-equivalent Chunnel rows, seven rows remain for non-Chunnel Tow investigation:

```text
360690 T41  tower425 target353  same_line_route
360690 T44  tower291 target417  same_line_route
360690 T84  tower22  target422  off_route
360690 T123 tower190 target49   off_route
360690 T124 tower190 target49   off_route
360690 T185 tower436 target124  same_line_route
620694 T126 tower408 target95   off_route
```

The two consecutive `360690/T123` and `T124` rows use tower hull `46`, one of the repository's documented Gravitonic Accelerator hull IDs. Gravitonic movement is already represented in the generic movement geometry and must not be treated as a new unexplained mechanic.

## Next bounded question

Before interpreting these seven rows as Tow fuel proration, test whether the apparent Tow route can instead result from Tow breaking and the participants moving under their own navigation state.

The repository already contains prior Tow-break diagnostics establishing the required evidence boundary: a common post-turn endpoint is route evidence, not by itself proof that the Tow lock succeeded. The next gate should therefore inspect, for each exact remaining row:

- tower independent navigation endpoint, including Gravitonic speed and ordinary warp wells;
- target independent navigation endpoint under the same geometry rules;
- strict damage-limited alternatives where the existing conservative damage guard applies;
- current documented Four Fingers predicate as a snapshot-supported diagnostic only;
- the non-fuel Four Fingers proof used by the finite-fuel Tow discovery gate, so snapshot fuel is not silently promoted to Tow-phase fuel.

Independent navigation exactness is an alternative-explanation lead, not automatic Tow-break attribution. Missing phase fuel remains unknown.

## Decision boundary

```text
classic storm family removed from Tow fuel evidence = 44 rows
route-equivalent Chunnel removed = 2 rows
remaining bounded population = 7 rows
finite-fuel Tow fuel basis = OPEN
planets-intel transfer = NO
```
