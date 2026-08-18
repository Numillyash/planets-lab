# Horwasp Red Mite tracking

Status: `DOCUMENTED` for the public Mite limitations and pursuit-duration rules, `CORPUS_OBSERVED` / `INFERRED` for the historical NuHost behavior reconstructed below.

This note freezes the Red Mite tracking investigation for historical game `591478`. It is intentionally scoped to observed behavior and must not be generalized to other games, rulesets or map topologies without new evidence.

## Primary documented behavior

Planets.nu documents the Mite ability as follows:

- a Mite is launched with a target starship and attempts to intercept it;
- Red Mite payload is one minehit of damage;
- documented pursuit duration depends on launch speed: warp 9 -> 1 turn, warp 7 -> 10 turns, warp 6 -> 10 turns, warp 3 -> unlimited;
- Mites cannot target or track cloaked starships;
- a Mite loses target lock when the target is outside 150 ly scanning range of every Horwasp ship and planet;
- Mites cannot be launched against a ship at a planet / warpwell and are not launched if the target goes to a planet on the launch turn;
- the public rule text says a successful interception delivers the payload immediately and self-destructs the Mite.

Primary source: `https://help.planets.nu/abil-mite`.

The corpus observations below do not silently force historical Host behavior to match that text when the wire data disagrees.

## Corpus scope

Evidence source:

```text
validation/corpus/cache/loadall/game-591478.zip
```

Observed map metadata reports a spherical map with raw width/height `2150`, but the specific wrapped-coordinate relationships used by this investigation match an effective period of `2170`.

`2170` is therefore an evidence-scoped topology parameter for game `591478`, not a global formula such as `mapwidth + 20`.

Red Mite hull id in this game: `213`.

For lifecycle comparisons, ship identity is treated as:

```text
(owner, hull, name, raw ship turn)
```

Numeric ship ids are not lifecycle identities and are aggressively reused.

## Tracking-run identity boundary

Across all `327` observed positive-target Red Mite tracking runs:

- `raw ship turn == tracking_start` in `327/327`;
- the exact Red Mite identity is first observed at `tracking_start` in `327/327`;
- the same numeric id had been used earlier in `322/327` runs, but never by the same exact identity;
- only four runs have the same numeric id present on the immediately preceding snapshot, and all four are a different identity (`STINGER -> RED MITE`) with large spatial discontinuities.

Therefore `tracking_start = S` is an observable new-identity boundary, not merely a mission change on an already continuous Red Mite object.

For the `326` runs where the target exists on `S`:

```text
Mite.wp(S) == target.xy(S)
```

in `326/326` cases.

The remaining run has no owner-authoritative target record at `S` and is not a meaningful counterexample to target-waypoint initialization.

## Launch-boundary predecessor coordinate

Define the evidence-only coordinate:

```text
A = target.xy(S - 1)
```

where the target identity is owner-authoritative and continuous across `S-1 -> S`.

This coordinate was originally called an `anchor` in diagnostics. The safer specification term is **fallback target coordinate** or **launch-boundary predecessor coordinate**. The corpus does not prove that NuHost stores a literal field named anchor.

Important launch-boundary observations:

- `A` is available for `327/327` tracking runs;
- `A` is exactly at a planet in `0/327` runs;
- the current target at `S` is exactly at a planet in `119/327` runs;
- for the clean target-continuity subset, `A` belongs to the same target identity as the target at `S`.

These facts are compatible with `S-1` being a pre-launch / launch-boundary observation and `S` being a later Host snapshot, but exact internal Host phase ordering remains inferred.

## Active tracking

During ordinary observed tracking, Red Mite waypoint follows the owner-authoritative current target position.

For the clean initialization subset:

```text
Mite.wp(S) = target.xy(S)
```

and later current-target waypoints continue to update while lock remains valid.

Raw numeric mission values are preserved as evidence. This note does not assign a semantic name to `mission=7`; it only uses the observed positive `mission1target` tracking pattern.

## Same-target-identity immediate clears

There are `62` runs where:

- the target exact identity continues into the following snapshot; and
- the Red Mite leaves positive-target tracking immediately, appearing as the same exact Mite identity with `mission=0`, `mission1target=0` on the next snapshot.

Observed branch coverage:

```text
60  target visibly cloaked during the run
 1  exact Mite-target coordinate coincidence (target 329)
 1  no visible cloak, exact contact, 150-ly scan loss or documented timeout (target 206)
```

The one scan-loss signature found inside this subset overlaps a visible-cloak event; it is not an additional independent clear count.

For the warp-6 clean clears, the observed tracking lengths are far below the documented 10-turn lifetime in the cloak and unexplained examples, so those events are not explained by pursuit timeout.

## Fallback navigation after lock termination

The strongest reconstructed behavior is the post-termination navigation path.

For `60/62` clean clears, the last active tracking waypoint is the launch-boundary predecessor coordinate `A`.

The two exceptions are both Red Mites tracking target `380`; this target becomes visibly cloaked while its current position temporarily equals `A`, then both Mites switch waypoint to their own position and stop rather than flying to `A`.

For every normal fallback case with observable post-clear movement:

- the moving Red Mite keeps `wp == A`;
- movement is straight toward `A` within rounding tolerance;
- movement step is consistent with `min(previous_warp ** 2, remaining_distance_to_A)` within `1.5 ly` tolerance;
- the aggregate diagnostic reports `NAVIGATION MISMATCHES = 0`.

In the clean clear sample:

- `45` Mites were observed to reach `A` before disappearance / id reuse;
- for `44` of those, `warp` becomes `0` on the following snapshot;
- waypoint becomes the Mite's own position at the arrival snapshot;
- `15` Mites disappear or change identity before reaching `A`, including target `206`'s Mite.

Therefore `mission=0, mission1target=0` is not a destruction marker. It is an observable post-lock state in which the same Red Mite identity can continue navigating toward the fallback target coordinate.

## Focus event: target 329

Mite `1185`, target `329` (`RU30 GUNBOATS`), tracking start `S=51`.

Evidence-scoped fallback coordinate:

```text
A = target.xy(50) = (3060, 2201)
```

At turn `56`:

```text
Mite.xy   = (3085, 2331)
target.xy = ( 915, 2331)
```

which is the same topology point modulo `2170`.

At that same snapshot:

- target is visibly uncloaked;
- no 150-ly Horwasp scan loss is observed;
- Mite warp is `6`, well before the documented 10-turn pursuit timeout;
- Mite waypoint has already changed to `A`;
- target damage remains `0` in the observed snapshots.

Post-clear lifecycle:

```text
t56 (3085,2331)  mission positive-target, wp=A
t57 (3078,2296)  mission=0, wp=A
t58 (3071,2261)  mission=0, wp=A
t59 (3065,2226)  mission=0, wp=A
t60 (3060,2201)  mission=0, reaches A
t61                warp=0, wp=self
```

The spatial coincidence is unique in the relevant uncloaked control population and is strongly associated with lock termination. However, this corpus does **not** prove a documented successful Mite interception because the target has no observed minehit damage and the same Mite identity does not self-destruct; it instead enters ordinary fallback navigation.

Treat `329` as an exact-contact termination edge case, not as a proven successful-intercept implementation oracle.

## Focus event: target 206

Mite `1167`, target `206` (`DETH SPECULA`, hull `1033`), tracking start `S=65`.

```text
A = target.xy(64) = (2329, 2239)
```

At turn `66` the Mite loses normal current-target tracking and switches waypoint to `A` while:

- target remains visibly uncloaked;
- Mite-target distance is about `123 ly`;
- Horwasp scan coverage remains available, including Horwasp support well inside `150 ly`;
- Mite warp is `6` and tracking length is only two snapshots;
- target is at planet `452`, owner `6`;
- target changes `damage 0 -> 1` and `podcargo 0 -> 8`;
- target raw fields change `transfertargetid 0 -> 452`, `transfertargettype 0 -> 1`;
- target mission changes `9 -> 1` and `mission1target 346 -> 0`.

On subsequent snapshots the same Red Mite identity follows the normal fallback law toward `A` with warp-6-sized steps, then disappears before reaching the destination.

Control populations show that target damage, podcargo change, DETH SPECULA hull type, proximity and merely being at a planet are individually insufficient explanations.

`206` therefore remains the one clean **unresolved lock-termination trigger**. Its downstream fallback behavior is not unresolved.

Do not assign semantics to `transfertargettype=1` without independent evidence.

## Focus event: target 380

Two Red Mites (`1110`, `1163`) begin tracking target `380` at `S=93`.

```text
A = target.xy(92) = (1419, 2837)
```

At `t94`, target becomes visibly cloaked and is itself exactly at `A`. This makes `wp == A` observationally indistinguishable from ordinary `wp == current target`.

At `t95`, while target remains cloaked, both Mites have `wp == self`; at `t96` both are `mission=0`, `mission1target=0`, `warp=0`.

This is the only clean clear pattern that bypasses observable fallback flight to `A`. It is consistent with immediate loss of navigation lock when cloak occurs while the target coincides with the fallback coordinate.

## Implementation boundary

The empirical study is complete enough to stop diagnostic iteration and move back to simulator / dataset work.

Safe implementation facts for a future Horwasp-specific ruleset module:

1. Numeric ship id must never be used as lifecycle identity by itself.
2. A new observable Red Mite tracking identity begins at `S`; clean starts initialize visible waypoint to the current target position.
3. Visible cloak is the dominant observed target-lock termination trigger.
4. Loss of 150-ly Horwasp scan coverage and documented pursuit lifetime must remain explicit rule branches because they are documented even though they are sparse in this clean-clear subset.
5. Ordinary lost-lock behavior uses `target.xy(S-1)` as a fallback destination and continues physical warp movement toward it after `mission1target` clears.
6. Arrival at the fallback destination normally changes waypoint to self and then `warp` to `0` on the next snapshot.
7. `mission=0, mission1target=0` must not be interpreted as immediate physical destruction.
8. Target `380` demonstrates a self-waypoint / immediate-stop lost-lock variant.
9. Target `206` must stay represented as an unresolved trigger; do not invent a generic planet, damage, transfer or cloak rule from this single event.
10. Target `329` must stay represented as an exact-contact termination edge case rather than being silently promoted to a successful documented interception.

The engine should not yet encode the unresolved `206` trigger or the exact success semantics of `329`. The corpus fixture/tests preserve these observations for later implementation work.

## Regression evidence

Compact privacy-safe golden observations are stored in:

```text
tests/fixtures/red_mite_game_591478.json
```

and exercised by:

```text
tests/test_red_mite_empirical_model.py
```

The full raw archive remains local and gitignored.

Key diagnostic scripts used to reconstruct this rule include:

- `tools/diagnostics/mite_identity_boundary_audit.py`
- `tools/diagnostics/mite_tracking_anchor_audit.py`
- `tools/diagnostics/mite_loss_anchor_transition_audit.py`
- `tools/diagnostics/mite_uncloaked_loss_control_audit.py`
- `tools/diagnostics/mite_deth_specula_raw_transition_audit.py`
- `tools/diagnostics/mite_official_mechanics_corpus_audit.py`
- `tools/diagnostics/mite_clear_poststate_lifecycle_audit.py`
- `tools/diagnostics/mite_clear_fallback_navigation_audit.py`
