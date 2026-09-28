# Independent VCR consumers and legacy-engine triage — 2026-09-28

## Scope

This pass follows the c2ng capture/order audit and asks a narrower question:

```text
Which additional external projects actually construct combat pair/order/LEFT-RIGHT,
and which merely consume factual VCRs or provide unrelated client/API functionality?
```

The current planets-lab blocker remains:

```text
post-capture ship LEFT / RIGHT side assignment
```

Evidence boundary remains unchanged:

```text
third-party implementation != NuHost evidence
```

No mechanics evidence labels are changed by this note.

## Executive result

The targeted projects split cleanly:

- **c2ng remains the only audited external project in this set that actually contains a Host-like ordinary combat-order driver relevant to post-capture queue semantics.**
- **Kecupo/planets-vcr-sim** consumes an already supplied factual VCR pair and runs a pair/fleet combat resolver. It does not reconstruct the co-located Host combat queue.
- **ChallengeSY/nu-replayer** parses factual VCRs from loadturn and replays/simulates those supplied combats. It does not implement battle-order selection.
- **Kecupo/PMS-Planets.nu** exposes general Planets.nu turn/API/client data but no VCR/order/LEFT-RIGHT implementation was found in the targeted audit.
- **xer0x/vgaphost** is an empty historical stub: one README containing only `hi`, no engine code.
- **JHOST/JPHost** is historically confirmed as a real Java port of PHost 3 with staged Host processing in CVS, but its source tree was not recovered in this pass, so no capture/order rule can be attributed to it yet.
- **OpenPlanets** is historically confirmed as a GPLv3 Java/MySQL planning-stage PHost4/VPA-inspired successor, but no auditable processing core was recovered in this pass.

For the current blocker, the strongest new result is not a new queue hypothesis but an additional **LEFT/RIGHT adapter cross-check**: c2nu, Kecupo's VCR simulator, and ChallengeSY's Nu Replayer all preserve or explicitly interpret the server-provided combat orientation rather than deriving a new side assignment.

## Comparison matrix

| category | project / pin | external location | implementation behavior | planets-lab equivalent/status | candidate difference | discriminator already possible? | next action |
|---|---|---|---|---|---|---|---|
| A | Kecupo/planets-vcr-sim `299a17b04b16b3b9764226dd2a27332c89d7d712` | `Scripts/Combat/combat_factory.gd` | maps turn `left` directly to simulator left and `right` directly to simulator right | factual LEFT/RIGHT are comparator data in planets-lab | independently agrees with literal Nu side mapping | yes | use as mapping cross-check only |
| B | same | `combat_simulator_thost.gd::_simulate_fleet_sequence` | resolves already supplied left/right fleets; advances fleet index on destruction/capture | not the current Host queue model | fleet-sequence logic must not be mistaken for Nu co-located battle order | no useful C5 discriminator | exclude from queue-candidate set |
| A | ChallengeSY/nu-replayer `a1955501eb1519497c7cef70a123649f6eca8570` | `LoadTurn.bi`, `ParseData.bas`, `VCRPlr.bi` | parses factual `vcrs`; stores LeftOwner/RightOwner and two ordered combatants; replay code treats combatant 1 as LEFT and combatant 2 as RIGHT | factual side mapping under audit | independently preserves server-emitted orientation | yes | use as second mapping cross-check |
| B | same | VCR player/simulator | computes what-if outcomes for each supplied VCR; no battle-order/queue generator found | pair resolver is not current blocker | no post-capture queue semantics | no | exclude from queue-candidate set |
| B | Kecupo/PMS-Planets.nu `42041025d049924d50c4963400de7032287569bc` | API/data scripts | general Planets.nu client/API/save mappings; no VCR/left/right/battle-order path found in targeted source search | API field work only | no current combat-side candidate | no | defer to API/economy work |
| B | xer0x/vgaphost `01809a5d6518f4428fb51297ddac7ae529b542d3` | entire repository | exactly one README file containing `hi`; no source code | previously unassessed | repo name is misleading; no engine exists to audit | no | close as dead end |
| B | JHOST/JPHost SourceForge | project/CVS history | historically a Java port of PHost 3; news confirms staged Host processing existed | potentially valuable server-side reference | source unavailable in current pass, so no candidate rule can be extracted | not yet | retain high-priority source-recovery task |
| B | OpenPlanets SourceForge | project/code listing | planning-stage Java/MySQL project intended to mimic PHost4/VPA | potential architecture/reference only | no recovered engine core | not yet | low priority until source snapshot recovered |
| C | c2ng (from prior audit) | `game/sim/run.cpp` | frozen pre-combat order + RIGHT-outer/LEFT-inner cursor + captured-LEFT suppression | exact current blocker | concrete post-capture queue candidate | yes | run existing 8-row official Nu cursor diagnostic |

## 1. Kecupo/planets-vcr-sim

### Provenance

```text
repository: Kecupo/planets-vcr-sim
pin: main@299a17b04b16b3b9764226dd2a27332c89d7d712
pin date: 2026-09-15
language/runtime: Godot / GDScript
license: not established in this audit; no root LICENSE file was present in the pinned tree
```

README describes it as a Planets.nu offline VCR viewer and battle simulator.

### Factual VCR mapping

`Scripts/Combat/combat_factory.gd::create_vcr_from_turn_vcr_dict()` performs:

```text
left_data  = data["left"]
right_data = data["right"]

ClassicVcr.left  <- left_data + leftownerid
ClassicVcr.right <- right_data + rightownerid
```

No side swap or side inference occurs in this adapter.

The same direct mapping appears in `create_vcr_from_turn_dict()`.

This is independent corroboration of c2nu's mapping:

```text
Nu factual .left  -> left
Nu factual .right -> right
```

### What its simulator actually does

`combat_simulator_thost.gd::_simulate_fleet_sequence()` starts from a previously constructed:

```text
left_fleet
right_fleet
```

and repeatedly resolves:

```text
current_left vs current_right
```

If a combatant is destroyed or captured, that side's fleet index advances.

This is useful for multi-ship/fleet combat simulation, survivor behavior and pairwise VCR checks, but it does **not** answer:

- which co-located ship becomes the next Host opponent;
- how ordinary Host battle order is generated;
- whether capture resets an ordinary Host cursor;
- how Nu assigns LEFT/RIGHT to a newly selected post-capture pair.

Therefore this project is **not a second implementation of the c2ng queue candidate**.

### Classification

For the current blocker:

```text
A: literal LEFT/RIGHT adapter cross-check
B: pair/fleet resolver reference
C: none
```

## 2. ChallengeSY/nu-replayer

### Provenance

```text
repository: ChallengeSY/nu-replayer
pin: master@a1955501eb1519497c7cef70a123649f6eca8570
pin date: 2026-09-27
language: FreeBASIC
license: MIT (license.md)
```

The manual states that Nu Replayer watches VCRs that have already occurred and computes what-if outcomes for each VCR.

### Factual VCR ingestion

`LoadTurn.bi` finds the factual `"vcrs"` array and parses for each record:

```text
seed
x / y
battletype
leftownerid  -> LeftOwner
rightownerid -> RightOwner
turn
id
two combatant objects in server-emitted order
```

The parser uses a sequential two-object loop rather than independently locating nested `left` and `right` keys. This is important: it relies on server-emitted nested-object order at this step.

However, all downstream semantics consistently bind:

```text
Combatants(1) -> LEFT
Combatants(2) -> RIGHT
LeftOwner     -> Combatants(1) side
RightOwner    -> Combatants(2) side
```

Examples from `VCRPlr.bi`:

- explicit comment `Left side first` before processing `Combatants(1)`;
- explicit comment `Right side` before processing `Combatants(2)`;
- LEFT owner coloring is attached to combatant 1;
- RIGHT owner coloring is attached to combatant 2;
- if combatant 1 is captured, UI reports RIGHT side wins by capture;
- if combatant 2 is captured, UI reports LEFT side wins by capture.

`ParseData.bas::exportVCRs()` exports:

```text
LeftOwner, RightOwner,
Combatants(1), Combatants(2)
```

in that same orientation.

### Queue audit

Targeted code searches found:

- no battle-order implementation;
- no Host queue builder;
- no post-capture pair-selection routine;
- `queue` references are unrelated audio/UI queues.

Nu Replayer contains a pairwise combat resolver in `VCRPlr.bi`, including capture determination, but its input is a factual VCR pair.

Therefore it is not an independent source for post-capture Host pair/side generation.

### Classification

```text
A: independent factual side-orientation cross-check
B: pairwise Nu VCR resolver/reference
C: none for current post-capture queue blocker
```

## 3. Three-way external LEFT/RIGHT cross-check

After this pass, three independent codebases point in the same direction.

### c2nu

```text
data["left"]  -> first/left legacy VCR object
data["right"] -> second/right legacy VCR object
```

### Kecupo/planets-vcr-sim

```text
data["left"]  -> ClassicVcr.left
data["right"] -> ClassicVcr.right
```

### ChallengeSY/nu-replayer

```text
leftownerid/rightownerid retained explicitly
server first combatant -> Combatants(1) -> LEFT
server second combatant -> Combatants(2) -> RIGHT
```

These projects are independent enough to make a generic semantic inversion such as:

```text
Nu "left" actually means right
```

a weak candidate.

This still does **not** substitute for checking our own official raw payload. The bounded canonical diagnostic remains:

```text
raw vcr.left.objectid  == planets-lab factual LEFT object
raw vcr.right.objectid == planets-lab factual RIGHT object
```

on the known capture rows.

## 4. Kecupo/PMS-Planets.nu

### Provenance

```text
repository: Kecupo/PMS-Planets.nu
pin: main@42041025d049924d50c4963400de7032287569bc
pin date: 2026-06-03
language/runtime: Godot / GDScript
license: not established in this audit; no root LICENSE file was present in the pinned tree
```

Targeted searches for:

```text
vcr
leftownerid
rightownerid
battle order
left / right combat fields
```

did not expose a combat/VCR path.

The repository does contain useful Planets.nu API/save/data mappings such as ship, planet and turn command fields. Those may be useful for future API/economy work, but not for the active capture-side blocker.

Classification: **B / defer**.

## 5. xer0x/vgaphost

### Provenance

```text
repository: xer0x/vgaphost
pin: master@01809a5d6518f4428fb51297ddac7ae529b542d3
single commit: 2009-02-27, "first commit"
license: none found
```

Full recursive tree at the pinned commit contains exactly:

```text
README
```

Its content is:

```text
hi
```

There is no engine, source tree, Host pipeline or useful historical implementation.

This closes the earlier "repository name looks promising" uncertainty.

Classification: **dead end / remove from high-priority engine backlog**.

## 6. JHOST / JPHost

Public SourceForge metadata confirms JHOST as:

- an **Alpha** project;
- a Java port of **PHost 3**;
- GPLv2;
- registered in 2001;
- historically maintained by `soronthar`. External project metadata and the old news archive support those points. 

The historical news archive provides stronger architectural evidence than the project summary:

- first CVS upload in December 2002;
- by January 2004 first-milestone features were nearly complete;
- starbases could build defenses/fighters;
- ghost planets were cleared;
- a messaging mechanism existed;
- by March 2004 messages were generated by every implemented stage that needed them;
- by May 2004 only the Alliance interface was described as pending for Milestone One and work on Milestone Two had started.

This strongly suggests an actual staged Host processing engine existed, rather than only a UI/client shell.

### Current limitation

This pass did **not** recover an inspectable JHOST CVS source snapshot through the available GitHub/web paths.

Therefore we cannot responsibly state:

- how its combat queue was represented;
- whether capture modified queue state;
- whether LEFT/RIGHT was explicit;
- which PHost source/docs its combat stage followed.

No mechanics candidate can be extracted from project-news metadata alone.

Classification:

```text
B: high-value unresolved source-recovery target
C: none yet
```

## 7. OpenPlanets

Public SourceForge metadata describes OpenPlanets as:

- status: **Planning**;
- Java;
- MySQL;
- GPLv3;
- registered in 2010;
- an unofficial VGA Planets successor intended to mimic PHost4/VPA features.

The SourceForge project page advertises code browsing, but this pass did not recover an inspectable source snapshot or locate a GitHub mirror.

Therefore the previous hypothesis that it might contain a real processing core remains unverified.

No capture/order candidate is justified.

Classification:

```text
B: historical architecture/source-recovery backlog
C: none
```

Its priority should remain below JHOST because JHOST's historical news independently demonstrates implemented Host stages, whereas OpenPlanets remains planning-status in the currently accessible evidence.

## Revised priority for current blocker

### Immediate

1. Run the **c2ng frozen-order / persistent-cursor / captured-LEFT suppression** candidate against the existing eight official Nu capture continuations.
2. Run the raw official Nu LEFT/RIGHT adapter invariant on the same population.

### Do not spend blocker time on

- Kecupo/planets-vcr-sim queue reconstruction;
- ChallengeSY/nu-replayer queue reconstruction;
- PMS;
- vgaphost.

They do not expose an independent Host queue for the active question.

### Continue opportunistically

- recover JHOST CVS/source snapshot;
- recover OpenPlanets source snapshot only if inexpensive.

## Category summary

### A — already equivalent / useful cross-check

- c2nu literal LEFT/RIGHT mapping;
- Kecupo planets-vcr-sim literal LEFT/RIGHT mapping;
- ChallengeSY Nu Replayer's explicit first=LEFT / second=RIGHT semantics.

These strengthen an adapter-level interpretation but do not promote a Host mechanic.

### B — reference/dead-end/non-discriminating for current blocker

- Kecupo pair/fleet resolver;
- ChallengeSY pairwise VCR resolver;
- PMS API/client layer;
- vgaphost empty stub;
- JHOST until source recovered;
- OpenPlanets until source recovered.

### C — immediately testable mechanics candidate

Still only:

```text
c2ng:
frozen pre-combat order
+ persistent RIGHT-outer/LEFT-inner cursors
+ no post-capture re-sort/reset
+ captured-LEFT suppression
```

## Main-track implication

This pass narrows rather than expands the hypothesis set.

For the active C5 blocker, there is no reason to invent a rule from these additional VCR tools. They independently reinforce that factual LEFT/RIGHT is a server-side datum they consume.

The one external queue hypothesis worth immediate official-Nu testing remains c2ng's cursor model.

## External source metadata

Web-retrieved historical metadata used for JHOST/OpenPlanets:

- SourceForge JHOST project page: project is Alpha, Java, GPLv2 and describes itself as a port of PHost 3.
- SourceForge JHOST news archive: documents CVS uploads and multiple implemented Host stages in 2002–2004.
- SourceForge OpenPlanets project page: status Planning, Java/MySQL, GPLv3, attempts to mimic PHost4/VPA.

These are project/provenance facts only, not mechanics evidence.
