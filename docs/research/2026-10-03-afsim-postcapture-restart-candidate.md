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
