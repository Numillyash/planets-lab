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

## Latest detailed checkpoints

Read first:

- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`

## Former mission-7 residuals — removed from standard tuning

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Case 1 runtime found exactly one ordinary reciprocal-only candidate, the target itself. The documented reciprocal branch explains the Firecloud80/Meteor89 pairing inside the larger physical stack. Scoped pair/pre-standard attribution is `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; `candidate_rows=1` is insufficient to promote a universal reciprocal-interceptor side or multi-VCR ordering rule.

Case 2 is closed as the Standard-game Evil-Empire Gorbie Galactic Power forced-left exception. Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either former residual.

## Matching Friendly Code / HWM positive gate — RUNTIME COMPLETE

Primary Planets.nu documentation states that exact case-sensitive matching ship Friendly Codes normally suppress ship-vs-ship combat, with `MKT`, `NTP`, and `LFM` as documented ship-combat exceptions. Bird Harmonic Weapon Modulation can override matching-FC suppression when effectively enabled; race alone does not establish Campaign advantage state.

User runtime on source:

```text
ff66d4b8d268205adb8b0d096b12be4fee57df90
```

passed targeted tests and the positive factual VCR audit:

```text
tests rc=0
audit rc=0
payload_conflicts=0
matching_fc_vcr_rows=55
```

Ordinary scope excluding game `591478`:

```text
rows=54
matching_fc_kind:
  documented_ship_exception=54
matching_friendly_code:
  lfm=32
  mkt=22
ordinary exact-match HWM candidates=0
```

Special game `591478` contributes one additional factual same-FC `mkt` battle.

Therefore all 55 factual same-FC ship combats in the current corpus are documented MKT/LFM exceptions. No NTP example is present; this is a coverage gap, not contrary evidence. No ordinary HWM candidate is present.

Evidence status:

```text
matching-FC suppression text:                DOCUMENTED
MKT/NTP/LFM exception text:                  DOCUMENTED
matching-FC/HWM eligibility primitives:      TESTED
55 factual same-FC VCR rows:                 CORPUS_OBSERVED
54/54 ordinary rows documented exceptions:  CORPUS_OBSERVED
ordinary HWM factual support:                NOT PRESENT IN CURRENT CORPUS
ordinary matching-FC suppression:            NOT YET DIFF_VERIFIED
```

Do not infer suppression from absence of a VCR based only on this positive gate.

## Immediate gate — strict ordinary matching-FC suppression controls

Prepared, but **not yet user-runtime-validated**:

```text
tools/diagnostics/combat_host_matching_fc_suppression_audit.py
tests/test_combat_host_matching_fc_suppression_audit.py
```

The audit excludes game `591478` and searches for stationary owner-current pairs that remain at the same coordinate from T-1 to T, keep the same owners, have exact ordinary matching FC, resolved non-Bird races, known non-cloakable hulls, positive fuel before/after, are alive and armed, and have Kill!/Primary-Enemy hostility.

Diplomacy is controlled without assigning undocumented numeric relation labels. Because Safe Passage is directional, a candidate must have a unique T-1 relation signature **and at least one of its actual Kill!/PE request directions** (`low_to_high` / `high_to_low`) must already be observed as an aggression direction in factual ship combat under the same relation signature in the same game. A stronger subset requires the same directed control in the same turn.

The target differential is a strict candidate satisfying all those conditions with **no factual VCR between the pair**. The cleanest subset also requires neither ship to participate in any other ship VCR at that site.

If a non-empty clean population exists, ordinary matching-FC suppression can be promoted toward `DIFF_VERIFIED`. If the strict population is empty or diplomacy remains ambiguous, keep the rule `DOCUMENTED + TESTED` and move on rather than relaxing controls until the desired answer appears.

## Next order

1. run the strict matching-FC suppression negative-control gate;
2. integrate matching-FC eligibility with normal PIA, reciprocal Intercept and C&I in one dynamic pair-selection layer;
3. handle capture/reinsertion and ownership changes;
4. place between-phase repair before ship-vs-planet combat;
5. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
