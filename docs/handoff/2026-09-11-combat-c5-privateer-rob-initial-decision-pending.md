# C5 Host combat — Privateer Rob initial-decision pending

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Dependencies:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md
docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md
```

The attack-opportunity runtime produced 16 independently reconstructed strict/conditional plain-STANDARD opportunities against Privateer race5 mission9/Rob PE0 cloak-capable targets:

```text
prior true:  attacker_fought_other=8, pair_vcr=2
prior false: pair_vcr=5, neither_vcr=1
```

The two `true:pair_vcr` rows reject raw prior `iscloaked` as a blocker. The eight `attacker_fought_other` rows cannot yet be read as protected targets because ordinary target priority and attacker survival can explain a skipped target after another fight.

## Diagnostic

```text
tools/diagnostics/combat_host_privateer_rob_initial_decision_audit.py
tests/test_combat_host_privateer_rob_initial_decision_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-initial-decision-audit.v1
```

The diagnostic reuses the already defined attack-opportunity population, then uses factual VCR order only as a held-out queue observation. For each opportunity it resolves:

```text
target standard_battle_priority_key
first factual VCR involving the attacker
whether that attacker VCR is the first VCR at the site
factual first opponent of the attacker
that opponent's standard_battle_priority_key
whether the opportunity pair is the attacker's first factual pair
whether the skipped target outranks the factual first opponent
```

Classifications:

```text
initial_pair_vcr
later_pair_vcr
initial_skip_target_outranks_factual
initial_skip_target_not_above_factual
noninitial_attacker_context
attacker_no_factual_vcr
```

## Strong evidence boundary

The strongest blocker residual is:

```text
initial_skip_target_outranks_factual
```

because no earlier VCR at that site can have mutated the attacker or target list. If a reconstructed target is genuinely targetable, documented/highly-validated STANDARD ordering says it should be selected before a lower-priority factual target.

Known target `360690/T83/ship98` is expected to fall into this bucket from the previous initial-target audit:

```text
active264 is the factual first active ship
target98 priority rank 1
factual target190 priority rank 2
Host chooses 190, not 98
```

This is a clean missing-blocker/state residual, independent of later attacker survival.

Conversely, `true:pair_vcr` controls must be checked for whether they are initial. If a prior-true Privateer Rob target is itself selected as the first pair without any earlier queue mutation, raw prior cloak is even more decisively disproved as effective target protection.

## What this gate does not do

- no survivor/destruction replay for later attacker appearances;
- no Loki/ion/mine/glory decloak inference;
- no ordinary active-cloak reconstruction;
- no `selection.py` or `queue.py` change;
- no target-order inversion.

After this runtime, investigate dynamic decloak/effective-state context only for clean initial residuals. Later queue cases should be deferred to the mutable survivor/destruction phase rather than used to infer targetability.
