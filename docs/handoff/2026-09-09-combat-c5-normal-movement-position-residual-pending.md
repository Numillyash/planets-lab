# C5 Host combat — normal-movement position residual context gate — pending runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains open/draft. Game `591478` remains excluded from ordinary promotion.

## Input population

The successful v2 position runtime on source:

```text
5da7144a9a1c2940b4d6e07c13f88b08274a90af
```

produced:

```text
artifacts/combat-c5-normal-movement-position-20260909-225503/report.json
```

with:

```text
position_exact ship occurrences = 1800 / 3204
position_exact factual pairs     = 677 / 1986
position_mismatch occurrences    = 10
position_mismatch factual pairs  = 9
mismatch sites                   = 7
payload_conflicts                = 0
```

The ten mismatches are a bounded movement-position residual population. They are not combat residuals.

## Diagnostic

```text
tools/diagnostics/combat_host_normal_movement_position_residual_audit.py
tests/test_combat_host_normal_movement_position_residual_audit.py
```

Schema:

```text
planets-lab.combat-host-normal-movement-position-residual-audit.v1
```

The diagnostic consumes the exact saved position report and refuses a truncated mismatch example population.

## Existing mechanics reused

No new movement formula is introduced.

For each mismatch row the audit checks:

1. archived `nuionstorms` setting, using only the mechanical boolean extracted from first/last historical turn payloads;
2. exact endpoint equality under the already implemented Nu/cloudy and Classic ion-storm models, including their existing warp-well composition;
3. the existing strong `DIFF_VERIFIED` mine-hit classifier;
4. existing route-equivalent observed Tow evidence;
5. factual post-turn survivor state only as diagnostic context.

If `nuionstorms` cannot be resolved, exact Nu/Classic storm matches remain explicitly mode-conditional rather than being promoted.

## Evidence boundary

This is an attribution-only gate.

The independent predictor result remains the T-1 position audit. The residual-context audit is allowed to inspect T/post-state and route-equivalent Tow because it is trying to explain an already-observed mismatch.

Post-state facts must never be copied into candidate-set prediction.

If a mismatch is attributable only through a random/external movement event that cannot be independently known from T-1, the correct candidate-set integration is to mark that position source `uncovered`.

## Runtime interpretation

Require first:

```text
tests rc=0
audit rc=0
```

Then inspect:

```text
summary.mismatch_rows
summary.single_exact_context_family
summary.multiple_exact_context_families
summary.unresolved
summary.candidate_family_counts
summary.candidate_context_counts
```

and every residual row.

Possible outcomes:

- **single exact context family**: strong attribution lead; verify the row detail before changing predictor coverage;
- **multiple exact context families**: keep ambiguous; do not choose one merely for closure;
- **unresolved**: preserve as a movement residual and inspect a narrower existing mechanic next (e.g. Chunnel or another pre-movement mutation) rather than weakening normal geometry.

## Promotion rule

Do not call the whole stationary/normal position layer zero-residual `DIFF_VERIFIED` until every currently predicted mismatch is either:

- explained by an independently justified mechanic and handled in the predictor, or
- moved back to an explicit fail-closed `uncovered` class.

After that, rerun the position gate. Only a clean rerun should feed validated stationary/normal positions into candidate-set v2.
