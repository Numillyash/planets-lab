# C5 Host combat — Privateer Rob attack-opportunity runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

Runtime source:

```text
bab8689c18d894399448543d3362f1cec288f5b4
```

Artifact:

```text
artifacts/combat-c5-privateer-rob-attack-opportunity-20260911-111655
```

Runtime result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
rob_pe_zero_targets_at_factual_sites=45
raw_attack_opportunities=16
conditional_plain_standard_opportunities=16
strict_plain_standard_opportunities=16

conditional / strict outcomes:
  attacker_fought_other=8
  pair_vcr=7
  neither_vcr=1

by prior raw iscloaked:
  true:attacker_fought_other=8
  true:pair_vcr=2
  false:pair_vcr=5
  false:neither_vcr=1
```

The exact original residual remains present:

```text
360690/T83 @ 2374,2260
Privateer target98: race5, Meteor hull46, mission9/Rob, PE0, T-1 iscloaked=true
attacker264: owner11/race11, hull99, mission3/Kill!
strict diplomacy independently allowed
canonical current pair decision: eligible STANDARD, target98 LEFT / attacker264 RIGHT
factual outcome: attacker264 instead fights ship190
ship98 remains stable true->true and does not appear in a VCR
```

## Critical negative result

Raw prior `iscloaked=true` is **not** a valid Privateer-Rob target blocker.

The population contains two strict and conditional `true:pair_vcr` opportunities. Both refer to the same physical Privateer target:

```text
620694/T64/site 1371,2382/ship118
  target118: Privateer Meteor, mission9, PE0, T-1 iscloaked=true, fuel5
  pair [118,134] factual VCR
  pair [118,152] factual VCR
```

Therefore neither of these is safe to encode:

```text
raw T-1 iscloaked=true => target protected
Privateer mission9 + prior iscloaked=true => target protected
```

This is consistent with the existing negative control `511506/T94/ship332`, which also has raw prior `iscloaked=true` but fights under a different current mission.

## What the eight skips do and do not prove

Eight prior-cloaked opportunities have `attacker_fought_other`, including the target residual. This is stronger than the earlier no-VCR population because a hostile Kill!/PE requester is independently reconstructed at the same site.

However, an `attacker_fought_other` label is **not by itself** an effective-cloak differential. The attacker may simply select a higher-priority target first and then be destroyed/captured or otherwise have no later queue opportunity. Queue ordering and mutable combat outcome therefore have to be separated before any cloak/state blocker is promoted.

The two `true:pair_vcr` rows are also one physical target/site, not two independent target-state controls. Any later effective-cloak analysis should check precombat decloak context (fuel/damage/Loki/ion/mine/glory or other documented causes) before treating the raw bit as contradictory.

## Documentation boundary

Planets.nu Cloaking Details documents that ships begin the Host uncloaked; ordinary cloak is engaged by the `Cloak` mission, with later Loki/ion/mine/fuel/glory effects able to decloak before combat. Privateer `Rob Ship` is a separate mission/Host step. Bird `Super Spy` is a separate documented case that explicitly attempts to cloak on a cloak-capable hull.

Accordingly:

- Privateer mission9/Rob is **not** promoted as a cloak-generating rule;
- archive `iscloaked` remains an observed state field, not a current-Host effective-cloak oracle;
- no `selection.py` change follows from this runtime.

## Next gate

Use:

```text
tools/diagnostics/combat_host_privateer_rob_initial_decision_audit.py
tests/test_combat_host_privateer_rob_initial_decision_audit.py
```

The next gate classifies the 16 opportunities by factual queue position and canonical target priority. Strong evidence is restricted to initial-decision cases where the attacker is in the first factual VCR at the site and the skipped Rob target has strictly higher standard target priority than the factual opponent. Later-attacker cases remain separate until survivor/destruction replay is composed.
