# AFSim 1.31 post-capture queue candidate — frozen external rule

Date: 2026-10-03

Branch:

```text
research/external-engine-analysis
```

Artifact under analysis:

```text
AFSIM.EXE
size   72368
sha256 a5f4bd1f4679585b30ea47057201d4a656f346c9defcb087a04443a0d142bd53
```

## Evidence boundary

This document freezes an **AFSim external-implementation candidate**.

It is not NuHost truth.

Allowed use:

```text
AFSim external behavior
  -> bounded candidate
  -> discovery Corpus DB discriminator
  -> held-out only after candidate freeze
```

Do not promote anything in this document directly to DOCUMENTED,
CORPUS_OBSERVED, TESTED or DIFF_VERIFIED Nu mechanics.

## Proven prerequisite: capture mutation reaches persistent state

The recovered VCR outcome handler at `0x4e2d` operates on a standard 100-byte
THost VCR record.

The live VCR combatant objects are:

```text
left  0x324a
right 0x3274
stride 42 bytes
```

The capture branches implement:

```text
if left.crew == 0:
    left.owner = right.owner
    left.crew = 10

if right.crew == 0:
    right.owner = left.owner
    right.crew = 10
```

The main battle routine `0x675a` writes both resulting 42-byte VCR objects and
their shields back into persistent AFSim combat entries before another pair is
selected.

Persistent entry layout:

```text
entry[index] = 0x32dc + index * 0x36
stride       = 54 bytes

+0x06 shield
+0x0c embedded 42-byte VCR object
+0x24 ship ID
```

Thus captured owner/crew is part of the mutable persistent state used for the
next selection pass.

## Proven post-battle control flow

After writeback, `0x675a` invokes `0x2c68` on both involved persistent
entries.

The routine then returns to the ship-pair loop:

```text
0x68ad:
    call 0x5627
    call 0x51c6
    ...
```

So the next pair is selected only after both `0x5627` and `0x51c6` run
again.

## 0x5627 is a full persistent-array re-sort/rebuild

`0x5627` first walks entries 1..50 and refreshes per-entry auxiliary state.

It then executes a nested pair loop:

```text
outer i = 1 .. 49
inner j = i+1 .. 50
    if comparator_0x5572(i,j):
        swap entry[i], entry[j]        # complete 54-byte entry
        swap parallel byte-array state
```

The swap is explicit:

1. copy entry[j] to a local 54-byte temporary;
2. copy entry[i] to entry[j];
3. copy temporary to entry[i];
4. swap corresponding values in the parallel arrays rooted at
   `0x3d9d`, `0x3dcf`, and `0x3e01`.

Therefore this is not a UI-only routine and not a cursor increment. It
materially reorders the complete persistent combatant array.

After sorting, `0x5627` scans the reordered entries from index 1 and computes
`0x3e34`, the active ship-entry count/boundary.

The exact sort key/order remains pending recovery of comparator `0x5572`.

## 0x51c6 restarts traversal from the beginning

Every invocation of the ship-vs-ship selector `0x51c6` begins with:

```asm
mov WORD PTR [bp-0x2],0x0001
mov WORD PTR ds:0x313a,0x0001
mov WORD PTR ds:0x313c,0x0001
```

It then scans candidate entries using local loop state and the active-entry
bound `0x3e34`.

If no pair is found, it again writes:

```asm
mov WORD PTR ds:0x313a,0x0001
mov WORD PTR ds:0x313c,0x0001
```

before returning.

There is no preserved inter-battle cursor entering `0x51c6`.

## Frozen AFSim structural candidate

The following rule is now frozen **before Nu corpus testing**:

> **AFSim 1.31 ship-combat queue rule AFSIM-R1**
>
> After every completed ship-vs-ship combat, AFSim writes the mutated VCR
> combatant state back into its persistent combat array, normalizes the two
> involved entries, fully rebuilds/re-sorts the persistent combatant array, and
> restarts ship-pair traversal from the beginning of the newly sorted array.
>
> A captured ship therefore participates in subsequent pair selection through
> its mutated persistent owner/crew state and its position after the new sort.
> AFSim does not continue a frozen pre-capture pair cursor.

Authority:

```text
EXTERNAL_IMPLEMENTATION / independent AFSim reverse engineering
```

Not claimed:

```text
- exact 0x5572 sort comparator
- exact eligibility predicate 0x513d
- exact mapping from selected indices to VCR LEFT/RIGHT
- any NuHost equivalence
- Nu "O" vs "C" terminology equivalence
```

## Why this is relevant to the Nu blocker

The previously rejected c2ng/PCC2-style frozen cursor model is not the only
historical THost simulator behavior.

AFSim provides an independent counter-model:

```text
post-capture mutable state
  -> full queue reorder
  -> traversal restart
```

This is directly capable of producing post-capture opponents/sides that cannot
be represented by a frozen continuation cursor.

That makes AFSIM-R1 a useful discovery-corpus discriminator for NuHost, but only
after the remaining comparator and side-mapping details are recovered.

## Next bounded reverse pass

Recover:

```text
0x5572  sort comparator
0x513d  ship eligibility helper
0x3eb9  persistent entry -> VCR side builder
0x46be  dead/removal mutation, if needed
```

Required outputs:

1. exact fields used by the sort comparator;
2. comparator direction and tie behavior;
3. exact conditions by which `0x51c6` accepts a pair;
4. mapping of selected ship index / lower-ID canonicalization to VCR
   LEFT/RIGHT;
5. deterministic pseudocode sufficient to run AFSIM-R1 against discovery
   Corpus DB rows.

Held-out must remain closed until that candidate is frozen in executable form.


## Deterministic refinement from comparator / selector / side-builder pass

The post-freeze audit of `0x5572`, `0x513d`, `0x3eb9`, and `0x46be`
does not contradict AFSIM-R1. It materially refines it.

### Exact sort comparator 0x5572

`0x5627` calls `0x5572(i,j)` from the nested sort loop and swaps the two
complete 54-byte entries when the comparator returns true.

With the actual call order:

```text
bp+6 = outer/current i
bp+4 = inner/candidate j
```

the comparator is lexicographic:

```text
1. parallel byte 0x3dcf[index]:
     nonzero sorts before zero

2. entry.owner:
     ascending

3. entry.attack_value at +0x04:
     ascending

4. entry.ship_id:
     ascending
```

The first field behaves as a boolean class: if the two values differ, `j`
is moved before `i` exactly when `j` is nonzero.

The owner and ship-id fields are exact because they reside inside the already
mapped embedded VCR object:

```text
entry +0x26 = VCR owner
entry +0x24 = VCR ship ID
```

The `+0x04` field is recomputed by `0x5627` from the leading numeric content
of the entry's 3-character code field; invalid/zero values are assigned a
large sentinel. Together with the AFSim manual, this identifies it as the
friendly-code attack-value sort key.

Thus the concrete persistent sort shape is:

```text
aggressive-class first,
then owner,
then friendly-code attack value,
then ship ID
```

The exact external-input identity of parallel byte `0x3dcf[index]` is still
being proven from write sites. Its use in the selector is consistent with the
AFSim Kill-mission class.

### Exact weapon-capability predicate 0x513d

`0x513d(index)` returns true iff the persistent ship can participate in a VCR
fight through at least one weapon system:

```text
beam_count > 0
OR
(torp_tubes > 0 AND ammo > 0)
OR
(fighter_bays > 0 AND ammo > 0)
```

Mapped offsets:

```text
entry +0x2c beam_count
entry +0x2e fighter_bays
entry +0x32 fighters/torpedoes
entry +0x34 torpedo_tubes
```

The predicate contains no owner, mission, PE, capture or WasCaptured check.

Therefore AFSim has no captured-state special case at this eligibility layer.

### Exact VCR LEFT/RIGHT builder mapping

`0x3eb9(entry_index, side_number)` copies the persistent 42-byte embedded VCR
object to:

```text
0x3220 + side_number * 0x2a
```

Hence:

```text
side_number 1 -> 0x324a -> VCR LEFT
side_number 2 -> 0x3274 -> VCR RIGHT
```

`0x497e` invokes:

```text
side 1 with its bp+6 ship argument
side 2 with its bp+4 ship argument
```

Immediately before `0x497e`, the main battle loop compares the selected
persistent ship IDs and swaps `0x313a/0x313c` if necessary so that:

```text
ship_id[0x313a] <= ship_id[0x313c]
```

It then pushes:

```asm
push 0x313a
push 0x313c
call 0x497e
```

With the Pascal stack layout this means:

```text
0x313a (lower ship ID) -> bp+6 -> side 1 -> VCR LEFT
0x313c (higher ship ID)-> bp+4 -> side 2 -> VCR RIGHT
```

Therefore AFSim 1.31 canonicalizes every selected ship-vs-ship pair as:

```text
LEFT  = lower ship ID
RIGHT = higher ship ID
```

This is independent of which member originally caused the pair to be selected.

### 0x46be correction

The routine previously given the provisional label
`persistent_remove_or_kill` is not an array-removal/compaction routine.

Its disassembly is output/report formatting: it reads persistent/VCR result
fields and writes battle result text.

Destruction handling is instead already visible in `0x2c68` and `0x5627`:

```text
damage == -1:
  normalize entry to destroyed/sentinel state

0x5627:
  detects destroyed entry
  fills record with sentinel data
  assigns sort-last values
  clears associated aggressive-class state
```

No compaction step has been observed.

### Selector structure now recoverable

`0x51c6` consists of two selection phases.

The first phase begins only when the first sorted entry has a nonzero
`0x3dcf` class and the corresponding parallel state permits combat. It scans
for the first different-owner opponent with usable state and accepts the pair
if at least one member passes `0x513d`.

The fallback phase scans candidate initiators from the start and uses the
parallel byte array rooted at `0x3e01` as a target-owner selector:

```text
parallel_0x3e01[initiator] == candidate.owner
```

This behavior, together with the manual's Kill / Primary Enemy ordering, is
consistent with:

```text
0x3dcf[index] = Kill/aggressive class
0x3e01[index] = Primary Enemy
```

and `0x3d9d[index]` behaves as the per-ship availability/fuel gate.

Those three human-readable names are not yet promoted solely from this
behavioral match; the next pass targets their concrete write sites/input
prompts.

## Remaining pre-corpus proof obligation

AFSIM-R1 is now deterministic except for naming the three parallel metadata
arrays from their input/write sites.

Next bounded target:

```text
0x3d9d[1..50]
0x3dcf[1..50]
0x3e01[1..50]
entry +0x00 3-character friendly code
entry +0x04 parsed attack value
```

The next pass must map setup/edit/import writes into these fields and confirm:

```text
fuel
Kill mission
Primary Enemy
friendly code
```

After that, freeze an executable AFSim queue model and only then run it against
the Nu discovery Corpus DB. Held-out remains closed.


## Metadata storage / selector refinement

The OOB metadata pass materially strengthens the remaining field mapping.

### Parallel-array persistence format

AFSim maintains three byte arrays in lockstep with the persistent 54-byte ship entries:

```text
0x3d9d[index]
0x3dcf[index]
0x3e01[index]
```

Routine `0x5c9b` decodes them from the high byte of the packed word at persistent entry offset `+0x08` / byte `+0x09`:

```text
parallel_3d9d = 1 iff packed bit 0x80 is clear
parallel_3dcf = 1 iff packed bit 0x40 is clear
parallel_3e01 = packed & 0x0f
```

Routine `0x5d0b` is the exact inverse encoder:

```text
packed_high = 0

if parallel_3d9d == 0:
    packed_high |= 0x80

if parallel_3dcf == 0:
    packed_high |= 0x40

packed_high |= parallel_3e01 & 0x0f
```

Thus these three values are not transient UI state; they are persisted with the ship record.

### New-ship setup bridge

Routine `0x5883` initializes three locals before invoking the ship-entry editor `0x2f14`:

```text
local_A = 1
local_B = 1
local_C = 0
```

On successful entry creation it copies those exact locals to:

```text
local_A -> 0x3d9d[new_index]
local_B -> 0x3dcf[new_index]
local_C -> 0x3e01[new_index]
```

The AFSim ship-entry UI/manual exposes exactly three corresponding OOB metadata fields beyond owner/ID/friendly code:

```text
Mission set to KILL?  Y/N
Fuel on board          Y/N
Primary enemy          0..11
```

Behavioral use already distinguishes the low-nibble field: `0x3e01[index]` is compared directly to opponent owner in the second ship-selection phase, therefore it is the Primary Enemy value.

The remaining two booleans are now reduced to proving their exact editor argument order in `0x2f14`; behavioral use strongly identifies:

```text
0x3d9d = fuel/availability
0x3dcf = KILL mission
```

but that name assignment remains pending the direct editor write path.

### Exact ship selector shape

`0x51c6` has two ordered phases after reset to `1/1`.

Phase 1 considers the first sorted ship as the active aggressive ship when its `0x3dcf` flag is nonzero and it has availability. It scans entries in sorted order and chooses the first different-owner, different-record candidate with availability for which at least one side is weapon-capable.

Phase 2 iterates active ships from the beginning. For an initiator with a nonzero `0x3e01` value and availability, it scans from index 1 for the first candidate whose owner equals that byte and which satisfies the same availability / weapon-capability conditions.

This directly establishes `0x3e01` as a target-owner / Primary Enemy field.

### Destroyed-entry handling

`0x5627` recognizes entries whose result/damage sentinel is `-1`, overwrites the complete 54-byte record with sentinel data, assigns sort-last values (owner 15, ship ID 1500, attack value 2000), and clears `0x3dcf`.

It then runs the normal full sort and recomputes the active-entry boundary. There is no observed physical compaction of the persistent array.

## Final binary proof before executable freeze

The only unresolved naming edge is the ordering of the two boolean arguments to ship editor `0x2f14`.

Next bounded pass must disassemble `0x2f14` and trace its three caller-provided metadata pointers to the visible form fields:

```text
Mission set to KILL?
Fuel on board
Primary enemy
```

Once those two booleans are named directly, AFSIM-R1 can be frozen as executable pseudocode and evaluated against the discovery Corpus DB.
