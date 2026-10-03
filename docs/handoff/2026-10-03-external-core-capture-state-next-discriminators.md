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


## PCC1/CCBSim runtime result: exact simulator symbols recovered

The first PCC1 package audit succeeded.

Pinned 1.1.22 artifacts:

```text
cc1122.zip
e8fda19768c8c96d4a4813017121d450ff00e598593a338267403fb5c3914704

cc1122db.zip
199056dfc9838eb055b7e5bce322f9b0d0470acef5f2c2ad09da852a2143dbcc

ccbsim1122.zip
2080e502f098a029fee73b00465d490bac9a52264d4f79a94bdfa9fd31694c1e
```

The debugger archive contains `CC1122.MAP`, and it exposes the historical
Pascal battle-simulator unit directly. Simulator segment `2A92` contains:

```text
SetShipOwner
SortFCBO
CalcBattleOrder
FreeVCRList
KeepVCR
MakeVCR
MakePlanetVCR
NoFightWarning
FillInPlanetAggressiveness
SortResult
```

This is a high-value source-recovery result, but it changes the provenance
interpretation.

### PCC1 is not independent from c2ng

Pinned c2ng source explicitly labels modern routines with their PCC1 ancestry:

```text
ccsim.pas:SortFCBO
ccsim.pas:MakeVCR
ccsim.pas:MakePlanetVCR
ccsim.pas:IsAttacking
ccsim.pas:Attacking
ccsim.pas:AddFighters
```

Those names line up with the recovered PCC1 MAP. c2ng history also has:

```text
bf6d27e440a8ea2ea61f33dc6e8d99ef02a30dab
PCC1 alignment: document relation to PCC1, port some minor functions
```

and the pre-fix `game/sim/run.cpp` identifies itself as a close PCC2 port.

Treat the family as:

```text
PCC1 ccsim.pas
 -> PCC2 simulator
 -> c2ng game/sim
```

So PCC1 cannot be counted as independent corroboration for the c2ng THost queue.

### Why the recovered binary still matters

Immediately before c2ng commit

```text
76b3eed65bee4506758c258b6fc33e10d1a031ee
Simulator: implement battle order peculiarities
```

the descendant queue already used a fixed battle-order vector with outer RIGHT /
inner LEFT traversal. Capture changed owner, crew=10 and aggressiveness=passive,
but had no captured-this-turn flag.

That commit added `fl_WasCaptured` and rejected a captured ship specifically
when supplied as LEFT/inner in Host simulation.

PCC/CCBSim 1.1.21 was released 2021-05-31, only days before that c2ng fix;
PCC/CCBSim 1.1.22 is from 2024. Therefore the DOS lineage gives us a clean
pre/post historical comparison opportunity.

Tracked helper:

```text
tools/research/audit-pcc1-simulator-lineage.sh
```

Default comparison:

```text
1.1.20
1.1.21
1.1.22
```

It downloads each PCC/debug/CCBSim family, extracts the simulator MAP segment
containing `CalcBattleOrder`, computes target routine spacing, searches
`CC.DM`, records CCBSim rule/changelog text, fingerprints the binaries, and
diffs simulator symbols across releases.

This is now the next bounded external-core action. Do not perform a blind full
binary disassembly yet. If the 1.1.21 -> 1.1.22 delta isolates
`CalcBattleOrder` and/or `MakeVCR`, only those routines should receive a
targeted binary pass.


## PCC1 lineage runtime: 1.1.21 -> 1.1.22 structural no-change

The requested 1.1.20 / 1.1.21 / 1.1.22 lineage audit completed.

The decisive structural result is:

```text
1.1.21 ccSim: 145 symbols
1.1.22 ccSim: 145 symbols
```

and every ccSim symbol keeps the same routine offset in 1.1.22 after only the
segment selector changes from `2A8E` to `2A92`.

Capture-relevant routine boundaries are therefore identical:

```text
CalcBattleOrder             0x8114, size 0x17C
Attacking                   0x84D6
KeepVCR                     0x86E5, size 0x89
MakeVCR                     0x8F37, size 0x292
MakePlanetVCR               0x91EF, size 0x8D8
FillInPlanetAggressiveness  0x9DFD, size 0x6D
SimulateOnce                0x9FA0
Simulate                    0xC87E
```

The 1.1.22 CCBSim changelog says only:

```text
fixed formula errors, in particular related to PList 3
```

No battle-order/capture change is documented.

Interpretation: there is no structural evidence that the June-2021 c2ng
captured-LEFT correction was backported into PCC1 by 1.1.22. This is strong
negative source-lineage evidence, but not byte-level proof because same-size
instruction replacement is still possible.

The 1.1.20 -> 1.1.21 change is real but earlier than the c2ng fix:
`CalcBattleOrder` grows from `0x14C` to `0x17C`; `SortFCBO` grows by two
bytes. `MakeVCR`, `KeepVCR`, and `MakePlanetVCR` keep their lengths.

Next tracked discriminator:

```text
tools/research/audit-pcc1-simulator-overlay-bytes.py
```

It parses the Turbo/Borland overlay thunk/control header from `CC.EXE`, uses
its OVR file offset/code size/relocation table to extract the exact ccSim image
from `CC.OVR`, relocation-normalizes it, then compares both whole-unit bytes
and exact MAP-bounded routines.

Run:

```bash
cd ~/projects/planets-lab-external
git pull --ff-only origin research/external-engine-analysis

python3 tools/research/audit-pcc1-simulator-overlay-bytes.py \
  | tee /tmp/pcc1-simulator-overlay-byte-audit.log
```

Do not start a broad disassembly before this result. If 1.1.21 and 1.1.22 are
byte-identical after relocation normalization, close this PCC1 backport line.
If only specific capture-relevant routines differ, disassemble those routines
only.


## PCC1 exact overlay byte result

The exact overlay-byte audit completed successfully.

```text
1.1.21 ccSim:
  code  = 0xCC0D
  reloc = 0x0ABA
  entry points = 37

1.1.22 ccSim:
  code  = 0xCC0D
  reloc = 0x0ABA
  entry points = 37
```

So the unit remains structurally identical, but raw/generated bytes are not:

```text
1121 -> 1122:
  raw changed bytes = 3091
  first-pass relocation-normalized changed bytes = 2232
```

Every capture-relevant routine shows small-to-moderate operand-byte churn,
including routines whose symbol offsets and lengths are unchanged.

The changed ranges are dominated by one-/two-byte differences spread through
the entire ccSim unit, including formatting/UI routines. Because unrelated
program units also changed sizes/segment layout between 1.1.21 and 1.1.22,
this pattern is more consistent with linked address/global-symbol churn than a
localized capture-state patch.

Do **not** interpret the 2232 normalized-byte count as 2232 semantic code
changes.

Next tracked helper:

```text
tools/research/audit-pcc1-simulator-semantic-diff.py
```

It disassembles only the target routines in i8086 mode and resolves changed
numeric operands against both MAP symbol tables.

Run after pulling the research branch:

```bash
python3 tools/research/audit-pcc1-simulator-semantic-diff.py \
  | tee /tmp/pcc1-simulator-semantic-diff.log
```

The gating classes are:

```text
mapped_symbol_relocation
  -> layout churn, not a mechanics change

operand_value_change
  -> inspect; could be a changed constant or an unlabelled address

operand_shape_change / mnemonic_change /
instruction_size_change / instruction_boundary_change
  -> actual generated-code delta; bounded reverse required
```

Focus interpretation on:

```text
CalcBattleOrder
Attacking
KeepVCR
MakeVCR
```

If those routines contain no unresolved instruction-shape/control-flow delta,
close the PCC1 1.1.22 backport hypothesis and return to the external-core
candidate search / Nu corpus discriminator instead of spending more time on
the DOS binary lineage.
