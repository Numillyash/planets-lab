# C5 Host combat phase — current handoff

GitHub is the only source of truth. Verify actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 must remain **open + draft** and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

Progress overview: `docs/handoff/2026-09-11-reverse-progress-assessment.md`.

## Stable C5 layers

Do not reopen absent a direct contradiction:

- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- direct ordinary STANDARD priority: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I attacker: 7/7 RIGHT;
- scoped Galactic Power Case2, reciprocal PIA and matching-FC closures;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- owner-current `T-1` is the precombat order/state source;
- `T` is post-Host/postcombat and may reuse Ship IDs; never use it as production precombat state;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

## Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383
  factual pairs exact=678 mismatch=4 unresolved=1304

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

No candidate-covered factual pair is conditionally hard-blocked.

## Initial STANDARD ordering — CLOSED

Evidence order:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

Original diagnostic checkpoint:

```text
conditional exact-set: 169/169 first pair + RIGHT exact
strict exact-set:      162/162 first pair + RIGHT exact
informative exact-set target-order controls: 15/15 rank1
```

Production selector:

```python
InitialStandardPairInput
InitialStandardSelection
select_initial_plain_standard(...)
```

Implementation:

```text
2f18cb6d2fe8edb5dd0d38ec9ec870a0bafbdefe
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md
```

Production-vs-established selector differential:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

All unit/regression tests passed after a fixture-only Galactic Power state repair at `0225ff7116ca662fdf7e079bedaf58482d7d9f4d`.

Status:

```text
initial plain-STANDARD stack selector:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The selector is intentionally bounded: unresolved candidates, eligible pre-standard pairs, unsupported priority or STANDARD side overrides fail closed.

## Directional ordinary-STANDARD targetability — CLOSED at pair/selector boundary

Original broad mismatch sites:

```text
360690/T83: active264; extra98; factual190   # Privateer Rob
511506/T94: active496; extra202; factual332  # Bird ordinary Super Spy
```

Population gate runtime:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md
```

Observed:

```text
supported_block_rows=10
  privateer_rob_ordinary=7
  bird_super_spy_ordinary=1
  bird_super_spy_advanced_historical_control=2
supported_block_conflicts=0
blocked_factual_pair_rows=0
potential_first_selector_regressions=0
baseline mismatch profiles fixed=4/4
unrelated baseline mismatches=0
```

Canonical pair input:

```python
ShipCombatSideInput.standard_targetable_by_opponent: bool | None = True
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md
```

Semantics:

- applies only to the opponent's ordinary STANDARD attack request;
- is evaluated after PIA/reciprocal-PIA/C&I classification;
- is directional, not a symmetric pair blocker;
- does not suppress the potentially cloaked ship's own attack request;
- does not encode cloak by abusing `has_fuel=False`;
- explicit unknown remains fail-closed.

Pair-level runtime retained all population acceptance, all 4/4 projected mismatch repairs, zero factual-pair regressions, and exact-set controls.

## Privateer Rob ordinary cloak — CLOSED within scope

Production helper:

```python
privateer_rob_ordinary_cloak_state(...)
```

Supported scope:

```text
Privateer race5 + mission9 Rob + ordinary cloak-capable hull:
  prior false                          -> effective cloak False
  prior true + fuel <= reference cost -> effective cloak False
  prior true + fuel >  reference cost -> effective cloak True
  advanced cloak                       -> unresolved
```

Selector-impact differential:

```text
overlay_rows=16
blocked=7 eligible=9
blocked factual pair rows=0
potential selector regressions=0
Privateer residual profiles fixed=2/2
Bird residual profiles affected=0/2
```

Status:

```text
Privateer Rob ordinary-cloak directional STANDARD targetability:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Bird ordinary Super Spy — production effective-state gate ACTIVE

Historical/documented population remains:

```text
bird_super_spy_targets_at_factual_sites=30
raw/conditional/strict one-way plain-STANDARD opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked factual-pair regressions=0
```

Focused ordinary residual `511506/T94 ship202 <- attacker496` has:

```text
Bird race3 / Red Wind / mission9 Super Spy
damage=0
fuel=37, ordinary reference cost=5
reference movement remaining fuel=29
prior iscloaked=true
ion storm=False
planet pulse=False
Loki=False
active Glory=False
```

The matched factual target ship332 also had raw prior cloak but mission2 and fought; raw `iscloaked` therefore cannot be a blanket blocker.

Production helper added at:

```text
0b88541df32c441ead4b9b9d6054af04fd2fee7a
```

API:

```python
bird_super_spy_ordinary_cloak_state(...)
standard_targetability_from_effective_cloak(...)
```

The helper consumes only precombat-resolvable inputs and preserves the conservative diagnostic boundary. It never reads post-Host T, VCR outcome or Host messages.

Targetability projection:

```text
effective_cloak=True  -> standard_targetable_by_opponent=False
effective_cloak=False -> standard_targetable_by_opponent=True
effective_cloak=None  -> standard_targetable_by_opponent=None
```

Active runtime gate:

```text
docs/handoff/2026-09-16-combat-c5-production-effective-state-pending.md
tools/diagnostics/combat_host_bird_super_spy_production_effective_state_audit.py
tests/test_combat_effective_state.py
tests/test_combat_host_bird_super_spy_production_effective_state_audit.py
```

The diagnostic reuses the existing Bird population reconstruction but substitutes the production helper for the diagnostic candidate. Required acceptance:

```text
population_no_race_conflicts=True
population_no_payload_conflicts=True
population_no_blocked_factual_pair_regressions=True
population_no_decisive_mismatch=True
population_target_residual_present=True
population_target_residual_supported=True
production_targetability_blocks_target_residual=True
advanced_rows_remain_unresolved=True
production_effective_state_gate_passed=True
```

## Advanced Cloak — historical rows closed, generic predictor NOT promoted

Three decisive Bird population rows:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

Historical closure:

- ship68 has an explicit mine hit -> damage55 -> same damage in factual VCR -> combat eligible;
- ship26/69 have stable same-owner/same-hull T attribution, damage0 and iscloaked=true -> skipped.

Evidence boundary:

```text
Advanced Cloak + mine-hit decloak:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

fully predictive generic Advanced-Cloak state resolver:
  NOT promoted
```

Do not encode ship IDs, post-Host T or messages into production. Advanced Cloak must remain unresolved until movement/mine/decloak state is independently predictive.

## After the active effective-state gate

If green, ordinary Privateer Rob and ordinary Bird Super Spy may feed production targetability within their tested scopes. Then leave the cloak/initial-selector loop and proceed with mutable C5 queue state:

1. survivor/destruction mutation;
2. mutable second-pass eligibility and side reversal;
3. capture continuation;
4. ship-to-planet / planet-base integration.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct.
