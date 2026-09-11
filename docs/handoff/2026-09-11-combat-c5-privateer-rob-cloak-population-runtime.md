# C5 Host combat — Privateer Rob cloak population runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` is excluded from ordinary promotion.

Runtime source:

```text
e0b7f9ac91f99e8006546b80ec4a940ab21e2a6e
```

User runtime:

```text
TARGETED TESTS: 10 passed
audit rc=0
payload_conflicts=0
artifact: artifacts/combat-c5-privateer-rob-cloak-population-20260910-233117/
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_cloak_population_audit.py
tests/test_combat_host_privateer_rob_cloak_population_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-cloak-population-audit.v1
```

## Runtime population

```text
candidate_rows=2223
stable_identity=2174
identity_unresolved=26
identity_mismatch=23
stable_no_vcr=2172
stable_vcr_participant=2
before_cloak_true=1433
before_cloak_false=790

stable cloak transitions:
  true_to_true=1378
  false_to_true=693
  false_to_false=68
  true_to_false=35

games:
  511506=1100
  360690=631
  620694=492

hulls:
  46=1954
  45=87
  44=83
  31=41
  29=40
  28=18
```

The counter keys `stable_before_cloaked_pe_zero_vcr` and `stable_true_to_true_pe_zero_vcr` are absent from the serialized summary, therefore they are zero under this diagnostic's Counter serialization. Corresponding no-VCR populations are:

```text
stable_before_cloaked_pe_zero_no_vcr=1394
stable_true_to_true_pe_zero_no_vcr=1360
```

This is strong `CORPUS_OBSERVED` persistence evidence for the archive `iscloaked` field in the Privateer race5 + mission9 + cloak-capable population. It is **not** by itself combat-effective-cloak evidence because most rows do not establish that an eligible hostile attacker was present at the same combat site.

## Exact residual

`360690`, before turn 82 -> battle turn 83, ship98:

```text
owner=5 / race=5 Privateer
hull46 Meteor Class Blockade Runner
mission9
PE=0
stable physical identity=true
T-1 iscloaked=true
T iscloaked=true
fuel 45 -> 40
ordinary cloak reference cost=5
VCR participant=false
```

The row is typical of the broad stable `true_to_true` / PE=0 / no-VCR population rather than an isolated archive anomaly.

## Documentation boundary

Current Planets.nu documentation places `Cloak` before `Rob` in Host Order and documents ordinary cloaking as being activated by the `Cloak` mission. It also documents that all ships begin the Host turn uncloaked before the cloak step. Therefore race5 mission9 / Rob must not be promoted as a cloak-generating mission from the archive transition population alone.

This makes the archive `iscloaked` bit a state/observation field whose current-host combat meaning must be reconstructed rather than copied directly into pair eligibility.

## Consequence for C5

Do **not** add a blanket blocker from raw `T-1 iscloaked=true`.

Do **not** change STANDARD target ordering. Exact-set initial target ordering remains clean.

The two broad initial-target residuals remain mechanically distinct:

```text
511506/T94 ship202: Bird Super Spy + cloak-capable Red Wind; strong effective-cloak candidate
360690/T83 ship98: Privateer Rob + persistent raw cloak state; effective combat cloak unresolved
```

## Immediate follow-up

Before any cloak blocker is promoted, inspect the two stable Privateer mission9 VCR-participant rows explicitly. They are the only direct same-population combat rows in the current audit and can bound whether prior/current raw cloak state ever coexists with factual ship combat.

After those two rows are classified, move to a site-conditioned attack-opportunity differential: require a reconstructed hostile co-located attacker and distinguish raw cloak persistence from actual combat targetability.
