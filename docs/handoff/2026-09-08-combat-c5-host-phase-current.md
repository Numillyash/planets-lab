# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is intentionally a compact pointer. Detailed evidence is in dated handoffs and Git history.

## Current objective

Reconstruct the NuHost combat phase that generates VCR engagements, queue order and left/right sides. Facts, inferred semantics and simulator rules remain separate; unknown branches fail closed.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Standard battle priority uses documented `001..999`; exact signed three-character FCs are a separate `CORPUS_OBSERVED + DIFF_VERIFIED` extension.
- Direct isolated standard classification remains 413/413 right-higher after C&I reclassification.
- Factual isolated C&I attacker is 7/7 right.
- Ordinary linked normal-PIA pairs are 37/37 before regular ship combat and 37/37 with the PIA attacker on the right.
- Directed T-1 diplomacy was symmetric for both former mission-7 residuals.

## Latest completed gates

Read first:

- `docs/handoff/2026-09-09-combat-c5-source-context-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-physical-stack-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-mission7-controls-galactic-power.md`
- `docs/handoff/2026-09-09-combat-c5-galactic-power-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`

## Case 2 — CLOSED: 621896 / T28 / VCR67

Matched controls reject a universal non-cloakable Intercept side rule: 40/41 structurally matched rows follow canonical standard right-higher ordering; the sole residual is the exact Evil Empire Gorbie/T-Rex target.

Corrected public Planets.nu `loadinfo` resolves game `621896` as `Standard Beginners`. Primary Planets.nu game-type documentation explicitly enables Galactic Power for Beginner/Standard and disables it for Classic. The target is race8 / hull70 / factual LEFT and is one of seven corpus rows where a forced-left override is actually required relative to canonical standard priority.

Scoped evidence status:

```text
Galactic Power:                          DOCUMENTED
Case2 race8/hull70/factual LEFT:         CORPUS_OBSERVED
fail-closed primitive:                   TESTED
Case2 Galactic Power attribution:        DIFF_VERIFIED
```

Do not change Intercept semantics, FC parsing, diplomacy, or standard priority to fit this row. `galactic_power_forces_left(...)` remains tri-state/fail-closed because Classic and Campaign/custom contexts differ.

## Case 1 — CURRENT GATE: 511506 / T19 / VCR13

This is not a clean two-ship physical stack. T/T-1 context shows Firecloud80 plus Meteors29/89/102 and ship73 at or converging on the battle location. Only Firecloud80 vs Meteor89 appears in the factual VCR, with Firecloud on the LEFT and Meteor89 on the RIGHT.

Known context:

- Firecloud80: owner6, hull56, mission3 Kill, PE5, FC027, already at battle coordinate;
- Meteor89: owner5, hull46, cloak-capable, mission7 target80, PE0, FC2eC;
- Meteor29: owner5, hull46, mission1 target80, PE0, FCypg, same origin as 89;
- Meteor102: owner5, hull46, mission1, PE0, FCroo, same origin;
- ship73: owner6 hull17, already at battle location, unarmed.

### Newly identified documented branch — reciprocal Priority Intercept

Primary Planets.nu Priority Intercept documentation contains a second pre-standard branch in addition to a normal interceptor-initiated PIA: **if the intercepted target would combat the intercepting starship, that combat also occurs before other combats at the location**.

This fits Case 1 structurally:

```text
Meteor89: cloak-capable + mission7 + target80
Meteor89 PE: 0 -> does NOT satisfy normal PIA-attacker signature
Firecloud80: Kill + PE5 -> would combat owner5 Meteor89
factual pair: Firecloud80 LEFT / Meteor89 RIGHT
```

Therefore Case 1 may not require an unknown ordinary target selector at all. The Intercept relation uniquely binds ship89 to ship80 in the documented reciprocal pre-standard branch; ships29/102 are not Intercept-linked to Firecloud80 even though they are physically present.

Canonical `priority_intercept_order_signature(...)` remains unchanged and still models the normal interceptor-initiated PE-matching branch. A separate fail-closed `priority_intercept_reciprocal_target_signature(...)` primitive has been added for the target-initiated branch.

Prepared but **not yet user-runtime-validated**:

```text
tools/diagnostics/combat_host_priority_intercept_reciprocal_audit.py
tests/test_combat_host_priority_intercept_reciprocal_audit.py
new reciprocal tests in tests/test_combat_order.py
```

The audit selects ordinary factual ship-vs-ship pairs where:

1. a cloak-capable ship is mission7 and targets the factual opponent;
2. that interceptor does **not** satisfy the normal PIA PE signature;
3. the intercepted target has Kill!/PE orders requesting combat with the interceptor;
4. the factual pair exists and FCs are supported/nonmatching.

It reports interceptor side, site queue position, standard relation, target hostility shape and target Case1. Population counts remain unknown until runtime.

## Immediate gate

Run only the reciprocal Priority Intercept targeted tests and audit. Do not rerun source-context, physical-stack, diplomacy, matched-control or Galactic-Power audits.

If the population confirms reciprocal-only pairs consistently occur pre-standard with the interceptor on the right, close Case 1 under that documented branch. If not, retain the documented pre-standard pairing but isolate side/queue exceptions before changing mechanics.

## Next order

1. close the reciprocal Priority Intercept Case1 gate;
2. resolve matching-FC / Harmonic Weapon Modulation boundaries;
3. integrate normal PIA, reciprocal intercept and C&I into one dynamic pair-selection layer;
4. handle capture/reinsertion and ownership changes;
5. place between-phase repair before ship-vs-planet combat;
6. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
