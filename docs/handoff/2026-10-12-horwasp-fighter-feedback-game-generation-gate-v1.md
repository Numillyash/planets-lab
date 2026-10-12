# Horwasp postcombat — 2021 fighter-feedback generation gate audit V1

## Actual independent runtime evidence (PR #171)

Source commit main e6a4787a23004a3cccee0bfd28629a26735c2c24.
Evidence path runtime-logs/combat-horwasp-postcombat-clan-projection-v1/20261011T200111Z_e6a4787a2300/
Published report JSON Git blob SHA1 d58fc71d414a08f2a60618981ee3c550b7d7bf2a.
Fixed prerequisite terminal replay blob 04144af2d862a5040d822648f93bfeca8d22c1eb.
Original independent T-1 Horwasp snapshot blob 358c354d424907488dffd3665e6d6d07c8d04f64.

Five Horwasp same-turn VCR-ID transitions were evaluated with an independent
T-1 clan baseline and a derived Classic combat terminal from previous VCR N.
All five source predictions were calculable, but:
- Model mass equals observed next VCR in only 1/5.
- Model next fighter count equals next VCR in 0/4 with known fighter formula.
- Four ordinary documented-postcombat transforms show resets of damage
  to zero, torp proxy to 10000, and regenerated fighter count.
- Classic replay terminal fields are NOT yet proven to be identical to
  real Host terminal fields; VCR ID chronological order is not proven.

Specific published mass error factual minus proposed mass:
- G350094 T153 ship34 V1776->1777: +66 KT (270 predicted, 336 observed)
- G350094 T153 ship513 V1778->1779: +61 KT (832 predicted, 893 observed)
- G350094 T153 ship513 V1779->1780: +125 KT (600 predicted, 725 observed)
- G371631 T41 ship19 V314->315: +5 KT (285 predicted, 290 observed)
- G449095 T134 ship1022 V1700->1701: 0 KT (146 predicted, 146 observed)

## Critical documentation correction

Official Horwasp combat page states explicitly that fighter-destruction
feedback killing clans is enabled **for games generated on or after
January 1, 2021**. It is NOT necessarily applicable to all games in
historical validation corpora. Source:
https://help.planets.nu/horwasp-combat-strength

We must establish game GENERATION date, not the current turn's host date,
fictional Nu year, game ID or when the replay was downloaded. Without
an authoritative independent creation timestamp, the feedback flag is
UNKNOWN, not guessed. Other model assumptions still unproven:
damage rounding floor, Classic replay equivalence, fighter loss counts
and the order of postcombat state mutations.

## Next strictly controlled experimental V1

Code tools/diagnostics/combat_horwasp_fighter_feedback_gate_v1.py
Tests tests/test_combat_horwasp_fighter_feedback_gate_v1.py
Runner tools/run-combat-horwasp-fighter-feedback-gate-v1.sh
Evidence tools/run-combat-horwasp-fighter-feedback-gate-v1-with-evidence.sh

Read exact frozen source JSONs, pinned by Git blob hash. Verify explicit
immutable public100 SHA256 before read-only DuckDB open; never CURRENT.
Reconstruct each game's owner/other exact-T-1 archival game metadata
and surface candidate creation-date fields with precise member provenance.
Only explicit creation-date fields qualify for provisional ON/OFF.
Missing, conflicting or semantically ambiguous fields => gate UNKNOWN.
No game-ID/yearfrom extrapolation and no web-only date guess.

Before reading the next VCR comparator, independently construct two
fixed counterfactual transitions from the preceding Classic replay:
  OFF:  clans_next = clans - floor(cargo * terminal_damage / 100)
  ON:   clans_next = clans - floor(cargo * terminal_damage / 100)
                     - factor * (start_fighters - terminal_fighters)

where factor is 20 for Hive and 2 for other documented Horwasp hulls.
Both branches use the identical, still unverified Classic terminal.
Use fixed T-1 hull, cargo and clans, propagate each branch's own
calculated state; never adjust by the actual next VCR mass.
Then report each branch's mass and fighter error against next VCR.
Only use the historical generation-date candidate to select the
applicable branch when available, never the branch with better fit.

Illustrative frozen control before server re-run:
G371631 T41 Brood ship19 has 900/900 clans and Classic terminal 0%
damage but 13 fewer fighters. With feedback ON, predicts 285 KT,
actual VCR is 290 KT. With feedback OFF, predicts 290 KT.
This is a strong gate discriminator but NOT independent proof of
creation date, and is not a license to fit game settings from mass.
At G350094 T153 Hive ship513 first transition, both hypotheses
miss 893 KT: OFF gives 850 KT, ON gives 832 KT. Hence the time gate
alone cannot explain all discrepancies.

## Single command

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-horwasp-fighter-feedback-gate-v1-with-evidence.sh

Evidence goes to runtime-logs/combat-horwasp-fighter-feedback-gate-v1/.
This is observational/falsification research, not a new Host executor.
Do not touch planets-intel, combat executor, or DuckDB CURRENT.
