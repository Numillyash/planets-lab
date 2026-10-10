# Held-out static prediction: independent T-1 Federation race audit

Mainline after PR #165. Exact published runtime evidence:
runtime-logs/combat-mass-time-indexed-static-v1/20261010T193531Z_8949258559d5

12 independent games / 15 ship-versus-ship VCR / 30 sides. Static catalog
T-1 resolver resolved 30/30, and 26/30 *static hull component* values
happened to equal the factual total combat mass. This is NOT a 26/30
full-host-mass prediction rate.

## Four observed +50 KT residuals

- G228199 T7 V1 right, owner1, hull5: 170 hull -> 220 factual.
- G233558 T9 V1 right, owner1, hull7: 101 hull -> 151 factual.
- G235762 T8 V1 left, owner3, hull16: 60 hull -> 110 factual.
- G235762 T8 V3 left, owner5, hull9: 90 hull -> 140 factual.

Official documented Federation Crew Bonus provides +50 KT:
https://help.planets.nu/combat-mass
https://help.planets.nu/combat-races

Crucially, player slot/owner ID is **not** the race ID. In this
population there are +50 residuals for owner3 and owner5 as well.

## Follow-on experimental audit

New diagnostics: tools/diagnostics/combat_mass_tminus1_race_bonus_audit_v1.py
Wrapper: tools/run-combat-mass-tminus1-race-bonus-audit-v1-with-evidence.sh

- Reuse **exactly the already successful frozen 12-game/30-side held-out
  report**, with source schema/count/status and corpus SHA pinned.
- Reopen explicit public100 DB read-only, verify full SHA256 once.
- At each game T-1, read all archived perspectives and extract
  players[id==owner_id].raceid; missing/conflicting roster or identity
  **abstains**, never use owner slot or future/VCR race as fallback.
- Calculate **conditional documented race component** from the independent
  T-1 hull component: +50 KT for T-1 owner raceid=1, otherwise +0 KT.
- Only then compare with current factual VCR mass and VCR raceid. Current
  raceid is not a predictor input. Preserve numeric negative controls.
- Explicitly distinguish documented rule arithmetic from unverified
  campaign settings and true owner/race at combat phase, including capture.
- Never claim a full NuHost combat-mass prediction; SG, Horwasp mutable
  clans, carrier random +360 and capture activation remain unresolved.

## Single server command

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-mass-tminus1-race-bonus-audit-v1-with-evidence.sh

Produces artifacts/combat/mass-tminus1-race-bonus-audit-v1/published/report.json
and runtime-logs/combat-mass-tminus1-race-bonus-audit-v1/ evidence.

CI validates pure provenance/calculation/abstention tests; real T-1
roster availability and numerical checks require server runtime.
No production client, canonical DB, or combat executor changes.
