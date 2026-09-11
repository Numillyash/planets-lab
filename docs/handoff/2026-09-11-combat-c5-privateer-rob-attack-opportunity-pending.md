# C5 Host combat — Privateer Rob attack-opportunity pending — superseded

This gate completed successfully and is superseded by:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-pending.md
```

Runtime source:

```text
bab8689c18d894399448543d3362f1cec288f5b4
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
strict/conditional plain-STANDARD opportunities=16
prior true: attacker_fought_other=8, pair_vcr=2
prior false: pair_vcr=5, neither_vcr=1
```

The two `true:pair_vcr` rows reject raw prior `iscloaked=true` as a Privateer-Rob blocker. The eight skips require queue/rank separation before any effective target-protection interpretation.

No canonical combat rule was promoted from this gate.
