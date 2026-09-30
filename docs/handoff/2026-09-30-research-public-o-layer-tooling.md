# Public discovery O-layer tooling imported — 2026-09-30

## Why the old narrow runner stayed at 8 rows

The research checkout can see 102 shared archives, but
`run-combat-post-capture-candidate-discovery.sh` is intentionally scoped by
`validation/corpus/compiled/v1/metadata/game_features.parquet` and the
`combat-planar-no-horwasp` feature profile. Its runtime therefore continued to
use the original 11 selected games / 8 ship-capture observations and reported
the remaining archives as unindexed for that gate.

This was an expected scope limitation, not a shared-corpus failure.

## Imported from main

The research branch now carries the final public-discovery tooling from main:

- `tools/diagnostics/combat_public_capture_side_harvest.py`
- `tools/diagnostics/combat_public_capture_o_layer_probe.py`
- `tools/run-public-capture-side-discovery.sh`
- `tools/run-public-capture-o-layer-discovery.sh`
- corresponding tests
- targeted `selected_game_ids` / `site_filter` support in
  `combat_host_initial_standard_target_audit.py`

The O-layer probe consumes the already produced discovery artifact and only the
20 discovery games. It leaves the 16 deterministic held-out games sealed.

## Input discovery population

Current public discovery artifact:

```text
ship->ship capture continuations: 50
captured LEFT: 37
captured RIGHT: 13
T-1 order context resolved: 45
```

## Next runtime

From the research checkout, with the local compose override that read-only mounts
the main checkout's `validation/corpus/cache/loadall`:

```bash
COMPOSE_FILE="$PWD/compose.yaml:$PWD/compose.external-local.yaml" \
bash tools/run-public-capture-o-layer-discovery.sh
```

The probe tests the bounded external c2ng/THost original-order cursor against
the 50 discovery observations and reports:

- adjacent vs non-comparable rows;
- O pair reachable / not reachable;
- factual LEFT/RIGHT split within each;
- external O exact / mismatch.

Held-out games must not be opened until the O/C candidate is frozen.
