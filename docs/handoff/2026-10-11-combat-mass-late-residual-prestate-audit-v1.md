# Experimental late combat mass residual / T-1 prestate audit V1

## Frozen public100 result

Successful independent early/late stress at source main
95ed2f51e7bbad0d5355c60f0f50eba2c1568ffa.

Immutable evidence:
runtime-logs/combat-mass-independent-late-turn-stress-v1/20261010T225044Z_95ed2f51e7bb/

Pin: runtime-logs published report.json Git blob SHA-1
b6a373e4ea9f6274f9169c8e8aad4db7cc5e2f2e.

24 new independent games, 48 preselected windows (44 ship-bearing).
212 ship-vs-ship VCR, 424 sides, 241 out-of-scope VCR.
Independent exact T-1 hull mass and owner race resolved for all 424.
Conditional T-1 hull+Fed mass equals factual VCR total in 353/424;
71 observed residuals. No full combat mass predictions.

Breakdown verified directly against frozen report:
- 35 ordinary-race sides +360KT: ALL right sides, across 9 races.
  This is numerical/side evidence, NOT proof of the carrier RNG or
  the left fighter bay condition.
- 26 Horwasp race12 sides: 25 have various mutable deltas; 1
  shows +1KT. Do not substitute a postcombat clan count.
- 10 other standard race4/hull35 right sides, several deltas
  including +1, +150 and +361. Potential shield/capture phase
  needs independent engine and SG geometry controls.
- 17/132 (12.88%) early sides and 54/292 (18.49%) later sides
  mismatch. These are not independent binomial samples at ship
  level because repeated ships and same-site battle chains cluster.
- G350094/T153 VCR1771-1781 supplies especially interesting
  repeated-combat site/ship identities; investigate chronology.

## New read-only observational audit

Code:
tools/diagnostics/combat_mass_late_residual_prestate_audit_v1.py
Runner / evidence wrapper:
tools/run-combat-mass-late-residual-prestate-audit-v1.sh
tools/run-combat-mass-late-residual-prestate-audit-v1-with-evidence.sh

Scientific constraints:

1. Pin exact upstream 1.8MB report by Git blob SHA1 and the explicit
   immutable public100 DB by SHA256, open database read-only. Never
   touch CURRENT.
2. Retain ALL frozen 424 sides, original game/turn/VCR/owner/ship,
   conditional mass, observed mass and residual classifications.
   Detect any drift against independently reconstructed current VCR.
3. Derive T-1 owner ship, clans, engine, and hull cargo ONLY from
   owner-perspective T-1 archive, checking all owner perspectives.
   Missing owner ship, inconsistent clans or catalog cause explicit
   ABSTAIN; never backsolve clans from observed combat mass.
4. For retrospective carrier geometric cross-tab, compare right
   combat side and LEFT baycount from current VCR against all
   +360 sides and matched right-side negative controls. The VCR
   fighter bay count is NOT an independent prebattle prediction.
   Do not promote Host randomness or claim +360 deterministically.
5. Record T-1 exact-position shield generator ships for owner
   relative to the *observed* current VCR site. Since site was
   obtained from factual VCR, and same-turn movement or captures
   remain unresolved, co-location is observational support only.
   Documented engine bonus table is not generator activation.
6. Capture Horwasp T-1 clans and hull cargo independently; keep
   the 26 race12 residual cases as distinct mutable-state
   questions. No guessed interpolation/clan attrition by inverted
   factual masses.
7. Record early versus late and all categories; do not recalibrate
   or introduce a new runtime combat-mass predictor.

No changes to production planets-intel or mainline combat executor,
no db mutation and no NuHost mechanics promoted.

## Server command

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-mass-late-residual-prestate-audit-v1-with-evidence.sh

Output:
artifacts/combat/mass-late-residual-prestate-audit-v1/published/report.json

Evidence:
runtime-logs/combat-mass-late-residual-prestate-audit-v1/

The real server result must establish carrier control specificity,
historical clans availability and SG T-1 coverage. Do not claim
these from static CI.
