# New chat handoff — resume Host combat engagement/order reconstruction

Date: 2026-09-21

Repository: `Numillyash/planets-lab`
Branch: `main`

GitHub `main` is the only source of truth.

Do not trust SHA values from chat history without re-reading the actual GitHub
branch first.

## Checkpoint base

The semantic/code state immediately before this documentation-only transition
checkpoint is:

```text
b31a15e132deeaa146f1bbe43b9d9083dc5a9ecb
```

That commit is:

```text
docs: record shared combat feature scope layer
```

GitHub Actions for that HEAD completed successfully.

Recorded suite result:

```text
390 passed
```

A later documentation-only transition commit may therefore be the actual HEAD
when the next chat starts.

## Read first

Before changing code, read:

1. `README.md`
2. `docs/ROADMAP.md`
3. `docs/COMPILED_CORPUS.md`
4. `docs/ARCHITECTURE.md`
5. `docs/WORKFLOW.md`
6. `docs/handoff/2026-09-21-corpus-feature-index-v1.md`
7. `docs/handoff/2026-09-21-corpus-feature-index-v1-runtime.md`
8. `docs/handoff/2026-09-21-combat-feature-scope-selector-runtime.md`
9. this handoff

Also inspect the latest combat-related commits and the current
`src/planets_lab/rules/combat/` implementation before planning new mechanics
work.

## Feature Index v1 — closed

The historical corpus has a deterministic Game / Host Feature Index:

```text
schema: planets-lab.game-feature-index.v1
storage: normalized typed Parquet + DuckDB
games: 12
rows: 1152
known: 1116
unknown: 36
missing archives: 0
```

Accepted archive rebuild SHA:

```text
cb72f539775d22726d8d7f225fc7b3deeb8f936312873df12db59340e1dd7735
```

Strict selector:

```text
ordinary-classic
  -> 360690
  -> 511506
  -> 620694
```

This index is population-selection infrastructure only:

```text
feature-index match
!= mechanic observation
!= discriminator
!= DIFF_VERIFIED
```

## Combat feature-scope migration — mechanically neutral

The historical C3/C4 clean scope is now represented by factual profile:

```text
combat-planar-no-horwasp
```

Predicates:

```text
game.status == 3
settings.sphere == false
population.horwasp_present == false
```

On the current 12-game corpus it selects 11 games and excludes the
Sphere/Horwasp population without hardcoding game id `591478`.

The first archive runtime before the shared-resolver refactor passed exactly:

```text
exact=true
failures=[]

C4 selected transitions                103
C4 match                               102
C4 not_comparable                        1

C3 selected same-location transitions 1169
C3 strict ship->ship survivor oracle    764/764
C3 gap=1 oracle                         751/751
C3 ship->planet boundary transitions     397
C3 ship->planet match                    374
C3 capture reappearances                  15
C3 boundary mismatches                     8

excluded same-location transitions       316
UNKNOWN scope                              0
```

Durable runtime:

`docs/handoff/2026-09-21-combat-feature-scope-selector-runtime.md`

## Shared FeatureScope resolver

After that successful archive runtime, scope plumbing was consolidated into:

```text
src/planets_lab/corpus/feature_scope.py
```

Public API:

```text
FeatureScope
load_feature_scope(...)
optional_feature_scope(...)
```

It owns:

- selected game IDs;
- known-mismatch excluded game IDs;
- UNKNOWN game IDs;
- unindexed classification;
- JSON-safe report metadata.

Required partition invariants:

```text
selected ∩ excluded = empty
selected ∩ unknown  = empty
excluded ∩ unknown  = empty
```

An unindexed game is not silently treated as selected.

Current consumers:

```text
combat_classic_corpus_parity_audit.py
combat_planet_chain_audit.py
combat_ship_chain_phase_audit.py
combat_ship_chain_cluster_audit.py
```

`combat_ship_chain_audit.py` does not construct a clean/special-game partition
and therefore intentionally does not consume this selector layer.

## One remaining infrastructure acceptance

The shared `FeatureScope` refactor is CI-verified but, at the time of this
handoff, there is no durable archive-host runtime recorded against the
post-refactor `b31a15e...` code state.

Therefore the first bounded action in the next chat is:

```bash
bash tools/run-combat-feature-scope-gate.sh
```

Run it only after syncing a clean checkout to the actual GitHub `main`.

Expected acceptance:

```text
selector_partition_shared: true
selector_partition_disjoint: true
planet_c4_checkpoint_preserved: true
ship_c3_checkpoint_preserved: true
cluster_partition_preserved: true

exact: true
failures: []
```

If this passes, append the runtime result to the durable selector handoff and
consider selector plumbing closed. Do not spend another workstream polishing
Feature Index/FeatureScope unless a later mechanic exposes a concrete problem.

If it fails, treat the failure as infrastructure/population evidence first; do
not change mechanics rules merely to make the gate green.

## Existing combat evidence boundaries

Do not redo or weaken the established checkpoints:

### C1/C2 — pairwise Classic replay

Current corpus:

```text
archives              12
raw VCR observations 22256
unique VCRs           6469
replay supported      6469
replay unsupported       0
payload conflicts        0
ship-vs-ship          2750
ship-vs-planet        3719
```

Pairwise replay is mature. The major open problem is Host choosing which VCRs
exist and in what order, not replaying an already supplied VCR.

### C3 — ordinary ship sequence carry

Strong selected ordinary oracle:

```text
ship->ship survivors 764/764 exact
gap=1                 751/751 exact
```

Evidence:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Federation between-fight shield recovery is:

```text
next_shield = min(100 - damage, shield + 25)
```

and is also scoped `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

### C4 — planet/starbase sequence carry

Selected clean population:

```text
103 transitions
102 exact
1 not comparable
0 mismatch
92 starbase
11 no-starbase
103/103 shield carry
```

Supported plain-planet carry and starbase shield persistence are checkpointed.
Hidden persistent state for a surviving starbase after non-zero hull damage
remains fail-closed.

### Ship->planet boundary

Do not force the eight damage-only boundary residuals into the pairwise
resolver:

```text
397 transitions
374 match
15 capture reappearance
8 damage-only mismatch
```

This boundary has a separate Host repair/interphase step.

## Immediate substantive target after the one rerun

Return to **Host combat engagement/order reconstruction**.

The next objective is predictive Host queue generation:

```text
factual co-located precombat state
        |
        v
eligibility / attack requests / blockers
        |
        v
phase classification
PIA / C&I / STANDARD / other supported prestandard branches
        |
        v
active combatant + opponent selection
        |
        v
LEFT / RIGHT side assignment
        |
        v
pairwise VCR resolver
        |
        v
mutable survivor/capture state
        |
        v
next pair
        |
        v
ship->planet boundary
        |
        v
planet/base sequence
```

Success is not "we can replay a VCR". Success is predicting the factual
**set, order and sides of VCRs** from factual precombat state.

## Mechanics work order

Use the current code and existing historical gates; do not start from scratch.

1. inventory the current canonical engagement/order primitives and diagnostics;
2. identify which initial pair-selection / directional targetability / PIA /
   C&I / Galactic Power / matching-FC rules are already productionized;
3. identify which mutable-queue / repeated-pair / capture-continuation rules are
   already productionized;
4. build the next bounded predictive queue gate around the largest clean
   attributable population;
5. hold factual VCR N+1 out until comparison wherever possible;
6. only promote a rule after competing hypotheses/confounders are separated;
7. keep special/campaign/Horwasp behavior separate from ordinary promotion.

Prefer one larger tracked `tools/run-*.sh` batch that runs multiple related
diagnostics and tests over chat-driven chains of tiny commands.

## Evidence discipline

For every new mechanics rule:

1. define attributable population;
2. enumerate competing hypotheses;
3. control known confounders;
4. add deterministic unit tests;
5. add historical differential gate;
6. record evidence status and scope;
7. update ROADMAP/handoff in the same logical change.

Never infer:

```text
missing == false
unknown == disabled
selector membership == mechanics evidence
post-Host snapshot == precombat state
```

## Workflow

- GitHub `main` is source of truth.
- Work directly from actual GitHub state.
- Prefer coherent larger blocks of work.
- Commit completed work to `main`.
- Keep generated archives/caches/artifacts gitignored.
- Long local/corpus orchestration belongs in tracked `tools/run-*.sh`.
- Do not ask for confirmation on routine technical decisions.
- If local immutable archives are required, prepare one tracked runner and ask
  for one execution rather than many individual shell commands.

## Next-chat completion target

A good next session should ideally finish one substantial mechanics block, not
just inventory.

Minimum target after the FeatureScope rerun:

- a bounded predictive combat-queue hypothesis implemented in canonical code or
  a decisive diagnostic narrowing the next queue unknown;
- deterministic tests;
- one reproducible historical gate;
- updated ROADMAP/handoff;
- committed `main` state.
