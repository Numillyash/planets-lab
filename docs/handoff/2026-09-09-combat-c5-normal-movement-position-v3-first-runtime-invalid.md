# C5 Host combat — first storm-aware position v3 runtime invalidated by metadata source

Date: 2026-09-09

First v3 runtime source:

```text
070cb150a7b88e9a406f3ef8ca9f5984b873211e
```

Artifact:

```text
artifacts/combat-c5-position-v3-20260909-234137/position-v3.json
```

Targeted tests passed and the diagnostic exited successfully, but the historical differential itself is **not valid evidence for position coverage** because storm-mode metadata was read from the prepared mechanical projection, which intentionally retains `nowarpwells` but does not retain `nuionstorms`.

Observed summary:

```text
tests rc=0
position-v3 rc=0
payload_conflicts=0
storm_mode_games={'nuionstorms_unknown': 11}

ship occurrences:
  factual=3204
  position_uncovered=3193
  uncovered:storm_mode_unknown=1810

factual pairs:
  total=1986
  position_uncovered=1986
```

This is an instrumentation/source-context failure, not a Host mechanics result. It must not be interpreted as evidence that the historical games had unknown ion-storm mode.

The contradiction was immediately visible because the preceding residual audit read raw archived turn payloads and resolved `nuionstorms=False` for the relevant games.

## Root cause

`ArchiveTurnSnapshot.mechanics_payload` is privacy/minimal-mechanics projected state. `normalizer._mechanics_settings(...)` deliberately projects only the warp-well switch and does not preserve `nuionstorms`.

The first v3 implementation used that prepared projection for `_nuionstorms_consensus(...)`, so every game became unknown despite the raw archives containing the setting.

## Repair

`tools/diagnostics/combat_host_normal_movement_position_audit.py` now resolves `nuionstorms` directly from the first/last raw `.trn` payloads inside each local archive, matching the evidence source used by the successful residual attribution audit.

A regression test constructs a synthetic archive and verifies:

- stable `False/False` resolves `False`;
- conflicting `True/False` fails closed to `None`.

No storm geometry or combat rule was changed by this repair.

## Status

```text
first v3 historical position output: INVALID AS COVERAGE EVIDENCE
focused four-row context output from same user run: VALID, recorded separately
storm-aware predictor after raw-setting fix: pending user runtime
```
