# Handoff: official Nu docs bound the c2ng capture candidate — 2026-09-28

## Primary source

Current Planets.nu Help:

```text
https://help.planets.nu/battle-order
```

The documented ship-combat model explicitly says captured ships can fight:

```text
1. within the current order; and
2. in an additional order set anew when captured,
   with a limited number of such fights.
```

The same page states the general rule that the more aggressive combatant fights
first and from the RIGHT side, while complex stacked combat can shift
dynamically.

## Why this changes the external-engine hypothesis

c2ng's shared Host/NuHost `simulateHost()` path has:

```text
one pre-sorted battle_order
RIGHT outer / LEFT inner cursor
capture mutation in place
captured-LEFT suppression
no capture-generated second order
```

Therefore the c2ng cursor model is **not a complete NuHost capture queue**.

Its useful scope is narrowed to a candidate for the documented
"within this order" continuation layer.

It supplies no implementation candidate for the documented additional order
created at capture.

## Immediate diagnostic recommendation

Before fitting another global LEFT/RIGHT rule across all eight capture rows,
classify each factual N -> N+1 continuation as:

```text
O-only  = reachable only from original-order continuation
C-only  = reachable only from capture-generated additional order
both
unresolved/neither
```

Then evaluate side assignment separately inside O and C.

For O, the c2ng candidate is:

```text
frozen original order
+ persistent RIGHT-outer / LEFT-inner cursors
+ captured-LEFT suppression
```

For C, do **not** import c2ng semantics. Reconstruct from primary Nu docs and
official observations.

The principal row:

```text
511506 / T26
captured ship27
next opponent ship119
factual captured side RIGHT
```

should be explicitly tagged O/C before being used as the decisive side-rule
discriminator.

## Evidence impact

This handoff does not promote a side rule.

It does establish a primary-documentation boundary on the external candidate:

```text
c2ng can at most explain the original-order portion;
NuHost documentation requires a second capture-generated order.
```

Detailed research note:

`docs/research/2026-09-28-official-nu-capture-order-vs-c2ng.md`
