# C5 Host combat — Bird Super Spy population opportunity gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Prior checkpoint

The combined structural projection has passed:

```text
baseline_mismatch_examples=4
privateer_residual_profiles_projected_fixed=2/2
bird_residual_profiles_projected_fixed=2/2
unrelated_baseline_mismatches=0

privateer_gate_still_clean=True
bird_context_gate_clean=True
all_original_broad_mismatches_projected_fixed=True
```

See:

```text
docs/handoff/2026-09-11-combat-c5-initial-standard-combined-blocker-projection-runtime.md
```

That result is structural and still does not justify a corpus-wide Bird targetability rule from one focused Bird row.

## Active diagnostic

```text
tools/diagnostics/combat_host_bird_super_spy_attack_opportunity_audit.py
tests/test_combat_host_bird_super_spy_attack_opportunity_audit.py
```

The diagnostic scans all ordinary historical archives except game `591478` and reconstructs hostile one-way plain-STANDARD opportunities against:

```text
Bird race3
mission9 Super Spy
cloak-capable target hull
```

Targets and attackers must independently reach the factual combat site through the same position-v3 / candidate-set-v2 movement layer used by the initial STANDARD audit. Visible foreign mine-route risks fail closed. The attacker must request combat; opportunities where the Bird target also requests combat are separated rather than treated as simple directional-targetability controls.

Factual VCRs are used only after opportunity construction as outcome and queue labels.

## Effective-cloak candidate

Each Bird target is evaluated through the same conservative focused candidate that closed ship202:

```text
ordinary cloak only
damage resolved and zero
prior archived iscloaked=true
fuel safely above ordinary reference cost
reference normal movement resolved
post-move fuel safely above reference cost
ion-storm context clear
Super-Spy planet Ion Pulse context clear
Loki exposure clear
active Glory context clear
```

Advanced cloak and unresolved dynamic contexts remain unresolved. They do not silently become blockers.

## Queue-decisive labels

Only two initial queue shapes are treated as decisive:

```text
initial_pair_vcr
  => pair is proven eligible
  => expected_blocked=False

initial_skip_target_outranks_factual
  => target would have been selected first if eligible
  => expected_blocked=True
```

All later/noninitial/lower-priority shapes remain nondecisive controls.

## Acceptance

Strong acceptance requires:

```text
no_race_conflicts=True
no_payload_conflicts=True
no_blocked_factual_pair_regressions=True
no_decisive_mismatch=True
target_residual_present=True
target_residual_supported=True
```

Interpretation of unresolved rows:

- `decisive_unresolved=0` would be ideal and would materially strengthen a population-wide Bird rule;
- `decisive_unresolved>0` is not automatically a contradiction because the candidate intentionally fails closed. Every unresolved decisive row must be inspected by reason before promotion;
- any `decisive_mismatch>0` or `blocked_factual_pair_regressions>0` is a direct blocker to generic Bird targetability promotion.

## Next step after runtime

If the Bird population gate is clean enough, compose its supported states with the already DIFF_VERIFIED Privateer Rob targetability overlay and rerun the full initial STANDARD selector differential. Require all previously exact first selectors to remain exact and both original broad residuals to remain fixed.

Do not modify canonical `selection.py` or `queue.py` before that combined population differential.
