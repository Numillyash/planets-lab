# C5 Host combat — Privateer Rob cloak/fuel attribution runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Runtime source:

```text
16f9253b92f7e48f7f2179f9c3b704469de4128a
```

Executed:

```text
tests/test_combat_host_privateer_rob_cloak_fuel_state_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_attribution_audit.py
tools/diagnostics/combat_host_privateer_rob_cloak_fuel_attribution_audit.py
```

Runtime result:

```text
tests rc=0
audit rc=0

stable_prior_true_rows=1413
threshold_at_or_below_rows=14
clean_stationary_no_visible_fuel_mutation=12
clean_exact_reference_debit=2

clean_relation:
  zero_debit=7
  other_debit=3
  exact_reference_debit=2

clean_transition:
  true_to_true=12
```

Therefore this attribution gate is **TESTED** at its diagnostic boundary.

## Clean fuel-attribution result

The cleaner visible-input subset does **not** preserve the previously dominant exact ordinary-cloak-reference debit signal.

The earlier broad same-position / damage0 / PE0 / no-VCR bucket had:

```text
exact_reference_debit=515
other_debit=112
zero_debit=86
exact share=72.2%
```

After requiring the more conservative visible-input controls:

```text
damage0
effective requested Warp0
same T position
no submitted outbound transfer
not a submitted inbound-transfer target
no foreign owner-current ship at the T-1 Rob origin
```

the surviving population is only 12 rows:

```text
exact_reference_debit=2 / 12 = 16.7%
zero_debit=7 / 12 = 58.3%
other_debit=3 / 12 = 25.0%
```

All 12 remain `true_to_true`.

This rejects the simple interpretation that stable prior-true mission9/Rob rows generally consume the ordinary cloak reference fuel cost in an otherwise quiet stationary state. The historical exact-debit population remains a real structured correlation, but not a cleanly isolated universal Rob fuel-consumption rule.

The two clean exact-reference-debit examples are both game `511506`, T47->T48, Meteor hull46:

```text
ship401: 48 -> 43, reference cost 5
ship439: 45 -> 40, reference cost 5
```

No ion/Loki/active-Glory start exposure is present in either row.

## Low-fuel threshold result

The 14 stable rows with `fuel_before <= reference_cost` are much more informative than the clean debit population.

Aggregate transition:

```text
below_reference_cost:
  true_to_false=10
  true_to_true=1

equals_reference_cost:
  true_to_false=3
```

The sole `true_to_true` row is:

```text
game 620694 / T96->T97 / ship199
hull29
advanced cloak static special=true
fuel 21 -> 87
reference cost 24
foreign_origin_count=1
```

After separating that advanced-cloak control, every ordinary-cloak hull row at or below the reference cost transitions out of the archived cloak signal:

```text
ordinary-cloak hull threshold rows: 13
true_to_false:                       13
true_to_true:                         0
```

Those 13 ordinary threshold rows have no archived T-1 ion-disturbance, Loki or active co-located Glory exposure according to this diagnostic.

This is a strong **CORPUS_OBSERVED + TESTED** threshold correlation. It does not yet prove the exact Host predicate because every threshold row has nonzero requested Warp (`1` or `9`) and the diagnostic only observes archived before/after state rather than the internal precombat effective-cloak phase.

## Focus residuals

The original four focus rows remain:

```text
360690/T57 ship46:  fuel 58, reference 5, exact 58 -> 53, skipped
360690/T57 ship280: fuel 9,  reference 5, exact 9  -> 4,  skipped
360690/T83 ship98:  fuel 45, reference 5, exact 45 -> 40, skipped
620694/T64 ship118: fuel 5,  reference 5, T identity unresolved, fought
```

Thus the three clean initial skipped Meteors are all above the reference-cost threshold and preserve `iscloaked=true` at T where identity is stable. The fought control starts exactly at the reference cost, but its T physical identity is unresolved, so the expected threshold transition cannot be observed directly for that ship.

The population threshold result makes ship118's `fuel == reference_cost` state materially more suspicious, but it is still not sufficient to promote `fuel <= reference_cost => combat-visible` without an explicit effective-state differential.

## Evidence status

Promoted:

```text
clean visible-input Rob population does not support universal exact reference debit:
  CORPUS_OBSERVED + TESTED

ordinary-cloak archived prior-true rows with fuel <= reference cost:
  13/13 true_to_false in this threshold population
  CORPUS_OBSERVED + TESTED
```

Rejected / not promoted:

```text
"Rob Ship universally consumes ordinary cloak fuel"
"mission9 itself is ordinary Cloak"
"raw prior iscloaked=true is directly combat-effective"
"fuel <= reference_cost is already a canonical combat blocker predicate"
"ship118 definitely decloaked before combat because of fuel"
```

## Next gate

Do not modify `selection.py`, `queue.py`, STANDARD priority or Friendly Code parsing yet.

The next diagnostic should test an explicit effective-cloak threshold candidate rather than another broad debit prevalence count:

1. partition stable Privateer mission9 prior-true rows by ordinary-cloak vs advanced-cloak static hull class;
2. compute fuel margin `fuel_before - reference_cost` and transition rates around the boundary, especially `<=0`, `1..reference_cost`, and larger positive margins;
3. compare like-for-like requested-Warp / same-position / no-visible-transfer / no-ion / no-Loki / no-active-Glory contexts so the threshold is not merely a movement-order proxy;
4. apply an evidence-scoped candidate effective-cloak helper to the initial-target opportunities without changing canonical selection code;
5. rerun the first-target differential and ask whether the three skipped Meteors become blocked while ship118 remains eligible and matched prior-false controls stay eligible;
6. keep Bird `511506/T94/ship202` on the separate Super Spy/effective-cloak branch.

Only if that differential improves without new contradictions should the threshold become part of an explicit fail-closed precombat effective-state model.
