# Ordinary Host C5: public100 independent-site coverage v1

Date: 2026-10-14. Mainline continuation after Horwasp special-rule work
was explicitly paused in
`docs/handoff/2026-10-14-horwasp-park-c5-restart.md`.

## Motivation and confirmed baseline

The bounded `combat-planar-no-horwasp` ordinary predictive queue has an
accepted 22/22 held-out next-VCR comparison:
`docs/handoff/2026-09-22-combat-predictive-queue-runtime.md`.
A separate capture mutable-site example G400330/T141 has 3/3 transitions:
`docs/handoff/2026-10-07-site-combat-terminal-replay-v1.md`.
Neither checkpoint independently proves generalized Host battle selection
on arbitrary games. The site replay diagnostic uses
`combat_capture_immediate_continuation_gate._fixture_order` and a
capture-predecessor-only target loop. Blindly running it on new games
would *not* be a meaningful validation of generality.

This stage expands the **evaluation surface** rather than inventing a
speculative full Host simulator. It is an actionable, broad C5 site
candidate set frozen independently of battle outcomes.

## Pre-registered population (strict no outcome-based selection)

Read immutable public100 DuckDB:
`generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb`,
SHA256:
`3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`.
Read-only, SHA256 exactly once before connect; never modify `CURRENT`.

From `source_members` archive turn and `typed_vcrs` EXISTENCE only,
require consecutive T-1/T and at least six qualifying archived turns
spanning >=20 turns. Preselect up to 48 distinct games by sorted
game-ID evenly spaced quantiles; choose the 20th-percentile and
85th-percentile eligible turn per game. Freeze all selected
game-turns **before reading any actual VCR payload, race, mass,
site position, pair, outcome, or capture result**. Do not filter
for attractive multi-VCR sites after seeing their battles.

For each preselected window (including zero ordinary cases), enumerate
all factual VCR shapes and exact coordinates. Produce explicit
observational `ORDINARY_SHIP_ONLY_MULTIVCR_SITE`,
`ORDINARY_MIXED_SHIP_PLANET_SITE`,
`OUT_OF_SCOPE_HORWASP_SITE`, and miscellaneous categories.
Count VCR-ID adjacent pairs and repeated owner+ship identities;
this is **not** a proof that VCR ID equals Host scheduling.

Use factual VCR ship IDs solely as target identifiers for independent
T-1 owner-perspective order-consensus readiness checks. Explicit
`ABSTAIN_NO_TMINUS1_OWNER_PERSPECTIVE` or
`ABSTAIN_OWNER_ORDER_MISSING_OR_CONFLICTING` when absent/ambiguous.
Unknown and Horwasp observations remain in denominators/out-of-scope
counts; nothing is silently removed.

The resulting per-site queue candidate list and T-1 readiness matrix
identify ordinary multi-ship cases to bring into the reusable
`site_executor` + `site_input_adapter` next, while preserving a
genuinely fresh holdout for validation. This release does **not**
predict pair/side/seed/capture order and does not score queue exactness.
Do not call it a new DIFF_VERIFIED predictor.

## Implementation

- `tools/diagnostics/combat_c5_public100_site_coverage_v1.py`
- `tests/test_combat_c5_public100_site_coverage_v1.py`
- `tools/run-combat-c5-public100-site-coverage-v1.sh`
- `tools/run-combat-c5-public100-site-coverage-v1-with-evidence.sh`

Output:
`artifacts/combat/c5-public100-site-coverage-v1/published/report.json`.

Evidence branch:
`runtime-logs/combat-c5-public100-site-coverage-v1/`.

## One server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-public100-site-coverage-v1-with-evidence.sh
```

## Follow-up: actual C5 prediction

Promote a GENERAL site queue evaluator, not more ad hoc Horwasp math:
replace the 400330-only frozen capture order with independently
reconstructed/guarded parent queue and temporary-capture inputs;
support ordinary (non-capture) predecessor as well as capture and
document unsupported O and special cases. Validate its first pair
from T-1 state then hold out next VCR N+1 after replaying N,
with strict fail-closed on missing perspective or historical outcome.
Do not use selected site observations as a fresh validation set
after fitting a candidate; acquire another preselected site split.
No production `planets-intel` changes, no mechanics promotion in v1.

Important: PR #28 is intentionally draft/open and MUST NOT be merged or
marked ready without explicit user instruction.
