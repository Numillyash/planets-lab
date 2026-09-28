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
| C | `game/sim/run.cpp::doCombatOrder` | outer loop `right`, inner loop `left`; pair passed as LEFT/RIGHT directly | best current control `opponent_initiator_right = 7/8` | concrete mechanism for RIGHT bias | yes | test cursor position, not pair-local priority |
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

Main reports:

```text
opponent_initiator_right = 7 / 8 exact
```

with principal discriminator:

```text
511506 / T26
captured ship27
next opponent ship119
factual captured-ship side = RIGHT
```

c2ng independently creates the same directional bias:

- RIGHT is the outer cursor;
- captured LEFT is explicitly rejected;
- captured RIGHT can still be attacked as opponent.

The remaining 1/8 is therefore especially useful: it can distinguish a simplistic captured->RIGHT rule from the stronger frozen-order/cursor candidate, or falsify c2ng's candidate.

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

Combined candidate:

```text
post-capture continuation preserves pre-combat sorted object order and
current nested combat-order cursors; a captured ship is suppressed as LEFT
but can continue as RIGHT opponent.
```

The existing eight attributable Nu capture continuations already form a bounded discriminator population.

## Proposed bounded diagnostic for main

Do **not** import c2ng code. Implement a candidate-only diagnostic over existing factual capture rows:

1. reconstruct pre-combat ship order from already available order inputs;
2. record RIGHT/LEFT cursor coordinates of the capture VCR under candidate traversal;
3. mutate only already-established factual capture state;
4. continue cursors without re-sort;
5. apply candidate `captured-as-LEFT => reject`;
6. predict next pair and LEFT/RIGHT orientation;
7. compare to factual VCR N+1 only at the final comparator.

Per-row output:

```text
game / turn
capture VCR
captured ship
capture side
pre-combat sorted indices
cursor at capture
next candidate cursor
predicted pair
predicted captured side
factual pair
factual captured side
exact?
reason for first divergence
```

Interpretation:

- **8/8 exact:** freeze candidate, then validate unchanged on newly acquired held-out continuations.
- **7/8 with same residual:** determine whether residual is initial-sort reconstruction or genuine Nu divergence.
- **different residual set:** cursor model remains more discriminatory than scalar 7/8 control.
- **clear contradiction:** reject for NuHost and retain as external historical/reference behavior.

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
  YES — existing eight attributable historical capture continuations

evidence effect:
  NONE until official-Nu diagnostic/differential verification
```
