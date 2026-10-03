# Handoff: external-core capture-state archaeology — 2026-10-03

## Branch

```text
research/external-engine-analysis
```

This handoff is for the external-core stream only. It does not promote mechanics
into `main`.

Detailed note:

```text
docs/research/2026-10-03-jphost-recovery-thost-phost-capture-state.md
```

## Strongest new findings

### THost traversal has independent historical support

Donovan's detailed HOST documentation describes an explicit nested initiator
loop:

```text
sort by battle value
for initiator in order:
    for other ship in order:
        check whether either side supplies aggression
        initiator fights on RIGHT
```

The documented three-ship timeout sequence is:

```text
1->2, 1->3, 2->1, 2->3, 3->1, 3->2
```

This independently supports the broad outer-RIGHT / inner-LEFT cursor shape used
by c2ng for Tim-Host.

It does **not** independently support c2ng's captured-inner exclusion.

### c2ng bug #428 provenance

Pinned c2ng:

```text
425d623e5d44b017abea50bae4dc9c668870398d
```

Historical commit:

```text
76b3eed65bee4506758c258b6fc33e10d1a031ee
Simulator: implement battle order peculiarities
```

It introduces `fl_WasCaptured` and suppresses a captured ship specifically when
it is supplied as LEFT/inner combatant in non-PHost simulation.

The source attributes that asymmetry to a reverse-engineered HOST typo
(`youship` vs `you`). Treat this as an attributable external claim, not
verified Tim-Host source fact.

The same change carries regression fixtures identified as Host-generated:

```text
test.sim  -> c2hosttest/combat/04_order/a
test2.sim -> c2hosttest/combat/04_order/b
```

### PHost is a useful state-machine comparator

PHost 4.x documentation exposes an explicit “captured this turn” ship flag,
emergency crew, and a rule that a captured ship becomes passive for further
fights in that turn.

Its aggressor/opponent algorithm is role-based, but physical VCR sides are
randomized and its own docs explicitly warn that combat/order differs from
HOST.

Do not transfer PHost mechanics into Nu. The useful structural lesson is that
capture may create a dedicated intra-turn state bit that changes later queue
eligibility.

### c2ng remains rejected as Nu classifier

Canonical Corpus DB discovery:

```text
31 adjacent/comparable rows
O pair reachable      5  (LEFT 2 / RIGHT 3)
O pair not reachable 26  (LEFT 23 / RIGHT 3)
external O exact      3
external O mismatch  28
```

So neither:

```text
RIGHT => c2ng-like O
LEFT  => C
```

is a valid discovery classifier.

### JPHost source recovery now has a concrete route

JPHost is confirmed as a real Java GPLv2 PHost3 port with multiple CVS updates
through 2004. No GitHub mirror/indexed source tree was found.

SourceForge documents complete ZIP snapshots for legacy CVS repositories. The
candidate project snapshot is:

```text
https://sourceforge.net/code-snapshots/cvs/j/jp/jphost.zip
```

It has not yet been fetched/validated in the current web environment.

Tracked helper:

```text
tools/research/fetch-jphost-cvs-snapshot.sh
```

Run it from the external checkout. It keeps recovered GPL source under ignored
`artifacts/external-sources/`, validates the snapshot, attempts CVS checkout,
then inventories/searches the tree.

## Next action if snapshot succeeds

Do not read the whole tree randomly. First search:

```text
capture / captured / crew / owner
battle / combat / VCR
aggressor / opponent
friendly code / primary enemy / kill
order / priority / queue / sort
```

Then identify:

1. the combat phase entry point;
2. ordinary ship-order construction;
3. result mutation after a capture;
4. whether the captured ship remains in a list/queue;
5. whether a second/fresh order is generated;
6. whether mission/PE/FC are reset or preserved;
7. repeat-fight limits.

Pin snapshot SHA256 and record the CVS revision metadata of any mechanics files.

## Next action if snapshot does not exist

Record HTTP status/redirect output. Then try anonymous CVS directly:

```text
:pserver:anonymous@jphost.cvs.sourceforge.net:/cvsroot/jphost
```

and SourceForge archive/mirror endpoints. Do not silently replace failure with a
different JPHost-named project.

## Evidence boundary

The primary Nu constraint remains:

```text
captured ship can fight within existing order
+
additional order set anew at capture
+
same pair can fight at most twice
```

External code is useful only if it predicts an independently testable
discriminator against the discovery Corpus DB population.
