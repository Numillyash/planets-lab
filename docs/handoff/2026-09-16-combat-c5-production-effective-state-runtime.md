# C5 precombat effective-state -> STANDARD targetability runtime — 2026-09-16

Branch: `agent/combat-c5-host-phase`

GitHub remains the source of truth. PR #28 remains draft/open. Game `591478` remains excluded from ordinary promotion.

## Runtime source

```text
6a5e39796e385f4d98dc10697d30c958ad3a8898
```

Production implementation:

```text
0b88541df32c441ead4b9b9d6054af04fd2fee7a  combat: promote Bird ordinary Super Spy effective state
6a5e39796e385f4d98dc10697d30c958ad3a8898  combat: export effective-state API
```

## Targeted tests

The user ran:

```text
tests/test_combat_effective_state.py
tests/test_combat_host_bird_super_spy_cloak_context_audit.py
tests/test_combat_host_bird_super_spy_production_effective_state_audit.py
tests/test_combat_standard_targetability.py
tests/test_combat_initial_standard_selector.py
```

Result:

```text
......................................... [100%]
41 passed
```

## Production Bird population differential

Diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_production_effective_state_audit.py
```

Artifact:

```text
artifacts/combat-bird-super-spy-production-effective-state.json
```

Observed population:

```text
bird_super_spy_targets_at_factual_sites=30
archives_considered=11
raw_attack_opportunities=8
conditional_plain_standard_opportunities=8
strict_plain_standard_opportunities=8

decisive_rows=4
nondecisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
bidirectional_request_opportunities=2
payload_conflicts=0

factual_outcomes:
  attacker_fought_other=7
  pair_vcr=1

initial_classifications:
  initial_skip_target_not_above_factual=4
  initial_skip_target_outranks_factual=3
  initial_pair_vcr=1

decisive_matrix:
  expected_blocked:unresolved=2
  expected_blocked:candidate_blocked=1
  expected_eligible:unresolved=1

candidate_reasons:
  advanced_cloak_unresolved=24
  documented_super_spy_ordinary_cloak_supported=4
  planet_ion_pulse_possible=1
  prior_cloak_not_positive=1

target_residual_rows=1
```

No blocked factual-pair regression was observed.

## Focused residual

The original Bird broad-selector residual now projects through the production helper as:

```text
game_id=511506
battle_turn=94
target_ship_id=202
attacker_ship_id=496

effective_cloak=True
standard_targetable_by_opponent=False
reason=effective_cloak:documented_super_spy_ordinary_cloak_supported
```

This is the intended mechanical chain:

```text
precombat ordinary Bird Super Spy state
  -> effective_cloak=True
  -> standard_targetable_by_opponent=False
  -> opponent ordinary STANDARD request is suppressed
```

The target ship's own attack request remains independent and pre-standard PIA/C&I remain outside this projection.

## Acceptance

Every required gate passed:

```text
population_no_race_conflicts=True
population_no_payload_conflicts=True
population_no_blocked_factual_pair_regressions=True
population_no_decisive_mismatch=True
population_target_residual_present=True
population_target_residual_supported=True
production_targetability_blocks_target_residual=True
advanced_rows_remain_unresolved=True
production_effective_state_gate_passed=True
```

The retained `decisive_unresolved=3` is required. Those are the known Advanced-Cloak rows. They were historically explained in the separate Advanced-Cloak closure, but no generic precombat Advanced-Cloak resolver has been promoted.

## Evidence status

Within the narrow ordinary Bird Super Spy scope implemented by `bird_super_spy_ordinary_cloak_state(...)`:

```text
Super Spy / cloak semantics:                DOCUMENTED
decisive historical behavior:               CORPUS_OBSERVED
production helper implementation:            TESTED
production population differential:          DIFF_VERIFIED
```

Therefore ordinary Bird Super Spy directional STANDARD targetability is now production-ready within this conservative scope:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Privateer Rob ordinary-cloak targetability was already `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; both ordinary branches can now supply production precombat targetability without Host `T`, factual VCR outcome or Host messages as state inputs.

## Boundary

Do not promote:

- a generic Advanced-Cloak state resolver;
- historical ship IDs or case IDs into production;
- post-Host `T` state, factual VCR outcome or Host messages as precombat inputs;
- cloak into symmetric pair eligibility;
- cloak into `has_fuel=False`.

Advanced Cloak remains fail-closed until movement/mine/decloak phases can predict it independently.

## Next C5 gate

Move to mutable queue state, reusing the already DIFF_VERIFIED C3 ship-state carry-over:

1. survivor/destruction mutation;
2. second-pass pair eligibility and occurrence-aware side reversal;
3. capture continuation as a separate gate;
4. ship-to-planet / planet-base queue integration.

Capture must not be folded into destruction: C3 explicitly excluded captured-predecessor transitions because capture may change ownership and subsequent hostility.
