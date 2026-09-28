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

## Why it matters — corrected orientation

The earlier version of this handoff incorrectly said c2ng produced the same
directional bias as the 7/8 control.

The planets-lab diagnostic stores the **prize/captured ship side**, and defines:

```text
opponent_initiator_right -> prize side LEFT
```

Thus the factual population implied by the existing result is:

```text
captured/prize LEFT   7 / 8
captured/prize RIGHT  1 / 8

sole RIGHT row:
511506 / T26 / ship27 -> ship119
```

c2ng does the opposite for its captured special case: captured LEFT is rejected,
so the captured ship can continue only on RIGHT in the audited Host path.

Therefore c2ng is already contradicted as a **global NuHost post-capture side
rule (7/8 mismatches)**. Its remaining value is narrower: T26 is the only
existing row whose side is compatible with the c2ng/THost original-order
candidate.

## Official documentation status

Not established by this audit.

c2ng itself shares this queue driver between TimHost and NuHost simulation, so
the behavior should be treated as a PCC2 assumption about NuHost, not primary
Nu evidence.

## Official Nu discriminator

**Yes.**

The existing eight attributable historical ship-capture continuations are
already sufficient to reject captured-RIGHT as a global Nu rule. They also
isolate T26 as the sole current side-compatible row for a narrower original-order
cursor test.

The principal known row remains:

```text
511506 / T26
captured ship27
next opponent ship119
factual captured side RIGHT
```

## Proposed bounded diagnostic

First expose c2ng's side invariant explicitly in the existing diagnostic:

```text
external_c2ng_captured_right = RIGHT
```

This should make the global rejection measurable in archive runtime.

Then test only the meaningful unresolved question: whether `511506/T26` is
reachable by continuing the independently reconstructed original battle-order
cursor without re-sort/reset and with captured-LEFT suppression.

Do not classify T26 as original-order merely because its side is RIGHT; require
cursor reachability without consulting VCR N+1 until the final comparator.

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
