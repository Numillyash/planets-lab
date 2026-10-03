# VPA / PCC1 / CCBSim combat-queue triage — 2026-10-03

## Scope

This note follows the JPHost closure and asks a narrower question:

> Is there an independent historical implementation of the THost multi-ship
> battle queue that can supply candidate post-capture state transitions?

External implementations remain candidate generators only. Nothing in this note
is NuHost evidence by itself.

## 1. VPA-Linux / VPA 3.67

Repository:

```text
https://github.com/promano7/vpa-linux
```

Pinned revision inspected:

```text
a8774eaba8b457ec065ae7a7218fbc80a9d083db
Bump version to 3.67.7
```

The repository identifies itself as a native GNU/Linux port/reconstruction of
VGA Planets Assistant 3.67. Its licensing note separates the historical VPA
core (SourceForge project metadata: MPL 1.1) from PCC/PCC2-derived components,
which retain Stefan Reuther's PCC II BSD-style terms.

Relevant files:

```text
VPA/VCS.PAS
VPA/TCOMBAT.PAS
VPA/VPA2.PAS
VPA/PVCRALG.PAS
CC/PHOSTM.PAS
```

### VPA combat simulator is pairwise, not a host queue

`VPA/VCS.PAS` declares:

```text
Unit VCS;  (* Video Combat Simulator *)

procedure CombatSimulation;
```

The simulator state is exactly two participants:

```text
v : array [LRType] of VRec;
```

and `StartCombat` creates a single `VCRData` from LEFT/RIGHT. For PHost it
calls `CombatPHost(...)`; otherwise it calls `Combat(...)` for THost.

Therefore VPA's F5 simulator is a **1:1 pairwise resolver**. It does not select a
multi-ship sequence and cannot answer the post-capture queue question.

This matches Stefan Reuther's client fact sheet, which distinguishes:

```text
VPA   -> one/one THost battle simulator
PCC   -> multi-ship THost + PHost simulator
PCC2  -> multi-ship THost/PHost/NuHost/FLAK simulator
```

### VPA's "Sort by battle order" is UI ordering

`VPA/VPA2.PAS::InitObjList` contains a useful historical display heuristic:

```text
numeric FC + aggressive:      key = FC + 1000
aggressive, no numeric FC:    key = ship id + 2000
can fight but not willing:    key = ship id + 3000
cannot fight:                 key = ship id + 4000
no fuel:                      key = ship id + 5000
unknown/enemy data:           key = ship id + 6000
```

The code is in the starchart/object-list sort path. It builds icons/colors and
display keys; it is not a combat traversal and has no result mutation,
captured-this-turn bit, queue cursor, repeat bound, or regenerated order.

Use it only as historical evidence that VPA exposed a player-facing
approximation of ordinary THost battle priority.

### VPA disposition

```text
VPA:
  pairwise combat physics/viewer: useful historical reference
  multi-ship queue: absent
  post-capture queue mechanics: absent
```

Do not spend more time trying to derive the missing queue from VPA.

## 2. PCC1 / CCBSim is the next high-value target

Stefan Reuther's surviving PCC page explicitly describes PCC 1.x as containing
a built-in **multi-ship battle simulator**.

The standalone utility page describes CCBSim as being based on PCC's built-in
simulator, supporting up to 200 ships plus one planet/starbase and both THost
and PHost families.

This is materially different from VPA:

```text
VPA:
  1:1 THost resolver

PCC1 / CCBSim:
  multi-ship THost queue
  multi-ship PHost queue
```

That makes PCC1/CCBSim the strongest remaining candidate for an independent
historical THost queue implementation.

## 3. Available historical packages

Surviving download index:

```text
https://phost.de/~stefan/planets/
```

Current PCC1 family visible there:

```text
cc1122.zip
cc1122db.zip
cc1122doc.zip
...
```

Current standalone simulator:

```text
ccbsim1122.zip
```

The index also preserves older standalone simulator builds, including:

```text
ccbsim.zip
ccbsim1191.zip
ccbsim11122.zip
ccbsim1115.zip
ccbsim1117.zip
ccbsim11171.zip
ccbsim1119.zip
ccbsim1120.zip
ccbsim1121.zip
```

The site identifies the `cc112x db` packages as PCC's core-dump debugger.
PCC's D4TP support uses MAP symbols for core-dump analysis, so the debugger
package is worth auditing even if the application source itself is absent.

## 4. What must be recovered from PCC1 / CCBSim

Do not start by reverse-engineering combat arithmetic. The relevant target is
the **orchestrator around pairwise fights**.

Search recovered package/debug material for names or strings corresponding to:

```text
battle order / battle value
sort / queue / list
aggressor / opponent / enemy
capture / captured / surrender
owner / crew
passive / disabled
left / right
fight / combat / VCR
repeat / twice
```

For any candidate queue routine, extract only these dimensions:

```text
initial ordinary sort key
outer/inner traversal roles
physical LEFT/RIGHT assignment
state mutation on capture
captured ship eligibility after capture
whether current ordinary cursor continues
whether queue/order is rebuilt
whether a fresh order is inserted
which FC/mission/PE state it uses
per-pair repeat limit
```

Then compare that model against the existing Nu discovery corpus. Never promote
PCC behavior directly.

## 5. Reproducible package-audit helper

Tracked helper:

```text
tools/research/audit-pcc1-ccbsim-packages.sh
```

It downloads only the small surviving PCC/CCBSim packages into ignored
`artifacts/external-sources/pcc1/`, records URL/SHA256/size, lists every archive
member, extracts debugger/map/symbol material, inventories DOS executables, and
runs bounded strings/symbol searches for the queue-state terms above.

The first pass deliberately avoids decompilation. If MAP/debug data exposes
routine names, those names should drive the next bounded binary pass instead of
blind disassembly.

## Evidence boundary

```text
PCC1/CCBSim THost behavior:
  historical external comparator

PCC1/CCBSim NuHost behavior:
  none; PCC1 predates NuHost

NuHost rule:
  must still be established from primary Nu docs + factual Nu corpus
```
