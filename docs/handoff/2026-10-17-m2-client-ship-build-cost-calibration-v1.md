# M2 — client ship-build price calibration (observational V1)

## Empirical inputs and limitations

The owner's two locally redacted HAR captures yielded 555 observed
`/game/save` calls; 20 co-saved Starbase `IsBuilding:false→true`
transitions had a unique simultaneously reduced Planet MC/D/T/M
resource vector, after the StarbaseN→PlanetN ID-matching bug was
corrected in PR #221.

Only 19 of these 20 have **no registered Starbase TechLevel/TechUp
change in that save**. The 20th changed EngineTechLevel 7→10 and
EngineTechUp 0→3, with +2,400 MC relative to the same-build
no-tech-change reference. This is a **compound, client-associated
difference**, not independent proof of the per-level upgrade cost,
the precise engine price, server construction acceptance, or the
NuHost construction phase.

The 20 events describe **6 distinct game-scoped recipes**, all
stable when the one tech-change event is excluded. Repeated saves
for one recipe across many turns establish reproducibility within
the game, not independent constraints on the individual parts.

## Two contrasts that the existing data do identify

Compare only successful client co-saved resource deductions in the
**same game**, keeping hull, engine, count of changed components, and
all other selected components identical:

| Isolated client substitution | 4-component cost delta | Per-unit delta (MC,D,T,M) |
|---|---|---|
| Beam ID 2→6, count 4 | +44 MC,+48 D,0 T,+4 M | **(+11,+12,0,+1)** |
| Torpedo launcher ID 4→6, count 4 | +56 MC,+4 D,0 T,0 M | **(+14,+1,0,0)** |

A change in multiple components or a comparison spanning different
games is *not* an isolated price contrast.

This is an evidence-limited relative **client** cost mapping:
neither the component identities nor the full NuHost cost model
are causally host-verified. Repeated recipes with different spending
are marked `ABSTAIN_DIFFERENT_SPENDING_FOR_SAME_RECIPE` and not
used as calibrators. Client controls/other unobserved actions can
still contaminate these apparently isolated contrasts.

### Linear identifiability

For the explicit candidate additive model, the unknowns are
game-specific composite base costs of (HullId,EngineId) plus
per-weapon beam and torpedo launcher prices. The current stable
recipe design has:

| Client game group (anonymized) | Stable recipes | Unknown composite+weapon prices | Rational matrix rank |
|---|---:|---:|---:|
| Group A | 2 | 4 | 2 |
| Group B | 4 | 6 | 4 |

Thus **4 component price degrees of freedom remain unidentified**
even for the more modest *hull+engine bundle* additive model.
Splitting a bundle into a hull and each engine would add more
unknowns. Exact repetition does not increase rank. The public
repo's synthetic test fixture contains no live game IDs or raw
capture data.

## Implemented tools and strict safety/evidence gates

- `src/planets_lab/data/nu_build_cost_calibration.py`
  - Reads fully observed client price pairs from the existing
    `starbase_build_costs.csv`, preserving game boundaries.
  - Identifies exact repeated game-scoped recipe totals and
    single-component changes; computes **exact integer**
    per-component cost contrasts.
  - Tests linear model identifiability with exact rational
    Gaussian elimination (no floating-point approximation).
  - Separates all tech-change-associated events; it never
    adds +2400 MC as an intrinsic ship component price.
  - Exposes `predict_additive_static_build(...)` for a
    **candidate** sum of hull + (number of engines × drive cost)
    + selected beams + selected torpedo launchers. It does not
    interpret `torpedocost` as the launcher price; NuStaticSpecs
    already distinguishes launcher cost.

- `tools/diagnostics/nu_build_cost_calibration_v1.py`
  - Local read-only CSV diagnostic. No Planets.nu requests,
    HAR handling, keys or login.
  - Prints only aggregate counts; private JSON result is optional,
    created with `x` mode (never silently overwritten).
  - Static comparison is **NOT run** without all of:
    an independently supplied `/static/all` JSON,
    its expected SHA256 hash, and explicit
    `{game_id:{client_BuildHullId:global_catalog_hull_id}}` mapping.
  - Actual static source records must expose the complete price
    fields; missing components, unverified hull identities, hull
    slot mismatch and tech upgrades cause explicit abstentions.
    An exact static candidate total is still *not* an independently
    verified NuHost order-execution rule.

### Usage

From the local project checkout, after running the existing private
HAR analyses:

~~~powershell
python tools/diagnostics/nu_build_cost_calibration_v1.py --input 'C:\mydata\starbase_build_costs.csv' --output 'C:\mydata\client_build_calibration.json'
~~~

Optional external static check:

~~~powershell
python tools/diagnostics/nu_build_cost_calibration_v1.py --input 'C:\mydata\starbase_build_costs.csv' --catalog 'C:\mydata\static_all.json' --catalog-sha256 '<SHA256 OF RAW static_all.json BYTES>' --hull-map 'C:\mydata\explicit_client_to_catalog_hulls.json' --output 'C:\mydata\client_static_hypothesis.json'
~~~

Do not guess that `BuildHullId=4` means catalog `hulls[4]`.
Some game-specific hull lists or campaign choices can use different
identities. Until an independently confirmed mapping is provided,
the optional comparison must abstain.

The default run on the two private HAR files was performed locally.
All actual game IDs and economic observations remain outside the
public repository. Only aggregate conclusions and synthetic tests
are committed.

## Research status

**Observed:** client-selected recipe, same-save four-resource
deduction, isolated *relative* substitution, compound tech
associated cost.

**Still unverified:** complete price of individual hulls/engines/
weapons against a pinned static catalog for these games, actual
accepted saved command and server/Host execution, NuHost ship-build
ordering, or historical `DIFF_VERIFIED` parity.

Next: obtain verified catalog snapshots and race-specific hull
mapping through already approved data sources (without new manual
user experiments), or continue analyzing independently evidenced
in-game recipe variation. Keep C5/combat, corpus CURRENT, production
IntelBoard and draft PR #28 frozen.

See also: [555-save source handoff](2026-10-17-m2-har-continuation-151-v1.md)
and [client witness layer](2026-10-17-m2-client-economic-witness-layer-v1.md).
