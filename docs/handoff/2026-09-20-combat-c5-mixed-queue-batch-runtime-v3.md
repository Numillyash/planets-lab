# C5 mixed ship / planet-base queue — batch runtime v3

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
26703b5556e5fe40a0bea2e3ea9c3d9f3378bbc2
```

PR #28 remained open + draft. Game `591478` remains isolated from ordinary promotion.

## Batch execution

All seven stages completed successfully:

```text
REGRESSION TESTS                         rc=0
FACTUAL QUEUE SHAPE                      rc=0
PLANET CARRY                             rc=0
SHIP NEXT-PAIR REGRESSION                rc=0
POST-CAPTURE INITIATOR REGRESSION        rc=0
SHIP->PLANET INTERPHASE STATE            rc=0
MIXED SHIP/PLANET DISCOVERY V3           rc=0
```

## Stable regressions

Still green:

```text
ordinary mixed sites=391
ship block before planet block=391/391
planet RIGHT=435/435

ordinary planet carry:
  103 transitions
  102 match
  1 not comparable
  0 mismatch

ship post-mutation next pair:
  strict 22/22
  conditional 22/22

post-capture independent initiator:
  23/23
  required unresolved=0

ordinary repeated planet order:
  production comparable=27
  production exact=27
  production mismatch=0
```

## Interphase supply repair — PRODUCTION GATE PASSED

Observed ordinary ship->planet same-ship transitions:

```text
397 total
374 exact carry
8 damage decreases
15 defeated/captured predecessor reappearances
```

Ordinary survivor state:

```text
damage:
  same=374
  decrease=8

crew:
  same=382

torpedoes:
  same=382

fighters:
  same=382
```

Supply-repair compatibility:

```text
full_tminus1_budget_exact=376
compatible_with_prior_supply_consumption=6
hard contradictions=0

observed positive repair transitions=8
production positive repair exact=7
production positive repair mismatch=0
```

The one positive repair row that is not full-T-1-budget exact remains compatible with earlier Host supply consumption. Five unchanged rows also require earlier supply consumption if one naively treats T-1 supplies as still current at the interphase step.

Acceptance:

```text
ship_to_planet_population_present=True
payload_conflicts_absent=True
required_inputs_resolved=True
supply_repair_population_present=True
all_damage_changes_supply_repair_compatible=True
production_full_budget_rows_exact=True
production_positive_repair_population_present=True
production_positive_repairs_exact=True
repair_rows_preserve_crew_and_ammunition=True
repair_rows_do_not_recharge_shields=True
ordinary_transition_population_present=True
interphase_supply_repair_gate_passed=True
```

Status:

```text
automatic supply repair:
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Production:

```text
src/planets_lab/rules/combat/interphase.py
```

## MKT boundary inventory

```text
MKT-candidate rows=36
torpedoes unchanged=36/36
```

This does **not** prove that MKT is inert at the interphase step. T-1 minerals/MC are not guaranteed to remain after earlier MKT opportunities. No MKT production rule is promoted by this corpus shape alone.

## Mixed planet initiator v3

Current mixed-site population:

```text
ship_only=338
planet_only=17
both=69
neither_basic_order=5

planet T-1 unresolved=5
ship T-1 unresolved=1

owner changed since T-1 among planet attackers=14
```

The five `neither_basic_order` rows all have the same distinctive shape:

- VCR ship owner equals VCR planet owner;
- T-1 reconstructed planet owner also equals the ship owner;
- VCR planet-side `raceid` is a different race;
- ship Primary Enemy points at that different owner/race slot in the observed examples.

The five rows are:

```text
360690/T67  ship73  planet74
511506/T24  ship158 planet299
511506/T77  ship197 planet492
511506/T78  ship176 planet63
620636/T12  ship11  planet86
```

Because documented combat requires unfriendly owners, these rows must not create a same-owner combat exception. They instead motivate an owner-attribution audit using player slot<->race mapping and post-Host planet owner state.

## Capture-containing repeated planet groups

Population remains:

```text
groups with post-capture entrant=9
captured after all ordinary attackers=8
captured interleaved before an ordinary attacker=1
```

The nine groups are fully emitted by v3.

A stronger common hypothesis emerged:

```text
for captured entrants:
  preserve Friendly Code priority
  clear old Mission/Primary Enemy aggression priority
  then apply ordinary STANDARD Combat Priority
```

This explains the observed ordering patterns qualitatively:

- nonnumeric captured ships drop to the least-aggressive priority group;
- numeric Friendly Codes remain numeric priority;
- multiple captured nonnumeric ships fall back to Ship ID ordering;
- the `621896/T25 planet5` interleaving remains possible because captured ship34 keeps numeric FC `999`.

This remains a hypothesis until a whole-population differential runs.

## V4 large batch prepared after this runtime

V4 extends the same one-command batch with:

1. race->player owner mapping from normalized `players` metadata;
2. same-owner VCR planet owner repair only when race mapping uniquely identifies a different player slot;
3. T current planet-owner confirmation of those repairs;
4. all-planet engagement population audit over all ordinary ship-vs-planet VCRs, not only mixed sites;
5. capture-reset aggression-priority differential over all capture-containing repeated planet groups;
6. all existing regression and interphase gates.

New diagnostic:

```text
tools/diagnostics/combat_host_planet_engagement_population_audit.py
```

The next runtime should determine whether the five initiator residuals are entirely owner-attribution artifacts and whether capture-reset priority is exact on every comparable capture group.
