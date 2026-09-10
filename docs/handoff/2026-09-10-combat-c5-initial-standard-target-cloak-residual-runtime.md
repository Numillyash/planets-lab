# C5 Host combat — initial STANDARD target cloak residual runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Runtime

Source:

```text
3d3b8d91f3ff281b0563a0f7112fadbe86222f2b
```

Artifact:

```text
artifacts/combat-c5-initial-target-cloak-residual-20260910-202102
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
target_sites=2
rows_found=2
extra static Bird Super-Spy cloak signature true=1
extra basic cloak reference fuel sufficient=true=2
extra T iscloaked=true=2
factual target owner changed by T=2
```

## Residual 511506/T94 — documented Super Spy cloak attribution

```text
active: 496 owner5/race5 Bloodfang, PE3, FC001
extra:  202 owner3/race3 Red Wind, mission9, PE0
factual target: 332 owner3/race3 Resolute, mission2, PE0
```

For ship202:

```text
race_id=3
hull47 Red Wind can cloak
mission9
T-1 iscloaked=true
T-1 fuel=37, ordinary basic-cloak reference cost=5
T same owner/hull and iscloaked=true
```

This is a clean archive/static signature for documented Bird Super Spy attempting cloak on a cloak-capable hull. The pair `[202,496]` therefore has a concrete missing target-cloak blocker candidate. This does **not** yet promote a generic current-host effective-cloak implementation because Loki/ion/damage/cloak-type and exact Host-step state are not reconstructed globally.

Ship332 is an important negative control against using the raw T-1 `iscloaked` bit directly:

```text
race3 Resolute, cloak-capable
mission2, not the Bird Super Spy signature
T-1 iscloaked=true
factual VCR728 occurs against ship496
T later shows same hull captured by owner5 and iscloaked=false
```

Therefore `T-1 iscloaked=true` is **not** a safe blanket combat blocker.

## Residual 360690/T83 — not Super Spy; remains open

```text
active: 264 owner11/race11 Virgo
extra:  98 owner5/race5 Meteor, mission9, PE0
factual target: 190 owner5/race5 Meteor, mission9, PE0
```

Owner5 resolves to race5 (Privateer), so mission9 is not Bird Super Spy. Ship98 nevertheless has:

```text
cloak-capable Meteor
T-1 iscloaked=true
T-1 fuel=45, ordinary basic-cloak reference cost=5
T same owner/hull and iscloaked=true
```

Factual target190 has only 4 kt at T-1, below the ordinary 5 kt basic-cloak reference, `T-1 iscloaked=false`, and is captured by the factual VCR.

The ship98 state is suggestive but cannot be promoted as a Rob-causes-or-preserves-cloak mechanic from one row. Official mission semantics distinguish Privateer Rob from Bird Super Spy, and the raw T-1 cloak bit has already failed as a universal combat-phase state oracle via ship332.

## Evidence boundary

Promoted conclusion from this runtime:

```text
511506/T94 ship202 extra-target blocker:
  documented Super Spy cloak signature + corpus state support
  => strong scoped attribution candidate

360690/T83 ship98:
  Privateer mission9 + persistent archived cloak bit
  => unresolved until population/context evidence

raw T-1 iscloaked as generic combat blocker:
  REJECTED
```

No change is made to `selection.py`, standard Combat Priority or target ordering from this runtime.

## Next gate

Run the population diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_cloak_population_audit.py
tests/test_combat_host_privateer_rob_cloak_population_audit.py
```

It inventories archive-resolved Privateer race5, mission9, cloak-capable ships across consecutive T-1 -> T states, requiring conservative physical-ship identity continuity before interpreting cloak transitions. It reports VCR participation separately and keeps T-state attribution-only.

If Privateer mission9 + prior cloak systematically persists into the next state for stable physical ships, investigate whether NuHost preserves cloak state through Rob or whether the archive field has different timing semantics. If the target row is isolated, keep ship98 bounded and move to another candidate blocker/state source. Do not alter target priority from this residual.
