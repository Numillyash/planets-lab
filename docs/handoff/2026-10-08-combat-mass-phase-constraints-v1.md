# Mass phase constraints — Horwasp VCR sequence and SG waypoint evidence

Date: 2026-10-08

## Runtime checkpoint

Published V4 runtime at `runtime-logs/combat-mass-prestate-projection-v4/20261008T070643Z_4a23e110375d`, source `4a23e110375d6c3013c67e5d650fe8ef23865596`, clean, exit=0.

14 factual VCR sides, 10/14 matches to CONDITIONAL T-1 candidate sets, five of six original exceptional sides. One of the six (Brood ship253) is unresolved because T-1 owner ship state is missing.

Four V4 misses:
- game217591 T149 Brood ship253 V2421: absent T-1 participant row
- game217591 T149 Kittyhawk ship60 V2399 and Nova ship828 V2398:
  T-1 position differs from VCR site, actual SG movement requires checking
- game253449 T82 Brood ship48 V618: T-1 full cargo 900/900, but VCR
  mass287 rather than 290, consistent with intra-turn clan attrition

Published rules:
- https://help.planets.nu/horwasp-combat-strength: Brood/Soldier lose
  2 clans per fighter destroyed since 2021 and lose clans after combat
  based on damage; exact fighting losses must be independently determined.
- https://help.planets.nu/horwasp-ships: Horwasp mass depends on
  clan occupancy, fully-loaded 2x is documented; linear partial-clan
  interpolation remains an unverified hypothesis.
- https://help.planets.nu/abil-shield-generator: same-owner co-located
  generator adds half engine MC as combat mass, max two (engine7 +85,
  engine9 +150 each). A waypoint is not a resolved movement prediction.

## Read-only experiment

`tools/diagnostics/combat_mass_phase_constraints_v1.py`
`tools/run-combat-mass-phase-constraints-v1.sh`
`tools/run-combat-mass-phase-constraints-v1-with-evidence.sh`

Input uses already published v3 owner snapshots. Targets all Horwasp
ships selected by v3, including Brood48, 119, 253, 517; pulls every
current-VCR appearance at the specified game/turn. It records ordered
VCR start masses, fighters, damage, bays, site and side.

For each observed mass it **inverts** the proposed (not proven) formula

    mass = H + floor(H*clans/capacity) + optional_right_360

to a bounded interval of possible integer clan counts. H is the per-game
catalog mass; for Brood117 with non-145 historic H, published default
145 is kept as an explicitly separate, unverified alternative.
The +360 branch is only allowed when the ship is on the right against
a factual left side with effective fighter bays, and is NOT a predicted
random draw or evidence of Host bonus eligibility ordering.

Consecutive appearances of the same ship have interval subtraction,
possible clan loss ranges and start fighter-count changes. No inferred
clan count is fed to a subsequent VCR: both VCR masses remain factual
comparators, not N+1 forecasts.

For non-Horwasp samples, the tool reads T-1 owner-perspective raw ship
rows for all named combat participants and **every own generator**,
including raw coordinates, ordered waypoint, warp, damage, mission and
fuel. A generator at the right waypoint is a rendezvous candidate, not
proof of actual precombat position. A T-1 snapshot at the site is not
phase-accurate either.

No changes to the probabilistic ensemble, site executor, corpus DB
CURRENT, or production. All unresolved fields remain explicit.

## Server command

    cd ~/projects/planets-lab
    git fetch origin && git switch main && git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-phase-constraints-v1-with-evidence.sh

Output:

    artifacts/combat/mass-phase-constraints-v1/public100-phase-constraints.json

Evidence branch:

    runtime-logs/combat-mass-phase-constraints-v1/

A completed observational gate is NOT validated Host parity.
