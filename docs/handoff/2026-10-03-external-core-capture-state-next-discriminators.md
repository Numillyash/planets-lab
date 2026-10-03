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

## JPHost snapshot recovery succeeded

The legacy CVS snapshot was fetched and validated:

```text
SHA256:
a9b1ac89ded3604350cdfde33eefea28c29348a60b3ce54a19b44145b93dd6ae

module:
jhost

checkout:
artifacts/external-sources/jphost-cvs/checkout/jhost
```

The source tree is real and includes `src/jhost`, `src/jhostcore`, tests,
configuration, historical Attic material, and an old `Jhost.jar`.

The initial grep only exposes the named `Combat` stage in `JHost.java` plus
generic combat fields in `Ship.java`; it does not yet expose an implementation
class. Treat that as provisional until the deep source/Attic audit completes.

Tracked next-stage helper:

```text
tools/research/audit-jphost-cvs-checkout.sh
```

It checks the full source inventory, pipeline/config wiring, CVS history, deleted
Attic content, and historical JAR classes.

## Next action on the recovered snapshot

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


## JPHost current-source verdict

The complete checked-out CVS HEAD has now been audited:

```text
169 Java source files
70 Java test files
no combat/battle/capture/VCR implementation class
```

`jhost.JHost.turn()` contains the PHost-like host order as comments, including
`Combat`, but that stage is not instantiated or executed. The actual executable
pipeline only contains the subset of stages already implemented in the project.

So JPHost HEAD is **not** a usable external combat engine.

Do not discard the project yet: the first history/JAR portion of the audit had a
CVS addressing bug. A focused final historical pass is ready:

```text
tools/research/audit-jphost-cvs-history.sh
```

This pass is the closure criterion for JPHost:

- inspect every raw Attic Java RCS file;
- use `cvs rlog` rather than working-copy `cvs log`;
- recover deleted source using logical non-Attic paths;
- recover the historical `Jhost.jar`;
- compare binary class inventory with final source;
- use `javap` on any combat/capture-related or otherwise missing class.

If no combat implementation appears there, mark JPHost CLOSED for the active
capture-order blocker and move external archaeology to the next engine/source.


## JPHost closure

The corrected CVS history / Attic pass has now been run against the recovered
snapshot.

Recovered historical material includes:

```text
71 deleted/Attic Java files
jhost/Attic/Jhost.jar,v
```

The raw RCS search, restored deleted Java revisions, current source tree, and
historical binary inventory all converge on the same result: there is no
ship-to-ship combat-order engine in the recovered JPHost history.

Historical JAR:

```text
revision: 1.1
date:     2002-12-27
SHA256:   fecfc0dd9b09f5c2a54580ecd21185e450df7be26ae16f6c3bb102b2b084b1fc
size:     130331 bytes
ZIP/JAR:  valid
```

Its complete class inventory contains the early object model, GUI, ship/planet
classes and utilities, but no combat/battle/capture/VCR orchestration class.

The audit stopped after the complete class inventory because the final
source-vs-JAR comparison had a malformed `sed` expression. That helper bug is
fixed in:

```text
662080dacb8c871f8232762505268f496856d7df
research: fix JPHost historical JAR source comparison
```

A rerun can finish bookkeeping, but it is not gating. Final disposition:

```text
JPHost / JHOST:
  CLOSED as a source for the active capture-order blocker
  retained as historical provenance / architecture evidence
```

## VPA triage and PCC1 / CCBSim target

A separate historical client path was checked next.

Pinned VPA-Linux:

```text
promano7/vpa-linux
a8774eaba8b457ec065ae7a7218fbc80a9d083db
```

VPA's `VCS.PAS` simulator is strictly pairwise:

```text
state: array [Left..Right] of one combatant each
THost: Combat(...)
PHost: CombatPHost(...)
```

So VPA does not contain the missing multi-ship queue.

`VPA2.PAS` has a player-facing "Sort by battle order" key, but that path sorts
starchart/object-list rows and assigns icons/colors. It is not a combat
orchestrator and has no post-capture state mutation.

By contrast, surviving PCC documentation explicitly identifies PCC1's simulator
as **multi-ship THost + PHost**, and CCBSim as the standalone form of the same
PCC battle engine. This makes PCC1/CCBSim the next high-value archaeology target.

Detailed note:

```text
docs/research/2026-10-03-vpa-pcc1-ccbsim-combat-queue-triage.md
```

Tracked package-audit helper:

```text
tools/research/audit-pcc1-ccbsim-packages.sh
```

Default packages:

```text
cc1122.zip
cc1122db.zip
ccbsim1122.zip
```

The helper pins URL/hash/size, inventories package contents, searches debug/MAP
material, identifies any source-like files, and performs bounded binary strings
searches for queue/capture routine names. Recovered binaries remain under
ignored `artifacts/external-sources/pcc1/`.

If MAP/debug data yields useful routine names, the next pass should target those
routines rather than blind-disassemble the full DOS binaries.
