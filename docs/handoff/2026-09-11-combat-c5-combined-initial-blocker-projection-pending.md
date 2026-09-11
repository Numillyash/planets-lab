# C5 Host combat — combined initial blocker projection gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Preconditions

Both original broad initial-target blockers now have independent evidence-scoped closures:

```text
360690/T83 ship98:
  Privateer Rob ordinary-cloak threshold targetability
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

511506/T94 ship202:
  Bird Super Spy documented ordinary-cloak targetability
  DOCUMENTED + CORPUS_OBSERVED + TESTED
```

The Bird runtime is recorded in:

```text
docs/handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-runtime.md
```

## Active diagnostic

```text
tools/diagnostics/combat_host_initial_standard_combined_blocker_projection_audit.py
tests/test_combat_host_initial_standard_combined_blocker_projection_audit.py
```

Schema:

```text
planets-lab.combat-host-initial-standard-combined-blocker-projection-audit.v1
```

This is a structural composition gate only. It intentionally reuses the already accepted Privateer selector-impact differential and the accepted Bird dynamic-context gate. It does **not** yet generalize Bird targetability over the entire corpus and does not alter canonical selection.

## Projection rule

For each baseline initial-target mismatch, a blocker may project a repair only when:

```text
predicted target == independently supported blocked target
predicted active == factual RIGHT/active ship
factual target rank within that active ship == 2
```

This means removing exactly the independently supported rank-1 target exposes the factual rank-2 target without changing active-ship ordering.

## Acceptance

Require all flags true:

```text
privateer_gate_still_clean
bird_context_gate_clean
privateer_residual_all_profiles_projected_fixed
bird_residual_all_profiles_projected_fixed
no_unrelated_baseline_mismatches
all_original_broad_mismatches_projected_fixed
```

Expected profile counts from the current baseline are two Privateer profiles and two Bird profiles (strict + conditional for each residual).

Any unrelated mismatch means the original broad mismatch inventory changed and must be investigated before proceeding.

## Next step if clean

A clean result closes **composition of the two known initial residuals**, but is not yet sufficient for canonical integration.

Next gate:

1. build population-wide Bird Super Spy directional targetability opportunities using the same independent position/candidate reconstruction;
2. apply the strict documented/dynamic Bird state across those opportunities;
3. combine that with the already population-tested Privateer overlay;
4. rerun full initial STANDARD targetability/selector impact;
5. require zero factual-pair and first-selector regressions across the corpus;
6. only then promote the generic directional STANDARD targetability layer and canonical first selector.

Do not special-case ship IDs in canonical code.
