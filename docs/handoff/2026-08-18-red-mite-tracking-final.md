# Red Mite tracking investigation — final handoff

Date: 2026-08-18

Repository: `Numillyash/planets-lab`

Status: **research stage closed; return to simulator/corpus product work**.

The durable rule/specification is now:

```text
docs/rules/red-mite-tracking.md
```

Compact golden observations and regression tests are:

```text
tests/fixtures/red_mite_game_591478.json
tests/test_red_mite_empirical_model.py
```

## Final empirical model

For historical game `591478`:

1. Positive-target Red Mite tracking starts at a new observable Red Mite identity boundary `S`; exact identity uses `(owner, hull, name, raw ship turn)`. Numeric ids are reused and are not physical identity.
2. On clean starts, visible Mite waypoint is current target position.
3. The owner-authoritative target position at `S-1` acts as the observed fallback target coordinate after target-lock termination.
4. Visible cloak explains `60/62` same-target-identity immediate clears.
5. Target `329` is the unique exact Mite-target topology coincidence in the relevant uncloaked controls, but it is not promoted to a documented successful intercept because the observed target receives no minehit damage and the Mite does not self-destruct.
6. Target `206` is the only clean unexplained termination after excluding visible cloak, exact contact, 150-ly scan loss and documented pursuit timeout. The trigger remains unresolved; downstream behavior is ordinary fallback navigation.
7. In ordinary fallback, Mite keeps waypoint at the fallback coordinate and moves straight toward it with steps matching `min(warp^2, remaining distance)` within coordinate-rounding tolerance. The final corpus audit reported zero navigation mismatches.
8. `mission=0, mission1target=0` is an observable lost-lock/post-clear state, not immediate physical destruction.
9. Target `380` is the known special observable branch: when cloak occurs while current target equals the fallback coordinate, both Mites switch to self-waypoint and stop instead of performing observable fallback flight.
10. Effective wrapped-coordinate period `2170` remains scoped to game `591478`; do not turn it into a global `mapwidth + 20` rule.

## What is deliberately unresolved

Do not spend more research time on these unless a future simulator implementation or new corpus evidence requires it:

- exact internal Host representation/name of the fallback coordinate;
- exact Host subphase that initializes it;
- target `206` lock-loss trigger;
- whether target `329` represents a historical successful Mite intercept, a contact-without-success condition, or another historical Host variant;
- exact semantics of raw numeric `transfertargettype=1`;
- generalization of period `2170` outside game `591478`.

These are non-blocking unknowns.

## Post-research corpus integration

The first product integration of this result is now in the compiled movement-label layer:

```text
src/planets_lab/corpus/movement_horwasp_mite_context.py
tests/test_movement_horwasp_mite_context.py
```

`compiled-movement-context-labels` was bumped to schema `v2` and now promotes a residual Red Mite transition to the strong category:

```text
mite_fallback_navigation_g591478
```

only when all of the following are reconstructed from owner-authoritative historical state:

- game id is exactly `591478`;
- the Red Mite exact identity is continuous through the tracking run and clear snapshot;
- the target exact identity is continuous from `S-1` through the clear snapshot;
- the fallback row is the same Mite identity in `mission=0`, `mission1target=0`;
- waypoint equals the reconstructed `target.xy(S-1)` fallback coordinate under the evidence-scoped `2170` wrap period;
- the observed movement is straight toward that coordinate and matches `min(warp^2, remaining distance)` within the same `1.5 ly` rounding tolerance used by the final audit.

All other Mite residuals, all `380` self-waypoint stop variants, and every Mite transition from other games remain fail-closed residuals. This integration deliberately does not generalize the game-591478 reconstruction across the historical corpus.

## Next work

Stop adding one-off Mite diagnostics. After the scoped corpus label integration is regression-tested and rebuilt locally, the next useful work should be one of:

1. integrate broader Red Mite behavior into an explicit Horwasp/race-mechanics simulator module only when that simulator milestone is selected;
2. continue M5 residual classification on the next high-volume non-Mite hull/mechanic;
3. return to the Planets intelligence/dashboard integration that consumes the lab's evidence.

Use `docs/rules/red-mite-tracking.md`, the compact golden fixture and the scoped compiled-label classifier as the starting contract rather than reconstructing the investigation from diagnostic scripts.
