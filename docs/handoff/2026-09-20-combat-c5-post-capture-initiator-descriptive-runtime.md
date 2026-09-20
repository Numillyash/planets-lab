# C5 post-capture initiator population — descriptive runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
b59f363e4e8a44ecfa6ba4da4f6080e1cf0b0c49
```

PR #28 remained open + draft. Game `591478` remained excluded.

## Tests

```text
............ [100%]
```

## Population

```text
capture_continuations=23

opponent_type:planet=15
opponent_type:ship=8

independent_attack:planet=15
independent_attack:ship=8
independent_opponent_attack_candidate=23

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

payload_conflicts=0
```

## Interpretation

Every observed same-turn post-capture continuation has an independently attributable opponent-side initiator under already documented/implemented ordinary attack semantics:

```text
ship opponent:
  8/8 T-1 Kill!/Primary Enemy requests combat against the prize ship's new owner

planet/base opponent:
  15/15 T-1 Friendly Code is NUK or ATT
```

Therefore the observed corpus does not require old captured-ship Kill!/PE orders to persist through capture in order to explain any continuation.

Old captured-ship T-1 aggression:

```text
2 rows compatible with the factual next opponent
19 rows explicitly not compatible
2 rows unavailable
```

The two compatible rows are classified `both`, not `captured_old_orders_only`. They therefore do not identify old-order persistence because the opponent independently initiates combat anyway.

The two unavailable captured-ship T-1 rows are an optional historical-observability gap, not an initiator reconstruction gap. The original v1 acceptance incorrectly counted:

```text
unresolved:captured_ship_tminus1=2
```

as a required adapter failure even though the diagnostic's evidence boundary explicitly treats captured old orders as optional historical alternatives.

That acceptance bug is repaired in v2:

```text
6747d672e499ef6da3974c6713cf0560801798a1
  combat: scope capture initiator acceptance to required inputs

71ebdabe6888739e6a7e3a559271581715c6c441
  test: keep optional old-order gaps out of initiator gate
```

v2 hard acceptance requires:

```text
no_required_adapter_unresolved=True
all_continuations_have_independent_opponent_attack=True
all_third_party_have_independent_attack=True
ship_and_planet_continuations_present=True
```

and reports `optional_old_order_unresolved` separately.

## Evidence status before v2 rerun

Empirical initiator statement:

```text
all 23 observed post-capture continuations have an independent opponent initiator
```

is:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED
```

A final v2 runtime is still required to close the diagnostic gate after the acceptance-scope repair.

## Consequence

Do not implement persistence of the captured ship's old mission/PE merely to reproduce this corpus.

The Planets.nu capture-generated target/order list remains a documented Host mechanic, but this corpus does not identify its contents because every observed post-capture continuation can already occur from opponent-side aggression.

After the v2 initiator gate is green, the next useful queue problem is mixed ship/planet ordering rather than inventing an unidentifiable captured-ship attack list.
