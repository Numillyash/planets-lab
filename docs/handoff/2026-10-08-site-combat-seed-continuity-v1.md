# Classic combat seed continuity audit v1

Date: 2026-10-08.

The 22/22 combat mass result is checkpointed in
`docs/handoff/2026-10-08-site-combat-mass-candidates-v1.md`.
The conditional right-side anti-carrier +360 KT mass modifier has not been
predictively reconstructed: 5 successes and 3 failures among 8 eligible
current-VCR observations in game 400330 T141.

This read-only gate records every factual VCR N start seed and independently
replays N to obtain Classic `final_seed`. It then checks whether the observed
N+1 start seed equals that final_seed or equals final_seed+1 (mod 119).
These are deliberately naive falsification controls. Seed initialization,
Host-wide random draws, carrier-bonus probability and cross-site sequencing
remain unresolved, even if an equality is observed.

Code:
- `tools/diagnostics/combat_site_seed_continuity_v1.py`
- `tools/run-site-combat-seed-continuity-v1.sh`
- `tools/run-site-combat-seed-continuity-v1-with-evidence.sh`

Run on the server:

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-site-combat-seed-continuity-v1-with-evidence.sh

Evidence is published to `runtime-logs/site-combat-seed-continuity-v1/`.
The marker `OBSERVATIONAL_NOT_PROMOTED` means only that diagnostics ran;
it does not demonstrate full Host RNG recovery or generative combat payloads.
