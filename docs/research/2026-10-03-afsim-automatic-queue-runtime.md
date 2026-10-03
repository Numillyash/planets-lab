# AFSim automatic queue runtime — 2026-10-03

## Scope

This note belongs to the separate external-engine research stream:

```text
branch:
  research/external-engine-analysis

active canonical unknown:
  post-capture ship combat order / LEFT-RIGHT assignment
  especially O = continuation in an existing order
             C = additional order generated on capture
```

AFSim is an external historical THost-era simulator. Its behavior is a
candidate/comparator only:

```text
AFSim implementation != NuHost truth
```

No canonical mechanics or evidence labels are promoted by this note.

## Source / provenance

Program:

```text
AFSim
author: Sean Martens
platform: DOS
role: multi-ship VGA Planets battle simulator / VCR front-end
```

Primary recovered archive locator:

```text
Apajalista ID: 41859
filename:       AFSIM.ZIP
index date:     1995-12-31
index size:     41757 bytes
```

Apajalista description says AFSim is a menu-driven front-end able to simulate
battle scenarios from VGA Planets.

The archive was fetched manually through a Windows browser because the
Apajalista HTTP endpoint delivered only about 8 KiB over two-minute bounded
curl attempts from the WSL environment.

Recovered local archive:

```text
actual size:
  41844 bytes

SHA256:
  778dde575b8293b6cb266ea62a456b972ddf5d4d33de526e3c5700825f5ed3e2

ZIP validation:
  clean
```

The size difference between the historical Apajalista index and the currently
served archive is recorded but not interpreted. The exact recovered SHA256 is
the artifact identity for all further analysis.

Archive members:

```text
AFSIM.CFG
AFSIM.DOC
AFSIM.EXE
FILE_ID.DIZ
```

No source, MAP, SYM, DBG, TDS or listing material was recovered in this package.

External binaries remain local under ignored artifacts and are not committed.

## Historical corroboration

PlanetsCentral identifies AFSim as a multi-ship simulator which delegates the
individual pairwise combat to Tim Wisseman's VCR. Its technical file list also
identifies AFSim-specific saved simulation data.

Contemporary Usenet/FTP inventories separately list AFSim among multi-ship
battle simulators and later name `afsim131.zip` as a distributed DOS
shareware build.

The exact version of the recovered generic `AFSIM.ZIP` remains deliberately
UNKNOWN until the package header/manual metadata is extracted. Do not equate the
archive automatically with AFSim 1.2 or 1.31.

License/distribution status is also not yet pinned beyond historical shareware
distribution references; preserve the package as research-only local material.

## Runtime decision-gate result

The first package audit answers the main candidate question.

AFSim's own manual states that battle order is determined by:

```text
ship ID
friendly code
mission
primary enemy
```

The same manual exposes an OOB display containing ship ID, friendly code and
primary enemy, and later documents attack-value / mission / primary-enemy
ordering behavior.

This means AFSim is **not merely consuming a user-prescribed pair sequence**.
It derives battle-order state from ship attributes.

The manual also describes simulation continuing until no ships remain capable
of fighting, while the executable contains explicit VCR integration and result
handling.

Relevant executable strings show:

```text
vcr.exe
afsvcr.exe
vcr11.dat
vcrinit.tmp
afsim.tmp
afsim.log
captured
```

and an explanatory text block states that AFSim reads the battle result from the
screen at the end of the VCR battle and then drives VCR to exit.

Therefore the observed architecture is:

```text
AFSim ship/planet setup
  -> AFSim derives battle/order state
  -> AFSim selects a pair
  -> Tim VCR resolves pairwise combat
  -> AFSim reads the terminal result back
  -> AFSim mutates multi-ship simulation state
  -> AFSim selects the next battle
  -> repeat until no eligible fight remains
```

This is exactly the independent architecture sought after PCC1/PCC2/c2ng
lineage closure.

## Decision-rule outcome

Previous gate:

```text
AFSim automatically builds battle sequence:
  -> deep audit queue/capture semantics

AFSim requires user-specified sequence:
  -> close AFSim
```

Result:

```text
AFSim:
  AUTOMATIC ORDER/ORCHESTRATION CONFIRMED

disposition:
  ACTIVE — deep audit first
```

BSim is no longer the immediate target. Its recovery can wait until AFSim's
capture/order semantics have been exhausted.

## Why AFSim is independent enough to matter

Current known lineage:

```text
PCC1 ccsim.pas
  -> PCC2
  -> c2ng game/sim

AFSim:
  Sean Martens
  separate DOS program
  pairwise backend delegated to Tim VCR
```

No source/provenance link from AFSim into Stefan Reuther's PCC simulator family
has been identified.

Thus AFSim can serve as an independent historical THost-era queue comparator.

This independence does not increase its evidence authority for NuHost. It only
makes agreement/disagreement more informative when generating candidates.

## Current useful implementation surfaces

Recovered useful files:

```text
AFSIM.DOC:
  automatic battle-order rules
  setup fields
  OOB display
  simulation-loop descriptions
  historical behavior notes

AFSIM.EXE:
  independent orchestration implementation
  VCR launch/result-ingestion path
  explicit "captured" result string
  no symbols/source in package

AFSIM.CFG:
  simulator configuration; audit for behavior switches

FILE_ID.DIZ:
  package identity/summary
```

No routine names are available yet.

## Candidate mechanics to extract next

Do not reverse pairwise VCR physics. Tim's VCR is only the delegated backend.

The high-value AFSim questions are:

```text
initial OOB construction:
  exact sort key and per-owner interpretation

pair traversal:
  outer/inner order?
  initiator/opponent distinction?
  LEFT/RIGHT assignment?

post-result mutation:
  destroyed ship removal?
  captured ship owner change?
  crew change?
  mission/PE/FC preservation or reset?
  aggressiveness/passive state?

post-capture eligibility:
  prize remains in existing traversal?
  fresh order generated?
  queue restarted/re-sorted?
  role restrictions?
  same-pair repeat possible?

termination:
  exact definition of "capable of fighting"

planet participation:
  phase location relative to ship-to-ship queue
```

The active Nu discriminator remains specifically O/C and LEFT/RIGHT after
capture. Ordinary OOB rules are useful only insofar as they explain the
post-capture transition.

## Next bounded audit

Tracked helper:

```text
tools/research/audit-afsim-queue-semantics.sh
```

It does not disassemble the full executable.

It first:

1. pins ZIP/DOC/EXE/CFG/DIZ hashes and sizes;
2. normalizes the DOS manual deterministically;
3. emits the manual header/version/provenance lines;
4. emits the exact OOB/setup/simulation-loop sections;
5. emits merged keyword windows around capture/order/fight/result terms;
6. records offset-bearing executable strings and local context;
7. dumps AFSim configuration/package identification.

Only if the manual cannot resolve capture/re-entry behavior should the next pass
perform bounded executable archaeology around the VCR-result/capture path.

Run:

```bash
cd ~/projects/planets-lab-external

git fetch origin
git pull --ff-only origin research/external-engine-analysis

bash tools/research/audit-afsim-queue-semantics.sh \
  2>&1 | tee /tmp/afsim-queue-semantics.log
```

## Evidence authority

Current status:

```text
AFSim archive identity:
  locally recovered historical artifact

AFSim automatic multi-ship ordering:
  EXTERNAL_IMPLEMENTATION + package-documentation confirmed

AFSim post-capture algorithm:
  UNKNOWN

NuHost post-capture algorithm:
  still UNKNOWN
```

Any AFSim rule extracted next must be frozen as an external candidate before
testing it against the Nu discovery Corpus DB. Held-out Nu data remains sealed
until that candidate is fixed.


## Focused queue/capture audit result

The bounded manual/string audit was run against the pinned recovered package.

Artifact hashes:

```text
AFSIM.ZIP
  778dde575b8293b6cb266ea62a456b972ddf5d4d33de526e3c5700825f5ed3e2

AFSIM.DOC
  f394cfd9f9147b4efb627d48ccad3524a30e7fb7655f0d7fdfcf8a65e3195490

AFSIM.EXE
  a5f4bd1f4679585b30ea47057201d4a656f346c9defcb087a04443a0d142bd53
```

### Version identity

The documentation header says:

```text
AFSIM v1.3
Sean Martens, 1994
```

but the executable itself contains both:

```text
Version 1.31
AFSIM version 1.31
```

Contemporary 1995/1996 Usenet software inventories also distribute:

```text
Afsim131.zip
```

Therefore the executable can be pinned as **AFSim 1.31**. The bundled manual
header is stale at 1.3 and must not be used as the executable version.

### Automatic ordering confirmed more strongly

The manual states:

```text
battle order determined by:
  ship ID
  friendly code
  mission
  primary enemy

result of one battle becomes input to the next
```

The setup schema ranks the OOB determinants explicitly:

```text
mission Kill?     most important
primary enemy     number 2 determinant
friendly code     number 3 determinant
ship ID           least important
```

The OOB display is recalculated whenever it is displayed.

The appendix reproduces the HOST 3.15 ordering description:
Kill ships first, then Primary Enemy ships, then passive defenders, with attack
value and ship ID resolving order inside groups.

This appendix is a quoted historical HOST document, not independent proof of
AFSim's internal implementation. The package's automatic OOB behavior and
result-chaining independently show that AFSim implements an orchestrator, while
the exact binary equivalence to every HOST 3.15 detail remains a reverse target.

### Capture semantics: documentation boundary

The manual contains one important capture-order statement:

```text
passive ships are protected by Kill/Primary-Enemy ships
until those ships are destroyed or captured
```

This proves that capture is queue-relevant in AFSim: a captured protector no
longer protects the old owner's passive ships.

However the manual does **not** state:

```text
whether the captured ship remains in the current OOB traversal
whether OOB is re-sorted immediately
whether mission is reset
whether primary enemy is reset
whether friendly code is preserved
which side/role the prize receives
whether capture creates a fresh order
whether the prize can fight again immediately
```

So AFSim has not yet yielded a frozen O/C candidate.

### Repeat-pair warning

The manual defines:

```text
Combat = one pairwise fight
Battle = one or more combats
```

and gives an explicit example in which the same two Outrider scouts time out
twice and then one wins on the third combat.

This means AFSim can schedule at least three combats for the same pair in one
simulated battle.

That behavior must **not** be conflated with Nu's documented same-pair maximum
of two. It also warns against assuming AFSim is simply the same fixed nested
cursor as c2ng/Donovan without inspecting its repeat logic.

### Executable result surface

The executable contains a compact result-string family:

```text
Both ships blew up
 won
 captured
The battle timed out
```

along with the VCR integration state:

```text
vcr.exe
afsvcr.exe
vcr11.dat
vcrinit.tmp
afsim.tmp
afsim.log
```

The executable text explicitly says AFSim reads the completed VCR result from
the screen, then simulates keystrokes to exit VCR.

That makes the code referencing the four result strings the best narrow static
entry point for post-result state mutation.

### Configuration is not the missing variable

Recovered `AFSIM.CFG` contains only:

```text
BOOST
SCOTTY
QUICK
APPEND
REB_ATT
FAC_ATT
```

No battle-order mode, capture mode, queue policy or repeat-limit switch is
exposed in configuration.

## Next bounded binary locator

Tracked helper:

```text
tools/research/audit-afsim-result-handler.py
```

The helper avoids whole-program disassembly. It:

1. validates and fingerprints the MZ executable;
2. locates the exact Pascal-style result strings;
3. checks length-byte prefixes;
4. searches paragraph-aligned segment-base candidates;
5. finds strong immediate xrefs from generated 16-bit code;
6. clusters xrefs to the four result outcomes;
7. disassembles forward only from instruction-boundary anchors;
8. preserves raw slices under ignored artifacts.

Run:

```bash
cd ~/projects/planets-lab-external
git fetch origin
git pull --ff-only origin research/external-engine-analysis

python3 tools/research/audit-afsim-result-handler.py \
  2>&1 | tee /tmp/afsim-result-handler.log
```

The desired result is one compact routine/cluster referencing several of:

```text
won
captured
both destroyed
timed out
```

Only that cluster should receive the next semantic reverse pass.


## Result-handler locator v1 correction

The first run of `tools/research/audit-afsim-result-handler.py` did **not**
produce valid semantic xrefs.

It ranked arbitrary paragraph-aligned bases and therefore matched unrelated
small immediates:

```text
captured  -> 0x001e
timed_out -> 0x0028
both_destroyed -> 0x0004
```

The resulting disassembly windows contained instructions such as:

```text
add ax,0x1e
add ax,0x28
cmp ax,0x4
```

Those are not references to the string literals. No owner/crew/OOB inference may
be drawn from that v1 output.

The raw string pool itself exposed the correct addressing model. The MZ header
has:

```text
load_image_offset = 0x18a0
initial_cs        = 0
```

and the adjacent Turbo-Pascal short strings are at file offsets:

```text
Both ships blew up   pointer 0x4df4
 won                 pointer 0x4e07
 captured            pointer 0x4e0d
The battle timed out pointer 0x4e18
```

Therefore their actual initial-CS-relative offsets are:

```text
Both ships blew up   0x3554
 won                 0x3567
 captured            0x356d
The battle timed out 0x3578
```

The pool is immediately adjacent to generated code; a new procedure prologue
starts directly after it. This is consistent with Turbo Pascal code-segment
short-string literals and gives a much tighter static-recovery path.

Commit:

```text
2005dd1d4b9cabaa22cb7f552eb148e6f319df4f
research: fix AFSim result handler xref model
```

The corrected helper now:

1. fixes the address base to the actual MZ load image plus initial CS;
2. validates full Pascal short-string lengths, including trailing spaces in
   `" won "` and `" captured "`;
3. searches only for the true 16-bit offsets;
4. gives special weight to the Turbo-Pascal
   `mov di,offset; push cs; push di` literal-address pattern;
5. finds the nearest real procedure prologue for each xref;
6. separately disassembles the procedure immediately preceding the string pool;
7. explicitly records that the previous v1 result is invalid for semantics.

Run the same command again after pulling the branch:

```bash
python3 tools/research/audit-afsim-result-handler.py \
  2>&1 | tee /tmp/afsim-result-handler-v2.log
```

Do not use any v1 result-handler disassembly as evidence.


## Result-handler locator v2 result

The corrected v2 locator established the true Turbo-Pascal short-string
addresses:

```text
MZ load image base: 0x18a0
initial CS:         0

Both ships blew up   CS+0x3554
 won                 CS+0x3567
 captured            CS+0x356d
The battle timed out CS+0x3578
```

The four literals form one compact Pascal short-string pool at file range:

```text
0x4df4 .. 0x4e2d
```

and a new `55 89 e5` procedure prologue starts immediately at:

```text
0x4e2d
```

No immediate references were found **before** the string pool.

That is not a negative result for the outcome decoder because v2 searched only
the pre-pool range. The adjacency makes the post-pool procedure a high-priority
candidate: compilers can place a procedure's string constants directly before
its generated code.

The preceding procedure begins at:

```text
0x4c4c
```

and remains a secondary candidate for a result formatter/table producer.

No semantic claim about owner, crew, OOB mutation or capture re-entry is made
from v2.

## Result-handler locator v3

Commit:

```text
1879af088b3cec2b6b351348b57b2ac2476bf71b
research: scan AFSim result pool across full load image
```

V3 keeps the fixed MZ/CS model but removes the accidental pre-pool search
restriction. It now:

1. scans the complete MZ load image for the four true 16-bit CS offsets;
2. excludes the literal pool itself from hits;
3. classifies strong Turbo-Pascal address materialization patterns;
4. disassembles both procedures adjacent to the pool;
5. searches the entire load image for near CALL/JMP references to those
   procedures;
6. prints the adjacent procedure disassemblies directly into the audit report
   while preserving full local copies.

Next run:

```bash
python3 tools/research/audit-afsim-result-handler.py \
  2>&1 | tee /tmp/afsim-result-handler-v3.log
```

The preferred discriminator is a post-pool procedure or its caller which
references multiple outcome strings and then mutates simulation state.


## Result-handler locator v3: confirmed outcome decoder and capture mutation

V3 resolved the string-pool ambiguity completely.

All four true CS-relative offsets have strong Turbo-Pascal literal xrefs inside
one procedure:

```text
procedure file range:
  0x4e2d .. 0x4f8a

Both ships blew up:
  mov di,0x3554 ; push cs ; push di

 won :
  two literal xrefs

 captured :
  two literal xrefs

The battle timed out:
  mov di,0x3578 ; push cs ; push di
```

So `0x4e2d` is the actual outcome formatter / result-state handler.

The immediately preceding procedure `0x4c4c` parses battle-end screen values
into temporary globals. Both procedures are called consecutively from the same
caller beginning at:

```text
0x4f8b
```

### Proven symmetric capture mutation

The handler contains two symmetric capture branches.

First branch:

```asm
cmp  WORD PTR ds:0x32,0
jne  ...

; format "<A> captured <B>"

mov  ax,ds:0x328e
mov  ds:0x3264,ax
mov  WORD PTR ds:0x32,0x000a
```

Second branch:

```asm
cmp  WORD PTR ds:0x34,0
jne  ...

; format "<B> captured <A>"

mov  ax,ds:0x3264
mov  ds:0x328e,ax
mov  WORD PTR ds:0x34,0x000a
```

The result slots are then copied into two paired state blocks:

```text
A:
  0x325e <- 0x2e
  0x3260 <- 0x32
  0x3264 <- capture-mutated paired field
  0x3270 <- 0x36

B:
  0x3288 <- 0x30
  0x328a <- 0x34
  0x328e <- capture-mutated paired field
  0x329a <- 0x38
```

The paired structures have exact stride:

```text
0x2A bytes
```

This is strong structural evidence that capture modifies one field in the
captured combatant by copying the corresponding field from the captor and
forces another result field to decimal 10.

The obvious historical interpretation is:

```text
owner/race := captor owner/race
crew       := 10
```

but those field names are **not promoted yet**. They must be independently
identified from initialization/use sites in the executable.

### Outcome predicates

The same procedure establishes the result classifier structure:

```text
0x2e == -1 and 0x30 == -1:
  both destroyed

0x2e == -1:
  one side won

0x30 == -1:
  the opposite side won

0x32 == 0:
  capture branch A

0x34 == 0:
  capture branch B

otherwise:
  timed out
```

Again, the exact semantic names of the numeric slots remain pending field
mapping.

### Next bounded state-flow pass

Tracked helper:

```text
tools/research/audit-afsim-capture-state-flow.py
```

It targets only:

```text
shared caller 0x4f8b
screen parser 0x4c4c
outcome handler 0x4e2d

paired state:
  0x325e / 0x3260 / 0x3264 / 0x3270
  0x3288 / 0x328a / 0x328e / 0x329a
```

The pass:

1. disassembles the complete shared caller;
2. identifies the calls to parser/outcome;
3. enumerates direct uses of the paired post-result state;
4. groups uses by owning procedure;
5. focuses on the two capture-mutated fields and the adjacent result fields;
6. tests whether the mutated state is fed back into OOB construction or sorting.

Run:

```bash
python3 tools/research/audit-afsim-capture-state-flow.py \
  2>&1 | tee /tmp/afsim-capture-state-flow.log
```

Only after the +6 and +2 fields are independently identified should the
external candidate be frozen as an explicit AFSim capture rule.
