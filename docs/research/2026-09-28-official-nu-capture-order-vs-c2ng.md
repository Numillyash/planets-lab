# Official Nu capture-order documentation vs c2ng cursor model — 2026-09-28

## Purpose

This note narrows the c2ng post-capture hypothesis after comparing it to current
primary Planets.nu documentation.

It does **not** change canonical mechanics by itself. It records a material
boundary on what c2ng can and cannot model.

## Primary source

Current official Planets.nu Help:

```text
https://help.planets.nu/battle-order
section: Order Of Battle / Starships vs Starships
retrieved: 2026-09-28
```

The page states, in substance:

1. combat has ordered stages;
2. as a general rule, the more aggressive combatant fights first and from the
   RIGHT side;
3. ordinary ships proceed through their target list while alive and uncaptured;
4. a captured ship may fight for its new owner;
5. critically, a captured ship can fight **within the existing order and then
   in an additional order that is set anew when captured**, with a limit on the
   number of such fights;
6. ordinary combat priority is numeric FC first, then Kill/PE categories, then
   ship ID within each category.

This is primary documentation for NuHost behavior and has higher authority than
any third-party implementation.

## External comparator

Pinned c2ng:

```text
stefanreuther/c2ng
425d623e5d44b017abea50bae4dc9c668870398d
BSD-style 3-clause
```

Relevant implementation:

```text
game/sim/run.cpp::simulateHost
game/sim/run.cpp::doCombatOrder
game/sim/run.cpp::makeShipShipVcr
```

For both `VcrHost` and `VcrNuHost`, c2ng:

- constructs one battle-order vector;
- sorts it once before ordinary ship combat;
- traverses RIGHT outer / LEFT inner;
- mutates captured ships in place;
- does not re-sort or create a second capture-generated order;
- suppresses a captured ship as LEFT using `fl_WasCaptured`.

## Material divergence

The earlier external candidate was phrased too broadly as:

```text
post-capture continuation preserves frozen pre-combat order/cursors
```

That can only be a candidate for **one component** of documented NuHost
behavior.

Official Nu documentation explicitly requires another component:

```text
additional combat order set anew when captured
```

c2ng has no corresponding second-order construction in the audited
`simulateHost()` path.

Therefore:

```text
c2ng is not a complete NuHost capture-order implementation
```

and a failure of the c2ng cursor model on a factual continuation is not, by
itself, surprising.

## Revised candidate decomposition

The useful hypothesis is now two-layered.

### Layer O — original-order continuation

Candidate from c2ng/THost archaeology:

```text
the captured object remains at its original pre-combat position
current nested order cursors continue
captured object is suppressed in one directional role
```

This may help model the documented statement that captured ships can still fight
"within this order".

### Layer C — capture-generated additional order

Primary Nu documentation requires a second combat order that is created when
capture happens.

The exact Nu semantics still needing reconstruction include:

- when Layer C becomes eligible relative to remaining Layer O work;
- what state is sampled when C is built;
- whether friendly code is preserved or refreshed/neutralized for priority;
- how LEFT/RIGHT is assigned to a C-generated pair;
- how many C-generated fights are allowed;
- whether occurrence/repeated-pair state carries into C.

c2ng supplies **no implementation evidence** for this layer.

## Relevance to current eight-row side population

The existing planets-lab control is easy to misread. In the
pair-recomposition diagnostic:

```python
"opponent_initiator_right": "left"
```

because the stored control value is the **captured/prize ship side**. Therefore
the current official-Nu population is:

```text
captured/prize LEFT   7 / 8
captured/prize RIGHT  1 / 8

unique RIGHT:
511506 / T26
captured ship27
next opponent ship119
```

That has a direct consequence for the external comparison.

The audited c2ng Host path explicitly suppresses a captured ship as LEFT.
With random side swapping disabled, its captured special case therefore permits
the prize only on **RIGHT**.

So:

```text
c2ng captured-RIGHT candidate
  compatible side = 1 / 8

opponent-initiator-RIGHT control
  prize LEFT      = 7 / 8
```

The c2ng candidate is already falsified as a global NuHost post-capture side
model. It cannot explain the seven captured-LEFT continuations.

Primary Nu documentation, however, requires two post-capture contexts:

```text
O = participation within the existing order
C = additional order set anew when captured
```

This makes a narrower structural hypothesis worth testing:

```text
T26 RIGHT may be an O-layer continuation compatible with the THost/c2ng quirk.
The seven LEFT rows may instead arise from C-layer orders where the independently
aggressive opponent starts on RIGHT.
```

That assignment is **not established by side orientation**. In particular, T26
must be proven reachable by continuing the pre-capture original-order cursor;
otherwise c2ng should be rejected even for that row.

The second-capture ship34 case remains useful for the C layer because ordinary
same-pair occurrence reversal does not automatically transfer to a newly
created capture order.

## Proposed bounded diagnostic

Separate two questions.

### Global external side control

Add a read-only external comparator to the existing pair-recomposition report:

```text
external_c2ng_captured_right = RIGHT
```

This makes the already implied global result explicit in archive evidence:

```text
expected from current population:
exact    1
mismatch 7
```

This comparator is not a proposed Nu rule.

### O-layer reachability

For each factual capture continuation, but especially T26, report:

```text
game / turn
capture VCR N
captured ship
factual VCR N+1 pair/side

candidate O:
  pre-combat c2ng/THost order
  capture RIGHT/LEFT cursor coordinates
  continued cursor after capture
  first independently eligible continuation pair
  candidate captured side
  matches factual N+1?

candidate C:
  not inferred from c2ng
  whether a fresh capture order is independently required/consistent
```

Classification may then be:

```text
O-explained
O-rejected / C-required-or-consistent
both-reachable
unresolved
```

Do not label the seven LEFT cases C solely because c2ng rejects them; and do not
label T26 O solely because its side is RIGHT. Context classification must be
derived from independently reconstructed order reachability.

## Immediate main-track implication

The c2ng handoff remains useful only in a narrowed sense:

```text
global post-capture Nu side model: already contradicted by 7/8 rows
possible original-order continuation model: still testable, chiefly on T26
```

not:

```text
candidate implementation for the complete NuHost post-capture queue
```

The primary documentation already says complete NuHost behavior is richer.

## Historical THost context

Independent historical references such as Donovan's describe classic Host side
assignment by battle-order position: lower battle-order value obtains the RIGHT
side. That is consistent with c2ng being principally a THost-derived queue
model.

This historical material is useful provenance, but it should not override
current primary Nu documentation.

## Evidence classification

### DOCUMENTED

Primary Planets.nu documentation supports:

- dynamic combat order in complex stacks;
- general aggressive-combatant RIGHT-side rule;
- captured ships can fight for new owner;
- captured ships can participate in existing order;
- an additional order is created on capture.

### EXTERNAL CANDIDATE

c2ng supports a candidate mechanism for the original-order portion:

- frozen pre-sort;
- persistent nested cursors;
- captured-LEFT suppression.

### UNKNOWN

Still unresolved from documentation/source comparison:

- exact boundary between original-order and capture-generated-order fights;
- exact capture-generated LEFT/RIGHT rule;
- exact limit/counter semantics;
- exact sampled FC/mission/PE state for the newly generated order.

## Evidence effect

This comparison does not by itself promote an inferred side rule.

It **does** constrain candidate design: a single-order c2ng replay must not be
treated as a complete model of documented NuHost capture combat.
