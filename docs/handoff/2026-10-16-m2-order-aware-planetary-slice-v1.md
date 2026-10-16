# M2 order-aware planetary transition — research slice v1

This implementation **composes** the existing `PlanetCargoTransferPhase` and
`PlanetaryHostPipeline` using the existing `HostEngine`, without replacing
any existing economy equations or changing canonical combat execution.

## Scope and epistemic boundary

`PlanetaryOrderAwareSlice(specs, placement=...)` requires **explicit**
`transfer_before_planetary` or `transfer_after_planetary`. These are
*counterfactual research assumptions*, **NOT** established NuHost chronology.
The 13 existing planetary phases retain their current relative order.

`step(state, TurnOrders)` produces a next cloned state, original HostEvents
and phase-by-phase `PhaseResourceBalance` entries for ship cargo, planet
cargo, underground minerals and combined net resources. Transfer phases
must conserve every recorded resource exactly. Mining moves minerals between
surface and ground; factory and tax phases create supplies and MegaCredits.
Negative balance entries identify depletion/loss, not inferred source orders.

`attempt_step` returns `ABSTAIN_UNSUPPORTED_OR_INVALID` with no next state,
events or phase-ledger on unsupported/invalid inputs, including foreign
ownership, unknown hulls, overcapacity, illegal fuel loads, unsupported
ship orders/missions, ship movement, starbase/storm contexts, and unsupported
population mechanics. Source `GameState` remains unchanged.

This slice does not implement ship movement, trade with enemies, purchases,
building, combat, starbase interactions, global Host ordering, or full
campaign/racial abilities. Without authenticated historical orders it
makes **zero** new claims about the 402 historical net-stock mismatches.
C5 remains frozen. Production IntelBoard, canonical combat, corpus CURRENT
and archival datasets are untouched.

## Reproducibility

`tools/diagnostics/planetary_order_aware_slice_v1.py` runs three deterministic
turns in both hypothesized phase placements using actual `TurnOrders`.
The published trace records every phase's events and inventory deltas,
and its stable SHA256. These are internal controlled scenarios, not historical
NuHost differential tests.

The server wrapper invokes targeted tests first, then produces
`artifacts/planetary/order-aware-slice-v1/published/report.json`; the
existing runtime-evidence publisher records the clean source commit, logs
and report on `runtime-logs`.

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-order-aware-slice-v1-with-evidence.sh
```

Future independent comparison requires independently authenticated source
orders and trustworthy snapshots. Unknown orders or phase boundaries must
remain abstentions rather than fitted pseudo-ground-truth.
