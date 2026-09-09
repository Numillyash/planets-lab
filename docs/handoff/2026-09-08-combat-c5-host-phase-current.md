# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is a compact pointer. Use the dated handoffs for full evidence and runtime logs.

## Stable C5 corpus/evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts in the established C5 corpus.
- Ordinary factual queue: ship combat precedes planet combat in every observed ordinary queue.
- Owner-current `T-1` is the precombat order/state source for battle turn `T`; factual `T` survivor state is postcombat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Direct isolated standard classification: 413/413 right-higher after documented special branches are removed.
- Factual isolated C&I attacker: 7/7 right.
- Ordinary linked normal Priority Intercept population: 37/37 before regular ship combat and 37/37 with PIA attacker on right.

## Closed combat-specific gates

Read first when touching pair/queue semantics:

- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-factual-queue-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-repeated-pair-side-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-candidate-set-v1-runtime.md`

Former residuals remain closed for their scoped reasons:

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Evil-Empire Gorbie
```

Do not weaken standard priority, Intercept semantics, diplomacy or Friendly Code parsing to fit them.

## Unified pair/queue layer

Canonical deterministic pair composition:

```text
src/planets_lab/rules/combat/selection.py
```

Status: `TESTED`.

Canonical scoped repeated-pair side helper:

```text
src/planets_lab/rules/combat/queue.py
standard_pair_sides_for_occurrence(...)
```

Runtime source `de824ab4ecc0bc8cd32784ce4d3df9021eddd71b` passed the combat/queue regression gate. The complete ordinary repeated-pair population is exactly two groups/four VCRs; both show first RIGHT = static higher priority and second RIGHT = opposite ship. This reversal is `CORPUS_OBSERVED + DIFF_VERIFIED`, not primary `DOCUMENTED`; `standard_battle_priority_key(...)` remains unchanged.

## Factual-positive queue differential

Runtime source:

```text
31509d2c9e9f4af89f80e5088597452d40f393c1
```

Result:

```text
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
payload_conflicts=0
known phase-prefix violations=0
```

Exact-target normal Priority Intercept binding is runtime validated.

## Candidate-set v1

Runtime source:

```text
1ef175f77419970b244c5d69df2863a06390ab6c
```

Result:

```text
factual_unique_pairs=1986
candidate_pairs=107
factual_pairs_candidate_covered=1
factual_pairs_movement_uncovered=1985
```

The one covered factual pair was eligible with no hard blocker. This was not broad candidate-set validation; `self_movement_possible=1606` dominated exclusions. Therefore movement-derived precombat position remains the dependency before candidate-set v2.

## T-1 stationary/normal-movement position v2 — runtime complete

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-runtime.md
```

Runtime source:

```text
5da7144a9a1c2940b4d6e07c13f88b08274a90af
```

Artifact:

```text
artifacts/combat-c5-normal-movement-position-20260909-225503
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0

ship occurrences:
  factual=3204
  predicted=1810
  exact=1800
  mismatch=10
  uncovered=1383

factual pairs:
  total=1986
  exact=677
  mismatch=9
  uncovered=1300

sites:
  total=1220
  all factual pairs position-exact=345
  mismatch sites=7
```

This expanded independent factual-pair position coverage from `1/1986` to `677/1986` without using factual T survivor positions as predictor inputs.

## Bounded v2 residual attribution — runtime complete

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-residual-runtime.md
```

Runtime source:

```text
1d880ca6e0a1e0784f2fae4437c981ce71ac49ed
```

Artifact:

```text
artifacts/combat-c5-normal-movement-position-residual-20260909-231621
```

Result:

```text
tests rc=0
audit rc=0
mismatch_rows=10
single_exact_context_family=6
unresolved=4
candidate_family_counts={'ion_storm': 6}
candidate_context_counts={'ion_storm_classic:ion_storm_drag': 6}
```

All six attributed rows are exact classic ion-storm drag with authoritative `nuionstorms=False`:

```text
360690/T114 ships 238,440
620694/T117 ship 450
620694/T128 ships 146,214,278
```

## Focused four-row attribution — runtime complete

Read:

```text
docs/handoff/2026-09-09-combat-c5-unresolved-movement-context-runtime.md
```

Runtime source:

```text
070cb150a7b88e9a406f3ef8ca9f5984b873211e
```

Artifact:

```text
artifacts/combat-c5-position-v3-20260909-234137/unresolved-context.json
```

Result:

```text
tests rc=0
focused-context rc=0
unresolved_rows=4
vcr_start_found=4
exact_scaled_floor_geometry=3
exact_scaled_floor_with_field_crossing=3
single_focused_candidate_family=2
still_unresolved=2
vcr_damage_normal_mine_multiple=2
```

Two rows are now historically attributable to one normal-mine hit plus the existing low-tech scaled-floor slowdown:

```text
620694/T62/ship83:
  tech 6
  exact one-hit scaled-floor endpoint
  hostile normal-field crossing visible at T-1 and T
  T-1 damage 0 -> VCR-start damage 40
  normal-mine quantum 40

680910/T14/ship65:
  tech 6
  exact one-hit scaled-floor endpoint
  hostile normal-field crossing visible at T
  T-1 damage 0 -> VCR-start damage 30
  normal-mine quantum 30
```

Specific historical attribution for these rows is `CORPUS_OBSERVED + DIFF_VERIFIED`. Exact candidate-time mine-hit position remains stochastic/not reconstructed. In particular, ship65's matching field is not present in the T-1 crossing set, so battle-turn minefield state must never be used as a predictor input.

Two rows remain bounded unresolved:

```text
360690/T54/ship26
511506/T95/ship332
```

For ship26 there is no exact storm, strong-mine, observed Tow or route-equivalent observed Chunnel match despite 166 observed Chunnel events in that game. Ship332 is tech 7, has no T-1->VCR damage increase, and therefore the trivial one-light-year scaled-floor geometric coincidence is explicitly rejected as mine evidence. Do not create case-specific rules for either row.

## Storm-aware position v3 — first runtime invalid as coverage evidence

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-first-runtime-invalid.md
```

The first v3 run on source `070cb150...` exited cleanly but produced:

```text
storm_mode_games={'nuionstorms_unknown': 11}
position_uncovered=3193
uncovered:storm_mode_unknown=1810
factual_pairs position_uncovered=1986
```

This is an instrumentation/source-context failure, not a Host mechanics result. Root cause: `ArchiveTurnSnapshot.mechanics_payload` is a privacy/minimal mechanics projection whose settings projection intentionally retains only `nowarpwells`; it does not retain `nuionstorms`.

## Immediate gate — repaired full storm-aware position v3

`src/planets_lab/corpus/movement_storm_context.py` exposes:

```text
storm_offset_for_mode(...)
```

The helper is endpoint-independent and reuses the already validated Nu/classic storm implementations.

`tools/diagnostics/combat_host_normal_movement_position_audit.py` remains schema:

```text
planets-lab.combat-host-normal-movement-position-audit.v3
```

but storm mode is now resolved from the first/last **raw archived `.trn` payloads**, matching the successful residual audit. A regression test builds a synthetic archive and verifies stable `False/False -> False` and conflicting `True/False -> None` behavior.

The independent predictor order remains:

```text
T-1 owner-current ordinary navigation
-> strict effective warp / Host normal movement / Gravitonic distance
-> authoritative ion-storm drag
-> warp-well snapping
-> factual battle coordinate only as comparison target
```

Tow/Intercept/C&I/HYP/obvious Chunnel-source/transfer/MKT/sphere/fuel-proration branches remain outside this gate. Historical stochastic mine-hit rows are attribution evidence, not deterministic predictor inputs.

### Required next runtime

Run the targeted storm/position tests and the complete ordinary v3 position audit again on the repaired source. Do not rerun the four-row focused attribution unless a contradiction appears; that gate is complete.

Success criterion before candidate-set v2:

- tests and audit rc=0;
- raw archived storm mode resolves as expected rather than all-unknown;
- payload_conflicts=0;
- the six classic-storm rows move from mismatch to exact;
- no new unexplained predicted mismatch population;
- the two DIFF_VERIFIED stochastic mine rows and two bounded unresolved rows stay outside any claimed deterministic position guarantee.

After this, candidate-set v2 may consume the independently predicted position layer with explicit accounting for remaining stochastic/unresolved position residuals. Mutable target-list/queue reconstruction, capture continuation and ship-to-planet repair/planet participation remain later phases.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct.
