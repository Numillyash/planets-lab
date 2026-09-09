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
- Direct isolated standard classification remains 413/413 right-higher after removing documented special branches.
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
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`

## Former Case 2 — CLOSED: 621896 / T28 / VCR67

Matched controls reject a universal non-cloakable Intercept side rule: 40/41 structurally matched rows follow canonical standard right-higher ordering; the sole residual is the exact Evil Empire Gorbie/T-Rex target.

Corrected public Planets.nu `loadinfo` resolves game `621896` as `Standard Beginners`. Primary Planets.nu documentation enables Galactic Power for Standard and states that an Evil-Empire-owned Gorbie fights from the left. The target is race8 / hull70 / factual LEFT and is one of seven corpus rows where forced-left actually overrides canonical standard priority.

Scoped status:

```text
Galactic Power:                          DOCUMENTED
Case2 race8/hull70/factual LEFT:         CORPUS_OBSERVED
fail-closed primitive:                   TESTED
Case2 Galactic Power attribution:        DIFF_VERIFIED
```

`galactic_power_forces_left(...)` remains tri-state/fail-closed. Never infer enablement from race8+hull70 alone because Classic and Campaign/custom contexts differ.

## Former Case 1 — pair/phase CLOSED: 511506 / T19 / VCR13

Physical-stack runtime proved this is not a two-ship stack. T/T-1 context contains Firecloud80, Meteors29/89/102 and ship73, but the only factual VCR is:

```text
LEFT  Firecloud80 owner6 hull56
      mission3 Kill / PE5 / FC027

RIGHT Meteor89 owner5 hull46
      cloak-capable / mission7 target80 / PE0 / FC2eC
```

Primary Planets.nu Priority Intercept documentation contains a reciprocal pre-standard branch: if the intercepted target would itself combat the intercepting ship, that combat also occurs before other combats at the location.

Case1 matches exactly:

```text
Meteor89: cloak-capable + mission7 + target80
Meteor89 PE=0 -> normal PE-matching PIA signature is false
Firecloud80: Kill + PE5 -> requests combat with owner5 Meteor89
```

User runtime on source `1576dd083b2691464b98e3260d7c6474fb2ed339` passed targeted regressions and the reciprocal audit:

```text
tests rc=0
audit rc=0
payload_conflicts=0
candidate_rows=1
target_case_rows=1
interceptor_side: right=1
standard_relation: left_higher_priority=1
target_aggression_shape: kill_and_pe=1
site_first_ship_vcr: True=1
multi_vcr_site_rows=0
```

Thus the sole old Case1 standard-side contradiction is the sole ordinary reciprocal-only candidate. The Intercept relation explains why ship89 is paired with Firecloud80 despite the larger physical stack.

Scoped status:

```text
reciprocal Priority Intercept text:                DOCUMENTED
Case1 stacked context / factual pair:              CORPUS_OBSERVED
priority_intercept_reciprocal_target_signature:   TESTED
Case1 reciprocal pair/pre-standard attribution:   DIFF_VERIFIED
```

Important boundary: `candidate_rows=1` gives no independent population control. Do **not** promote `reciprocal interceptor always RIGHT`, reverse-ID ordering, or multi-VCR queue semantics as universal diff-verified rules from this gate alone. The factual Case1 side is CORPUS_OBSERVED and is consistent with the documented general aggressor/right principle, but the reciprocal-specific side rule remains un-generalized.

## Consequence for former mission-7 residuals

Both former `left_higher_priority` rows are removed from standard battle-priority tuning for different documented reasons:

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either row.

## Immediate gate — matching Friendly Codes / Harmonic Weapon Modulation

Next reconstruct the matching-FC suppression boundary separately from battle priority:

1. identify ordinary co-located hostile pairs whose FCs match and therefore suppress combat;
2. identify documented exceptions / special FCs and Harmonic Weapon Modulation cases;
3. separate game/race advantage enablement from raw matching-FC equality;
4. only then integrate matching-FC eligibility with normal PIA, reciprocal Priority Intercept and Bird C&I dynamic pair selection.

Do not use absence of a VCR as proof of matching-FC suppression until physical co-location, hostility, fuel, diplomacy and other blockers are controlled.

## Next order

1. resolve matching-FC / Harmonic Weapon Modulation boundaries;
2. integrate normal PIA, reciprocal Intercept and C&I into one dynamic pair-selection layer;
3. handle capture/reinsertion and ownership changes;
4. place between-phase repair before ship-vs-planet combat;
5. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
