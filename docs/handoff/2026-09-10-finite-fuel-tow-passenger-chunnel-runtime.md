# Finite-fuel Tow passenger-Chunnel context runtime — 2026-09-10

GitHub is the source of truth. This handoff records completed server runtime evidence only; it does not promote a simulator rule.

## Runtime source

Server checkout candidate:

```text
e32ed887b7eb544ba37d847d04e2cf3f1dfce418
```

Completed gate:

```text
logs/finite-fuel-tow-passenger-chunnel-20260910T175552Z-e32ed887-19218
```

Source population:

```text
9 post-classic-storm Tow residual rows
0 bounded classic multi-root exact leads
```

All stages completed `0/0`.

## Closed accounting

```text
post_classic_storm_input=9
cases=9
ability_catalog_changed_games=1
rows_under_changed_ability_catalog=1
rows_with_observed_chunnel_destination=2
rows_with_observed_chunnel_origin_route=0
rows_with_observed_chunnel_geometry_route=0
rows_where_tow_pair_has_direct_chunnel_role=0
rows_with_structural_origin_chunnel=1
rows_with_numeric_fc_structural_origin_chunnel=0
rows_with_same_origin_comovers=0
observed_chunnel_route_exact_lead=0
numeric_fc_structural_origin_chunnel_lead=0
structural_origin_chunnel_lead=1
same_origin_comovement_only_lead=0
same_destination_observed_chunnel_only_lead=1
ability_catalog_changed_unresolved_lead=1
no_chunnel_lead=6
```

The archive-wide Chunnel ability catalog is stable in games `360690` and `511506`. It changes somewhere across archive `620694`; therefore the T126 row is fail-closed rather than treated as a negative Chunnel result.

## High-value rows

### 511506 / T34 / tower 188 / Tow target 136

```text
origin=(2522,1296)
Tow direct geometry=(2530,1331)
factual destination=(2606,1425)
lead=structural_origin_chunnel
```

At the exact Tow origin, ship `136` is hull `56` (Chunnel initiator ability), same known owner as stationary target-ability ship `155` already at `(2606,1425)`. Ship `136` ends at that same destination. The available owner record has sufficient observed fuel for the structural screen, but the numeric friendly code is unknown in the current classifier, so this remains structural rather than a proven Chunnel.

An independently observed same-turn Chunnel event also reaches `(2606,1425)` via initiator `200` -> target `155`; its reconstructed pre-Chunnel position is `(2530,1334)`. This is only three light-years from the Tow direct geometry and must be tested through the ordinary warp-well classifier rather than treated as route equality by proximity.

### 511506 / T39 / tower 17 / Tow target 321

```text
origin=(2606,1425)
Tow direct geometry=(2578,1467)
factual destination=(2514,1772)
lead=same_destination_observed_chunnel_only
```

An independently observed same-turn Chunnel event `200 -> 384` reaches the exact factual destination. Its reconstructed pre-Chunnel position is `(2576,1469)`, about 2.8 ly from the Tow direct geometry. The current gate deliberately requires exact equality and therefore does not call this route-equivalent. The next bounded check must apply ordinary eligible-planet warp-well normalization to the Tow geometry before comparison.

### 620694 / T126 / tower 408 / Tow target 95

```text
origin=(2040,1963)
Tow direct geometry=(2053,1958)
factual destination=(2074,1942)
lead=ability_catalog_changed_unresolved
```

The stable first/last Chunnel ability intersection is insufficient for a negative conclusion because the archive-wide ability catalog changes. Resolve the exact T126 catalog across same-turn perspectives before using this row as a no-Chunnel control.

## Remaining six rows

Six rows have no Chunnel lead under the stable catalog. This includes the three same-line-route cases that remain the most promising eventual finite-fuel Tow candidates, but they must not be promoted until the external-relocation cleanup is complete.

## Next bounded gate

`tools/run-finite-fuel-tow-passenger-chunnel-resolution-gate.sh` is intended to consume the completed runtime directory above and answer only three narrow questions:

1. Does ordinary warp-well normalization make the T34/T39 Tow geometry exactly route-equivalent to the independently observed Chunnel pre-position?
2. Is either tower/Tow target itself the structural Chunnel initiator/target candidate, and is the numeric friendly-code value actually available under another raw representation?
3. Does the exact archive-turn Chunnel ability catalog resolve the `620694/T126` catalog uncertainty?

No proximity-only Chunnel inference is allowed. Missing friendly code stays unknown. Exact-turn catalog resolution can remove an uncertainty but does not itself prove Chunnel.

## Decision boundary

```text
finite-fuel Tow fuel basis = OPEN
classic storm 44-row family = removed as attributable external context
post-classic residual = 9
passenger-Chunnel strong exact route = 0 so far
planets-intel transfer = NO
```
