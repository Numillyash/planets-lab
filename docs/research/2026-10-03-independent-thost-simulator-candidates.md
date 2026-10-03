# Independent THost simulator candidates after PCC1 closure — 2026-10-03

## Scope

The PCC1 -> PCC2 -> c2ng family has now been exhausted for the active
post-capture-order blocker.

PCC1 1.1.21 and 1.1.22 have the same `ccSim` instruction structure in every
audited capture/order routine. All residual numeric operand differences are
uniform build-layout shifts; no branch/opcode/instruction-shape change remains.

Therefore the next useful external source must be **independent of the
PCC/c2ng lineage**.

## Candidate inventory

Historical PHost/PlanetsCentral documentation distinguishes several battle
simulators:

```text
multi-ship:
  BSim      - Thomas Voigt
  CCBSim    - Stefan Reuther
  AFSim     - Sean Martens
  Tanascius
  PlayVCR / CCBSim 2

simpler one-vs-one:
  VPA
  EchoView
  Tim Wisseman's SIM
```

CCBSim and PlayVCR/CCBSim2 are same-family with PCC/c2ng and are no longer
independent candidates.

VPA has already been checked and is pairwise only.

That leaves the highest-value independent historical candidates:

```text
1. AFSim
2. BSim
3. Tanascius
```

## AFSim — highest priority

Author:

```text
Sean Martens
```

Historical descriptions independently identify AFSim as a multi-ship simulator
and say that it uses Tim Wisseman's VCR program to resolve individual combat.

This is exactly the architecture useful to us:

```text
AFSim:
  external multi-ship orchestrator
  +
  official Tim VCR as pairwise combat backend
```

Unlike PCC/CCBSim, that means AFSim had to decide which pair fights next without
sharing the later Stefan Reuther PCC2/c2ng implementation lineage.

Surviving package evidence:

```text
Apajalista ID: 41859
filename:       AFSIM.ZIP
indexed size:   41757 bytes
historical archive description:
  menu-driven front-end for simulating VGA Planets battles
```

Older archive lists also name:

```text
afsim12.zip
afsim131.zip
```

and identify AFSIM as a multiship battle simulator.

Informer 2.4 explicitly supported exporting several battle setups to AFSIM,
which corroborates that it was a real integrated utility rather than a toy
single-pair program.

### What to extract

Do not reverse pairwise VCR physics. Search only for orchestration semantics:

```text
battle order
ship id / friendly code ordering
aggressiveness / PE / Kill
pair selection
left / right assignment
capture / surrender
whether winner/captured ship stays in sequence
repeat-fight handling
planet insertion
```

A captured-ship rule in AFSim would be genuinely independent historical
evidence about how one contemporary simulator approximated THost.

It still would not be NuHost evidence by itself.

## BSim — second priority

Author:

```text
Thomas Voigt
```

Surviving package:

```text
Apajalista ID: 61688
filename:       BSIM22.ZIP
indexed size:   187333 bytes
version:        2.2
```

Historical documentation describes it as a multi-ship simulator.

PHost documentation says BSim simulates PHost 2 combat internally and uses the
host program for other combat families. Donovan's FAQ says BSim supports battle
order and allows a series of ships to be configured for battle.

This makes BSim useful, but weaker than AFSim for our exact target because its
workflow may let the user prescribe the sequence instead of independently
deriving the complete Tim-Host queue.

The package should therefore be audited for documentation/source/debug material
before any binary reverse work.

## Tanascius — third priority

PHost documentation also lists Tanascius among multi-ship simulators and says it
contains a built-in HOST VCR.

It is clearly independent of PCC, but the surviving download/source situation is
less obvious. Historical pages confirm that Tanascius supplied combat
simulation plus other exact Host calculators.

Keep it as the next recovery target if AFSim/BSim packages do not expose useful
queue logic.

## Lower-priority / closed candidates

```text
EchoView:
  pairwise simulator according to PHost documentation

VPA:
  pairwise THost/PHost combat only; already closed for queue logic

CCBSim / PCC1:
  same implementation lineage as PCC2/c2ng; exhausted

PlayVCR / "CCBSim 2":
  same Stefan Reuther implementation family; not independent

The Killing Floor / FLAK:
  replacement fleet-combat engines, not standard THost ordering
```

## Recovery helper

Tracked helper:

```text
tools/research/recover-independent-thost-simulators.sh
```

It currently targets the two surviving Apajalista packages:

```text
AFSIM.ZIP  ID 41859
BSIM22.ZIP ID 61688
```

The helper:

1. downloads the indexed detail pages;
2. discovers archive/download links dynamically instead of inventing a private
   endpoint;
3. validates any candidate as a real ZIP;
4. records SHA256 and size;
5. inventories every member/file type;
6. searches docs/text for battle-order/capture terms;
7. searches DOS binary strings;
8. inventories source/debug/MAP/SYM material.

Recovered binaries stay under ignored `artifacts/external-sources/`.

## Decision rule

```text
AFSim contains an automatic queue rule:
  analyze it first as independent THost comparator

AFSim only accepts user-specified sequence:
  close it for queue reconstruction, continue BSim

BSim contains automatic THost order:
  analyze

BSim only evaluates user-prescribed order:
  close it

neither useful:
  recover Tanascius next
```

Any external rule still has to be turned into a frozen discriminator and tested
against the Nu discovery Corpus DB before it has relevance to NuHost.
