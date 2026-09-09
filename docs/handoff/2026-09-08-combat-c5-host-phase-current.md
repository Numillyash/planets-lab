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
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`

## Former mission-7 residuals — removed from standard tuning

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Case 1 is the sole ordinary reciprocal-only candidate. The documented reciprocal branch explains the Firecloud80/Meteor89 pairing inside the larger physical stack. Scoped pair/pre-standard attribution is `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; one candidate is insufficient to promote a universal reciprocal-interceptor side or multi-VCR ordering rule.

Case 2 is closed as the Standard-game Evil-Empire Gorbie Galactic Power forced-left exception. Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either former residual.

## Matching Friendly Code / HWM — current boundary

Primary Planets.nu documentation states that exact case-sensitive matching ship Friendly Codes normally suppress ship-vs-ship combat, with `MKT`, `NTP`, and `LFM` as documented exceptions. Bird Harmonic Weapon Modulation can override matching-FC suppression when effectively enabled; race alone does not establish Campaign advantage state.

Positive factual runtime on source `ff66d4b8d268205adb8b0d096b12be4fee57df90`:

```text
tests rc=0
audit rc=0
payload_conflicts=0
matching_fc_vcr_rows=55
ordinary rows=54
ordinary documented_ship_exception=54
ordinary FCs: lfm=32, mkt=22
special 591478: mkt=1
hwm_candidate_rows=0
hwm_unshielded_first_site_rows=0
```

Thus every factual same-FC ship battle in the current corpus is a documented MKT/LFM exception. NTP has no historical example in the current corpus; this is a coverage gap only. No ordinary HWM candidate exists.

Strict suppression runtime on source `8bef008342c8760e6f33d450335f1b3fb95443bf`:

```text
tests rc=0
audit rc=0
payload_conflicts=0
stationary_colocated_pairs=199341
different_owner_pairs=21307
ordinary_exact_matching_fc_pairs=11
hostile_order_pairs=1
resolved_nonbird_pairs=1
known_noncloaking_pairs=0
strict_directed_relation_pair_vcr_absent_rows=0
strict_isolated_no_ship_vcr_rows=0
same_turn_directed_relation_rows=0
same_turn_directed_relation_isolated_rows=0
```

The clean suppression-control population is therefore empty. Do not relax the controls merely to manufacture `DIFF_VERIFIED`: the sole hostile ordinary matching-FC near-candidate is already confounded before the known-noncloaking gate.

Evidence status:

```text
matching-FC suppression text:                DOCUMENTED
MKT/NTP/LFM exception text:                  DOCUMENTED
matching-FC/HWM eligibility primitives:      TESTED
55 factual same-FC VCR rows:                 CORPUS_OBSERVED
54/54 ordinary factual rows MKT/LFM:         CORPUS_OBSERVED
ordinary HWM factual support:                NOT PRESENT IN CURRENT CORPUS
ordinary exact matching-FC suppression:      DOCUMENTED + TESTED
historical suppression differential:         NOT AVAILABLE IN CURRENT CORPUS
```

Close this research gate absent contradictory future end-to-end evidence or new historical data.

## Immediate gate — unified dynamic ship pair-selection layer

Integrate the bounded primitives without inventing unresolved Host state. The next canonical layer should expose pair-level decisions separately from the pairwise combat resolver:

1. base ship-combat request / dynamic eligibility inputs;
2. matching-FC blocker and HWM override;
3. normal Priority Intercept;
4. reciprocal Priority Intercept;
5. Bird Cloak-and-Intercept;
6. standard battle priority;
7. Galactic Power forced-left side override;
8. Intercept Interference, diplomacy/Safe Passage and unknown advantage state as explicit fail-closed inputs rather than guessed semantics.

Prefer a small deterministic decision object (eligibility / phase / side-order hints / unresolved reason) over a monolithic Host function. First tests should cover composition of already established primitives and unknown-state propagation. Historical stack-level queue differential comes after the pair-level API is stable.

## Next order

1. implement/test the unified pair-level decision layer;
2. build a stack-level factual queue audit against normal PIA, reciprocal PIA, C&I and standard priority;
3. handle capture/reinsertion and ownership changes;
4. place between-phase repair before ship-vs-planet combat;
5. integrate planet/base participation using C4 persistence;
6. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
