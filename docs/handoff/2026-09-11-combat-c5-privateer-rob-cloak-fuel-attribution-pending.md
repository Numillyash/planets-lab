# C5 Host combat — Privateer Rob cloak/fuel attribution gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

## Latest runtime attempt — INVALID / infrastructure only

Attempted source:

```text
180429508419581cf5082bb5363e1b8c528dd14f
```

Runtime result:

```text
tests rc=2
audit rc=99
```

Both targeted tests failed during pytest collection with:

```text
ModuleNotFoundError: No module named 'tools'
```

This is **not mechanics evidence** and does not change any combat conclusion. The new tests used `from tools.diagnostics...` while the established repository convention is to add `tools/diagnostics` to `sys.path` and import diagnostic modules directly.

The import regression is now repaired in both:

```text
tests/test_combat_host_privateer_rob_cloak_fuel_state_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_attribution_audit.py
```

The attribution gate remains pending until rerun on the repaired branch HEAD.

Depends on:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md
```

The population runtime established a large structured exact ordinary-cloak-reference fuel-debit cluster among stable prior-true Privateer mission9/Rob cloak-capable rows:

```text
stable prior-true rows=1413
exact_reference_debit=545
exact true_to_true=541
same-position quiet bucket: 515 exact / 112 other / 86 zero
```

The exact debit is therefore not a sparse coincidence, but it is still only `CORPUS_OBSERVED + TESTED` state correlation. Mission9 is documented Rob Ship, not ordinary Cloak.

The strongest unresolved control remains `620694/T64/ship118`: T-1 fuel equals the 5-KT Meteor reference cost and the ship enters the factual first battle. A hypothetical reference debit would exhaust it, but T identity after combat is not stable and the debit is not observed.

## Diagnostic

```text
tools/diagnostics/combat_host_privateer_rob_cloak_fuel_attribution_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_attribution_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-cloak-fuel-attribution-audit.v1
```

## Clean fuel-attribution subset

The diagnostic builds a deliberately conservative visible-input subset from stable prior-true mission9 rows:

```text
damage=0
effective requested Warp=0
T position unchanged
no nonzero submitted outbound transfer
not a visible submitted inbound-transfer target
no foreign owner-current ship co-located at T-1 Rob origin
```

This removes the dominant visible sources of net fuel mutation:

```text
normal movement fuel use
visible Rob fuel acquisition opportunity
visible submitted ship transfer
```

It does not claim complete causal isolation. Starbase refuel, web drain, hidden/visibility-dependent effects or other Host phases can still change T fuel.

## Low-fuel threshold controls

The previous population contains:

```text
fuel_before == reference_cost: 3 stable rows
fuel_before <  reference_cost: 11 stable rows
```

These 14 rows are emitted in full, including:

```text
fuel before/after/debit
reference cost
true_to_true / true_to_false
VCR participation
requested warp / same-position state
visible Rob-origin ships
submitted transfer context
T-1 ion-disturbance context
T-1 Loki exposure
co-located static-spec Glory Device with POP/TRG code
advanced-cloak static special flag
```

This is the highest-value threshold control population because it can test whether insufficient/exact fuel predicts loss of the archived cloak-state signal and/or combat participation.

## Decloak context

T-1 annotations are attribution only:

- ion disturbance: target origin lies within an archived T-1 storm circle;
- Loki: foreign hull7 with damage <=19% within 10 ly at T-1;
- Glory: foreign co-located hull whose archive static `special` contains `Glory`, with active `POP`/`TRG` FC separately flagged.

These annotations do not reconstruct diplomacy immunity, moving Glory arrival, post-movement Loki arrival or exact trigger resolution.

## Decision boundary

Strong support for a current-Host fuel-threshold state would require both:

1. a large clean stationary/no-visible-fuel-source population continuing to show exact reference debit; and
2. low-fuel controls showing a structured threshold transition, especially stable `fuel==reference_cost` or `fuel<reference_cost` rows becoming `true_to_false` or otherwise ceasing to behave like the positive-fuel population without an alternative documented decloak context.

Even then, do not immediately write `mission9 => cloak` into combat selection. First convert the evidence into an explicit effective-state helper with fail-closed inputs and rerun the initial-target differential.

If the clean population loses the exact-debit signal, or threshold controls contradict the model, reject the threshold explanation and retain raw prior `iscloaked` as non-causal historical state.

No canonical combat code changes in this gate.
