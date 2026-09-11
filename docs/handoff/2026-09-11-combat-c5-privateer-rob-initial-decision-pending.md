# C5 Host combat — Privateer Rob initial-decision pending

Status: **SUPERSEDED by completed runtime**.

Runtime handoff:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
```

Active next gate:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-pending.md
```

The completed runtime source was:

```text
7cb29984bc09b241241a8e738f6b6701bc61d5b4
```

Result:

```text
opportunities=16
initial_pair_vcr=5
initial_skip_target_not_above_factual=5
initial_skip_target_outranks_factual=3
attacker_no_factual_vcr=1
later_pair_vcr=1
noninitial_attacker_context=1
payload_conflicts=0
```

All three clean `initial_skip_target_outranks_factual` rows have prior `iscloaked=true`; the only clean prior-true `initial_pair_vcr` control is `620694/T64/ship118`. See the runtime handoff for the exact rows and evidence boundary.
