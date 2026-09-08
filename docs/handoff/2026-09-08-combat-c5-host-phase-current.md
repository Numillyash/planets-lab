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

### Former residual Case 1 — 511506 / T19 / VCR13

Not a clean two-ship physical stack. Additional owner5 Meteors and an owner6 ship survive at the battle coordinate. This row is removed from pairwise standard-side tuning and belongs to dynamic multi-ship eligibility / target selection / cloak-state reconstruction.

### Former residual Case 2 — 621896 / T28 / VCR67

Matched controls reject a universal non-cloakable Intercept side rule:

```text
41 matched rows
40 standard right-higher
 1 left-higher residual = exact Gorbie/T-Rex target
```

Primary Planets.nu documentation identifies **Galactic Power** as a forced-left mechanic for an Evil-Empire-owned Gorbie when that advantage is active. The target is race8 / hull70 / factual LEFT and is one of the rows where a forced-left override is actually needed.

However, the completed Gorbie corpus runtime on source `c88ade4604b3afd88b095af6ec1ec34a819ae933` shows mixed effective context:

```text
52 Gorbie appearances
48 Evil-Empire-owned
 4 non-Empire

Empire Gorbie factual side:
  right: 29
  left:  19

standard relation among Empire Gorbies:
  right_higher_priority: 41
  left_higher_priority:   7

forced-left override required:
  False: 41
  True:   7
```

All targeted tests passed (`27 passed`), audit rc=0, payload conflicts=0.

The 29 factual-right Empire Gorbies prove that `race8 + hull70` cannot imply Galactic Power enablement. The corpus mixes Standard/Classic/Campaign/Custom or otherwise enabled/disabled advantage contexts. Prepared/archive metadata exposed no usable game context or `activeadvantages` for these rows.

Target Case2 remains a strong Galactic-Power attribution candidate but is **not closed** until game `621896` configuration proves the advantage effective.

## Canonical Galactic Power primitive

`src/planets_lab/rules/combat/order.py` contains a fail-closed `galactic_power_forces_left(...)` primitive plus race/hull constants.

For the relevant race/hull it requires explicit effective `galactic_power_enabled` state:

- enabled -> `True`;
- disabled -> `False`;
- unknown -> `None`.

Race8+hull70 alone is never silently treated as enabled. The primitive is now `TESTED`; Galactic Power is not yet `DIFF_VERIFIED` against a resolved enabled-state historical row.

## Immediate gate — public game configuration

Use public Planets.nu `/game/loadinfo` for exactly the six ordinary games containing Empire Gorbie VCRs:

```text
360690
511506
620694
621253
621896
680435
```

Capture at minimum:

```text
game.id
game.name
game.shortdescription
game.gametype
game.maptype
game.iscustom
game.scenarioid
settings.campaignmode
settings.maxadvantage
race8 player id
race8 player activeadvantages
```

The decisive target is game `621896`. Do not infer Standard from `campaignmode=false` alone because Classic and Standard share broad API game-type buckets.

## Next order

1. resolve public game/advantage context and close or reject Galactic Power attribution for Case2;
2. move Case1 into dynamic multi-ship opponent selection / cloak eligibility;
3. resolve matching-FC / Harmonic Weapon Modulation boundaries;
4. integrate PIA/C&I pair selection;
5. handle capture/reinsertion and ownership changes;
6. place between-phase repair before ship-vs-planet combat;
7. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
