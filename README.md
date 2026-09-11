# planets-lab

Research and validation workspace for reconstructing Planets.nu / NuHost mechanics.

The repository intentionally separates:

- factual source data and prepared corpus caches;
- reconstructed mechanics and deterministic simulation code;
- diagnostics / differential audits;
- durable evidence handoffs and architecture notes.

## Source of truth

GitHub `main` is the project source of truth. Historical raw archives, prepared caches, compiled corpora and runtime artifacts are local and gitignored unless explicitly documented otherwise.

## Evidence labels

Mechanics should be described with explicit evidence status where relevant:

- `DOCUMENTED`
- `CORPUS_OBSERVED`
- `INFERRED`
- `TESTED`
- `DIFF_VERIFIED`

Unknown branches should fail closed rather than being guessed.

## Current focus

See:

```text
docs/ROADMAP.md
docs/handoff/2026-09-08-combat-c5-host-phase-current.md
```

for the active Host-combat reconstruction gate and current durable checkpoints.
