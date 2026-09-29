# Public capture-side discovery runtime

Date: 2026-09-30

## Canonical discovery evidence

Published runtime:

```text
runtime-logs/public-capture-side-discovery/20260929T212837Z_745a7bbe4976
source_branch: main
source_commit: 745a7bbe4976013f67d6136b1bb3807389975024
partition: discovery
exit_code: 0
```

The deterministic split kept 16 indexed games sealed as held-out and scanned
20 discovery games.

Observed capture continuations:

```text
capture continuations        61
next combat = ship           50
next combat = planet         11
ship prize LEFT              37
ship prize RIGHT             13
prior same-pair 0            46
prior same-pair 1             4
```

The previous small-population side controls do not generalize:

```text
always prize LEFT / opponent-initiator-right   37 / 50
sticky capture side                            22 / 50
```

A direct ship-id ordering check is also non-exact (33 / 50 on discovery).
No LEFT/RIGHT rule is promoted from these observations.

## Next diagnostic

The public harvester is extended to extract only the two authoritative T-1
owner-perspective turn members required for each ship continuation. It does not
build whole-game prepared caches.

For each discovery observation it now records:

- captured ship T-1 mission, mission target, Primary Enemy and Friendly Code;
- opponent ship T-1 mission, mission target, Primary Enemy and Friendly Code;
- standard battle priority keys;
- the three C5 side controls already defined by the earlier 8-row gate:
  - frozen T-1 priority;
  - neutral captured orders preserving FC;
  - neutral captured orders with a fresh nonmatching symbolic FC;
- exact/mismatch/unresolved counts against the factual discovery side.

This enrichment remains discovery-only. Held-out games are not read by the
runner and must remain sealed until a candidate rule is frozen.
