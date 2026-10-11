# Horwasp: documented postcombat clan/weapon reset research V1

## Frozen verified runtime

PR #170 source main e3ac3071609dcea2b1b71ca9a5d573fc46386759.
Evidence runtime-logs/combat-horwasp-terminal-continuity-v1/20261011T194131Z_e3ac3071609d
Published report Git blob SHA1: 04144af2d862a5040d822648f93bfeca8d22c1eb.
Original T-1 clan hypothesis blob SHA1: 358c354d424907488dffd3665e6d6d07c8d04f64.

Actual runtime returned FIVE Horwasp replay-N-to-next-VCR comparisons:
all 5 `CLASSIC_REPLAY_TERMINAL_TO_NEXT_START_MISMATCH`. All Classic
replays were available. The 15 ordinary-ship controls had 5 exact
and 10 mismatches.

Detailed cross-tab from immutable published 20-transition report:
- Horwasp (5): 4 terminal damage >0 -> next start 0; 4 prior
  terminal torpedoes under 10000 -> next start 10000; 4 next
  fighter counts exceed Classic terminal; all 5 crew and shield
  fields match the terminal.
- Ordinary (15): all fighter fields match; 7 damage mismatch
  toward higher next damage; 7 crew mismatch toward lower next
  crew; 9 shield mismatch. Ordinary damage/mutation behavior
  differs qualitatively from Horwasp.
- These are comparisons against DERIVED NuHost Classic replay
  terminal, not independent verified Host termination. No
  replay terminal Horwasp clans have been reconstructed.

## Official documented rules

https://help.planets.nu/horwasp-combat-strength
https://help.planets.nu/horwasp-ships

Horwasp combat damage is converted after each fight to lost clans:
e.g., a Hive damaged 12% loses 2880/24000 clans if sufficient.
Otherwise partial repair remains; this V1 ABSTAINS on insufficient clans.
For games generated 2021 onward, lost fighters kill 20 clans each
for Hive, 2 each for Soldier/Brood and other documented ships.
Torps are effectively unlimited (the VCR proxy count can reset
to 10000). Hive replenishes fighters up to its clan-dependent limit.
Documented capacity-based fighter complement for known ships:
Hive 70 max, 10 base; Brood 70 max,10 base; Soldier 40 max,10 base.
The start-minus-Classic-terminal-fighters loss proxy and floor
damage rounding in our experiment are UNVERIFIED for exact NuHost.

## New V1 experiment

tools/diagnostics/combat_horwasp_postcombat_clan_projection_v1.py
tools/run-combat-horwasp-postcombat-clan-projection-v1.sh
tools/run-combat-horwasp-postcombat-clan-projection-v1-with-evidence.sh
tests/test_combat_horwasp_postcombat_clan_projection_v1.py

Pins both completed reports byte-for-byte by Git blob SHA1.
Rechecks exact 4 frozen Horwasp chains and 5 transitions plus
all 15 standard-ship controls, and explicit public100 SHA256.
DuckDB is opened read-only. NEVER change CURRENT or production.

For each Horwasp chain: initialize clans from T-1 independently
observed owner archive. At encounter N use only N's factual
fighter start and the already FROZEN Classic replay terminal
damage/fighters, with no N+1 start or mass in the calculator.
Compute conditional after-combat clan loss as:

    fighters_lost_proxy = N_start_fighters - N_replay_terminal_fighters
    clan_fighter_loss = fighters_lost_proxy * (20 if Hive else 2)
    clan_damage_loss = floor(cargo_capacity * replay_damage_pct / 100)
    next_clans = prev_clans - clan_fighter_loss - clan_damage_loss
    next_mass = hull_mass + floor(hull_mass * next_clans / capacity)
    next_fighters = base + floor(next_clans*(max-base)/capacity)

Each candidate is built BEFORE reading the N+1 VCR comparator.
If no valid source, nonzero N start damage, inconsistent fighter
proxy, replay defeat or insufficient clans to repair, ABSTAIN.
Never invert next factual mass into clans, revise rule constants
based on residuals or substitute N+1 as predictor input.
Subsequent attempts carry only MODEL-predicted clans, not
observed next values; an abstention propagates.

Check whether this derived Classic-terminal/documented-phase
candidate actually matches the 5 observed next VCR masses and
fighter counts. Report all mismatches openly. A mismatch is
plausible because Classic replay's terminal and real Host N
outcome are NOT independently identical; numeric equality
alone is NOT proof of Host phase order or execution chronology.

## One server command

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-horwasp-postcombat-clan-projection-v1-with-evidence.sh

Output: artifacts/combat/horwasp-postcombat-clan-projection-v1/published/report.json
Runtime evidence: runtime-logs/combat-horwasp-postcombat-clan-projection-v1/

No production planets-intel change, no combat executor promotion,
no clone of postcombat observed mass into phase mechanism.
