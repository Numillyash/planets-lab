# Combat mass compositions v2 — Public100 signature decomposition

Date: 2026-10-08.

## Verified input checkpoint

    main 0ad926e1a3653ddde0cee5be4ae95a27ce27fdb0
    runtime-logs/combat-mass-crossgame-controls-v1/
      20261008T061802Z_0ad926e1a365

    exit_code: 0, 22 game-turns, 523 ship-vs-ship VCRs,
    1046 side mass observations

Original V1 categories:

    original Classic set:                  912
    Horwasp full-load 2× endpoint:          54
    Federation threshold-order candidate:    1
    outside those candidate sets:           79

These observations span 22 turns, not necessarily 22 distinct games. The
input VCR values are factual observational evidence, NOT predictive inputs.

## New arithmetic patterns in the 79 residuals

Official reference: https://help.planets.nu/abil-shield-generator

A Transwarp Drive 9 combat ship gets +150 KT combat mass PER effective
Saber Shield Generator. Up to two generators can contribute, so documented
numerical increments are +150 or +300. The actual generator position, its
owner, operational status, and precombat engine type are NOT given by the
VCR mass alone.

Hence possible numerical signatures are:

    +150 = 1 Transwarp Shield Generator
    +300 = 2 Transwarp Shield Generators
    +510 = +150 + right-side anti-carrier +360
    +660 = +300 + right-side anti-carrier +360

These numbers appear repeatedly among Fury (race 4) and occasional
Federation observations. Their arithmetic match does NOT prove the number
or location of generators, and the +360 RNG event is still unpredictable.

Horwasp source: https://help.planets.nu/horwasp-ships

Horwasp mass depends on clans/cargo: FULL-LOAD gives 2× hull mass.
Combat masses smaller than the doubled endpoint may indicate partially
filled cargo or casualties between sequential combats.

Examples in public100:

    game 253449 T82: Brood 145 -> 290 -> 650 -> 287
      290 = fully-loaded endpoint
      650 = 290 + 360 (right vs left carrier numeric candidate)
      287 = partial-load numeric candidate
    game 338264 T143: hull 75 -> 510 = 150 + 360
    game 217591 T149: Horwasp hull 475 -> 1310 = 950 + 360
    game 371631 T156: Fury hull 451 -> 751 = 451 + 300
      and right 451 -> 1111 = 451 + 300 + 360

Do not interpret all Horwasp fights as +100% mass: the partial-load
function and any combat-phase clan loss need independent validation.
Horwasp ships are also nonstandard dual torpedo/fighter weapon systems.

## Federation threshold order remains a narrow hypothesis

game 217591 T149 V2390, right Federation Wild Banshee:

    120 hull + 50 Federation = 170 combat base
    170 + 360 = 530 observed

This indicates *candidate* checking carrier bonus eligibility against
Fed-adjusted combat mass, rather than unadjusted hull mass. V1's
`fed_adjusted_only_eligible_sides=1` gives no additional independent
crossing cases. The rule is NOT promoted.

## Correctness hardening of conditional probability calculator

`src/planets_lab/rules/combat/probabilistic.py` now fails closed when:

- either side is race 12 (Horwasp): precombat clan-scaled mass unknown;
- a right-side Federation hull crosses the 140 KT bonus threshold only
  after Fed +50 and faces a carrier: bonus ordering unresolved.

This prevents a misleading conditional probability estimate. The existing
input restriction banning observed factual current-VCR seed and mass
still applies. All Classic-supported battles continue unchanged.

## New lightweight research gate

    tools/diagnostics/combat_mass_composition_signatures_v2.py
    tools/run-combat-mass-composition-signatures-v2.sh
    tools/run-combat-mass-composition-signatures-v2-with-evidence.sh

The tool reads the already-published local V1 JSON:

    artifacts/combat/mass-crossgame-controls-v1/public100-mass-controls.json

It verifies the source schema and all numerical side counts, then groups
the 79 original residuals by numerical candidate composition. It reports
per-race/per-game counts and a small selection of attributable examples.
NO database query or full corpus processing is required for this
postprocessing step; the runner SHA-verifies the same external public100 DB
for provenance. It does not modify any input files.

Classification is intentionally called `numeric_signature`, NOT an
independently verified Host mass rule. Unexplained residuals remain
explicitly unresolved.

## Next independent validation gate

For Fury +150/+300, collect the actual T-1 *owner-perspective* inventory
of Saber Shield Generator hulls, their engines, and precombat site/phase
colocation. A T-1 coordinate-only match is not sufficient if movement
occurs before combat.

For Horwasp, compare the T-1 owner-perspective clans to cargo capacity
and the sequence of VCR mass/weapon changes as battles consume clans.
Infer a partial-load formula only after positive and negative controls.
For the Federation threshold, seek more crossing-threshold cases.

## Server command

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-composition-signatures-v2-with-evidence.sh

Runtime evidence will publish to:

    runtime-logs/combat-mass-composition-signatures-v2/

The success marker `OBSERVATIONAL_NUMERIC_SIGNATURES_NOT_PROMOTED`
only means the arithmetic classification was completed.
