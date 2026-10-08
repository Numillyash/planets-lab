# Combat mass: owner-perspective provenance gate v3

Date: 2026-10-08.

## Verified cross-game numeric evidence

Source SHA: `8d6542094e3c2e06e07c26b73aac8e6664fc2a17`.

Published runtime evidence:

    runtime-logs/combat-mass-composition-signatures-v2/
      20261008T063453Z_8d6542094e3c

    status OBSERVATIONAL_NUMERIC_SIGNATURES_NOT_PROMOTED
    turns 22; VCRs 523; side observations 1046
    original unexplained 79
    numerically grouped candidate signatures 73
    unexplained even numerically 6

Result breakdown:

    912 original classic-mass candidate observations
     54 Horwasp 2x hull endpoints
     19 Horwasp 2x + 360 arithmetic candidates
     10 Horwasp partial-load numeric candidates
      1 Federation +50 before 140KT threshold hypothesis
      6 one-generator +150 candidates
     31 two-generators +300 candidates
      3 one-generator + anti-carrier +510 candidates
      4 two-generators + anti-carrier +660 candidates
      6 unresolved nonadditive observations

These are NOT causal reconstructions of the engine/generator positions,
intervening Host phases, Horwasp load, or global RNG.

## Why another probe, and what it tests

The six last residuals include Brood hull #117 in game 217591,
whose game-specific static hull mass is reported as 125 KT but whose
observed VCR mass can be 290 KT. Game 253449 has the same hull ID with
static 145 KT and observed 290 KT. Do not silently normalize distinct
historical per-game catalogs or assume an arbitrary 20KT correction.

Official Shield Generator documentation:
https://help.planets.nu/abil-shield-generator

Combat mass bonuses are tied to engine cost and presence of up to two
friendly generators in the same location. Transwarp generates +150 KT
per working generator. Generator location/owner in a historical snapshot
does NOT independently prove precombat effectiveness.

Official Horwasp documentation:
https://help.planets.nu/horwasp-ships
https://help.planets.nu/horwasp-combat-strength

Clan occupancy controls combat mass, weapon strength and fighter amount;
clan losses from successive combat can change these.

New read-only gate:

    tools/diagnostics/combat_mass_owner_provenance_v3.py
    tools/run-combat-mass-owner-provenance-v3.sh
    tools/run-combat-mass-owner-provenance-v3-with-evidence.sh

It reuses the v2 JSON already present on the server, selects ALL six
unresolved mass observations and up to eight representative arithmetic
controls. It verifies each against the actual current VCR, then reads
archived T-1/T OWNER-perspective snapshots for involved ship owners only.

The report includes:
- game-specific hull mass and cargo capacity for every selected hull;
- T-1/T participant clans, engine ID and engine MC cost when observed;
- owner's observed Saber Shield Generator inventory and exact T-1/T
  coordinate coincidence with the factual VCR site;
- missing owner perspectives and the temporal limitations of snapshot data.

An observed generator coordinate or clan count does not yet prove exact
Host precombat state. V3 does not modify probability evaluator, Host
mechanics, or corpus DB. It is a provenance instrument.

## Server execution

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-owner-provenance-v3-with-evidence.sh

Output:

    artifacts/combat/mass-owner-provenance-v3/public100-owner-provenance.json

Published evidence path:

    runtime-logs/combat-mass-owner-provenance-v3/

Next: use owner-perspective evidence and existing phase-aware movement
observations to build targeted positive/negative controls for SG support,
and separate game-specific Horwasp hull catalog semantics before
proposing a clan interpolation rule.
