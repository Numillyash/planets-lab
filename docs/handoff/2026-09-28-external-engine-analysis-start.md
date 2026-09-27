# External engine analysis — parallel research branch start

Branch:

```text
research/external-engine-analysis
```

This branch is deliberately separate from the primary NuHost reconstruction
track on `main`.

## Start-of-chat rule

GitHub is the only source of truth. Before substantive work:

1. inspect the actual HEAD of this branch and current `main`;
2. read:
   - `docs/ROADMAP.md`
   - `docs/COMPILED_CORPUS.md`
   - `docs/ARCHITECTURE.md`
   - `docs/WORKFLOW.md`
   - `docs/handoff/2026-09-28-main-combat-corpus-checkpoint.md`
   - `docs/handoff/2026-09-27-external-planets-tools-mechanics-reference.md`
   - `docs/research/2026-09-28-engine-core-internet-research-pass.md`
3. do not reconstruct branch state from old chat memory or a SHA copied into a
   prompt.

## Purpose

Use independent engines/clients/simulators to generate **specific candidate
rules, field mappings, ambiguity lists and historical discriminators** that can
accelerate planets-lab.

This is not a porting branch and not a source-authority branch.

Critical boundary:

```text
third-party implementation
!= NuHost evidence
```

Promotion path remains:

```text
third-party candidate
-> primary Planets.nu documentation where available
-> attributable official Nu observation
-> deterministic local test
-> differential verification
```

## Current main-track blocker

The primary C5 combat work on `main` is no longer blocked on geometry,
membership, opponent selection, diplomacy or pair eligibility after ship
capture.

The remaining bounded ship-capture blocker is:

```text
post-capture LEFT / RIGHT side assignment
```

Current independent controls on the eight observed ship continuations:

```text
opponent_initiator_right                   7 / 8 exact
neutral captured orders + fresh FC         6 / 8 exact
sticky capture side                        4 / 8 exact
frozen T-1 priority                        4 / 8 exact
neutral orders + preserved FC              4 / 8 exact
```

The research branch should therefore first ask whether an external
implementation exposes a **concrete post-capture combat-order / side-assignment
candidate** that can be tested against official Nu archives.

Do not spend the first pass comparing already-closed beam/torpedo formulas
unless the external source has no relevant queue/capture semantics.

## Priority order

### A. c2ng / PCC2 Next Generation

Highest-value source currently catalogued.

Target files/areas include:

```text
game/battleorderrule.cpp
game/vcr/classic/*
game/map/movementpredictor.cpp
game/map/movementcontroller.cpp
game/map/shippredictor.cpp
game/map/chunnelmission.cpp
game/map/minefieldformula.cpp
game/nu/loader.cpp
game/nu/turnloader.cpp
game/nu/specificationloader.cpp
```

First questions:

1. Is post-capture battle order represented explicitly?
2. Is LEFT/RIGHT generated from battle value, initiator, an order cursor,
   capture-created order, or VCR input?
3. Does capture reset any queue/occurrence state?
4. Are NuHost-specific branches explicit for capture/side assignment?
5. Are there comments/FIXMEs/tests identifying uncertain Host behavior?

Output must distinguish:

```text
already equivalent
candidate difference without discriminator
candidate difference with an immediately testable Nu discriminator
```

Only the third category should drive near-term mechanics work.

### B. c2nu / PMS / independent Nu loaders

Use these to cross-check:

- raw Nu VCR participant ordering;
- LEFT/RIGHT field mapping;
- owner/race changes after capture;
- historical turn addressing;
- missing/UNKNOWN field semantics.

Before inventing a new Host side rule, rule out an adapter/mapping mistake.

### C. Kecupo planets-vcr-sim / ChallengeSY nu-replayer

Determine whether they:

- only replay an already supplied VCR; or
- independently choose combat pairs / sides / post-capture continuations.

If they only consume factual LEFT/RIGHT, record that and stop treating them as
candidate queue engines.

If they construct ordering themselves, isolate the exact code path and convert
it into a candidate hypothesis only.

### D. JHOST / JPHost

Recover and inventory the complete server-side phase pipeline if source is
available.

High-value outputs:

- Host processing-stage ordering;
- battle queue lifecycle;
- capture mutation timing;
- battle-order or side state.

PHost-derived behavior is historical reference, not NuHost proof.

### E. OpenPlanets / xer0x-vgaphost / historical THost artifacts

Audit only after A-D or when they expose a clearly relevant discriminator.

Historical binaries are for executable archaeology/reference only, subject to
license/runtime constraints.

## Secondary research backlog

After the current capture-side question has yielded all useful candidates:

- Chained Intercept ordering;
- Moscow/SSC Intercept Interference;
- Campaign per-player advantages/hulls;
- Stack Ships and other entity-transforming abilities;
- mine/web/Safe Passage message signatures;
- race/hull capability mappings;
- movement/config/version boundaries.

Do not turn these into a competing main project while the main branch has an
active combat blocker.

## Allowed branch outputs

Good outputs:

- source/file/function maps;
- pinned external commit/release metadata;
- license/provenance notes;
- mechanics comparison matrices;
- minimal quoted/paraphrased candidate algorithms;
- candidate discriminator specifications;
- diagnostic/test scaffolding that does not assert Nu behavior;
- exact references to external tests/FIXMEs/ambiguity comments.

Avoid:

- copying third-party implementation code into canonical rules;
- changing evidence labels from external code alone;
- merging GPL/reference code into project mechanics;
- silently changing `main` mechanics;
- using external games as Nu evidence without official loadinfo/loadall
  acquisition.

## Branch integration contract

This branch may be long-lived.

When a useful finding is ready to return to `main`, produce a small handoff
containing:

```text
external source + pinned version
exact candidate rule or ambiguity
why it matters to a current planets-lab UNKNOWN
official documentation status
official Nu corpus discriminator available? yes/no
proposed bounded diagnostic
license/provenance note
```

The main mechanics chat decides whether to implement the discriminator and
whether the resulting official evidence justifies promotion.

## Immediate first deliverable

Deep-audit c2ng specifically for the current post-capture side/order blocker.

Produce a compact table:

| external location | observed implementation behavior | planets-lab status | discriminator available? | next action |
|---|---|---|---|---|

Do not start by producing a general encyclopedia of the repository.
