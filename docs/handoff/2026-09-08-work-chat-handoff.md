# Work chat handoff checkpoint — 2026-09-08

GitHub `Numillyash/planets-lab` branch `main` is the only source of truth.

This file is a concise entry point for a fresh ChatGPT Work chat. The detailed finite-fuel reconstruction state is in:

```text
docs/handoff/2026-09-08-intel-fuel-chat-handoff.md
```

## Source checkpoint before this handoff commit

Actual GitHub `main` HEAD immediately before creating this file:

```text
1a01339f4f3efa77db14270e55c51795a431b73a
docs: record partial fuel implementation candidate
```

The latest implementation/test checkpoint is:

```text
d002858e3eb2fe06a0f2c1876f14cfdaa3cd3ea1
tests: lock partial fuel nominal basis anchors
```

Its implementation parent is:

```text
993e76046c3ffaa40acf4b0aa7286d5bd9573480
sim: use nominal leg for partial fuel cost
```

GitHub Actions `tests` run `34237920543` for `d002858e` completed successfully.

Always verify the actual `main` HEAD again at the start of the new chat; do not trust these SHA values blindly.

## What changed

`src/planets_lab/sim/normal_movement.py` now contains a lab-only candidate for geometrically partial normal movement:

- integer movement endpoint is still produced by the verified Host major/minor-axis projection;
- fuel requirement for a geometrically partial route is based on the continuous effective one-turn leg, not the distance to the already-rasterized integer endpoint;
- if available fuel is below that requirement and expanded/proration mode is enabled, the continuous one-turn leg is prorated by fuel ratio and then projected to integer coordinates;
- the candidate is shared by Move Most, Intercept and Tow through `plan_full_normal_move()`; Tow still supplies combined movement mass through `movement_mass_override`.

Regression anchors were added for the two independent 40-vs-41 / 71-vs-72 discriminators corresponding to:

```text
360690 / T164 / ship41   Move Most
620694 / T73  / ship278  Intercept
```

## Evidence state

Strong Move Most anchor `360690/T164/ship41`:

```text
projected-distance cost = 40
continuous-nominal cost = 41
snapshot fuel = 11
after fuel = 0
factual endpoint = (1959,2969)
```

A phase-fuel scan from 0 through 5000 KT, recomputing movement mass for every candidate phase fuel, found:

```text
projected_exact_phase_fuel_ranges=()
nominal_exact_phase_fuel_ranges=((11,11),)
projected_exact_post_fuel_ranges=()
nominal_exact_post_fuel_ranges=((0,0),)
```

Known factual mine/storm/damage/Tow/Chunnel confounders were empty for this case.

Independent Intercept anchor `620694/T73/ship278` gives the complementary 71-vs-72 discriminator:

```text
29/71 -> (2741,2069)  not factual
29/72 -> (2742,2070)  factual
```

No observed discriminator supports the rasterized endpoint distance as the fuel-cost basis.

## Important boundary

The candidate has passed the repository unit-test suite in GitHub CI, but the post-change server historical differential gate has NOT yet been run.

Do not promote the rule into `Numillyash/planets-intel` production inference yet.

Do not update rule documentation to claim final differential verification until the historical runtime gate remains coherent.

Tow deserves an explicit evidence check before calling the primitive globally verified across all three callers; sharing the planner is architecturally clean but is not itself empirical proof of Tow semantics.

## Immediate continuation in Work

Start by reading, in full:

1. `docs/handoff/2026-09-08-work-chat-handoff.md`
2. `docs/handoff/2026-09-08-intel-fuel-chat-handoff.md`
3. `docs/handoff/2026-09-05-new-chat-context.md`
4. `docs/ROADMAP.md`
5. `docs/COMPILED_CORPUS.md`
6. `docs/ARCHITECTURE.md`
7. `docs/WORKFLOW.md`

Then verify the actual GitHub `main` HEAD and inspect the implementation/test commits rather than reconstructing state from previous chat text.

The next technical gate is server historical validation on `/opt/planets-lab` after updating that checkout to actual `main`:

- complete pytest suite;
- targeted `360690/T164/ship41` audit;
- corrected Move Most population audit;
- finite-fuel Intercept historical differential, especially `620694/T73/ship278` and aggregate support/contradiction counts;
- explicit review of Tow evidence before calling the common planner rule globally verified.

Do not rerun the deprecated broad `partial_move_fuel_cost_population_audit.py`; use the corrected fast Move Most audit recorded in the detailed handoff.

After successful historical validation, update durable rule/status documentation in `planets-lab`. Only then consider whether any corresponding logic should be promoted into `planets-intel`.

## Evidence discipline

Keep these invariants:

- GitHub is the source of truth;
- fact != inference != simulation;
- known zero != unknown;
- missing data != zero;
- pre-Host snapshot fuel is not automatically movement-phase fuel;
- unsupported or insufficiently reconstructed Host behavior fails closed.
