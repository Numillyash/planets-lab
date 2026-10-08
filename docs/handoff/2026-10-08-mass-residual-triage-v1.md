# Multigame conditional coverage v2: verified checkpoint and mass residual triage

Date: 2026-10-08.

## Verified V2 runtime

Source commit: `c00fe36cfa15ec7a19b1c9fe3c2ae8dc53b7c5ef`
Runtime evidence branch `runtime-logs`:

    runtime-logs/multigame-conditional-combat-coverage-v2/
      20261008T054704Z_c00fe36cfa15

Validated metadata: clean main, exit_code=0, no missing artifacts.

    10 distinct games selected (quota met)
    20/20 conditional fights evaluated
    3068 deterministic Classic scenario replays
    mass inside hull/Fed/+360 candidate set: 18
    mass outside candidate set: 2
    scan: 10 games, 10 turns, 20 VCRs; no rejections

Unlike V1 (5 games, 6 fights), V2 filled all cases without needing
multi-turn fallback. This does not independently validate conditional
outcome probabilities: current VCR supplies *all other* effective combat
fields, and uniform 1..118 seed / independent 60% carrier bonus remain
scenario assumptions.

## Two anchored residual VCRs

    game 217591 turn149 VCR2390
      left ship16 base mass980
      right ship220 base mass170, carrier bonus ineligible
      observed mass not stored in V2 JSON

    game 253449 turn82 VCR611
      left ship346 base mass70
      right ship48 candidates mass145 or 505
      observed mass not stored in V2 JSON

The original V2 report only saved boolean mass candidate coverage. Do
not invent actual observed masses or assign which side is the mismatch.

## Official external references, not independent Host evidence

- https://help.planets.nu/combat-mass — base hull, Federation +50,
  random right-side +360, Shield Generator presence
- https://help.planets.nu/abil-shield-generator — potential 1/2 engine MC
  shield generator bonus, up to two generators, and combat shield effects
- https://help.planets.nu/default-config — engine-shield default 0%

The exact source of either residual is UNKNOWN. In particular,
Shield Generator is a *hypothesis*, not a diagnosis.

## Bounded read-only follow-up

    tools/diagnostics/combat_mass_residual_triage_v1.py
    tools/run-combat-mass-residual-triage-v1.sh
    tools/run-combat-mass-residual-triage-v1-with-evidence.sh

Reads exact two original VCRs and independent hull catalog in public100,
reconstructs only their T-1/T turn snapshots and emits:

- observed side mass, hull base, residual by documented candidate
- race, owner, hull name and special text
- observed engine IDs and catalog engine cost/possible shield generator
  bonus, explicitly unproven until site and active Host modifier are known
- relevant game settings and raw ship fields from both T-1 and T
- co-located shield-generator hull candidates in raw snapshots, marked
  NOT evidence of precombat position.

This is factual diagnosis only, not a mass-rule promotion and not a
modification to the conditional simulator.

## Server run

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-residual-triage-v1-with-evidence.sh

Evidence will publish to `runtime-logs/combat-mass-residual-triage-v1/`.

Next gate after resolving exact residuals: build independent effective
combat-field projection for more than one game, with held-out current VCR
fields and explicit unsupported boundaries. Do not fit Host mass offsets
from the two observed exceptions.
