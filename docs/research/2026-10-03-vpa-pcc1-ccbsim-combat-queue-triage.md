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


## 6. Runtime result: PCC 1.1.22 debug symbols expose the complete simulator unit

The package audit was run successfully against the 1.1.22 release family.

Pinned packages:

```text
cc1122.zip
SHA256 e8fda19768c8c96d4a4813017121d450ff00e598593a338267403fb5c3914704
size   1225177

cc1122db.zip
SHA256 199056dfc9838eb055b7e5bce322f9b0d0470acef5f2c2ad09da852a2143dbcc
size   76572

ccbsim1122.zip
SHA256 2080e502f098a029fee73b00465d490bac9a52264d4f79a94bdfa9fd31694c1e
size   330224
```

The debugger package is much more valuable than expected. `CC1122.MAP`
contains private/public Pascal symbols for the battle simulator.

The simulator code lives in segment `2A92`. Relevant symbols include:

```text
2A92:5DF8  SetShipOwner
2A92:5E42  SetDefaultOwner
2A92:5F0A  SortId
2A92:5F21  SortOwner
2A92:5F49  SortHull
2A92:5F71  SortThings
2A92:5FFA  SortFCBO
2A92:60F7  SortMenu
2A92:672E  AddFighters

2A92:8114  CalcBattleOrder
2A92:8290  FreeVCRList
2A92:86E5  KeepVCR
2A92:8F37  MakeVCR
2A92:91EF  MakePlanetVCR
2A92:9C62  NoFightWarning
2A92:9DFD  FillInPlanetAggressiveness
2A92:A677  SortResult
2A92:AD9A  CSimResultList.Resort
```

This is the first recovered historical binary in this stream where the exact
multi-ship orchestration routines are named.

The standalone `CCBSIM.EXE` also contains strings proving that the same program
models:

```text
ship id affects battle order
aggressiveness / Kill / PE
random LEFT/RIGHT
captured result
captured back / captured by
multi-fight result aggregation
```

The bundled documentation explicitly says that THost non-numeric friendly-code
ordering is refined by Kill/PE aggressiveness and that Host simulation uses the
Host 3.2 battle-order rules.

## 7. Critical provenance correction: PCC1 is not an independent comparator to c2ng

The symbol names above allow a direct lineage match against the pinned c2ng
source.

Pinned c2ng:

```text
425d623e5d44b017abea50bae4dc9c668870398d
```

Its source explicitly names the old PCC1 Pascal routines:

```text
game/sim/sort.cpp:
  ccsim.pas:SortId
  ccsim.pas:SortOwner
  ccsim.pas:SortFCBO

game/sim/run.cpp:
  ccsim.pas:IsAttacking
  ccsim.pas:Attacking
  ccsim.pas:MakeVCR
  ccsim.pas:MakePlanetVCR

game/sim/fleetcost.cpp:
  ccsim.pas:AddFighters
```

Those names match the recovered PCC 1.1.22 MAP symbols exactly.

There is also an explicit c2ng history commit:

```text
bf6d27e440a8ea2ea61f33dc6e8d99ef02a30dab
PCC1 alignment: document relation to PCC1, port some minor functions
```

and the pre-fix simulator source states that `game/sim/run.cpp` was a close
port of PCC2. Thus the implementation family is:

```text
PCC1 ccsim.pas
   -> PCC2 simulator rewrite/port
      -> c2ng game/sim
```

Therefore **PCC1/CCBSim cannot be counted as independent corroboration** of the
c2ng THost queue. It is an ancestor/sibling implementation from the same author
and code lineage.

It remains useful for a different question: reconstructing how that lineage
changed over time.

## 8. Historical delta around c2ng bug #428

The c2ng parent immediately before the battle-order fix is:

```text
475b6c5b329ef77df8cbb657f12da8a76296f8fa
```

In that version the Host/PHost orchestration already has the familiar fixed
battle-order vector and nested traversal:

```text
outer loop = RIGHT
inner loop = LEFT
```

After a capture, `MakeVCR`/its C++ descendant immediately mutates:

```text
owner          -> captor
crew           -> 10
aggressiveness -> passive
```

but there is no dedicated captured-this-turn flag. The captured ship remains
in the same fixed vector and later pair eligibility is tested symmetrically.

Commit:

```text
76b3eed65bee4506758c258b6fc33e10d1a031ee
Simulator: implement battle order peculiarities
```

adds:

```text
fl_WasCaptured
```

and, for non-PHost simulation, rejects a captured ship specifically when it is
supplied as the LEFT/inner combatant.

The commit attributes that asymmetry to a reverse-engineered Tim-Host typo
(`youship` vs `you`). This remains external reverse-engineering evidence, not
NuHost evidence.

This history means that the recovered PCC1 binary is most valuable if we can
date whether the same capture-state correction was backported into the DOS
`ccsim.pas` line.

## 9. Next bounded archaeology: PCC 1.1.20 -> 1.1.21 -> 1.1.22

This comparison has an unusually useful natural boundary:

```text
PCC / CCBSim 1.1.21:
  released 2021-05-31

c2ng captured-LEFT fix:
  2021-06-05 / 2021-06-06 history

PCC / CCBSim 1.1.22:
  released 2024-04-28
```

So 1.1.21 is a clean pre-fix snapshot of the PCC1 branch, while 1.1.22 is a
later build that may or may not contain an equivalent backport.

Tracked helper:

```text
tools/research/audit-pcc1-simulator-lineage.sh
```

The helper compares 1.1.20, 1.1.21 and 1.1.22 package/debug/simulator families,
extracts the complete simulator MAP segment containing `CalcBattleOrder`,
computes target-routine spacing, searches `CC.DM` for source/unit metadata,
compares simulator symbols across releases, and records the relevant
`CCBSIM.DOC` changelog text.

The goal is **not** to prove Nu mechanics. The goal is to answer:

```text
Did the historical PCC1 ccsim.pas lineage acquire a captured-this-turn /
role-asymmetric THost correction after 1.1.21, and if so can its binary/debug
delta narrow the exact old Pascal routine that changed?
```

If the answer is yes, only that routine needs a bounded binary pass.


## 10. Runtime lineage comparison: 1.1.21 -> 1.1.22 is structurally unchanged

The three-version runtime audit completed successfully.

Important structural result:

```text
PCC 1.1.21 ccSim:
  simulator_symbols = 145

PCC 1.1.22 ccSim:
  simulator_symbols = 145
```

For the complete ccSim symbol table, every routine offset from 1.1.21 to
1.1.22 is identical after accounting for the changed segment selector:

```text
1.1.21 segment = 2A8E
1.1.22 segment = 2A92
```

In particular:

```text
SetShipOwner                  5DF8
SortFCBO                      5FFA
CalcBattleOrder               8114
FreeVCRList                   8290
Attacking                     84D6
KeepVCR                       86E5
MakeVCR                       8F37
MakePlanetVCR                 91EF
FillInPlanetAggressiveness    9DFD
SimulateOnce                  9FA0
Simulate                      C87E
```

The derived target sizes are also exactly unchanged:

```text
SetShipOwner                  0x4A
SortFCBO                      0xFD
CalcBattleOrder               0x17C
FreeVCRList                   0x42
KeepVCR                       0x89
MakeVCR                       0x292
MakePlanetVCR                 0x8D8
NoFightWarning                0x88
FillInPlanetAggressiveness    0x6D
SortResult                    0x179
```

The bundled CCBSim 1.1.22 changelog only describes the release as fixing
formula errors, especially PList 3. It does not mention battle order, captured
ships, or active/passive handling.

This is strong negative evidence against the idea that the 2021 c2ng
captured-LEFT correction was later backported into the PCC1 DOS simulator by
adding a structurally new state/check. It is **not yet byte-level proof**:
same-size replacement instructions remain theoretically possible.

The earlier 1.1.20 -> 1.1.21 transition is different. There:

```text
CalcBattleOrder 0x14C -> 0x17C
SortFCBO        0xFB  -> 0xFD
```

while `MakeVCR`, `KeepVCR`, and `MakePlanetVCR` retain their target
sizes. That transition predates the c2ng captured-LEFT fix and therefore cannot
be the June-2021 fix itself.

### Exact byte audit

Tracked helper:

```text
tools/research/audit-pcc1-simulator-overlay-bytes.py
```

The helper uses the PCC MAP selector plus the resident Turbo/Borland overlay
control header in `CC.EXE` to locate the exact `ccSim` code image in
`CC.OVR`. It then:

1. extracts the complete overlaid ccSim code image;
2. reads its relocation table;
3. zeros 16-bit relocation patch words to create a relocation-normalized image;
4. hashes the raw and normalized unit;
5. compares exact per-routine slices using MAP symbol boundaries;
6. reports every normalized changed byte range and the routine(s) containing it.

This is the required discriminator before spending time in a disassembler.

Expected interpretation:

```text
1121 == 1122 after relocation normalization
    -> PCC1 DOS simulator did not receive a code change in ccSim;
       c2ng captured-LEFT fix belongs to the later PCC2/c2ng lineage.

1121 != 1122 only in unrelated routines
    -> same conclusion for capture-state purposes.

1121 != 1122 in MakeVCR / Attacking / CalcBattleOrder
    -> perform a bounded disassembly only for changed routine(s).
```

The extracted local binary slices are research artifacts only and must not be
committed.


## 11. Exact overlay-byte audit: 1.1.21 -> 1.1.22 differs, but pattern is dominated by address/layout churn

The exact Turbo/Borland overlay extractor successfully located the `ccSim`
overlay image in all three builds using the MAP segment selector plus the
resident overlay control block in `CC.EXE`.

Recovered metadata:

```text
1.1.20:
  map segment 2A68
  EXE control block 0x31D20
  OVR offset 0x83603
  code bytes 0xDBAD
  relocation bytes 0x0C0E
  entry count 42

1.1.21:
  map segment 2A8E
  EXE control block 0x31F90
  OVR offset 0x8432E
  code bytes 0xCC0D
  relocation bytes 0x0ABA
  entry count 37

1.1.22:
  map segment 2A92
  EXE control block 0x32000
  OVR offset 0x8526C
  code bytes 0xCC0D
  relocation bytes 0x0ABA
  entry count 37
```

This confirms again that the 1.1.21 and 1.1.22 `ccSim` units have identical
overall code size, relocation-table size and entry-point count.

However, exact bytes are not identical:

```text
1.1.21 -> 1.1.22:
  raw changed bytes              3091
  relocation-normalized changed  2232
```

Capture-relevant routine byte deltas after the first relocation normalization:

```text
SetShipOwner                 1
SortFCBO                    26
CalcBattleOrder             20
Attacking                   25
KeepVCR                     17
MakeVCR                     60
MakePlanetVCR              208
FillInPlanetAggressiveness   6
SimulateOnce                82
Simulate                    35
```

These counts do **not** by themselves imply that all of those routines changed
semantically. The distribution is the opposite of what a localized
captured-state patch would normally look like: one- and two-byte deltas are
spread throughout essentially every routine, including UI/formatting helpers.
The MAP also shows that unrelated units changed size and shifted later segment
selectors between the two program builds. This strongly suggests that many
remaining byte changes are link-layout/global-symbol address changes which are
not represented by the overlay relocation table we normalized.

Therefore the previous "exact bytes" discriminator needs one more level:
instruction/operand classification.

### Instruction-level semantic triage

Tracked helper:

```text
tools/research/audit-pcc1-simulator-semantic-diff.py
```

It uses GNU `objdump` in i8086 mode and the 1.1.21/1.1.22 MAP symbol tables to
compare only the capture-relevant routines.

For each instruction it distinguishes:

```text
equal
mapped_symbol_relocation
operand_value_change
operand_shape_change
mnemonic_change
instruction_size_change
instruction_boundary_change
```

A changed numeric operand is classified as `mapped_symbol_relocation` when
the old/new operand values resolve to the same named MAP symbol across the two
builds. This is intended to strip out the exact class of program-layout churn
visible in the byte audit without masking opcode/control-flow changes.

The helper prints all unresolved numeric changes and every instruction-shape /
mnemonic / boundary change, while keeping the full machine-readable record in
JSON.

Interpretation:

```text
capture routines:
  only equal + mapped_symbol_relocation
    -> no generated-code evidence of a PCC1 capture backport

unresolved operand-only changes in unrelated formulas/UI
    -> still no capture backport

mnemonic / operand-shape / boundary changes in
CalcBattleOrder / Attacking / KeepVCR / MakeVCR
    -> bounded disassembly of only those exact instructions/routines
```

This pass is preferable to blind disassembly of the full 50-KiB overlay.
