# Finite-fuel Tow same-line stop-context runtime — 2026-09-11

Runtime source:

- candidate: `ab01248ca55d20dc34d7d3d5dfacdcb1d98e1ec5`
- source gate: `logs/finite-fuel-tow-same-line-reconcile-20260911T083834Z-661f9d97-15295`
- collected gate: `logs/finite-fuel-tow-same-line-stop-context-20260911T091457Z-ab01248c-25714`

All stages completed `0/0`, including the compatibility normalization stage:

```text
source_cases_marker=absent
recovered_inline_cases=3
recovered_turns=(41,44,185)
```

The bounded stop-context population remains exactly three same-line Tow rows in game `360690`.

Summary:

```text
cases=3
strong_mine_classifier_rows=0
tower_normal_damage_candidate_rows=0
tower_web_damage_candidate_rows=2
target_damage_candidate_rows=1
visible_normal_crossing_rows=1
visible_web_crossing_rows=2
observed_inside_visible_web_rows=2
research_scaled_floor_exact_rows=0
lead:damage_backed_visible_mine_context=2
lead:no_visible_mine_or_damage_lead=1
```

## T44

`360690/T44`, tower `291` -> target `417`:

- tower hull `56`, damage `8 -> 16`;
- web damage quantum is `8`, giving exactly one web-hit damage candidate;
- hostile visible web field `78` intersects the route and contains the factual endpoint;
- factual movement is only `1.0 ly` of a `34.928498 ly` route;
- the existing strong mine classifier does not fire because its production boundary is stricter than this Tow-specific context.

This row is a strong bounded **web-hit context confounder**, but the gate does not reconstruct the random hit location and therefore does not promote a new deterministic web-movement rule.

## T185

`360690/T185`, tower `436` -> target `124`:

- tower hull `17`, damage `0 -> 8`;
- web damage quantum is `8`, giving exactly one web-hit damage candidate;
- multiple hostile visible web fields intersect the route and contain the factual endpoint;
- one hostile normal minefield also intersects the route;
- factual movement is `10.77033 ly` of a `28.460499 ly` route;
- the existing strong classifier again remains outside its production boundary.

This row is also a strong bounded **web-hit context confounder**. It should not be used as finite-fuel Tow formula evidence unless the web context is independently disproved.

## T41

`360690/T41`, tower `425` -> target `353` remains the only row with no visible mine/web or tower-damage lead.

Important new phase-state clue:

- target hull `105` has static special text `Alchemy Ship - Converts 3 supplies to 1 mineral.`;
- target supplies change `2700 -> 0` across the transition;
- the previous finite-fuel phase envelope held target non-fuel mass fixed, so any pre-Tow Alchemy conversion could invalidate that envelope;
- converting `2700` supplies at `3:1` reduces target cargo mass by `1800 kt` before considering other cargo changes, which is large enough to materially change the Tow fuel requirement.

This is only a phase-order hypothesis at this checkpoint. The next bounded gate must inventory the target mineral delta, test whether the cargo transition is compatible with Alchemy, and rerun the physical Tow fuel envelope with the corresponding mass reduction.

## Evidence status

```text
T44/T185 = bounded web-hit context confounders; not deterministic movement reconstruction
T41       = clean of visible mine/damage; Alchemy pre-Tow mass mutation is the next lead
finite-fuel Tow = OPEN
planets-intel = unchanged
```
