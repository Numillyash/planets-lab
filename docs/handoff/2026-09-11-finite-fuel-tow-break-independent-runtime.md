# Finite-fuel Tow break / independent-movement runtime — 2026-09-11

## Source

Completed server gate:

`logs/finite-fuel-tow-break-independent-20260911T081659Z-95419561-9063`

Candidate GitHub main at runtime:

`95419561650f1d41cfdb4603072823b87be47076`

Source passenger-Chunnel-resolution gate:

`logs/finite-fuel-tow-passenger-chunnel-resolution-20260910T203118Z-23321c35-26120`

## Result

All stages completed 0/0.

The bounded population contains seven post-Chunnel rows:

- `same_line_rows=3`
- `off_route_rows=4`
- `neither_independent_exact=7`
- `tower_ordinary_exact=0`
- `target_ordinary_exact=0`
- `tower_strict_damage_exact=0`
- `target_strict_damage_exact=0`
- `nonfuel_lock_proven=7`
- `lock_depends_on_target_phase_fuel=0`
- `snapshot_four_fingers_false=7`

Thus none of the seven factual common endpoints is independently reproduced by either participant's own ordinary navigation, eligible-planet warp well normalization, or the existing strict no-repair damage-limited alternative. In all seven rows, the Tow lock is provable without using target fuel, so the result does not depend on promoting snapshot neutronium to Tow-phase fuel.

The three same-line rows are:

1. game 360690 T41, tower 425 -> target 353, origin `(2159,2741)`, waypoint `(2184,2685)`, factual `(2183,2688)`.
2. game 360690 T44, tower 291 -> target 417, origin `(2579,1495)`, waypoint `(2613,1503)`, factual `(2580,1495)`.
3. game 360690 T185, tower 436 -> target 124, origin `(2668,1452)`, waypoint `(2659,1425)`, factual `(2664,1442)`.

The four off-route rows remain separate external-context research targets and must not be mixed into a direct fuel-proration inference.

## Interpretation boundary

This runtime excludes a bounded set of Tow-break / independent-navigation alternatives. It does **not** by itself prove that finite-fuel Tow proration caused the same-line endpoints, and it does not establish a Tow fuel cost basis.

The next bounded step is a same-line fuel reconciliation over only the three rows above. It should compare:

- the existing physical Tow phase-fuel envelope with **combined tower + target movement mass**;
- a tower-only mass counterfactual;
- snapshot-state endpoint predictions as supporting evidence only;
- post-turn fuel/reset state as supporting evidence only.

Because all three same-line routes are shorter than a Warp-9 nominal leg, projected-vs-nominal partial-leg cost basis is not the discriminator here. The useful question is whether the factual short endpoint is physically compatible with finite-fuel proration and whether inclusion of the towed ship's mass is discriminating.

`finite-fuel Tow` remains **OPEN**. No `planets-intel` transfer is authorized by this runtime.