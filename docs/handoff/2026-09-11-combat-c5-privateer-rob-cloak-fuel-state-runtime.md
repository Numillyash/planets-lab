# C5 Host combat — Privateer Rob cloak/fuel-state population runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Runtime source:

```text
cf52a264c31418a8247987a64332c54e50e07a91
```

Executed:

```text
tests/test_combat_host_privateer_rob_cloak_population_audit.py
tests/test_combat_host_privateer_rob_initial_cloak_context_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_state_audit.py
tools/diagnostics/combat_host_privateer_rob_cloak_fuel_state_audit.py
```

Historical runtime result:

```text
tests rc=0
audit rc=0
payload_conflicts=0

stable_prior_true_rows=1413
fuel_delta_resolved=1413
damage_zero=1413

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

Therefore the population gate is **TESTED** at its diagnostic boundary.

## Strong structure

The exact ordinary-cloak-reference debit is not a sparse four-row coincidence:

```text
545 / 1413 = 38.6% of all stable prior-true rows
541 / 545 = 99.3% of exact-debit rows are true_to_true
```

The strongest stationary/quiet bucket is:

```text
same_position=True
damage_zero=True
PE0=True
VCR=False
```

with:

```text
exact_reference_debit=515
other_debit=112
zero_debit=86

515 / 713 = 72.2% exact reference debit
```

Across all same-position rows, exact-reference debit accounts for 520/718 = 72.4%.

The moving population is dominated by `other_debit`, as expected when normal movement and other Host fuel mutations are still mixed into the net T-1 -> T delta.

Game-level exact-debit counts are heterogeneous rather than universal:

```text
360690: exact=335 other=137 zero=11
511506: exact=62  other=487 zero=17
620694: exact=148 other=154 zero=62
```

This heterogeneity is a reason to perform attribution, not a reason to promote a universal Rob rule.

## Four clean initial rows

The three clean first-decision skips remain exact 5-KT observations:

```text
360690/T57 ship46:  58 -> 53, exact_reference_debit, T iscloaked=true
360690/T57 ship280:  9 -> 4,  exact_reference_debit, T iscloaked=true
360690/T83 ship98:   45 -> 40, exact_reference_debit, T iscloaked=true
```

All three:

```text
Privateer race5
Meteor hull46
mission9 / Rob
PE0
damage0
prior iscloaked=true
reference cost=5
reference debit leaves positive fuel
no Loki start exposure
```

The sole clean prior-true fought control remains:

```text
620694/T64 ship118
T-1 fuel=5
reference cost=5
stable T identity unavailable
hypothetical reference debit: 5 -> 0
factual first pair: [118,134]
```

The `5 -> 0` value is **not observed** and remains explicitly hypothetical.

## Evidence status

Promoted:

```text
large structured exact-reference-debit population:
  CORPUS_OBSERVED + TESTED

focus ships 46/280/98 exact -5 T-1 -> T transitions:
  CORPUS_OBSERVED
```

Not promoted:

```text
"Rob Ship consumes cloak fuel"
"mission9 preserves/engages cloak"
"prior iscloaked=true is directly combat-effective"
"ship118 definitely paid 5 KT before combat"
```

Official cloak documentation says ordinary cloak fuel is consumed by ships whose mission is `Cloak`; these rows are mission9/Rob. Therefore the current evidence is a strong NuHost state correlation that still needs phase/fuel-source attribution.

## Next gate

The immediate follow-up must exploit the low-fuel controls and remove visible net-fuel confounders:

1. inspect all stable rows with `fuel_before <= reference_cost`, especially the 3 exact-threshold and 11 below-threshold rows;
2. isolate T-1 requested-Warp-0 / same-position / damage0 rows;
3. exclude visible submitted inbound/outbound transfer;
4. distinguish rows with no foreign ship co-located at Rob origin, where Rob cannot visibly add fuel;
5. annotate T-1 ion-disturbance, Loki and active Glory-device exposure;
6. compare fuel-debit relation, cloak transition and VCR participation inside that cleaner population.

No canonical combat rule changes from this runtime alone.
