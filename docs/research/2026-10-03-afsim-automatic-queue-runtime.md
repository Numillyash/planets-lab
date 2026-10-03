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
