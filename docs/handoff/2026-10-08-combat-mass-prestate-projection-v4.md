# Combat mass from T−1 owner prestate: conditional candidate gate V4

Date: 2026-10-08.

## Verified V3 evidence

    runtime-logs/combat-mass-owner-provenance-v3/
      20261008T065249Z_23bdb6c50b87

    source main 23bdb6c50b87971fcf4aa0e6eecef3eb5378952e
    source_dirty false, exit_code 0
    14 selected sides, 6 original residual sides,
    T-1 owner ship observed for 13/14.

Key source observations:

- Game371631 T156 V1209: D19b hull39 catalog mass96, engine7 costs
  170 MC, two own Saber Shield Generators at VCR XY in T-1, mass266.
  Independent numeric candidate: 96 + 2*floor(170/2) = 266.
- Game371631 T156 V1193: Victorious hull35 mass451, Transwarp
  engine9 costs 300MC, same two Saber generators, VCR mass751:
  451+2*150. V1194 mass1111: 451+300+360.
- Game217591 T149 V2405/V2406/V2422/V2423: Brood hull117 game
  catalog base125 with owner T-1 clans=900 and cargo=900, yet current
  VCR mass290. Official RaceSheetPlus default Brood hull base145,
  whose full-load endpoint is 290. This mismatch requires explicit
  game-specific vs published reference catalog alternatives; do NOT
  overwrite the independent game catalog or assert Host canonicalization.
- Game217591 V2421: Brood #253 mass650, owner T-1 ship snapshot
  missing; 650 is arithmetically 2*145+360 but NOT independently
  predicted from that ship's clans.
- Game217591 V2428: Hive hull475, clans7752 / cap24000,
  mass628. Hypothetical 475+floor(475*7752/24000)=628. The
  partial-load interpolation remains unverified Host logic.
- Game253449 V618: Brood base145, T-1 900/900 clans, VCR mass287
  after prior combats in this turn: T-1 alone cannot predict mutable
  clan attrition, and a mismatch is a useful counterexample.

Official references:

- https://help.planets.nu/abil-shield-generator
- https://help.planets.nu/horwasp-ships
- https://help.planets.nu/RaceSheetPlus

## V4 gated experiment

New source:

    tools/diagnostics/combat_mass_prestate_projection_v4.py
    tools/run-combat-mass-prestate-projection-v4.sh
    tools/run-combat-mass-prestate-projection-v4-with-evidence.sh

The new pure `project_mass_candidates(prestate)` function does NOT
accept observed VCR mass. It derives candidate arithmetic masses using
independent game static hull mass plus T-1 owner-perspective evidence.

Shield Generator candidate assumptions: T-1 own combat ship at VCR XY,
up to two same-owner generator hulls there, valid engine MC cost and
documented 50%/engine rule. Both "none active" and "T-1 co-located
generators active" scenarios are enumerated, since T-1 != combat phase.
Right-side +360 is included only as a possible branch, WITHOUT proof
the opponent is an effective carrier or Host RNG fires.

Horwasp candidate assumptions: T-1 owner observed `clans/capacity`,
the documented fully-loaded 2x endpoint, and an explicitly unverified
linear interpolation for partially loaded ships. For Brood hull117,
when historic game catalog != default reference145, both bases are
retained and labelled, not collapsed. T-1 clans may be depleted during
earlier fights, so an output mismatch does not falsify the intrinsic
mass function.

The comparison with factual VCR mass occurs only AFTER projection.
Deduplicate summaries by game/turn/ship to avoid presenting 4 VCR
observations of the same Brood as 4 independent confirmations.

No modification to site executor, production, or probabilistic Classic
evaluator. This is a read-only **candidate projection research gate**,
NOT independent held-out validation.

## Server execution

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-prestate-projection-v4-with-evidence.sh

Existing local input:

    artifacts/combat/mass-owner-provenance-v3/public100-owner-provenance.json

Output:

    artifacts/combat/mass-prestate-projection-v4/public100-prestate-v4.json

Evidence:

    runtime-logs/combat-mass-prestate-projection-v4/

The status `CONDITIONAL_PRESTATE_HYPOTHESES_NOT_PROMOTED` marks
a completed observational comparison, NOT promotion of a Host rule.

Next: phase-accurate SG presence and mutable Horwasp clans over a
multi-VCR local battle queue, with independent N+1 held-out checks.
