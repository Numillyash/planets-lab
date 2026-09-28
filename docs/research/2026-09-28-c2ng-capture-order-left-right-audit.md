# c2ng capture/order/LEFT-RIGHT audit — 2026-09-28

## Scope and provenance

Current blocker: `post-capture ship LEFT / RIGHT side assignment`.

External implementation:

- repository: https://github.com/stefanreuther/c2ng
- pinned commit: `master@425d623e5d44b017abea50bae4dc9c668870398d`
- commit date: 2026-08-06 author / 2026-08-09 committer
- license: BSD-style 3-clause terms in `COPYING.txt`
- authority: **REFERENCE ONLY / candidate generator**

`c2ng implementation != NuHost evidence`. No evidence label changes here.

## Main finding

For `VcrHost` and `VcrNuHost`, c2ng uses the same `simulateHost()` queue driver. The relevant post-capture behavior emerges from four implementation choices:

1. ship pointers are sorted by TimHost battle order **once**, before ordinary combat;
2. ordinary combat has **RIGHT as the outer cursor** and LEFT as the inner cursor;
3. capture mutates the existing ship object in place but does **not** re-sort the vector or reset either cursor;
4. a captured ship is explicitly forbidden from fighting when supplied as LEFT, but there is no symmetric `fl_WasCaptured` ban for RIGHT.

Candidate semantics:

```text
frozen pre-combat order
+ persistent nested-loop cursors
+ captured ship becomes passive
+ captured ship cannot subsequently participate as LEFT
+ captured ship can remain/appear as RIGHT opponent if another ship attacks it
```

This is more specific than the existing scalar controls `sticky capture side` or `frozen T-1 priority`.

## Source-to-planets-lab comparison

| category | external location | implementation behavior | planets-lab equivalent/status | candidate difference | discriminator already possible? | next action |
|---|---|---|---|---|---|---|
| A | `game/battleorderrule.cpp`; `game/sim/run.cpp::sortByBattleOrderTHost` | TimHost battle value then ship id sorts Host/NuHost simulator ships | battle-order inputs/FC sensitivity already studied | c2ng hardcodes Host 3.22.48 interpretation for NuHost simulation | partially | use only as input to cursor candidate |
| C | `game/sim/run.cpp::simulateHost` | `battle_order` sorted once; no re-sort after each VCR | blocker asks whether capture resets/recreates combat order | candidate says **no re-sort/no new order** | yes: existing capture continuations | replay exact nested-loop cursor |
| C | `game/sim/run.cpp::doCombatOrder` | outer loop `right`, inner loop `left`; pair passed as LEFT/RIGHT directly | current `opponent_initiator_right = 7/8` means the **opponent** is RIGHT and therefore the captured prize is LEFT in 7/8 rows | c2ng's captured-LEFT ban predicts the opposite prize orientation for those seven rows; it is compatible only with a captured-RIGHT continuation | yes | reject c2ng as a global post-capture side model; test only original-order reachability of the unique RIGHT row |
| C | `game/sim/run.cpp::makeShipShipVcr` | Host/NuHost rejects `leftShip.fl_WasCaptured`; no symmetric captured-RIGHT guard | pair eligibility already resolved, side unknown | predicts captured continuation can use captured ship as RIGHT but not LEFT | yes | evaluate all 8 factual sides |
| A | same | capture sets owner to captor, crew=10, aggression=Passive, `fl_WasCaptured` | capture state transition already closed | mostly equivalent state | already covered | no mechanics change |
| B/C | same | capture mutation is in-place on object referenced by already-sorted vector | frozen priority and sticky side tested separately | candidate couples frozen position to persistent cursor and LEFT suppression | yes, but exact cursor reconstruction needed | bounded diagnostic |
| A | `game/sim/run.cpp::runSimulation` | `fl_WasCaptured` cleared once at simulation start | capture treated as same-turn transient state | no immediate difference | n/a | record only |
| B | `makeShipShipVcr` | optional simulator `RandomLeftRight` can swap sides | factual Nu side generation is unknown | simulator option is not Host evidence | no | disable for candidate reproduction |
| A/B | `test/game/sim/runtest.cpp::VcrHost:battle-order` | regression verifies ordinary TimHost order and RIGHT orientation | ordinary non-capture queue already closed | provenance for loop orientation, not Nu proof | ordinary only | do not reopen ordinary queue |
| B | `game/sim/run.cpp::isAttacking` comments | documents deviations/uncertainties and uses `fl_WasCaptured` for captured special case | independent eligibility work exists | implementation admits approximation | no new promotion | retain as ambiguity provenance |

## Exact candidate algorithm

For ordinary Host/NuHost ship combat, c2ng effectively does:

```text
battle_order = active ships
sort battle_order by THost battle value, then ship id

for right_cursor in battle_order:
    for left_cursor in battle_order:
        if left_cursor != right_cursor:
            attempt(left_cursor, right_cursor)

capture(ship):
    mutate owner in place
    crew = 10
    aggression = passive
    set WasCaptured
    do not resort
    do not restart cursors

attempt(left, right):
    evaluate aggression/eligibility
    if left.WasCaptured:
        reject
    otherwise resolve with supplied left/right
```

This is a **candidate model only**.

A captured ship does not receive a newly calculated vector position. Its pointer remains at the old sorted index while both loop cursors continue. Therefore this is history-dependent and not equivalent to a simple rule such as "captured ship goes RIGHT".

## Why this matters to the 7/8 control

The earlier version of this note described c2ng as producing the same directional
bias as the `opponent_initiator_right` control. That was backwards.

The canonical diagnostic defines:

```python
"opponent_initiator_right": "left"
```

where the stored value is the **captured/prize ship side**. Therefore:

```text
opponent_initiator_right exact = 7 / 8
=> captured/prize ship factual LEFT = 7 / 8

unique mismatch:
511506 / T26
captured ship27
next opponent ship119
factual captured/prize side = RIGHT
```

By contrast, c2ng's non-PHost path explicitly rejects a captured ship when that
ship is passed as LEFT. With simulator random-left/right disabled, the audited
c2ng path can therefore continue a captured ship only as **RIGHT**.

So the existing eight Nu observations already falsify the c2ng rule as a global
post-capture side model:

```text
c2ng captured-RIGHT side candidate: compatible with 1 / 8
opponent-initiator-RIGHT / prize-LEFT control: compatible with 7 / 8
```

This makes the unique T26 row more interesting, not less. Current primary Nu
documentation says a captured ship can participate both in the existing order
and in an additional order created at capture. A bounded hypothesis is therefore:

```text
O layer (original order): c2ng/THost captured-RIGHT behavior may be relevant
C layer (capture-generated order): c2ng has no implementation for it
```

The fact that T26 is the only observed captured-RIGHT continuation makes it the
sole existing candidate for the c2ng-like O layer. **Side orientation alone does
not prove that classification.** T26 must first be shown reachable by continuing
the independently reconstructed original-order cursor after the capture.

## NuHost-specific status inside c2ng

There is no separate NuHost queue implementation in this path.

`runSimulation()` dispatches:

```text
VcrHost   -> simulateHost(..., Host)
VcrNuHost -> simulateHost(..., NuHost)
```

Thus Host and NuHost share initial sorting, intercept driver, nested ordinary loop, capture mutation and captured-LEFT suppression. `type` changes the pairwise VCR algorithm and some ability/config behavior, not this audited queue structure.

This lowers its Nu-specific authority: it is best interpreted as c2ng/PCC2's assumption that NuHost follows TimHost here.

## Tests/FIXMEs

`test/game/sim/runtest.cpp` contains ordinary order regressions:

- `game.sim.Run:VcrHost:battle-order`
- `game.sim.Run:VcrHost:battle-order:planet`
- corresponding PHost tests.

The Host test references bug #428 and `c2hosttest/combat/04_order/b`, and verifies RIGHT-outer ordering on a three-ship setup.

No dedicated post-capture ordering regression was found in the targeted test search. Capture/cursor semantics therefore appear to follow from implementation composition, not an explicit captured-order test.

Relevant uncertainty comments include:

- `simulateHost` support functions "make up a host version";
- `isAttacking` documents deliberate deviations from Host behavior;
- mutual capture handling has a FIXME noting HOST may swap ships.

## Category classification

### A — already equivalent / no new promotion value

- capture owner mutation;
- crew reset to 10;
- captured aggression becomes passive;
- transient captured marker;
- ordinary battle-value sorting concepts.

### B — candidate differences without a clean new discriminator

- configurable random LEFT/RIGHT;
- documented simulator approximations in attack eligibility;
- exact THost 3.22.48 battle-value assumptions reused for NuHost.

### C — immediately testable against official historical Nu

The existing eight rows already reject this combined c2ng rule as a **global**
NuHost post-capture model because seven factual prize ships are LEFT whereas
c2ng suppresses captured LEFT.

The remaining Category C question is narrower:

```text
Can the unique captured-RIGHT row (511506/T26) be generated by continuing the
pre-capture original-order cursor under the c2ng/THost candidate?
```

If yes, c2ng supplies an external candidate for the documented original-order
portion only. It still says nothing about Nu's separately documented
capture-generated additional order.

## Proposed bounded diagnostic for main

Do **not** import c2ng code and do not fit the c2ng side rule over all eight
rows. The global side comparison is already known qualitatively: c2ng predicts
captured RIGHT while seven of eight factual continuations are captured LEFT.

The bounded diagnostic should instead:

1. expose an explicit external control `external_c2ng_captured_right = RIGHT`
   in the existing pair-recomposition report, so archive runtime records the
   expected exact/mismatch counts rather than relying on prose;
2. for `511506/T26`, reconstruct the pre-combat THost/c2ng candidate order
   from independent T-1 inputs;
3. identify the RIGHT/LEFT cursor coordinates of the capture VCR without using
   VCR N+1;
4. continue those cursors without re-sort/reset and with captured-LEFT
   suppression;
5. determine whether ship119 is the next independently eligible opponent with
   ship27 on RIGHT;
6. consult factual VCR N+1 only as the final comparator.

Per-row/global control output:

```text
external_c2ng_captured_right exact / mismatch
factual captured LEFT count
factual captured RIGHT count
```

T26 original-order output:

```text
pre-combat order
capture cursor
continued cursor
predicted pair
predicted captured side
factual pair/side
first divergence, if any
```

Interpretation:

- if T26 is cursor-reachable exactly, retain a **narrow O-layer candidate** and
  test it unchanged on newly harvested capture continuations;
- if T26 is not cursor-reachable, reject c2ng even for the sole captured-RIGHT
  observation;
- in either case, do not use c2ng to model the seven captured-LEFT rows or Nu's
  capture-generated additional order.

## Handoff summary

```text
source:
  stefanreuther/c2ng
  master@425d623e5d44b017abea50bae4dc9c668870398d
  BSD-style 3-clause

candidate:
  frozen pre-combat battle_order
  + RIGHT outer / LEFT inner cursor
  + no re-sort/reset after capture
  + captured object mutated in place
  + captured LEFT explicitly rejected
  + captured RIGHT still possible as opponent

official documentation status:
  not established by this audit

official Nu discriminator:
  YES — existing eight rows reject captured-RIGHT as a global rule; T26 is the
  sole current row for an original-order cursor reachability test

evidence effect:
  NONE until official-Nu diagnostic/differential verification
```
