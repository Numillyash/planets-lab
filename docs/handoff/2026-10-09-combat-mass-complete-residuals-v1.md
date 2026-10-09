# Complete public100 combat mass residual attribution V1

Date: 2026-10-09.

## Source evidence

Frozen 80-game survey `21ed8147018449a3d1e1918dba9ed40cc70fb16f`:

    runtime-logs/combat-long-mass-survey-v1/
      20261009T133620Z_21ed81470184

Validated digest `8d3f7acd0e07bc5d053c7bd14a6156c4470f3e14`:

    runtime-logs/combat-long-mass-survey-digest-v1/
      20261009T141911Z_8d3f7acd0e07

80/80 games, 320 selected turns, 3912 ship-vs-ship VCR,
7821 processed sides and three missing. Of 7821 sides,
52 non-Horwasp and 15 Horwasp/catalog mismatch remain outside
original numerical classes. The first-N checkpoint sampler retained
40 VCR-side identities; **27 lacked individual IDs**.

## New targeted full-identity gate

    tools/diagnostics/combat_mass_complete_residuals_v1.py
    tools/run-combat-mass-complete-residuals-v1.sh
    tools/run-combat-mass-complete-residuals-v1-with-evidence.sh

The tool reads the immutable summary, digest and per-game checkpoints
and accesses the SAME SHA-verified public100 generation READ-ONLY.
Only game-turn pairs containing original unexplained masses are
scanned. Exactly the original 150-unique-VCR/turn cap, original
T-1 owner reconstruction, independent static catalog, and original
`_numeric_class` are reused. For each selected turn, ALL class totals
are rechecked against the frozen checkpoint. All 40 originally
saved unresolved identities must match the new observations.
The tool rejects any divergence, including missing or extra
residuals; it must recover precisely 67 VCR-side identities, including
27 previously lost to first-20 sampling.

Per observed residual, it records game/turn/VCR/ship/side/race,
catalog hull and owner T-1 engine/clans, delta from catalog/Fed
base, generator starting/waypoint geometry, potential alternate
Horwasp clan-load intervals, and carefully labelled hypothesis
of engine-cost rounding. Reports repetition by game/turn/ship ID;
same ship appearing in multiple VCR is not an independent sample.

## New engine rounding hypothesis

Previously:
    mass bonus per generator = floor(engine MC cost / 2)

Observed residual examples with Engine 1 (cost 1 MC):
    +1 KT when one generator might support
    +2 KT when two generators might support
    optionally +360 KT on right side

The **candidate** alternative is:
    bonus per generator = ceil(engine MC cost / 2)

For engine1 this is 1, not zero. Test whether the
number of T-1 co-located or co-traveling generators is
compatible with the one/two bonus candidates.
Odd-cost engines in the selected turns are retained as
numeric positive/negative controls. Crucially, this is NOT
an established Host rounding rule. The actual phase
location, activity and engine state still need independent
validation. In particular, 2x1KT cannot be inferred solely
from a +2 observed mass.

Horwasp: the existing game-specific hull catalog remains
the primary source. The published default Brood=145, when
different from game catalog, is a separate explicit
alternative; partial-clan mass is inverted only as the
UNVERIFIED linear arithmetic hypothesis. No guessed
postbattle clan count is fed into an N+1 predictor.

No combat executor, production client, corpus CURRENT,
or conditional probabilistic combat model is modified.

## Server execution

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-complete-residuals-v1-with-evidence.sh

Output:
    artifacts/combat/mass-residual-complete-v1/published/residuals.json

Evidence:
    runtime-logs/combat-mass-complete-residuals-v1/

Before numerical mechanism promotion, use independent
T-1 movement constraints, test known negative controls,
and compare expected precombat states with held-out VCRs.
