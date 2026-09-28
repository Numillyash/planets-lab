# Handoff: independent VCR consumers narrow the capture-side blocker — 2026-09-28

## Purpose

Return only blocker-relevant findings from the external-engine research branch.

Detailed audit:

`docs/research/2026-09-28-independent-vcr-consumers-and-legacy-engine-triage.md`

## External sources / pins

```text
Kecupo/planets-vcr-sim
  main@299a17b04b16b3b9764226dd2a27332c89d7d712
  license not established in this audit

ChallengeSY/nu-replayer
  master@a1955501eb1519497c7cef70a123649f6eca8570
  MIT

stefanreuther/c2nu
  master@18fb95f16200009a7bee96b7f83c8eea428106ff
  MIT

xer0x/vgaphost
  master@01809a5d6518f4428fb51297ddac7ae529b542d3
  no license/source beyond one README

JHOST/JPHost
  SourceForge historical project
  Java PHost 3 port
  GPLv2
  source snapshot not recovered in this pass

OpenPlanets
  SourceForge historical project
  Java/MySQL, planning status
  GPLv3
  source snapshot not recovered in this pass
```

## Finding 1 — two more independent Nu VCR consumers preserve side orientation

### Kecupo/planets-vcr-sim

`combat_factory.gd` maps:

```text
turn["left"]  -> ClassicVcr.left
turn["right"] -> ClassicVcr.right
leftownerid/rightownerid preserved
```

It does not choose those sides.

### ChallengeSY/nu-replayer

Its loadturn parser stores:

```text
leftownerid  -> LeftOwner
rightownerid -> RightOwner
```

and downstream VCR code consistently treats:

```text
Combatants(1) = LEFT
Combatants(2) = RIGHT
```

It likewise does not construct Host battle order.

Together with c2nu, three independent codebases agree on literal factual
LEFT/RIGHT orientation.

## Finding 2 — these are not post-capture queue engines

Kecupo's simulator resolves already constructed left/right pair/fleet input.
ChallengeSY replays/simulates VCRs that were already supplied by Nu.

Neither contains an independent ordinary Host battle-order / post-capture pair
selection path in the targeted audit.

Therefore do not use them to derive a capture-side rule.

## Finding 3 — vgaphost is a dead end

`xer0x/vgaphost` contains exactly one file at its only commit:

```text
README -> "hi"
```

It is not a hidden Host implementation.

## JHOST/OpenPlanets

JHOST remains interesting because historical SourceForge material confirms an
actual staged Java PHost-3-derived Host implementation existed in CVS.

However, the source tree was not recovered here, so there is no bounded
capture/order rule to hand to main yet.

OpenPlanets remains planning-stage/reference backlog; no auditable engine core
was recovered.

## Immediate main diagnostics

### 1. Raw side-mapping invariant

On the existing official raw Nu capture rows assert:

```text
raw_vcr.left.objectid  == factual LEFT object used by planets-lab
raw_vcr.right.objectid == factual RIGHT object used by planets-lab
```

At minimum include:

```text
511506 / T26
the current opponent_initiator_right 1/8 residual
```

If exact, close generic adapter-level LEFT/RIGHT inversion as an explanation.

### 2. c2ng is not a global capture-side candidate

The canonical diagnostic means the current factual population is:

```text
captured/prize LEFT   7 / 8
captured/prize RIGHT  1 / 8
```

c2ng suppresses captured LEFT, so its captured-RIGHT consequence is already
contradicted by seven rows.

Retain only the narrower Category C question:

```text
Can 511506/T26, the sole captured-RIGHT continuation, be reached by continuing
the original pre-capture c2ng/THost cursor?
```

This is an original-order candidate only, not a model for Nu's documented
capture-generated additional order.

## Evidence effect

```text
NONE from external code alone
```

The useful effect of this pass is hypothesis reduction:

```text
do not invent new queue rules from Kecupo/ChallengeSY
do not pursue vgaphost
validate raw Nu side mapping
record c2ng captured-RIGHT as a 1/8 external comparator
test original-order cursor reachability only for T26
```
