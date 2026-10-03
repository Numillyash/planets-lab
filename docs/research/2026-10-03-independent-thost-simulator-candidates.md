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


## Web pre-recovery triage after Apajalista timeout

The first local recovery run established an operational problem rather than a
negative source result: Apajalista's detail page for ID 41859 transferred only
part of its small HTML response over several minutes and had to be interrupted.
The old helper used `curl -fL` without a total transfer deadline, so a slow
detail page could block the whole archaeology pass indefinitely.

A live web pass found a direct AFSIM archive candidate behind the Apajalista
download link:

```text
https://www.apajalista.net/tiedostot/Pelit/Purkkipelit/VGA_Planets/AFSIM.ZIP
```

This is a **recovery locator only** until the archive is fetched locally and
validated as ZIP with a recorded SHA256. Do not treat URL discovery as package
verification.

Independent historical documentation also sharpens the source priorities.

PlanetsCentral's technical file list identifies:

```text
AFSIM.SAV   AFSim: Saved simulation setup
AFSREPL.EXE AFSim: helper program
```

Source:

```text
https://planetscentral.com/doc.cgi/filefmt/file-list
```

This confirms AFSim maintains a multi-object simulation setup of its own, but
the surviving indexed page available in this pass does not by itself prove
whether fight sequence is derived automatically or can be prescribed by the
user. The package/manual remains the gating evidence for that distinction.

For BSim, the historical alt.games.vga-planets FAQ preserved by Donovan's says
the simulator supports battle order and describes the workflow as entering a
series of ships and then configuring the battle order for optimum results.

Source:

```text
https://www.donovansvgap.com/info/faq.htm
section 7.5.1 BSIM
```

This materially lowers BSim's priority for Host-queue reconstruction because it
is consistent with a user-prescribed optimization workflow. It is **not yet a
closure**: the package/manual still has to establish whether BSim also contains
an automatic THost-order mode.

The recovery helper was therefore hardened in commit:

```text
0f90ae0f914fa5cab3ad01ae72bf00502f4b424e
research: make independent simulator recovery fail-fast
```

Current behavior:

```text
AFSim:
  try the direct archive candidate first
  if that fails, use bounded detail-page discovery

BSim 2.2:
  use bounded detail-page discovery

if BSim 2.2 cannot be recovered:
  optionally inspect indexed BSim 2.00 only as a version-scoped architecture
  fallback; never report it as BSim 2.2 evidence

all page/download operations:
  have explicit max-time bounds
```

Next runtime remains:

```bash
cd ~/projects/planets-lab-external
git fetch origin
git pull --ff-only origin research/external-engine-analysis

bash tools/research/recover-independent-thost-simulators.sh \
  2>&1 | tee /tmp/independent-thost-simulators.log
```

Interpret the result with the existing decision rule. In particular, do not
close AFSim from secondary descriptions alone: inspect the recovered manual,
saved-setup semantics and executable strings/debug/source material first.


## AFSim runtime promotion to active deep-audit target

The recovered package has now crossed the decision gate.

Pinned recovered archive:

```text
AFSIM.ZIP
size   41844 bytes
SHA256 778dde575b8293b6cb266ea62a456b972ddf5d4d33de526e3c5700825f5ed3e2
ZIP    valid
```

Package documentation explicitly says AFSim determines battle order from ship
ID, friendly code, mission and primary enemy. The executable integrates Tim's
VCR, reads the result of each pairwise battle back into AFSim, and contains
capture-result handling strings.

Therefore:

```text
AFSim automatic battle-order/orchestration:
  CONFIRMED as external implementation behavior

AFSim user-prescribed-sequence-only hypothesis:
  REJECTED

AFSim:
  ACTIVE deep-audit target

BSim:
  DEFER until AFSim capture/order semantics are exhausted
```

Detailed runtime note:

```text
docs/research/2026-10-03-afsim-automatic-queue-runtime.md
```

Focused next helper:

```text
tools/research/audit-afsim-queue-semantics.sh
```

The next pass must extract capture/re-entry semantics from the manual first and
only then, if needed, reverse the smallest executable region around VCR result
ingestion. Do not spend time on Tim VCR pairwise physics.


### AFSim capture-boundary refinement

The focused AFSim 1.31 manual/string audit is complete.

New bounded conclusions:

```text
automatic OOB/result chaining:
  confirmed

capture affects old-owner protection grouping:
  confirmed by manual

exact captured-ship re-entry / re-sort / side role:
  not documented

same-pair repeat behavior:
  AFSim can run >=3 combats after repeated timeouts
  therefore not safe to equate with Nu max-two or c2ng cursor semantics

configuration switch for queue/capture policy:
  none found
```

The active target is now the smallest executable result-handler region around
the Pascal strings:

```text
Both ships blew up
 won
 captured
The battle timed out
```

Tracked locator:

```text
tools/research/audit-afsim-result-handler.py
```

BSim remains deferred until this AFSim path is exhausted.


### AFSim exact VCR capture-state mapping

The AFSim 1.31 result handler has now been mapped onto the standard 100-byte
THost VCR record layout.

Independent VCR format documentation:

```text
https://www.planetscentral.com/doc.cgi/filefmt/vcrx-dat
```

AFSim live record:

```text
record base       0x323e
left object       0x324a
right object      0x3274
object stride     42 bytes
left shield       0x329e
right shield      0x32a0
```

This identifies the capture-mutated fields exactly:

```text
0x3260 left crew
0x3264 left owner
0x328a right crew
0x328e right owner
```

AFSim external behavior is therefore:

```text
left crew == 0:
  left.owner = right.owner
  left.crew = 10

right crew == 0:
  right.owner = left.owner
  right.crew = 10
```

This remains third-party implementation evidence only.

Control-flow was also corrected: `0x4f8b` is a battle-end detector that
returns normally; the parser/outcome calls occur in a distinct interrupt-style
routine at `0x50ce`.

Active next target:

```text
tools/research/audit-afsim-vcr-queue-bridge.py
```

The goal is now strictly the bridge from the capture-mutated VCR object back to
persistent AFSim OOB state: re-sort vs cursor continuation vs restart.


### AFSim VCR -> persistent state bridge confirmed

The AFSim 1.31 battle loop has now been traced one step beyond the VCR outcome
handler.

Persistent combatants use 54-byte entries:

```text
entry = 0x32dc + index*0x36
+0x06 shield
+0x0c embedded 42-byte VCR object
+0x24 ship ID
```

After each ship-vs-ship VCR result, AFSim writes both mutated 42-byte VCR
objects and both shields back into those persistent entries, then invokes a
per-entry routine at `0x2c68` on each combatant.

Therefore captured owner/crew state is persisted before the next fight is
selected.

The next-pair loop then passes through:

```text
0x5627
0x51c6
```

before a new ship-vs-ship pair is used.

Before battle setup the selected pair is canonicalized by ascending persistent
ship ID.

The remaining AFSim queue discriminator is now bounded to:

```text
0x2c68
0x5627
0x51c6
```

and is specifically:

```text
full OOB rebuild/re-sort
vs
traversal restart
vs
saved-cursor continuation
```

Tracked helper:

```text
tools/research/audit-afsim-postcapture-selector.py
```

No NuHost mechanic is promoted by this result.


### AFSim structural queue candidate frozen: AFSIM-R1

The post-capture selector path is now resolved at the structural level.

After every completed ship-vs-ship combat AFSim:

```text
1. writes the mutated VCR combatant state back into persistent 54-byte entries;
2. runs per-entry post-result normalization;
3. fully re-sorts/rebuilds the persistent combatant array;
4. resets ship-pair selector indices to 1/1;
5. scans again from the beginning of the newly sorted array.
```

The re-sort is explicit: `0x5627` runs a nested pair loop and swaps complete
54-byte entries plus their parallel state arrays according to comparator
`0x5572`.

The restart is explicit: every `0x51c6` invocation initializes
`0x313a = 1` and `0x313c = 1`.

Frozen candidate:

```text
AFSIM-R1:
post-combat mutable state -> full re-sort -> traversal restart
```

This independently differs from the c2ng/PCC2 frozen-cursor model and is
therefore a useful Nu discovery-corpus discriminator.

It remains third-party evidence only.

Candidate freeze document:

```text
docs/research/2026-10-03-afsim-postcapture-restart-candidate.md
```

Next helper:

```text
tools/research/audit-afsim-sort-eligibility-sides.py
```

The helper recovers comparator `0x5572`, ship eligibility `0x513d`, VCR side
builder `0x3eb9`, and removal path `0x46be` before any discovery-corpus
comparison is implemented.


### AFSim comparator, eligibility, and LEFT/RIGHT mapping recovered

The post-freeze deterministic pass refines AFSIM-R1 without contradicting it.

Recovered comparator `0x5572` orders the persistent array by:

```text
1. parallel 0x3dcf class: nonzero before zero
2. owner: ascending
3. parsed friendly-code attack value: ascending
4. ship ID: ascending
```

The weapon-capability helper `0x513d` is exactly:

```text
beam_count > 0
OR (torp_tubes > 0 AND ammo > 0)
OR (fighter_bays > 0 AND ammo > 0)
```

It contains no captured-state special case.

The VCR side builder `0x3eb9` maps:

```text
side 1 -> VCR LEFT
side 2 -> VCR RIGHT
```

The battle loop canonicalizes the selected pair by ascending ship ID before
calling battle setup. The call/stack mapping proves:

```text
LEFT  = lower ship ID
RIGHT = higher ship ID
```

for AFSim ship-vs-ship combats.

The earlier provisional label for `0x46be` as a removal routine was wrong.
It is report/output formatting. Destroyed-entry sentinel handling is performed
through `0x2c68` and the subsequent `0x5627` rebuild; no array compaction
has been observed.

The final pre-corpus proof obligation is to map the three parallel metadata
arrays to their setup/input fields. Behavioral evidence currently identifies:

```text
0x3d9d[index]  fuel/availability candidate
0x3dcf[index]  Kill/aggressive-class candidate
0x3e01[index]  Primary Enemy candidate
```

Tracked helper:

```text
tools/research/audit-afsim-oob-metadata.py
```

It inventories write sites and prompt-string xrefs for Kill, fuel, Primary
Enemy and friendly code. Held-out remains closed.


### AFSim OOB metadata persistence recovered

The latest pass shows that the three parallel per-ship metadata arrays are persistent state, not transient selector scratch.

`0x5c9b` decodes a packed per-entry metadata byte into:

```text
0x3d9d[index] = inverse of bit 0x80
0x3dcf[index] = inverse of bit 0x40
0x3e01[index] = low nibble
```

`0x5d0b` performs the exact inverse encoding.

New-ship creation `0x5883` initializes three editor values to `1,1,0`, passes their addresses to ship editor `0x2f14`, and on success writes them respectively to `0x3d9d`, `0x3dcf`, and `0x3e01`.

Selector `0x51c6` proves `0x3e01` is a target-owner value: its second phase accepts a candidate exactly when `0x3e01[initiator] == candidate.owner`. This maps it to AFSim Primary Enemy semantics.

The remaining two booleans are behaviorally identified as Fuel/availability and KILL mission, but their direct editor argument order is the final binary proof obligation.

Tracked helper:

```text
tools/research/audit-afsim-ship-editor-metadata.py
```

It disassembles `0x2f14`, inventories the far-pointer arguments, and maps the visible `Ship mission kill`, `Fuel on board`, and `Primary enemy` form fields back to caller locals. After that mapping, freeze executable AFSIM-R1 and proceed to discovery Corpus DB only; held-out remains closed.


### AFSim metadata mapping closed; executable R1 frozen

The ship editor at `0x2f14` closes the final parallel-array naming ambiguity.

Caller `0x5883` passes three metadata pointers whose values are persisted as
`0x3d9d`, `0x3dcf`, and `0x3e01`. The editor's visible field order and
dispatch prove:

```text
0x3d9d[index] = fuel-present flag
0x3dcf[index] = KILL-mission flag
0x3e01[index] = Primary Enemy owner
```

The mapping is now direct binary evidence rather than behavioral inference.

AFSIM-R1 is therefore frozen as an executable external model:

```text
capture/result writeback
-> normalize metadata
-> full persistent-array re-sort
-> restart selector at index 1
-> KILL phase
-> Primary Enemy phase
-> canonicalize selected pair by ship ID
-> lower ID LEFT / higher ID RIGHT
```

Tracked executable transcription:

```text
tools/research/afsim_r1_model.py
tests/test_afsim_r1_model.py
```

Discovery-only Corpus DB gate:

```text
tools/research/probe_afsim_r1_discovery_db.py
tools/research/run-afsim-r1-discovery-db.sh
```

The gate deliberately imports canonical reconstruction from a separate current
`main` checkout and reads the shared Corpus DB read-only. It does not merge
main into the research branch.

Only globally adjacent capture -> next-VCR rows are compared. The AFSim
fuel-present input does not map perfectly onto post-movement Nu state, so the
probe computes two mappings:

```text
tminus1   = T-1 neutronium > 0
all_active = every post-history active ship has fuel
```

Rows whose predicted pair is identical under both mappings are reported as
fuel-robust. This prevents a fuel-mapping ambiguity from being silently counted
as evidence for or against the queue model.

Held-out remains closed until the discovery result is recorded.


### AFSim discovery gate runtime correction

The first Dockerized discovery attempt established:

```text
AFSIM-R1 model unit tests: 8/8 PASS
canonical main image:      built successfully
duckdb/pyarrow runtime:    available inside canonical lab image
```

The probe then stopped before reading corpus evidence because the research
wrapper attempted to invoke the `git` executable inside the canonical
`python:3.12-slim` image. That image intentionally contains the Python
dependencies but not Git.

This was an infrastructure-only failure; no discovery rows were evaluated.

The gate now performs branch / `HEAD == origin/main` verification on the
host before Docker launch and passes the verified 40-hex main SHA into the
container:

```text
--verified-main-head <sha>
```

The Python probe accepts that host-verified SHA and skips redundant Git
subprocess calls inside the slim image.

Commits:

```text
4dd94024e5366fbc959a6ce49204578a5e4becf0
research: accept host-verified main SHA in AFSim probe

ce75e560d0697ddc71a50109c35c35126346e297
research: pass verified main SHA into Docker probe
```

Evidence status remains unchanged: no Nu discovery result exists yet and
held-out remains closed.


### AFSIM-R1 rejected as a general Nu next-pair model on discovery

The frozen executable AFSIM-R1 model was evaluated against the canonical
discovery Corpus DB population.

Runtime provenance:

```text
research HEAD:
  796b78d218ca0da306cc4fde4350ffeed5c0a3d4

main HEAD:
  6c976da1e3db9ac3ee1a970cc7721023489e1e7f

Corpus DB:
  generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb
```

Result:

```text
capture rows:                    50
adjacent rows:                   31
resolved adjacent:               31
unresolved active state:          0
unresolved metadata:              0

fuel robust:                     31
fuel sensitive:                   0

pair exact:                       6
pair mismatch:                   25

conditional side exact:           5
conditional side mismatch:        1
```

Both fuel mappings produced exactly the same next-pair predictions on all 31
adjacent rows.

Therefore the complete AFSim architecture:

```text
capture mutation
-> persistent writeback
-> full re-sort
-> traversal restart
-> AFSim KILL/PE selector
-> lower-ID LEFT
```

is rejected as a general Nu post-capture next-pair model on discovery.

This is an important independent negative result: both the c2ng/PCC2
frozen-cursor model and the independently reconstructed AFSim full-restart
model fail on most of the same Nu blocker population.

AFSim components must now be tested separately rather than promoted as one
engine-level candidate.

The first isolated component is the AFSim side canonicalization rule:

```text
lower ship ID = LEFT
higher ship ID = RIGHT
```

Tracked post-analysis:

```text
tools/research/analyze-afsim-r1-discovery.py
```

It conditions only on the factual next-pair identity and tests side assignment
across all resolved adjacent discovery rows. This is not an independent queue
predictor. Held-out remains closed.
