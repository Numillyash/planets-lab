# Combat mass residuals: Federation threshold & Horwasp endpoint

Date: 2026-10-08.

## Verified observed residuals

Evidence path:

    runtime-logs/combat-mass-residual-triage-v1/
      20261008T060907Z_fa84d1c813b7

Source is clean main `fa84d1c813b7d45f237aab730af3cc2f43c3582e`, exit_code=0.

**Case A — game217591 T149 V2390**:

- LEFT: Gorbie, hull #70, 980 KT, 10 effective bays, race 8.
- RIGHT: Wild Banshee, hull #2006, race 1 (Federation).
- RIGHT independent hull mass is 120 KT.
- Observed combat mass is 530 KT = 120 + 50 Fed + 360 anti-carrier.
- The existing evaluator uses right `hull.mass >=140` to enable +360;
  hence it misses this case. A threshold checked *after* Federation +50
  gives 170>=140, consistent with the VCR. Official combat mass docs say
  a ship "of 140 KT or more", but do NOT define the exact ordering of
  these two modifiers. Do not promote this as a proven Host ordering rule.
- No co-located Shield Generator candidate in T-1/T snapshots, although
  absence from partial visibility does not rule it out.
- T-1 owner-perspective raw ship is present; some other perspective
  observations contain 0 engine/weapon IDs. Never treat hidden-data
  zeros as factual ship configurations.

**Case B — game253449 T82 V611**:

- LEFT: Red Wind Carrier, hull #47, race 3, 70 KT, 2 effective bays.
- RIGHT: Brood, hull #117, race 12 (Horwasp), 145 KT hull.
- Observed mass **290 KT = 2 x 145**.
- Official Horwasp starship rules explicitly say combat mass depends on
  clans/cargo and a fully loaded ship reaches double hull mass.
- **2x is an endpoint, not a formula for partially loaded Horwasp**.
  The current residual-probe left raw ship `clans` out; independent
  ship-clans provenance is still needed to verify the precombat load.
- Since the Brood has both torpedo tubes and fighter bays, do not
  reinterpret its shared Nu `ammo` as ordinary physical torps/fighters
  or promote Horwasp combat to ordinary Classic rules.
- No co-located Shield Generator candidate in observed T-1/T snapshots.

External docs (documented background, not independent experiment):

- https://help.planets.nu/combat-mass
- https://help.planets.nu/horwasp-ships
- https://help.planets.nu/horwasp-combat-strength

## Independent cross-game control experiment

Code:

    tools/diagnostics/combat_mass_crossgame_controls_v1.py
    tools/run-combat-mass-crossgame-controls-v1.sh
    tools/run-combat-mass-crossgame-controls-v1-with-evidence.sh

The observational-only tool compares the existing hull threshold candidate
against *separately labelled* Fed-adjusted threshold hypothesis and Horwasp
fully-loaded 2x endpoint on three fixed anchor turns and up to twenty further
diverse game/turn candidates from public100. It reads historical factual VCR
masses, never feeds these into the combat evaluator. It also queries the
Horwasp ship #48 T-1 owner-perspective `clans` and catalog cargo capacity.

It reports ALL non-matches instead of forcing a new universal mass formula.
Count evidence per game and classify positive/negative controls.

## Run on server

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-crossgame-controls-v1-with-evidence.sh

Evidence:

    runtime-logs/combat-mass-crossgame-controls-v1/

Success marker:

    OBSERVATIONAL_CROSSGAME_NOT_PROMOTED

Do not report this marker as predictive Host parity. The next research
step is to check the number of Fed threshold-crossing examples and Horwasp
partial/full-load examples. Only then consider extending the pure
probabilistic mass scenario builder, behind a dedicated Horwasp
fail-closed boundary until effective weapons and clan dynamics are known.
