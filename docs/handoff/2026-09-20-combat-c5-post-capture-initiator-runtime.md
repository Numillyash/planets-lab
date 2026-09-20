# C5 post-capture initiator population — runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
33145c99748642cc75a8f25b1bf819c1f7ba0445
```

PR #28 remains open + draft. Game `591478` remains isolated from ordinary promotion.

## Tests

User runtime:

```text
.............. [100%]
```

## Population

```text
capture_continuations=23

opponent_type:planet=15
opponent_type:ship=8

independent_opponent_attack_candidate=23
independent_attack:planet=15
independent_attack:ship=8

captured_old_orders_attack_candidate=2
captured_old_orders_no_attack_candidate=19
captured_old_orders_unresolved=2

explanation:opponent_only=21
explanation:both=2
explanation:captured_old_orders_only=0
explanation:neither=0

owner_relation:pre_capture_owner=22
owner_relation:third_party=1
third_party_independent_attack_exact=1

required_unresolved_total=0
optional_old_order_unresolved=2
payload_conflicts=0
```

Acceptance:

```text
capture_continuation_population_present=True
payload_conflicts_absent=True
no_required_adapter_unresolved=True
all_continuations_have_independent_opponent_attack=True
third_party_population_present=True
all_third_party_have_independent_attack=True
ship_and_planet_continuations_present=True
post_capture_initiator_gate_passed=True
```

## Closure

Every observed same-turn post-capture continuation has an independently attributable opponent-side initiator:

```text
ship opponents:
  8/8 T-1 Kill!/Primary Enemy request combat against the prize ship's new owner

planet/base opponents:
  15/15 T-1 Friendly Code is NUK or ATT
```

No observed continuation requires persistence of the captured ship's old mission/Primary Enemy:

```text
opponent_only=21
both=2
captured_old_orders_only=0
neither=0
```

The two unavailable captured-ship T-1 histories are optional historical observability gaps only and do not affect opponent-side initiator reconstruction.

Status:

```text
post-capture opponent-initiator population:
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The documented capture-generated target/order list remains a real Host mechanic, but this corpus does not identify its contents because every observed continuation is already explained by opponent-side aggression.

## Consequence

Do not invent or promote old mission/PE persistence merely to reproduce the current corpus.

The next high-value C5 problem is mixed ship/planet queue ordering and specific planet/base participation. Fifteen of the twenty-three observed prize-ship continuations already enter planet/base combat, so the remaining queue work is now primarily a mixed combat-order problem rather than a capture-state problem.
