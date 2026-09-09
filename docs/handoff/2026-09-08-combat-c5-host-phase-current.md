# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is intentionally a compact pointer. Detailed evidence is in dated handoffs and Git history.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Direct isolated standard classification: 413/413 right-higher after documented special branches are removed.
- Factual isolated C&I attacker: 7/7 right.
- Ordinary linked normal-PIA population: 37/37 before regular ship combat and 37/37 with PIA attacker on right.

## Read these current checkpoints first

- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-factual-queue-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-repeated-pair-side-pending.md`

## Former mission-7 residuals — closed

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Case1 is `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for pair/pre-standard attribution; reciprocal-specific universal side remains unpromoted from one row.

Case2 is closed as the Standard-game Evil-Empire Gorbie Galactic Power forced-left exception. Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either former residual.

## Matching Friendly Code / HWM — bounded

Positive runtime found 55 factual same-FC ship battles. All 54 ordinary rows plus the one `591478` row are documented MKT/LFM exceptions. NTP is unobserved. No ordinary HWM factual candidate exists. Strict suppression controls produced no clean negative-control population.

Evidence status:

```text
matching-FC suppression text:                DOCUMENTED
MKT/NTP/LFM exception text:                  DOCUMENTED
matching-FC/HWM eligibility primitives:      TESTED
54/54 ordinary factual rows MKT/LFM:         CORPUS_OBSERVED
ordinary exact matching-FC suppression:      DOCUMENTED + TESTED
historical suppression differential:         NOT AVAILABLE IN CURRENT CORPUS
```

Do not reopen this gate merely to relax controls.

## Unified pair-level selection — TESTED

Runtime source:

```text
7ac5d70a77f592dfd1d3660c237b244e61795305
```

Canonical layer:

```text
src/planets_lab/rules/combat/selection.py
```

Order + eligibility + pair-selection regressions passed together. Dynamic diplomacy, HWM/C&I enablement, C&I hull/active-cloak state, Intercept Interference and Galactic Power remain explicit tri-state inputs.

## Factual-positive queue differential — runtime complete

Successful runtime source:

```text
31509d2c9e9f4af89f80e5088597452d40f393c1
```

Artifact:

```text
artifacts/combat-c5-factual-queue-selection-20260909-212420
```

Result:

```text
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
payload_conflicts=0

conditional:
  engagement True=1968
  phase standard=1915, priority_intercept=37, unresolved=16
  normal PIA=36, reciprocal PIA=1
  side exact=1947, unresolved=19, mismatch=2

strict:
  engagement True=1949, unresolved=19
  phase standard=1895, priority_intercept=37, unresolved=36
  normal PIA=36, reciprocal PIA=1
  side exact=1927, unresolved=39, mismatch=2

strict fully_resolved_prefix_exact=1182/1182
conditional fully_resolved_prefix_exact=1202/1202
known phase-prefix violations=0
```

Case1 remains reciprocal PIA with side deliberately unresolved. Case2 remains exact under Galactic Power forced-left.

### Exact-target PIA binding — runtime validated

`_normal_pia_candidate(...)` requires the considered opponent ship to equal the interceptor's actual `mission1target`. This removed the three false PIA side mismatches where mission7 targeted another ship of the same owner.

The audit-specific normal-PIA count changed `47 -> 36`, larger than the initial estimate. Do not restore owner-only binding: primary semantics bind Priority Intercept to the actual Intercept target. The older 37-row linked-PIA audit has a different scope and is not reopened absent a direct contradiction.

Evidence status:

```text
exact PIA target binding text: DOCUMENTED
canonical pair binding:        TESTED
factual correction:             DIFF_VERIFIED
```

## Remaining side residuals — repeated-pair second passes

Only two resolved side mismatches remain:

```text
620917/T7/VCR6
621896/T25/VCR52
```

Targeted queue-history runtime proved both are the **second occurrence of the same pair** in one battle-turn/location:

```text
620917/T7:
  VCR5  LEFT14 RIGHT13
  VCR6  LEFT13 RIGHT14
  same pair (13,14), occurrence 2/2

621896/T25:
  VCR49 LEFT67 RIGHT34
  VCR52 LEFT34 RIGHT67
  same pair (34,67), occurrence 2/2
```

In both cases the first VCR places the static higher-priority ship on RIGHT; the second VCR reverses the same pair. Therefore **do not change `standard_battle_priority_key(...)`**. These rows are mutable queue-history observations, not static pair-priority contradictions.

Primary Planets.nu documentation establishes dynamic stacked order and a maximum of two combats per pair. Exact second-pass side reversal is corroborated by classic secondary documentation but is not yet labeled primary `DOCUMENTED`.

## Immediate gate — repeated-pair population

Committed, pending user runtime:

```text
tools/diagnostics/combat_host_repeated_pair_side_population_audit.py
tests/test_combat_host_repeated_pair_side_population_audit.py
```

The population tool now counts/skips invalid factual owner IDs instead of allowing an incomplete VCR to abort the pass.

See:

```text
docs/handoff/2026-09-09-combat-c5-repeated-pair-side-pending.md
```

The gate checks all ordinary repeated ship pairs for:

- documented maximum of two combats;
- stable-owner vs capture/ownership-change groups;
- side flip across exactly-two stable-owner pairs;
- conservative plain-static two-pass pattern: first RIGHT = static higher priority, second RIGHT = opposite ship;
- whether the two former residuals are ordinary members of the wider population.

Promote a reusable repeated-pair queue-side helper only after this population runtime is clean. Then proceed to candidate-set prediction from reconstructed post-movement stacks before implementing the full mutable target queue.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
