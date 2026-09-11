# C5 Host combat — Bird Super Spy population opportunity runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Runtime

Source:

```text
2edb1349562d0ed7fc7a6c74a807004e540c46b8
```

Targeted tests:

```text
17 passed
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_attack_opportunity_audit.py
```

Runtime artifact:

```text
artifacts/combat-bird-super-spy-attack-opportunities.json
```

## Population summary

```text
bird_super_spy_targets_at_factual_sites=30
conditional_plain_standard_opportunities=8
strict_plain_standard_opportunities=8
raw_attack_opportunities=8
bidirectional_request_opportunities=2

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
nondecisive_rows=4

payload_conflicts=0
race_conflicts=0
```

Factual outcomes:

```text
attacker_fought_other=7
pair_vcr=1
```

Queue classifications:

```text
initial_skip_target_outranks_factual=3
initial_pair_vcr=1
initial_skip_target_not_above_factual=4
```

Candidate-state reasons across the population scan:

```text
advanced_cloak_unresolved=24
documented_super_spy_ordinary_cloak_supported=4
planet_ion_pulse_possible=1
prior_cloak_not_positive=1
```

## Acceptance

All hard acceptance flags passed:

```text
no_race_conflicts=True
no_payload_conflicts=True
no_blocked_factual_pair_regressions=True
no_decisive_mismatch=True
target_residual_present=True
target_residual_supported=True
```

The focused original residual remains a clean positive:

```text
511506/T94 ship202 vs attacker496
classification=initial_skip_target_outranks_factual
expected_blocked=True
candidate_blocked=True
decisive_match=True
reason=documented_super_spy_ordinary_cloak_supported
```

## Decisive unresolved rows

All three decisive unresolved rows are Advanced Cloak, not ordinary cloak:

```text
620694/T119 ship26 vs attacker74
  Resolute hull31 / mission9 / prior cloak=true
  expected_blocked=True
  candidate=None advanced_cloak_unresolved

620694/T119 ship69 vs attacker74
  Resolute hull31 / mission9 / prior cloak=true
  expected_blocked=True
  candidate=None advanced_cloak_unresolved

680435/T31 ship68 vs attacker26
  Resolute hull31 / mission9 / prior cloak=true
  factual pair exists
  expected_blocked=False
  candidate=None advanced_cloak_unresolved
```

This is the key next contrast. A naive rule `Bird Super Spy + Advanced Cloak + prior cloak=true => blocked` would incorrectly block the factual `680435/T31 ship68` pair. Advanced Cloak must therefore remain unresolved until the dynamic decloak path is reconstructed.

## Documentation boundary for Advanced Cloak

Official Planets.nu documentation states:

- Super Spy attempts to cloak according to the ship's cloak type;
- Advanced Cloak consumes no cloak fuel but still requires at least 1 KT of fuel;
- Advanced Cloak is not decloaked by ion storms/nebulae merely for being inside them;
- mine hits can damage and decloak;
- Glory Devices detonate after movement and damage/decloak cloaked ships;
- Loki has post-movement decloak passes, subject to race Loki Immunity.

Sources:

```text
https://help.planets.nu/mis-super-spy
https://help.planets.nu/abil-advanced-cloak
https://help.planets.nu/cloak-details
https://help.planets.nu/abil-glory-device
```

## Evidence status

```text
ordinary-cloak Bird Super Spy focused blocker:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

Bird population gate hard contradictions:
  NONE OBSERVED

population-wide Advanced Cloak targetability:
  UNRESOLVED
```

The population runtime supports the ordinary-cloak branch and identifies Advanced Cloak as the only decisive unresolved branch. It does **not** justify generic Advanced Cloak blocking.

## Next gate

Build a focused Advanced Cloak post-movement decloak attribution diagnostic over the three decisive rows. Compare:

```text
movement path / final position
remaining fuel >= 1 KT
mine/web interaction evidence
post-movement POP/TRG Glory exposure
post-movement Loki exposure + Bird Loki Immunity state
planet ion-pulse context
T damage / cloak transition as attribution-only controls
```

The goal is to identify a concrete dynamic difference that explains why ship26/69 are skipped while ship68 is factually fought. Do not modify canonical selector/queue code until this branch is resolved or explicitly left fail-closed.
