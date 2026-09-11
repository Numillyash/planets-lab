# C5 Host combat — Privateer Rob cloak/fuel-state population gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Depends on:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-runtime.md
```

The focused cloak-context runtime rejected T-1 damage, normal-movement fuel exhaustion and Loki as discriminators between the three clean skipped prior-true Meteors and the sole clean prior-true fought control.

It also exposed a new empirical pattern:

```text
skipped ship46:  58 -> 53  exact -5 KT, stationary, T iscloaked=true
skipped ship280:  9 ->  4  exact -5 KT, stationary, T iscloaked=true
skipped ship98:  45 -> 40  exact -5 KT, stationary, T iscloaked=true
fought ship118:  T-1 fuel=5 KT; T identity unavailable
```

For Meteor hull mass 90 the ordinary-cloak reference cost is 5 KT. A hypothetical 5-KT debit would leave every skipped target with positive fuel and exhaust ship118 exactly.

This is a strong correlation but **not** a promoted mechanic: Privateer mission9 is Rob Ship, not the documented ordinary Cloak mission, and T is post-Host.

## Diagnostic

```text
tools/diagnostics/combat_host_privateer_rob_cloak_fuel_state_audit.py
tests/test_combat_host_privateer_rob_cloak_fuel_state_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-cloak-fuel-state-audit.v1
```

The diagnostic reuses the full Privateer race5 mission9 cloak-capable transition population and selects stable physical rows with prior archived `iscloaked=true`.

For every such row it measures:

```text
fuel_before - fuel_after
ordinary cloak reference cost
exact_reference_debit / zero_debit / other_debit
same_position / position_changed
damage zero vs nonzero/unknown
cloak transition
PE0 vs nonzero
VCR participation
fuel_before relative to reference cost
```

It also projects the four clean initial rows separately. For ship118, because the T physical identity is not stable, the 5 -> 0 result is explicitly labelled hypothetical and never reported as observed.

## Primary questions

1. Is exact `fuel debit == ordinary cloak reference cost` common and structured among stable prior-true Privateer Rob rows, or is the three-row focus pattern sparse coincidence?
2. Is exact debit concentrated in `true_to_true` rows?
3. Does exact debit occur on stationary rows where normal movement cannot explain it?
4. Is the pattern stronger among PE0/no-VCR rows than among VCR participants?
5. How often does the T-1 fuel equal the reference cost versus exceed it?

## Interpretation

A broad structured exact-debit population would justify a second attribution pass controlling Rob/transfer exposure and documented decloak contexts such as ion disturbance and Glory Device.

It would **not** by itself prove:

- that Rob Ship engages or preserves cloak;
- that the 5-KT debit occurs before combat;
- that archived prior `iscloaked` is the effective combat cloak state;
- that `selection.py` should block a target.

If exact-reference debit is sparse/noisy, reject the attractive four-row fuel-threshold explanation and investigate another hidden state discriminator.

No canonical combat code changes in this gate.
