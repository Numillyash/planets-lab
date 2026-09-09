# Finite-fuel Tow external-context follow-up — runtime result

Date: 2026-09-09

GitHub `main` is the source of truth. This handoff records the completed external-context follow-up from candidate `2c5d841fda1eef0b5d16a77c04bf2c8be90b0271`. It does **not** promote finite-fuel Tow and does not change `planets-intel`.

## Server gate

Runner:

```text
tools/run-finite-fuel-tow-external-context-gate.sh
```

Collected server log directory:

```text
logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098
```

All stages completed successfully:

```text
inputs            0 / 0
tooling           0 / 0
pytest            0 / 0
discovery-full    0 / 0
warp-well-full    0 / 0
external-context  0 / 0
summary           0 / 0
```

Full test suite:

```text
371 passed
```

The strict Tow discovery and warp-well follow-up reproduced the prior population exactly:

```text
direct phase_neither_possible             2585
geometry_warpwell_exact                   2529
phase_warpwell_both_possible              2529
phase_warpwell_nominal_only_possible         0
phase_warpwell_projected_only_possible       0
phase_warpwell_neither_possible             56
```

The cost-basis result remains non-discriminating after ordinary warp wells: the current strict historical Tow population still contains no nominal-only or projected-only candidate.

## External-context result

The exact 56 post-warp-well residuals were consumed with no identity/state loss:

```text
residual_input                               56
classified_cases                             56
identity_or_owner_state_mismatch              0
with_known_context_or_transfer_confounder     3
without_known_context_or_transfer_confounder 53
```

Attributable/currently modelled context found by the bounded audit:

```text
storm:ion_storm_drag               2
submitted_transfer_confounder      1
damage_limited_exact               0
observed_chunnel_target_route      0
storm_context_conflict             0
storm_context_invalid              0
```

No strong mine/web category was emitted for this 56-row population.

Interpretation boundaries:

- the two ion-storm rows are classified by the existing movement storm context rather than a Tow-specific rule;
- the single submitted-transfer row is a confounder only, not proof of successful execution or exact Tow-phase mass/fuel;
- `observed_chunnel_target_route=0` excludes only the deliberately narrow direct-target route checked by this diagnostic; it does **not** exclude passenger Chunnel relocation;
- zero damage-limited matches does not establish a new Tow mechanic;
- the remaining 53 rows are evidence-mining targets, not contradictions to the verified Move Most + Intercept nominal-leg rule.

## Performance note

The complete warp-well stage took about 4195 seconds. It was compute-bound rather than hung. The first game alone took roughly 2032 seconds before the first per-game result was printed. Future broad reruns should add case-level progress and avoid recomputing this stage when the preserved gate logs are sufficient for a narrower follow-up.

## Next step

Do not rerun the 2585-row warp-well envelope merely to inspect the remaining population. Reuse:

```text
logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098/external-context.log
```

First cluster the 53 rows with no known context/transfer flag by game, hull, warp, residual vector and along/cross-route geometry. Use those clusters to choose the next attributable check, with passenger Chunnel and combined Tow-plus-external-phase interactions kept separate from ordinary movement classifiers.

## Status

```text
finite-fuel Tow: OPEN
strict historical discovery: COMPLETED
ordinary warp-well follow-up: COMPLETED
external-context follow-up: COMPLETED
post-warp-well residual: 56
known context / transfer confounder: 3
clean residual for next clustering pass: 53
nominal-vs-projected Tow discriminator: NONE FOUND
planets-intel Tow transfer: BLOCKED
```
