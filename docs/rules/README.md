# Rules specification

This directory is the evidence-backed specification for mechanics implemented by `planets-lab`.

## Evidence states

- `DOCUMENTED` — explicitly stated in primary Planets.nu documentation.
- `CORPUS_OBSERVED` — directly observed in historical/current NuHost corpus data without claiming internal Host semantics.
- `INFERRED` — reconstructed from observations or secondary material.
- `TESTED` — covered by a local deterministic scenario/test.
- `DIFF_VERIFIED` — local result matched against a NuHost reference run.

A rule can carry more than one state. `DOCUMENTED` does not imply `DIFF_VERIFIED`.

## Policy

Simulator code must not silently fill gaps in the rulebook. If behavior is ambiguous, record the ambiguity here and keep the implementation out of the engine until a test or reference result resolves it.

Primary source registry: [`SOURCES.md`](SOURCES.md).

## Corpus-backed special mechanics

- [`red-mite-tracking.md`](red-mite-tracking.md) — completed empirical reconstruction of Red Mite tracking identity boundaries, target-lock termination and fallback navigation in historical game `591478`; unresolved trigger `206` and exact-contact edge case `329` remain explicitly non-generalized.
- [`ghost-ships.md`](ghost-ships.md) — documented ghost-ship state plus historical wire-encoding observations.
