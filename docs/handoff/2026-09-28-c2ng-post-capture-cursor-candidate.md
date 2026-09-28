# External-engine handoff: c2ng post-capture cursor candidate — 2026-09-28

## External source

```text
repository: stefanreuther/c2ng
commit: 425d623e5d44b017abea50bae4dc9c668870398d
branch at audit: master
license: BSD-style 3-clause (COPYING.txt)
authority: REFERENCE ONLY
```

Detailed audit:

`docs/research/2026-09-28-c2ng-capture-order-left-right-audit.md`

## Exact candidate

c2ng's shared Host/NuHost simulator does not create a new battle order after
capture.

It:

1. sorts the ship pointer vector once before ordinary combat;
2. traverses it with RIGHT as outer cursor and LEFT as inner cursor;
3. mutates a captured ship in place without re-sort/cursor reset;
4. marks it passive and `fl_WasCaptured`;
5. explicitly rejects a captured ship when it is the LEFT argument;
6. has no symmetric captured-RIGHT rejection.

Candidate:

```text
frozen pre-combat order
+ persistent RIGHT-outer/LEFT-inner cursors
+ captured LEFT suppression
+ captured RIGHT opponent continuation
```

This is not equivalent to a simple `captured ship -> RIGHT` rule.

## Why it matters

Current main control:

```text
opponent_initiator_right  7 / 8 exact
```

The external implementation supplies a concrete mechanism that can produce that
bias and may explain the remaining row differently from pair-local controls.

## Official documentation status

Not established by this audit.

c2ng itself shares this queue driver between TimHost and NuHost simulation, so
the behavior should be treated as a PCC2 assumption about NuHost, not primary
Nu evidence.

## Official Nu discriminator

**Yes.**

The existing eight attributable historical ship-capture continuations are
already sufficient to test the candidate before new corpus acquisition.

The principal known row remains:

```text
511506 / T26
captured ship27
next opponent ship119
factual captured side RIGHT
```

## Proposed bounded diagnostic

Reconstruct the candidate pre-combat sorted vector and nested cursor coordinates
for each existing capture row, then continue the cursor after factual capture
without re-sort and with `captured LEFT => reject`.

Compare predicted N+1 pair and side to factual N+1 only at the final comparator.

Do not modify canonical mechanics from this handoff.

## Evidence effect

```text
NONE
```

Required path remains:

```text
external candidate
-> official Nu observation
-> deterministic candidate diagnostic
-> held-out differential
-> only then consider promotion
```
