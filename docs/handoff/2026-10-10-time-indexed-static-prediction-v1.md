# Experimental pre-VCR time-indexed static resolver (V1)

Mainline continuation after temporal mass reconciliation PR #162.

## Scope and evidence gates

- Read-only, explicit SHA256-pinned public100 generation; never use or mutate CURRENT.
- Requires **successful actual V1 report** with seven reconciled sides and four aggregate-verified truncated zero-change controls. A green CI suite alone is not runtime evidence.
- Resolves only archived T-1 owner-perspective hull *mass component*. Rejects missing T-1, owner, hull, embedded-turn leakage, and disagreement among T-1 perspectives. Does not use an earliest archival catalog as a late-turn default, nor a post-turn catalog as fallback.
- Samples held-out **entire games**, excluding every game among the original 14 targeted controls. Uses the earliest available consecutive archive T-1/T pair per game, not the VCR mass, residual ranking or best-fit arithmetic. Tests contradictory and missing sources.
- Target identities (owner/hull/VCR ID) currently come from VCR for **offline evaluation**. This is not a ship identity/trajectory forecast. Neither observed mass nor any other current VCR metric enters static prediction. VCR mass enters only the evaluation function *after* the component forecast is computed.
- Reports predicted hull mass component and factual *total* VCR mass side-by-side. No claim of full combat mass prediction: generator activation, cargo/clans, Horwasp, carrier random bonus, ownership changes and mutable site ordering remain withheld. Numerical equality between the component and VCR total is a conditional observation, not proof of a phase-complete engine.
- No production, probabilistic combat executor, canonical DB, or existing V1 reconciliation mutations.

## Server execution

Run from freshly updated main:

    cd ~/projects/planets-lab
    git fetch origin && git switch main && git pull --ff-only origin main
    bash tools/run-combat-mass-predictive-pipeline-v1.sh

The pipeline first runs and publishes V1 reconciliation evidence, stopping on failure. Only then does it run the experimental resolver, recording its own evidence in the orphan runtime-logs branch.

New report: artifacts/combat/mass-time-indexed-static-v1/published/report.json
New runtime evidence: runtime-logs/combat-mass-time-indexed-static-v1/

## Next empirical boundaries

1. Inspect resolution-status distribution and truly independent game coverage from server evidence. Missing owner perspectives are not automatically negative rule examples.
2. Derive phase-aware Shield Generator eligibility from **archived T-1 geometry plus movement and precombat state**, with positive and negative controls. The current component-only code explicitly abstains from an exact mass.
3. Test Rush#27 owner transfer with terminal combat outcome replay, not VCR N+1 mass used as a feature.
4. Reconstruct Horwasp mutable clans from ordered independent battles; do not infer lost clans by subtracting VCR totals.

## 2026-10-10 runtime correction

The actual independent run (source ea2897e) failed closed with
`insufficient independent held-out games with VCRs`, after successfully
publishing reconciliation V1 evidence. V1 erroneously selected the *earliest
consecutive archive* for each independent game, which often contained no
battle VCR. It then discarded the entire game. The corrected selector
scans VCR-bearing archived candidate turns with an existing T-1 archive,
chronologically per game, and takes the first qualifying battle.
It selects on **VCR presence only** (never factual VCR mass), retains the
entire-game holdout exclusion, and never uses current mass as a resolver
input. Missing all eligible games still fails closed and reports candidate
counts. No promise of successful held-out coverage before server evidence.

The runner now shows progress before the corpus SHA verification and
throughout the game scan. Redundant shell-side full-file SHA computation
was removed; a single mandatory Python SHA256 check still runs before
the read-only database open.


## 2026-10-10 public100 runtime scope correction (after PR #164)

Actual evidence:
\`runtime-logs/combat-mass-time-indexed-static-v1/20261009T221318Z_32cd70be116d\`
completed SHA256 in 27.5 s, found 13,439 VCR-bearing archive pairs,
resolved 2/2 VCR sides in G2466 T11 and then failed in G218619 T8
with \`invalid prediction identity\`. The log does **not** include the offending
VCR ID, side, hull or owner; do not claim it is proven to be a planet.
Because game/turn were valid, a non-positive owner or hull is a plausible
trigger in the current \`resolve_mass\` validation.

Correction: explicitly define the hull-component population as ship/ship
VCRs with both positive integer hull IDs, consistent with the earlier long
mass survey. Record non-ship/unknown-hull VCRs as out-of-scope observations
rather than throwing or forecasting one side opportunistically. When owner
ID is missing/nonpositive in an otherwise in-scope VCR, abstain **only
for that side**, retaining the other side and the factually observed owner
field in the report; do not invent a faction or use postcombat ownership.
If numeric VCR comparator is missing/nonpositive, keep predicted T-1 static
component and report an explicit comparator abstention rather than a false
numeric validation. Failed full-scientific predictions remain fail closed.
The actual held-out result still requires an independent server run.
