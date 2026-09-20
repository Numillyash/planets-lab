# C5 post-capture opponent attribution — runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
d1c5be4318dbe58a93bab78659f4d79e5b359e0f
```

PR #28 remained open + draft. Game `591478` remained excluded.

## Tests

```text
......................... [100%]
```

## Population

```text
capture_continuations=23

captured_ship_side:left=22
captured_ship_side:right=1

next_combat:planet=15
next_combat:ship=8

next_owner_relation:pre_capture_owner=22
next_owner_relation:third_party=1
next_owner_relation:captor=0

payload_conflicts=0
missing next VCR=0
opponent projection unresolved=0
```

The attempted acceptance:

```text
next_opponent_always_pre_capture_owner=True
```

failed.

Therefore:

```text
"captured ship immediately continues against its pre-capture owner"
```

is NOT a universal rule and must not be encoded.

## Sole third-party row

```text
622476/T17 @ 1973,1734
ship7 owner5
  captured by ship44 owner3 in VCR37
  then VCR38 vs ship48 owner8
```

Targeted follow-up runtime is recorded in:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-third-party-residual-runtime.md
```

It shows ship48 independently has Kill! aggression against new owner3, which is sufficient to explain VCR38 under ordinary attack/defense semantics.

## Evidence status

The owner-distribution statement itself is:

```text
CORPUS_OBSERVED + TESTED
```

but no universal post-capture opponent-owner rule is promoted.

The next evidence target is initiator attribution across all 23 continuations.
