# Finite-fuel Tow historical discovery — prepared

Date: 2026-09-09

GitHub `main` is the source of truth. This handoff records prepared research tooling only. It is **not** historical evidence and it does **not** promote finite-fuel Tow.

## Why this pass exists

The normal-movement partial-fuel gate is now scoped:

```text
continuous effective one-turn fuel leg for true-partial normal movement
Move Most + Intercept
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

That result does not transfer automatically to Tow. The current `planets-intel` production boundary correctly keeps finite-fuel Tow fail-closed because Tow needs a Tow-phase fuel state and the combined movement mass of tower plus target.

The next evidence question is therefore narrower:

> In historical finite-fuel games, do strict successful Tow routes contain attributable fuel-limited cases that distinguish continuous nominal one-turn costing from rasterized-endpoint-distance costing when the movement mass includes both ships?

## Prepared tooling

Core diagnostic:

```text
tools/diagnostics/tow_finite_fuel_population_audit.py
```

Tracked orchestration runner:

```text
tools/run-finite-fuel-tow-historical-gate.sh
```

Server invocation after updating a clean `main` checkout:

```bash
bash tools/run-finite-fuel-tow-historical-gate.sh
```

The runner:

- requires a clean `main` checkout equal to freshly fetched `FETCH_HEAD`;
- consumes the existing compiled DB, `loadall` archives and prepared caches;
- does **not** rebuild L1/L2;
- runs the full pytest suite;
- runs the strict Tow discovery;
- preserves stage logs/status under `logs/finite-fuel-tow-*`;
- never promotes Tow or changes `planets-intel`.

## Strict discovery scope

A route can enter the fuel model only when all of these are satisfied:

- game setting is explicitly finite-fuel;
- effective topology is non-sphere;
- an ex-post owner-visible successful Tow route exists;
- exactly one matching tower identity exists;
- exactly one Tow attempt targets the target;
- no Tow chain/cycle participant is involved;
- tower and target have same-identity owner records before/after;
- tower owner record still points at the exact target;
- tower and target are exactly colocated before movement;
- target is present in the tower owner's factual snapshot and its visible coordinates agree with the target-owner perspective;
- tower hull has at least two engines;
- tower warp/waypoint and both physical mass states are complete;
- `hyp` is excluded for both participants;
- Four Fingers non-break can be proven **without using target snapshot neutronium**.

The last condition is important. A target is retained only when some non-fuel condition makes Four Fingers unable to break the Tow:

- target has fewer than two engines; or
- target waypoint is within its warp-square threshold; or
- target effective maximum speed is lower than the tower's.

If the lock outcome would depend on whether target Tow-phase fuel is above 25 KT, the row is excluded as `lock_nonfuel_unresolved`.

## Mass and visibility boundary

For mechanical research, full tower mass comes from the tower owner's historical perspective and full target mass comes from the target owner's historical perspective. The two are joined only inside the lab diagnostic.

This cross-perspective join is allowed for Host reconstruction, but it is **not** a production visibility claim. The target is separately required to appear in the tower owner's snapshot. Production must not infer hidden target internals merely because the historical lab can reconstruct them from another player's archive.

The candidate movement mass is:

```text
tower physical movement mass + target physical movement mass
```

using actual fitted component counts and factual cargo fields, not hull weapon capacities.

## Fuel-state uncertainty

Snapshot neutronium remains pre-Host evidence only.

The diagnostic reports two layers:

1. **snapshot differential** — what projected vs nominal costing predicts from the pre-Host tower/target snapshot;
2. **phase-fuel envelope** — vary tower neutronium over `1..tower fuel tank` and target neutronium over `0..target fuel tank`, recomputing combined mass, while holding all non-fuel mass fixed at the owner-visible snapshot state.

The target-fuel scan is reduced to the distinct `TRUNC(total_mass / 10)` bins seen by the documented fuel formula; it is mechanically equivalent to scanning every target-fuel integer for the fuel equation.

The envelope does **not** solve arbitrary earlier cargo transfers. Non-fuel cargo and installed components remain snapshot-fixed.

## Cost-basis comparison

For a true-partial Tow route:

```text
requested distance for this Host step = effective max one-turn distance
```

Two cost hypotheses are compared:

```text
projected basis = distance from origin to rasterized one-turn endpoint
nominal basis   = continuous effective max one-turn distance
```

Both use the same proportional insufficient-fuel endpoint rule; only the fuel-cost basis differs.

For a reachable route the two cost distances are identical, so it can support combined-mass/proration behavior but cannot distinguish nominal-vs-projected true-partial costing.

## Discovery signatures

Most interesting counters are:

```text
snapshot_nominal_only
snapshot_projected_only

phase_nominal_only_possible
phase_projected_only_possible
phase_both_possible
phase_neither_possible
```

`phase_nominal_only_possible` is the strongest first-pass cost-basis signature: with non-fuel mass fixed and neutronium allowed anywhere within both physical tank capacities, the factual endpoint is achievable under nominal costing and not achievable anywhere under projected-distance costing.

Even that is **not sufficient for promotion**.

Any discriminator still requires a targeted audit for:

- earlier fuel and non-fuel transfers;
- mine/web interaction;
- ion storms;
- damage-limited movement;
- warp wells;
- Chunnel;
- any other already-modelled external movement path;
- post-movement fuel only as supporting evidence.

## Status

```text
finite-fuel Tow: OPEN
historical discovery runner: PREPARED, NOT YET RUN
planets-intel production transfer: BLOCKED by separate Tow evidence gate
```

Do not weaken the existing production fail-closed Tow boundary based on this preparation commit.
