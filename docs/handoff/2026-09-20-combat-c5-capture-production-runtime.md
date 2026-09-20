# C5 production capture transition — runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
52cd8f07f03afa7eabebf03c8b742859ab11dd9f
```

PR #28 remained open + draft. Game `591478` remained excluded.

## Tests

User runtime:

```text
.................................. [100%]
```

## Production capture corpus

Population:

```text
capture_reappearance_transitions=23
hull_preserved=23
owner_changes_to_captor_exact=23
race_changes_to_captor_exact=23

next_opponent_planet=15
next_opponent_third_ship=8

post_capture_side:left=22
post_capture_side:right=1
```

Raw replay terminal -> factual next start:

```text
damage:    exact=22 mismatch=1
crew:      mismatch=23
torpedoes: exact=23
fighters:  exact=23

shield_models:
  exact_carry=22
  pre_capture_federation_recovery=1
```

Production state comparison:

```text
owner_id:  exact=23
race_id:   exact=23
hull_id:   exact=23
shield:    exact=23
damage:    exact=22 mismatch=1
crew:      exact=23
torpedoes: exact=23
fighters:  exact=23

production_capture_all_exact=22
production_capture_exact_without_damage=23
production_capture_not_all_exact=1
```

Known damage replay residual:

```text
621253/T17 ship84 VCR39->45
predicted terminal damage=11
factual next-start damage=7
```

The runtime residual set exactly equals the pre-declared known set:

```text
damage_replay_residuals
==
known_damage_replay_residuals
==
[[621253, 17, 84, 39, 45, 11, 7]]
```

Acceptance:

```text
capture_reappearance_population_present=True
no_capture_transition_adapter_errors=True
hull_preserved=True
owner_changes_to_captor=True
race_changes_to_captor=True
production_capture_state_exact_excluding_damage=True
no_new_damage_replay_residuals=True
capture_transition_gate_passed=True
```

## Closure

Bounded production capture state transition is closed:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Within the ordinary same-turn/same-location continuation population:

1. captured ship remains active;
2. hull identity is preserved;
3. owner changes exactly to captor owner;
4. race changes exactly to captor race;
5. prize crew is 10;
6. torpedoes/fighters carry exactly;
7. pre-capture Federation end-of-battle recovery explains the single shield residual and production reproduces shield 23/23;
8. no generic damage-repair rule is promoted from the one known upstream replay residual.

Backward-compatible production boundary remains:

```text
captured=True without explicit ShipCaptureTransfer
  -> unresolved / fail closed
```

## Immediate next evidence gap

The same runtime splits the next engagement after capture into:

```text
15 planet/base continuations
8 third-ship continuations
```

The next gate must determine the owner relation of that immediate opponent before attempting to encode post-capture mission/PE/diplomacy or specific target ordering.
