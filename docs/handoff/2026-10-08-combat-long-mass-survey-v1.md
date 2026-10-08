# Long Public100 Combat Mass Survey V1 — extended unattended gate

Date: 2026-10-08.

## Input checkpoint

Source main `c5270a961b92074b0b351d5995b289408532a90d`.
Runtime evidence `runtime-logs/combat-mass-phase-constraints-v1/20261008T072350Z_c5270a961b92`.

The narrow phase audit established 6 Horwasp ship/game/turn groups,
16 VCR appearances, 10 same-ship transitions and 3 generator owner/site
groups. Brood #48 game253449/T82 changed mass 290 -> 287 at V618 and
fighters 70 -> 68, consistent with 13–18 *candidate* clan losses under
an unverified partial-clan linear formula. This is NOT evidence that
only two fighters were killed; Horwasp also lose clans after damage.

For game217591/T149, Saber #524 and Kittyhawk #60 and Nova #828 share
the same T−1 origin [3007,1486], waypoint [3011,1435]; their factual
combat site is [3011,1432] (0,-3 relative to waypoint). This is
a co-travel order and warp-well hypothesis, NOT precombat proof.

See official background:
https://help.planets.nu/abil-shield-generator
https://help.planets.nu/horwasp-ships
https://help.planets.nu/combat-mass

## Large-run design

Files:
- `tools/diagnostics/combat_long_mass_survey_v1.py`
- `tools/run-combat-long-mass-survey-v1.sh`
- `tools/run-combat-long-mass-survey-v1-with-evidence.sh`
- `tests/test_combat_long_mass_survey_v1.py`

Default target: up to **80 distinct games** x **4 turns per game** x
**150 unique VCR per turn** = theoretical ceiling **48,000 VCR inputs
before eligibility filtering**. The code records actual volume and
does NOT assert that the corpus contains 48k supported battles.

Game selection retains verified 400330/T141, 217591/T149,
253449/T82, 371631/T156 and evenly samples remaining public100 game
IDs. Per game, high, median, low perspective-observation-count turns
are chosen. The VCR adapter resolves duplicate perspectives and
fails closed on conflicts.

Each game is audited for factual hull/Federation/carrier mass
arithmetic, T−1 owner ship and engine MC costs, generator counts at
the factual VCR site versus same-origin/same-waypoint movements, and
Horwasp within-turn factual VCR sequences and conditional inverse
clan ranges. Game-specific static catalog data are retained. Records
without a T−1 owner perspective remain unknown, never treated as
no-generator or zero-clan facts.

None of the current-VCR mass values are used to predict battle mass;
they are used only for observational arithmetic classification and
inverse Horwasp constraints. The Horwasp interpolation is UNVERIFIED,
carrier +360 is a possible Host RNG event not independently predicted,
and raw movement orders are not combat-phase positions. No simulator,
site executor or DB CURRENT is changed.

## Checkpoints and evidence publication

Per-game checkpoints are written atomically under:

    artifacts/combat/long-mass-survey-v1/checkpoints/game-<id>.json

After each completed game, a bounded summary is atomically refreshed:

    artifacts/combat/long-mass-survey-v1/published/summary.json

The summary distinguishes `PARTIAL_CHECKPOINT_RESUMABLE_NOT_PROMOTED`,
`COMPLETE_WITH_REJECTIONS_OBSERVATIONAL_NOT_PROMOTED`, and
`COMPLETE_OBSERVATIONAL_NOT_PROMOTED`. Even a failed game is
checkpointed with an explicit rejection reason. Resume of the
same source HEAD, generation, selection and limits skips completed
games. Incompatible/stale checkpoints fail closed.

The runtime evidence wrapper publishes only the bounded `published`
summary on `runtime-logs/combat-long-mass-survey-v1/`, not the whole
potentially huge per-game checkpoint directory. Checkpoints remain
local on the server so they can be resumed.

## Unattended command

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    nohup bash tools/run-combat-long-mass-survey-v1-with-evidence.sh \
      > /tmp/combat-long-mass-survey-v1.log 2>&1 < /dev/null &
    echo "PID=$!"

Inspect periodically (not required to complete the run):

    tail -n 40 /tmp/combat-long-mass-survey-v1.log

If interrupted, repeat the SAME command on the SAME HEAD and bounds;
first ensure the old process is stopped. Do not change the Git branch
or the public100 database generation while it is active.

Tunable before initial run:
    PLANETS_LONG_MASS_GAMES=80
    PLANETS_LONG_MASS_TURNS_PER_GAME=4
    PLANETS_LONG_MASS_MAX_VCRS_PER_TURN=150

To change bounds on a resumed run, use a NEW checkpoint directory
rather than implicitly mixing output from incompatible experiment
configurations. The SHA-pinned public100 external DB path is fixed.

`nohup` protects against terminal hangup, not host shutdown or WSL
termination. Keep the computer/WSL instance running.

## Next research gate

Examine by-game residual classes and select genuine held-out
positive/negative controls. Independently resolve combat-phase
generator movement, warp-well offset, Horwasp fighter attrition and
after-combat clan changes before promoting any Host formula.
