# Multigame Conditional Classic Coverage V2

Date: 2026-10-08.

## V1 runtime closure

Published attributable source:

    runtime-logs/multigame-conditional-combat-pilot-v1/
      20261008T052217Z_1da97c94668d

Metadata verified: clean main, exit_code=0, source commit
`1da97c94668da64c9e18264dd77a973d21a5e7c3`.

    games_selected: 5
    cases_evaluated: 6
    scenario_replays: 826
    factual masses inside conditional candidates: 6/6
    games rejected from first selected turn: 10
      4 first-turn extended/nonclassic combatrng
      6 first-turn non-ship-vs-ship

The previous pilot selected one turn/game by LOWEST number of perspective
VCR observations. As shown by the output, this often selected only one
unique VCR, and some games had only a planet battle on that turn. Therefore
5 games did not imply 10 supported battles.

## V2: Coverage-oriented multiple-turn selection

Research module:

    tools/diagnostics/combat_multigame_conditional_coverage_v2.py
    tools/run-multigame-conditional-combat-coverage-v2.sh
    tools/run-multigame-conditional-combat-coverage-v2-with-evidence.sh

V2 preserves v1 evaluator and the factual input boundary:

    ORACLE_ASSISTED_CURRENT_VCR_FIELDS_EXCEPT_SEED_AND_MASS

The evaluator still enumerates uniform seeds 1..118 and independent right
carrier bonus +360 scenarios weighted by the documented 60% probability
**as explicit scenario assumptions**, not as calibrated empirical NuHost
probabilities. No alternate Host RNG, production rule, or complete combat
payload reconstruction is claimed.

V2 changes the corpus sampling policy only:

1. Read compact public100 typed `vcrs` perspective-observation counts
   for candidate turns with 2..400 rows.
2. Choose games by a deterministic even spread across sorted game IDs,
   explicitly retaining the previously verified game400330/T141 anchor.
3. For each game, rank turns by HIGHER number of perspective observations,
   examine up to four different turns, and seek two supported ship-vs-ship
   Classic VCRs across those turns.
4. Never conflate perspective rows with unique VCRs. The compact VCR adapter
   deduplicates perspectives and fails closed on input conflicts.
5. Preserve per-game, per-turn, per-VCR rejection reasons. Report separate
   achieved game coverage, achieved case coverage, total scenario replays,
   and mass candidate-set matches/mismatches.
6. If the bounded sample cannot meet a target, output a
   `PARTIAL_GAME_OR_CASE_COVERAGE` report and *do not invent matches*.

No change to the production combat executor, no conversion of current VCR
metadata into a hidden predictive input, and no mutation of corpus DB CURRENT.

## First bounded V2 run

Default target: 10 distinct games, two supported ship-vs-ship battles each.
Scan <=35 diverse games and <=4 candidate turns per game.

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-multigame-conditional-combat-coverage-v2-with-evidence.sh

Output:

    artifacts/combat/multigame-conditional-coverage-v2/public100-coverage-v2.json

Evidence:

    runtime-logs/multigame-conditional-combat-coverage-v2/

The v2 runner uses the exact explicit public100 generation and SHA, and
does not rely on the corpus `CURRENT` alias. Its output is a scientific
coverage report: reaching ten games but fewer than twenty cases is PARTIAL.

After this run: compare coverage and mass residuals across independent
games, identify new variant classes; only then increase the sample to
20+ games or add independent effective-field reconstruction.
