# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is intentionally a compact pointer. Detailed evidence is in dated handoffs and Git history.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Direct isolated standard classification remains 413/413 right-higher after documented special branches are removed.
- Factual isolated C&I attacker is 7/7 right.
- Ordinary linked normal-PIA pairs are 37/37 before regular ship combat and 37/37 with the PIA attacker on the right.

## Latest detailed checkpoints

Read first:

- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-factual-queue-selection-pending.md`

## Former mission-7 residuals — removed from standard tuning

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Case 1 is closed for pair/pre-standard attribution as `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; the single reciprocal-only corpus row is insufficient to promote a universal reciprocal-specific side rule.

Case 2 is closed as the Standard-game Evil-Empire Gorbie Galactic Power forced-left exception. Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either former residual.

## Matching Friendly Code / HWM — bounded

- Positive runtime: 55 factual same-FC ship battles; all 54 ordinary rows plus the one `591478` row are documented MKT/LFM exceptions.
- NTP is unobserved in the current corpus; this is coverage only.
- No ordinary HWM factual candidate exists.
- Strict suppression runtime produced no clean negative-control population.

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

User runtime on source:

```text
7ac5d70a77f592dfd1d3660c237b244e61795305
```

passed:

```text
tests/test_combat_order.py
tests/test_combat_eligibility.py
tests/test_combat_selection.py
........................................................ [100%]
tests rc=0
```

Therefore `src/planets_lab/rules/combat/selection.py` is `TESTED` at the deterministic composition boundary. Dynamic diplomacy, advantage state, active cloak and Intercept Interference remain explicit tri-state inputs.

## Factual queue differential — runtime produced first real stack result

Successful user runtime on source:

```text
104332ee9d93c5de83bea613282b4c9a2d9cd863
```

reported:

```text
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
payload_conflicts=0

conditional:
  engagement True=1968
  phase standard=1904, priority_intercept=48, unresolved=16
  side exact=1944, unresolved=19, mismatch=5

strict:
  engagement True=1949, unresolved=19
  phase standard=1885, priority_intercept=48, unresolved=35
  side exact=1925, unresolved=38, mismatch=5

strict fully_resolved_prefix_exact=1183/1183
conditional fully_resolved_prefix_exact=1202/1202
known phase-prefix violations=0
```

Case1 remains reciprocal PIA with side intentionally unresolved. Case2 remains exact Galactic Power forced-left.

### Canonical normal-PIA pair-binding fix

Three of the five side mismatches were false PIA classifications:

```text
622476/T25/VCR87: ship40 intercept target15, factual opponent72
622476/T26/VCR93: ship65 intercept target27, factual opponent54
622476/T28/VCR110: ship45 intercept target35, factual opponent42
```

`_normal_pia_candidate(...)` now requires the considered opponent ship to equal the interceptor's actual `mission1target`. A mission-7 ship may later fight another hostile ship of the same faction in standard combat, but that pair is not the Priority Intercept pair.

Regression added:

```text
test_normal_pia_does_not_apply_to_other_ship_of_same_target_owner
```

This new code is committed but **not yet user-runtime-validated**.

### Remaining two side residuals — queue history gate

```text
620917/T7/VCR6
621896/T25/VCR52
```

Do not change `standard_battle_priority_key(...)` from these rows yet. Primary documentation notes dynamic shifts in complex stacked combat, and classic Host documentation identifies repeated same-pair combat after timeout as a side/initiator exception to the static battle-value rule.

Targeted diagnostic committed:

```text
tools/diagnostics/combat_host_factual_queue_side_residual_audit.py
tests/test_combat_host_factual_queue_side_residual_audit.py
```

It reports full same-site ship-VCR queues, same-pair occurrence indices and T-1 standard priority inputs for only these two residuals.

## Immediate gate

1. rerun the main factual queue audit after the exact-target PIA fix;
2. run the two-row side-residual queue-history audit;
3. verify the expected first-order change: normal PIA `47 -> 44`, standard `+3`, side mismatches `5 -> <=2`;
4. if remaining mismatches are repeated-pair/history-dependent, keep static pair-side rules unchanged and move that state into the future mutable queue layer;
5. only after the factual queue gate is understood, design candidate-set prediction from reconstructed post-movement stacks.

Do not implement mutable target selection yet. Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
