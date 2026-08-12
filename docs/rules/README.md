# Rules specification

This directory is the evidence-backed specification for mechanics implemented by `planets-lab`.

## Evidence states

- `DOCUMENTED` — explicitly stated in primary Planets.nu documentation.
- `INFERRED` — reconstructed from observations or secondary material.
- `TESTED` — covered by a local deterministic scenario/test.
- `DIFF_VERIFIED` — local result matched against a NuHost reference run.

A rule can carry more than one state. `DOCUMENTED` does not imply `DIFF_VERIFIED`.

## Policy

Simulator code must not silently fill gaps in the rulebook. If behavior is ambiguous, record the ambiguity here and keep the implementation out of the engine until a test or reference result resolves it.

Primary source registry: [`SOURCES.md`](SOURCES.md).
