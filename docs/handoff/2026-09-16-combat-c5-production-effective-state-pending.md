# C5 precombat effective-state -> STANDARD targetability — pending runtime

Branch: `agent/combat-c5-host-phase`

## Closed prerequisites

The following layers are already runtime-validated:

1. directional targetability population composition;
2. canonical pair-level `standard_targetable_by_opponent` semantics;
3. bounded initial plain-STANDARD stack selector.

Durable checkpoints:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md
docs/handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md
docs/handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md
```

Initial selector production differential is exact on the established comparable population:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

## Current gap

The pair predicate now accepts:

```python
ShipCombatSideInput.standard_targetable_by_opponent: bool | None
```

but effective cloak/decloak state must be reconstructed upstream from **precombat-only** evidence. Production must not use post-Host `T`, factual VCR outcome or Host messages as state inputs.

Privateer ordinary Rob already had a production helper:

```python
privateer_rob_ordinary_cloak_state(...)
```

Bird ordinary Super Spy previously had its supported reconstruction only in diagnostics.

## New production effective-state layer

Commit:

```text
0b88541df32c441ead4b9b9d6054af04fd2fee7a  combat: promote Bird ordinary Super Spy effective state
```

`src/planets_lab/rules/combat/effective_state.py` now contains:

```python
bird_super_spy_ordinary_cloak_state(...)
standard_targetability_from_effective_cloak(...)
```

The Bird helper reproduces only the previously documented/corpus-tested ordinary Super Spy scope using precombat-resolvable inputs:

- Bird race / Super Spy mission / cloak-capable ordinary-cloak hull;
- T-1 damage and fuel;
- positive prior `iscloaked` observation;
- ordinary cloak reference cost;
- independently reconstructed reference movement and remaining fuel;
- ion-storm context;
- possible Super Spy ion-pulse context;
- Loki exposure;
- active Glory co-location.

Positive effective cloak requires all conservative positive conditions. Known damage or clearly insufficient starting fuel returns `False`. Dynamic or unsupported states return `None`.

Advanced Cloak deliberately remains unresolved. Historical Advanced-Cloak ship26/69/68 evidence is not encoded in production.

Targetability projection is mechanical:

```text
effective_cloak=True  -> standard_targetable_by_opponent=False
effective_cloak=False -> standard_targetable_by_opponent=True
effective_cloak=None  -> standard_targetable_by_opponent=None
```

## Production population gate

New diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_production_effective_state_audit.py
```

It reuses the established Bird population audit and temporarily replaces only its effective-cloak candidate with the production helper. Position reconstruction, opportunity construction, diplomacy controls and factual labels remain unchanged.

Expected ordinary population invariants:

```text
raw_attack_opportunities=8
conditional_plain_standard_opportunities=8
strict_plain_standard_opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked_factual_pair_regressions=0
```

The three unresolved decisive rows must remain the known Advanced-Cloak population. The focused `511506/T94 ship202 <- attacker496` residual must be supported and project to:

```text
effective_cloak=True
standard_targetable_by_opponent=False
```

Acceptance requires:

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

## Tests

```text
tests/test_combat_effective_state.py
tests/test_combat_host_bird_super_spy_production_effective_state_audit.py
```

The first covers Privateer, Bird ordinary Super Spy and effective-cloak -> targetability projection. The second covers the diagnostic production wrapper.

## After this gate

If runtime is green, ordinary Privateer Rob and ordinary Bird Super Spy can be treated as production precombat targetability inputs within their tested scopes. Advanced Cloak remains unresolved until movement/mine/decloak state can be predicted independently.

Then C5 should move to mutable combat queue state:

1. survivor/destruction mutation;
2. second-pass pair eligibility and side reversal;
3. capture continuation;
4. ship-to-planet / planet-base queue integration.
