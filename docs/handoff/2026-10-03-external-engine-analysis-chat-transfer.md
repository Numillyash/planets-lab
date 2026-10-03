# New chat transfer — external engine analysis — 2026-10-03

## Scope

This handoff is for the **separate external-engine research branch** only.

Repository:

```text
Numillyash/planets-lab
```

Branch:

```text
research/external-engine-analysis
```

Do not switch this workstream to `main`, merge it, or modify canonical mechanics
without a separate evidence chain. GitHub is the source of truth: verify current
remote HEADs before doing any work.

Observed immediately before this transfer document was created:

```text
research/external-engine-analysis:
  c5e084bee152b86d5441f6e67a09e09c748467cd
  handoff: move external queue search to AFSim and BSim

main:
  370156ab21fb8faf5083436dff697dff200369e4
  research: record capture side heldout residuals
```

These are only handoff observations, not trusted startup state.

## Read first

Read these files completely before continuing:

```text
docs/ROADMAP.md
docs/COMPILED_CORPUS.md
docs/ARCHITECTURE.md
docs/WORKFLOW.md

docs/handoff/2026-09-28-external-engine-analysis-start.md
docs/handoff/2026-10-03-external-core-capture-state-next-discriminators.md

docs/research/2026-10-03-public36-corpus-db-external-core-discriminator.md
docs/research/2026-10-03-jphost-recovery-thost-phost-capture-state.md
docs/research/2026-10-03-vpa-pcc1-ccbsim-combat-queue-triage.md
docs/research/2026-10-03-independent-thost-simulator-candidates.md
```

## Evidence boundary

Always preserve:

```text
third-party implementation != NuHost truth
```

Allowed chain:

```text
third-party candidate
-> primary Planets.nu docs if available
-> attributable official Nu observation
-> deterministic local test
-> differential verification
```

Do not promote an external rule to DOCUMENTED / CORPUS_OBSERVED / TESTED /
DIFF_VERIFIED merely because another engine implements it.

## Active canonical unknown

The external stream is still supporting the main C5 blocker:

```text
post-capture ship combat order / LEFT-RIGHT assignment
especially the relation between:
  O = continuation in an existing order
  C = an additional order created at capture
```

Primary Nu documentation requires the captured ship to be able to continue in
the existing order and also receive an additional order set anew when captured.
The exact C insertion/order semantics remain unresolved.

Corpus DB discovery already rejects the simple c2ng frozen THost cursor as a
general Nu model:

```text
31 adjacent/comparable rows
external O exact      3
external O mismatch  28

O pair reachable      5
  factual LEFT        2
  factual RIGHT       3

O pair not reachable 26
  factual LEFT       23
  factual RIGHT       3
```

So neither `RIGHT => O` nor `LEFT => C` is a valid classifier.

## External-core results already closed

### c2ng / PCC2

Pinned c2ng family:

```text
stefanreuther/c2ng
425d623e5d44b017abea50bae4dc9c668870398d
```

Historical c2ng commit:

```text
76b3eed65bee4506758c258b6fc33e10d1a031ee
Simulator: implement battle order peculiarities
```

It adds `fl_WasCaptured` and a non-PHost rule that blocks a captured ship when
it appears as LEFT/inner. The source attributes this to a reverse-engineered
Tim-Host `youship` vs `you` bug.

Treat that as an attributable external reverse-engineering claim, not NuHost
evidence.

The ordinary THost nested traversal itself has independent historical
corroboration:

```text
outer initiator = VCR RIGHT
inner checked opponent = VCR LEFT
```

but the captured-LEFT asymmetry does not.

### JPHost / JHOST

Recovered complete SourceForge CVS snapshot:

```text
SHA256:
a9b1ac89ded3604350cdfde33eefea28c29348a60b3ce54a19b44145b93dd6ae
```

Current/deleted source, Attic history, and historical JAR were audited.

Final disposition:

```text
JPHost:
  CLOSED for the active combat-order blocker
  no implemented ship-to-ship combat engine recovered
```

### VPA

Pinned VPA-Linux:

```text
promano7/vpa-linux
a8774eaba8b457ec065ae7a7218fbc80a9d083db
```

Its combat simulator is pairwise only. Its "Sort by battle order" path is UI
ordering, not a multi-ship combat orchestrator.

Final disposition:

```text
VPA:
  CLOSED for post-capture queue reconstruction
```

### PCC1 / CCBSim

PCC1/CCBSim did contain a real multi-ship THost/PHost simulator and useful MAP
symbols such as:

```text
CalcBattleOrder
Attacking
KeepVCR
MakeVCR
MakePlanetVCR
FillInPlanetAggressiveness
```

However the symbols and c2ng comments prove that this is the same implementation
lineage:

```text
PCC1 ccsim.pas
-> PCC2 simulator
-> c2ng game/sim
```

Therefore PCC1 is not independent corroboration of c2ng.

The final 1.1.21 -> 1.1.22 instruction-level audit closed the possible backport
of the later c2ng captured-LEFT rule:

```text
equal                         1459
mapped_symbol_relocation        67
operand_value_change           237

mnemonic_change                  0
operand_shape_change             0
instruction_size_change          0
instruction_boundary_change      0
```

All changed numeric operands belong to only four layout-delta families:

```text
+138
-138
+4
+0x8A0000 == 138 << 16
```

No mechanics constant, branch shape, opcode, instruction boundary, new check or
removed check changes in `CalcBattleOrder`, `Attacking`, `KeepVCR`, or
`MakeVCR`.

Final disposition:

```text
PCC1 1.1.22 captured-state backport hypothesis:
  REJECTED

Further PCC1 binary archaeology for this blocker:
  NOT WARRANTED
```

## Current next target: genuinely independent THost simulators

The external search has now moved outside the PCC/PCC2/c2ng family.

Priority:

```text
1. AFSim — Sean Martens
2. BSim 2.2 — Thomas Voigt
3. Tanascius
```

Detailed rationale:

```text
docs/research/2026-10-03-independent-thost-simulator-candidates.md
```

AFSim is the strongest candidate because historical descriptions call it a
multi-ship simulator which delegates individual pairwise battles to Tim
Wisseman's VCR. If it determines fight sequence automatically, its queue
orchestrator is independent of Stefan Reuther's PCC lineage.

BSim is also multi-ship but may allow the user to prescribe battle sequence, so
its queue value is less certain.

## Next runtime helper

Tracked helper:

```text
tools/research/recover-independent-thost-simulators.sh
```

It currently attempts to recover:

```text
AFSIM.ZIP
  Apajalista ID 41859

BSIM22.ZIP
  Apajalista ID 61688
```

The helper dynamically resolves the historical download pages, validates ZIPs,
records hashes, inventories package contents, scans documentation/binaries for
queue/capture terms, and inventories source/debug/MAP/SYM material.

Artifacts are intentionally local and ignored:

```text
artifacts/external-sources/independent-sims/
```

## Decision rule for the next chat

If AFSim is recovered:

```text
automatic battle sequence:
  perform deep queue/capture audit first

user-specified sequence only:
  close AFSim for queue reconstruction and move to BSim
```

If BSim is recovered:

```text
automatic THost ordering:
  perform deep audit

user-prescribed sequence:
  close it for queue reconstruction
```

If neither yields useful ordering logic:

```text
recover Tanascius next
then continue broader independent Host/THost simulator archaeology
```

Do not return to PCC1 binary disassembly unless genuinely new evidence appears.

## Corpus DB

The shared historical public corpus remains available read-only:

Host:

```text
/root/projects/planets-corpus-db
```

Container:

```text
/corpus-db
```

Active generation is selected by:

```text
/corpus-db/CURRENT
```

Use Corpus DB for ordinary research/discriminators. Use immutable ZIP/TRN only
as oracle when independent source-data verification is necessary.

Do not modify CURRENT or generation files from mechanics/research tasks.

## Working rules

- Work autonomously in `research/external-engine-analysis`.
- Do not merge to `main`.
- Do not copy third-party code into canonical mechanics.
- Pin external version/commit/archive hash and license/provenance.
- Keep downloaded third-party binaries/source under ignored artifacts.
- Prefer bounded diagnostics over broad reverse engineering.
- When a candidate can discriminate Nu observations, freeze the candidate rule
  first, then test against the discovery corpus.
- Keep held-out/validation data sealed until the candidate is frozen.
- Commit complete logical research blocks to this branch.
