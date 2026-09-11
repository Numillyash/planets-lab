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
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md
```

Raw archived `T-1 iscloaked=true` remains rejected as a blanket or direct scoped Privateer-Rob blocker.

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

### Focused cloak-context runtime

Runtime source `fe9f1575b81d7ea4c922426c8f56d689dbd66ef3`, tests/audit rc0:

```text
focus_rows=4
damage=0 for all 4
normal movement distance=0 / fuel_used=0 for all 4
no active Loki within 10 ly for all 4
```

Damage, normal-movement fuel exhaustion and Loki therefore do not explain the fought ship118 versus the three skipped Meteors.

### Cloak/fuel-state population runtime

Runtime source:

```text
cf52a264c31418a8247987a64332c54e50e07a91
```

Tests/audit rc0; payload conflicts remain zero.

```text
stable prior-true rows=1413
exact_reference_debit=545
zero_debit=90
other_debit=778

same_position=718
position_changed=695

true_to_true=1378
true_to_false=35

threshold above reference cost=1399
threshold equals reference cost=3
threshold below reference cost=11
```

The exact ordinary-cloak-reference debit is a large structured signal, not a four-row coincidence:

```text
545 / 1413 = 38.6% overall
541 / 545 = 99.3% exact-debit rows are true_to_true
```

Strongest stationary quiet bucket:

```text
same_position=True, damage0, PE0, no VCR:
  exact=515
  other=112
  zero=86
  exact share=72.2%
```

The three skipped Meteors remain exact 5-KT observations:

```text
ship46:  58 -> 53
ship280:  9 -> 4
ship98:  45 -> 40
```

Meteor ordinary-cloak reference cost is 5 KT. Ship118 starts with exactly 5 KT, so a hypothetical reference debit would exhaust it exactly. Because ship118 T physical identity is not stable, `5 -> 0` is still **not observed**.

Evidence status:

```text
large structured exact-reference-debit population:
  CORPUS_OBSERVED + TESTED

"Rob Ship consumes cloak fuel" / "mission9 preserves cloak":
  NOT PROMOTED
```

Official cloak documentation describes fuel consumption for the `Cloak` mission; Privateer mission9 is documented `Rob Ship`. Therefore the population signal still needs phase/fuel-source attribution before any canonical effective-cloak rule.

## Immediate gate — Privateer Rob cloak/fuel attribution

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_cloak_fuel_attribution_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_attribution_audit.py
```

It has two purposes.

First, isolate a cleaner visible-input fuel population requiring:

```text
damage0
effective requested Warp0
same T position
no submitted outbound transfer
not a submitted inbound-transfer target
no foreign owner-current ship at the T-1 Rob origin
```

Second, emit all low-fuel threshold controls. The completed population contains 3 stable rows with `fuel==reference_cost` and 11 with `fuel<reference_cost`; these are higher-value controls than another broad prevalence count.

The attribution gate also annotates T-1 ion-disturbance, Loki and co-located active Glory-device context from archived state/static specs.

Decision boundary:

- clean stationary/no-visible-fuel-source rows retain a dominant exact-reference debit, and low-fuel rows show a structured threshold transition -> promote only an explicit evidence-scoped effective-state model, then rerun initial-target differential;
- clean signal collapses or low-fuel controls contradict the threshold -> reject the 5-KT threshold explanation;
- no `selection.py`, `queue.py`, target-order, STANDARD priority or FC parser change before this gate.

Later C5 work: close Privateer ship98 and Bird ship202 state; promote canonical first selector; compose mutable survivor/destruction state; second-pass orientation; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
