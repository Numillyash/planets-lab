# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is a compact pointer; use the dated handoffs for full evidence.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Direct isolated standard classification: 413/413 right-higher after documented special branches are removed.
- Factual isolated C&I attacker: 7/7 right.
- Ordinary linked normal-PIA population: 37/37 before regular ship combat and 37/37 with PIA attacker on right.

## Read these checkpoints first

- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-factual-queue-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-repeated-pair-side-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-candidate-set-pending.md`

## Closed special residuals

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Case1 is `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for pair/pre-standard attribution; reciprocal-specific universal side remains unpromoted from one row.

Case2 is the Standard-game Evil-Empire Gorbie Galactic Power forced-left exception. Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either former residual.

## Matching Friendly Code / HWM — bounded

Positive runtime found 55 factual same-FC ship battles; all 54 ordinary rows plus the one `591478` row are documented MKT/LFM exceptions. NTP is unobserved. No ordinary HWM factual candidate exists. Strict suppression controls produced no clean negative-control population.

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

Dynamic diplomacy, HWM/C&I enablement, C&I hull/active-cloak state, Intercept Interference and Galactic Power remain explicit tri-state inputs.

## Factual-positive queue differential — runtime complete

Runtime source:

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

Exact-target normal PIA binding is runtime validated: Priority Intercept is bound to the actual `mission1target`, not merely another ship of the same owner. The older 37-row linked-PIA audit has a different scope and is not reopened absent contradiction.

## Repeated-pair side history — closed

Population runtime source:

```text
692bde1fb4aad4b8e50801253a2294c01a0206ba
```

Across all 11 ordinary archives the entire repeated same-pair ship population is exactly two groups / four VCRs:

```text
repeated_pair_groups=2
occurrence_count={'2': 2}
max_occurrences=2
plain_static_comparable_groups=2
plain_static_first_right_exact=2
plain_static_second_reversed_exact=2
plain_static_two_pass_exact=2
```

They are the former two factual-queue side residuals. In both, first RIGHT is the static higher-priority ship and second RIGHT is the opposite ship. `standard_battle_priority_key(...)` therefore remains unchanged.

```text
maximum two fights / dynamic stack order: DOCUMENTED
repeated-pair factual population:           CORPUS_OBSERVED
second-pass side reversal:                  CORPUS_OBSERVED + DIFF_VERIFIED
exact reversal as primary documentation:    NOT PROMOTED
```

### Canonical queue primitive — TESTED

```text
src/planets_lab/rules/combat/queue.py
tests/test_combat_queue.py
standard_pair_sides_for_occurrence(...)
```

Implementation runtime source:

```text
de824ab4ecc0bc8cd32784ce4d3df9021eddd71b
```

Artifact:

```text
artifacts/combat-c5-queue-primitive-20260909-221345
```

Result:

```text
QUEUE PRIMITIVE TESTS
.................................................................... [100%]
tests rc=0
```

The helper is `TESTED`. It maps an already-selected ordinary STANDARD pair onto occurrence 1/2 sides; occurrence >2 fails closed. It does not decide whether a second combat occurs. PIA/C&I/Galactic Power/capture/target selection remain outside it.

## Immediate gate — candidate-set differential

Committed:

```text
tools/diagnostics/combat_host_candidate_set_audit.py
tests/test_combat_host_candidate_set_audit.py
```

Detailed boundary:

```text
docs/handoff/2026-09-09-combat-c5-candidate-set-pending.md
```

This v1 gate is intentionally **site-conditioned and movement-conservative**, not full post-movement reconstruction.

- factual VCRs supply site coordinates and the held-out comparison pair set only;
- candidate ship membership comes from owner-current `T-1`;
- only intrinsically stationary Warp-0/no-Tow/no-Intercept/no-C&I/no-HYP/no-obvious-Tow-target/no-obvious-Chunnel-source ships enter the v1 position-proven set;
- zero/missing `T-1` fuel stays unresolved rather than becoming a hard blocker;
- strict diplomacy is owner-aligned, directional, raw-signature based and leave-pair-out;
- conditional diplomacy is an upper-bound composition profile, not an independent predictor;
- `eligible_nonfactual` pairs are not queue false positives because mutable target selection is not implemented yet.

After a green runtime, the strongest contradiction is a candidate-covered factual pair classified `blocked`, especially in the conditional profile. Factual unresolved rows are coverage gaps. Do not weaken canonical rules from unresolved or movement-uncovered rows.

After this gate, expand movement-resolved stack membership and/or begin mutable target-list selection on clean fully reconstructed sites. Capture continuation and the ship-to-planet repair boundary remain later queue phases.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
