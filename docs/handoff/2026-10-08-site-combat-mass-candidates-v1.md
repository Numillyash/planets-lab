# Combat mass candidate set — V1 read-only gate

Date: 2026-10-08

## Input and observed signature

    source b1a88cb7e96ed1b93f5b70ad4e73155c4d8c5a62
    runtime-logs/site-combat-payload-provenance-v1/
      20261008T040314Z_b1a88cb7e96e

    status OBSERVATIONAL_NOT_PROMOTED
    4 current VCR observations
    8 factual side observations
    T-1 raw.mass vs VCR.mass: observed_different 8/8

The main striking signature:

    V592 right ship140 mass510 vs T-1 mass231; left ship184 carrier
    V593 left  ship140 mass150 vs T-1 mass231
    V593 right ship170 mass150 vs T-1 mass235; left ship140 noncarrier
    V594 right ship170 mass510 vs T-1 mass235; left ship184 carrier
    V595 left  ship170 mass150 vs T-1 mass235
    V595 right ship382 mass645 vs T-1 mass794

This is consistent with a combat-mass/base-hull distinction and possible
360 KT right-side anti-carrier bonus. No RNG outcome or Host formula was
deduced from these observations.

## Official documented rules

- https://help.planets.nu/combat-mass
- https://help.planets.nu/combat-basics

Ship combat mass is based on hull mass, not a ship's movement/cargo mass.
The right-side anti-carrier combat mass +360 occurs conditionally with
60% chance when the right ship's combat hull mass is >=140 and the left
ship is a carrier. Federation ownership adds +50 combat mass.
Shield Generators and special/campaign rules can add other modifiers.

## New research-only gate

    tools/diagnostics/combat_site_mass_candidates_v1.py
    tools/run-site-combat-mass-candidates-v1.sh
    tools/run-site-combat-mass-candidates-v1-with-evidence.sh

The script reads public100 game 400330 turn 141 using the existing compact VCR
reader and immutable game static NuStaticSpecs. It checks all ship-vs-ship VCR
observations for allowed sets:

    base = catalog[hullid].mass + (50 if factual raceid==1 else 0)

    left candidate = {base}

    right candidate = {base, base+360}
      ONLY if left effective baycount>0 and right hull mass>=140

This is deliberately an **observational candidate set**, NOT a binary
prediction of whether the probability fires. The left "is carrier" proxy
is inferred from factual effective baycount, not independently predicted
hull/ship equipment. No Shield Generator effects are modeled, so potential
residuals remain unresolved instead of being forced.

The classification supports documented_candidate_match,
outside_documented_candidate_set, and unresolved_hull_or_mass.

No rule is promoted, no changes to executor or terminal replay. Current-VCR
seed is recorded solely as a factual observation. O remains fail-closed.

## Runtime and evidence

    cd ~/projects/planets-lab
    git fetch origin && git switch main && git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-site-combat-mass-candidates-v1-with-evidence.sh

Evidence:

    runtime-logs/site-combat-mass-candidates-v1/

Successful completion marker:

    OBSERVATIONAL_NOT_PROMOTED

Interpretation: run completed, no candidate mass formula has been promoted.

## Runtime closure — 2026-10-08

Verified server evidence, source main 6e329474f940def9d202391a657cd57b85a5940c:

    runtime-logs/site-combat-mass-candidates-v1/
      20261008T041759Z_6e329474f940

    exit_code:                        0
    ship_vs_ship_vcrs:             11
    side observations:            22
    documented_candidate_match:   22
    outside_documented_set:        0
    right_carrier_bonus_eligible:  8
    right_carrier_bonus_observed:  5
    eligible without bonus:        3
    non_ship_vs_ship:              1

V587–V597 were checked against the actual public100 game 400330 turn 141
NuStaticSpecs. The observed hull-base and optional right-side +360 values
match the documented candidate sets for all 22 ship sides. All 11 factual
left-side masses were consistent with hull catalog mass; five eligible
right-side observations contained +360 and three contained no bonus.

This is DOCUMENTED + CORPUS_OBSERVED + TESTED for the *candidate-set scope*
of this one turn, not a deterministic 60% RNG branch reconstruction.
The 8 eligible observations are far too few to estimate or prove 60%.
No Federation +50 or Shield Generator branch is independently exercised
by this scoped population. Do not treat 22/22 as a universal engine.

Mass does not directly use T-1 loadturn.ship.mass. Combat seed and whether
+360 fires remain independent unresolved generative inputs.

Next evidence gate: replay each factual VCR to its internal final_seed,
then audit whether the next VCR's observed start seed is simply the same
global state or shifted by one. This must remain observational and cannot
use N+1 seed as an input to predicting N+1 combat.
