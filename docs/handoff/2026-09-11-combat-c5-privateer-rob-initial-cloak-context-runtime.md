# C5 Host combat — Privateer Rob initial cloak-context runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Runtime source:

```text
fe9f1575b81d7ea4c922426c8f56d689dbd66ef3
```

Historical runtime:

```text
tests rc=0
audit rc=0
artifact: artifacts/combat-c5-privateer-rob-initial-cloak-context-20260911-121452/report.json
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_initial_cloak_context_audit.py
tests/test_combat_host_privateer_rob_initial_cloak_context_audit.py
```

## Population

Exactly four prior-true clean initial rows were resolved:

```text
focus_rows=4
initial_skip_target_outranks_factual=3
initial_pair_vcr=1
privateer_targets=4
mission_not_standard_cloak=4
reference_move_resolved=4
tminus1_damage_zero=4
tminus1_basic_cloak_fuel_sufficient=4
```

Clean skips:

```text
360690/T57 ship46  vs attacker146
360690/T57 ship280 vs attacker146
360690/T83 ship98  vs attacker264
```

Clean prior-true fought control:

```text
620694/T64 ship118 vs attacker134
```

## Negative attribution result

The gate does **not** find the expected documented decloak discriminator for ship118:

- all four targets have T-1 damage `0`;
- all four reference normal moves are zero-distance and consume `0 KT` fuel;
- no active Loki/Tachyon source is within 10 ly at T-1;
- no attribution-only T Loki is within 10 ly;
- ship118 has no visible foreign ship at its T-1 origin;
- ship118 therefore does **not** exhaust its 5 KT on normal movement.

Thus movement-fuel exhaustion, raw damage and Loki do not distinguish the fought control from the three skipped rows.

## Strong new corpus pattern

The three skipped targets retain stable physical identity at T and show an exact 5-KT fuel debit while remaining `iscloaked=true` and stationary:

```text
ship46:   58 -> 53  delta=-5
ship280:   9 ->  4  delta=-5
ship98:   45 -> 40  delta=-5
```

For Meteor hull mass 90, the existing ordinary-cloak reference cost is:

```text
max(5, floor(90 / 20)) = 5 KT
```

The sole clean fought prior-true control starts with exactly:

```text
ship118 fuel=5 KT
```

A hypothetical 5-KT state debit would therefore separate the observed shapes perfectly:

```text
46:  58 -> 53 > 0   skipped
280:  9 ->  4 > 0   skipped
98:  45 -> 40 > 0   skipped
118:  5 ->  0        fought control
```

## Evidence boundary

This pattern is:

```text
CORPUS_OBSERVED + INFERRED
```

It is **not promoted** as a combat rule or as `Rob Ship consumes cloak fuel`.

Reasons:

- Privateer mission9 is Rob Ship, not the documented ordinary Cloak mission;
- the existing ordinary cloak-fuel diagnostic treats mission10 as the causal Cloak mission;
- non-Cloak exact cloak-cost deltas have previously been retained only as specificity controls;
- T is post-Host state, so an exact debit still requires phase attribution before it can become predictor input.

Raw T-1 `iscloaked=true` remains rejected as a direct combat blocker. No `selection.py`, `queue.py`, Combat Priority or Friendly Code rule is changed by this runtime.

## Next gate

Run a population-level Privateer Rob cloak/fuel-state differential before adding more four-row special handling.

The next diagnostic should measure, among stable physical Privateer race5 mission9 cloak-capable rows with prior `iscloaked=true`:

```text
before fuel - after fuel
reference cloak cost
same-position vs moved
true_to_true / true_to_false
PE0 vs PE nonzero
VCR participation
exact-reference-cost debit vs zero/other debit
```

The four clean initial rows should be emitted separately, including a clearly labelled hypothetical reference debit for ship118 because its T physical identity is not stable.

If the exact reference-cost debit is a broad, structured population signal, follow with a clean attribution pass controlling transfer/Rob exposure and documented decloak context (ion disturbance, Glory Device, etc.). If it is sparse/noisy, do not promote the 5-KT interpretation.
