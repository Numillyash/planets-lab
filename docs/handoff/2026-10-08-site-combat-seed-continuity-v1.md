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


## Published runtime result — 2026-10-08

Runtime evidence, source main `abd9b23f1f8b0b11153dfe7968ca9a9b4e991fee`:

    runtime-logs/site-combat-seed-continuity-v1/
      20261008T043819Z_abd9b23f1f8b

    exit_code:                       0
    VCR replay_supported:          12/12
    globally adjacent transitions:   11
    next seed = prior final:        0/11
    next seed = prior final + 1:    0/11
    same-site transitions:           9
    same-site naive matches:       0/9

The two cross-site transitions V587→588 and V597→598 also reject both
naive relations. Intra-site deltas modulo 119:

    588→589  73
    589→590  71
    590→591  95
    591→592   4
    592→593  70
    593→594  20
    594→595  99
    595→596  52
    596→597  12

This rejects only direct/no-extra-call carry from Classic local final_seed.
It does NOT falsify a shared Host global RNG with other draws, nor prove
independent per-VCR seeding.

## Companion bounded control: carrier mass bonus vs local VCR seed

The eight right-vs-left-carrier observations in game400330 T141 are frozen
with their runtime provenance in:

    validation/combat/carrier-bonus-seed-offset-game400330-t141.json

The pure deterministic check:

    tools/diagnostics/combat_carrier_bonus_seed_offset_control_v1.py

tries all 119 cyclic fixed offsets in the existing Classic RANDOM_1_100 table
for these two 60%-style comparisons:

    roll <= 60
    roll >= 41

Neither condition admits an offset that exactly reconstructs all 8 factual
outcomes (5 bonus, 3 no bonus). Both variants can fit at most 7/8 rows.
This refutes a **fixed-offset local VCR seed → +360 outcome rule** for
this observed chain; it does not refute Host-global RNG or a varying number
of intervening draws. Scanning 119 offsets can overfit small samples, so
even a match would not independently validate a rule.

No executor or production code is modified. The two observations are
evidence constraints on *future seed hypotheses*, not a generative seed
algorithm. Nu's documented start-seed support (118 distinct seeds) is
separate from the replay RNG's 119-position internal cycle. See:
https://help.planets.nu/VGAP-3-differences and
https://help.planets.nu/FAQ.

## Next research priority

The deterministic portions of static combat payload (catalog hull mass,
fitted weapons, carried ammunition and damage-limited counts) can be
isolated independently from the stochastic +360 branch and unknown VCR seed.
Build a fail-closed input-projection interface with explicit unresolved
fields and validate on **additional independent games/turns**, not only T141.
Do not stitch a seed from adjacent VCR final_seed.
