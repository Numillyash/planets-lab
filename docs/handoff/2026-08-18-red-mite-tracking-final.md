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

## Next work

Stop adding one-off Mite diagnostics. The next useful work should be one of:

1. integrate the now-stable observed behavior into an explicit Horwasp/race-mechanics model when that simulator milestone is selected;
2. continue M5 corpus/classifier work on another mechanic with higher product value;
3. return to the Planets intelligence/dashboard integration that consumes the lab's evidence.

If Red Mite implementation starts later, use `docs/rules/red-mite-tracking.md` and the compact regression fixture as the starting contract rather than reconstructing the investigation from diagnostic scripts.
