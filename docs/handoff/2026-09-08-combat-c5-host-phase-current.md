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
- Ordinary linked Priority Intercept pairs are 37/37 before regular ship combat and 37/37 with the PIA attacker on the right.
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

The Gorbie corpus gate found 48 Evil-Empire-owned Gorbie appearances, with 7 rows where factual LEFT actually requires overriding standard priority. The target is one of those seven.

Corrected public Planets.nu `loadinfo` resolves game `621896` as:

```text
New Boston Sector
shortdescription: Standard Beginners
iscustom: false
campaignmode: false
race8 player: id 5
```

Primary Planets.nu documentation explicitly lists Galactic Power as enabled for Beginner/Standard and disabled for Classic; the dedicated advantage page states that an Evil-Empire-owned Gorbie is forced to the left when the advantage is active.

Therefore the target is now closed as the documented Galactic Power forced-left exception:

```text
Galactic Power:                          DOCUMENTED
Case2 race8/hull70/factual LEFT:         CORPUS_OBSERVED
fail-closed primitive:                   TESTED
Case2 Galactic Power attribution:        DIFF_VERIFIED
```

Do not change Intercept semantics, FC parsing, diplomacy, or standard priority to fit this row.

`galactic_power_forces_left(...)` remains tri-state/fail-closed. Do not simplify `race8 + hull70` to enabled: Classic and Campaign/custom contexts differ, and effective game-type/advantage state belongs in the future settings layer.

## Case 1 — CURRENT GATE: 511506 / T19 / VCR13

This is not a clean two-ship physical stack. T/T-1 context shows Firecloud80 plus Meteors29/89/102 and ship73 at or converging on the battle location. Only ship89 vs Firecloud80 appears in the factual VCR.

Known context:

- Firecloud80: owner6, hull56, mission3 Kill, PE5, FC027, already at battle coordinate;
- Meteor89: owner5, hull46, mission7 target80, FC2eC, T-1 cloak true;
- Meteor29: owner5, hull46, mission1 target80, FCypg, same origin as 89, T-1 cloak true;
- Meteor102: owner5, hull46, mission1, FCroo, same origin, T-1 cloak true;
- ship73: owner6 hull17, already at battle location, unarmed.

The next task is dynamic engagement eligibility / opponent selection / cloak-state reconstruction. Do not put Case 1 back into pairwise standard-side tuning.

## Next order

1. reconstruct Case 1 dynamic multi-ship eligibility / target selection / cloak-state behavior;
2. resolve matching-FC / Harmonic Weapon Modulation boundaries;
3. integrate dynamic PIA/C&I pair selection;
4. handle capture/reinsertion and ownership changes;
5. place between-phase repair before ship-vs-planet combat;
6. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
