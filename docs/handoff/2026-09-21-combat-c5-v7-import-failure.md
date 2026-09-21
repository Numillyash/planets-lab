# C5 v7 first runtime attempt — invalidated by mixed-audit truncation

Branch: `agent/combat-c5-host-phase`

Runtime attempted from:

```text
e7086e0dfb084c0267100a34c2464f45c0e8f382
```

## Result

The run is **not an evidence-bearing v7 runtime**.

Independent stages that do not import the shared mixed diagnostic continued to run and remained green, including:

```text
FACTUAL QUEUE SHAPE
PLANET CARRY
SHIP NEXT-PAIR REGRESSION
POST-CAPTURE INITIATOR REGRESSION
MIXED SHIP/PLANET DISCOVERY V7 process exit
```

However the regression collection and four dependent diagnostics failed on import:

```text
_capture_reset_priority_order
_shape
_load_groups
HORWASP_RACE_ID
```

## Root cause

The shared file

```text
tools/diagnostics/combat_host_mixed_ship_planet_queue_batch_audit.py
```

was accidentally truncated during a schema-only GitHub edit.

Known-good v6 runtime HEAD:

```text
370ecaf5de029fadfd0acafd1107e1fb35c9cb54
file length: 42153 bytes
```

Broken v7 attempt HEAD:

```text
e7086e0dfb084c0267100a34c2464f45c0e8f382
file length: 1219 bytes
```

The cause was an editing error: only the first 40 lines were fetched, then that partial content was submitted as a complete file replacement.

This was not a mechanics/corpus failure.

## Repair

Commit:

```text
2d0dec4c497912ce93fcf596844214a05b75d24a
  fix: restore full mixed queue audit after schema truncation
```

The full known-good v6 diagnostic was restored and only the schema identifier was advanced to v7.

Structural verification after repair confirms presence of:

```text
HORWASP_RACE_ID
_shape
_load_groups
_planet_pair
_planet_projection
_priority_projection
_resolved_owner_at_turn
_capture_reset_priority_order
_production_planet_order
_same_planet_priority_group
_site_profile
```

The dependent diagnostic files are intact.

Additional prevention:

```text
a7959617d0da7ed851511ef22e939623ab54529e
  tools: add shared diagnostic import smoke gate
```

The batch now starts with `SHARED IMPORT SMOKE` before the full regression/corpus run.

## Evidence boundary

Do not promote, reject, or modify any C5 mechanics hypothesis from this failed v7 attempt.

The last evidence-bearing runtime remains:

```text
v6
HEAD 370ecaf5de029fadfd0acafd1107e1fb35c9cb54
10/10 stages rc=0
```

The directed clan-drop v7 gate remains pending and must be rerun from the repaired branch.
