# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

## Stable C5 layers

Do not reopen these absent a direct contradiction:

- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- direct ordinary STANDARD priority: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I attacker: 7/7 RIGHT;
- Galactic Power Case2, reciprocal PIA and matching-FC scoped closures;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

Owner-current `T-1` is the precombat order/state source. `T` is post-Host/postcombat and same Ship ID at T is not automatically the same physical ship because later construction can reuse an ID.

## Position / candidate checkpoint

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
docs/handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md
```

Position v3:

```text
factual ship occurrences=3204
predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs exact=678 mismatch=4 unresolved=1304
```

Candidate-set v2:

```text
factual unique pairs=1986
candidate-covered=428
conditional factual eligible=427 unresolved=1 blocked=0
strict factual eligible=420 unresolved=8 blocked=0
```

No candidate-covered factual pair is conditionally hard-blocked.

## Initial STANDARD target-order — runtime complete

Read `docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`.

```text
conditional exact-set: 169/169 first pair exact; 169/169 RIGHT exact
strict exact-set:      162/162 first pair exact; 162/162 RIGHT exact
informative exact-set target-order controls: 15/15 rank1
```

Strongly supported when the eligible set is correct:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

## Two original broad initial blockers

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Fuel exhaustion was rejected for both.

Bird `511506/T94/ship202` remains a separate Super Spy/effective-cloak residual. Do not mix it with the Privateer branch below.

## Privateer Rob blocker investigation

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-runtime.md
```

Raw archived `T-1 iscloaked=true` is rejected as a blanket or direct scoped Privateer-Rob blocker.

Initial-decision runtime isolated three genuine clean missing-state residuals with no prior queue mutation:

```text
360690/T57 ship46  vs attacker146
360690/T57 ship280 vs attacker146
360690/T83 ship98  vs attacker264
```

All three are Privateer race5 / Meteor hull46 / mission9 Rob / PE0 / prior `iscloaked=true` and strictly outrank the factual first target. Matched same-site controls with prior `iscloaked=false` are actually fought by the same attacker.

The only clean prior-true initial fought control is:

```text
620694/T64 ship118 vs attacker134
T-1 fuel=5
```

### Latest cloak-context runtime

Runtime source:

```text
fe9f1575b81d7ea4c922426c8f56d689dbd66ef3
```

Tests/audit rc0. The focused four-row gate found:

```text
focus_rows=4
damage=0 for all 4
normal movement distance=0 / fuel_used=0 for all 4
no active Loki within 10 ly for all 4
```

Therefore damage, normal-movement fuel exhaustion and Loki do **not** explain why ship118 is fought while the other three are skipped.

A strong new corpus correlation emerged on the three stable skipped Meteors:

```text
ship46:   58 -> 53  exact -5 KT, remains iscloaked=true
ship280:   9 ->  4  exact -5 KT, remains iscloaked=true
ship98:   45 -> 40  exact -5 KT, remains iscloaked=true
```

Meteor ordinary-cloak reference cost is 5 KT. The sole clean fought prior-true control starts with exactly 5 KT. A hypothetical 5-KT debit would therefore leave all three skipped targets with positive fuel and exhaust ship118 exactly.

Evidence status:

```text
CORPUS_OBSERVED + INFERRED
```

Do **not** promote this as `Rob Ship consumes cloak fuel`: mission9 is Rob Ship, not the documented ordinary Cloak mission, and T is post-Host. Existing ordinary cloak-fuel work uses mission10 as the causal Cloak branch.

## Immediate gate — Privateer Rob cloak/fuel-state population

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_cloak_fuel_state_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_state_audit.py
```

Measure across all stable physical Privateer race5 mission9 cloak-capable rows with prior archived `iscloaked=true`:

```text
fuel_before - fuel_after
ordinary cloak reference cost
exact_reference_debit / zero_debit / other_debit
same-position vs moved
damage
true_to_true / true_to_false
PE0 vs nonzero
VCR participation
fuel-before threshold vs reference cost
```

The four clean initial rows are emitted separately. Ship118 `5 -> 0` is hypothetical only because its T physical identity is not stable.

Decision boundary:

- broad structured exact-reference debit -> run a second clean attribution gate controlling Rob/transfer exposure plus ion/glory context;
- sparse/noisy exact debit -> reject the attractive 5-KT threshold explanation and search another hidden state discriminator;
- no `selection.py` or `queue.py` change before this evidence closes.

Later C5 work: close Privateer ship98 and Bird ship202 state; promote canonical first selector; compose mutable survivor/destruction state; second-pass orientation; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
