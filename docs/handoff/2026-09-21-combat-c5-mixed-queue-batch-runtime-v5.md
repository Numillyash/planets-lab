# C5 mixed ship / planet-base queue — batch runtime v5

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
8aadffd019fab8017dc149eb7b3fba72097e3068
```

PR #28 remained open + draft. Game `591478` remained isolated from ordinary promotion.

## Batch execution

All nine stages completed successfully:

```text
REGRESSION TESTS                         rc=0
FACTUAL QUEUE SHAPE                      rc=0
PLANET CARRY                             rc=0
SHIP NEXT-PAIR REGRESSION                rc=0
POST-CAPTURE INITIATOR REGRESSION        rc=0
SHIP->PLANET INTERPHASE STATE            rc=0
ALL PLANET ENGAGEMENT POPULATION         rc=0
PLANET OWNERSHIP TIMELINE                rc=0
MIXED SHIP/PLANET DISCOVERY V5           rc=0
```

## Production capture-generated planet priority — CLOSED

Production repeated-planet ordering:

```text
production comparable = 35
production exact      = 35
production unresolved = 1
production mismatch   = 0
```

Capture-generated subset:

```text
capture groups             = 9
capture-reset comparable   = 8
capture-reset exact        = 8
capture-reset unresolved   = 1
capture-reset mismatch     = 0
```

The sole unresolved group remains:

```text
622476/T13 planet55
captured ship68 has no T-1 ship state
```

Bounded production semantics:

```text
captured generated order:
  preserve Friendly Code priority
  clear old Mission priority
  clear old Primary Enemy priority
  evaluate ordinary STANDARD Combat Priority
```

Engagement eligibility/targetability remains an independent upstream input.

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Ordinary planet engagement population

Still green:

```text
ordinary ship-vs-planet VCRs = 2406
ship_only                     = 1981
planet_only                   = 86
both                          = 337
unresolved                    = 2
hard residuals                = 0
planet_engagement_population_gate_passed=True
```

All factual VCR defenders are foreign to the attacking ship:

```text
vcr_defender_foreign_to_ship = 2406/2406
vcr_race_owner_exact         = 2406/2406
```

## Planet ownership timeline

Unique ordinary planet-turn combat timelines:

```text
unique timelines                 = 2303
precombat owner unchanged        = 2334 VCR rows
precombat owner changed          = 60 VCR rows
T-1 owner unresolved             = 12 VCR rows

unique precombat owner changes   = 59 planet-turns
```

Changed-owner classes:

```text
T-1 owner == attacking ship owner -> factual defender:
  43 VCR rows
  42 unique planet-turns

T-1 owner -> different third-party factual defender:
  17 VCR rows
```

Postcombat/current-T attribution:

```text
attacker owns planet  = 2043
defender retained     = 212
neutral               = 48
current owner unknown = 103
```

Acceptance:

```text
ordinary_planet_population_present=True
payload_conflicts_absent=True
pair_projection_resolved=True
all_vcr_defenders_foreign=True
vcr_race_owner_consistent=True
timeline_population_present=True
ownership_timeline_gate_passed=True
```

## Interpretation boundary

The ownership timeline does not itself reconstruct precombat ownership.

Factual VCR defender owner and T current owner remain comparator/attribution evidence only.

The immediate production gap is:

```text
T-1 planet state
  -> earlier Host ownership-changing mechanics
  -> planet owner immediately before ship-vs-planet combat
```

Official Host documentation places cargo drop to foreign planets, including Imperial Assault and Ground Combat, before later combat and processes that step in ascending Ship ID order.

The 59 changed planet-turns therefore form the next focused population, but no ground-combat rule is promoted from timing alone.

## Stable regressions

```text
ordinary mixed sites                      = 391
ship block before planet block            = 391/391
planet on RIGHT                           = 435/435
ordinary repeated planet order            = 27/27
production repeated planet order          = 35/35 comparable
ship post-mutation next pair              = 22/22
post-capture independent initiator         = 23/23
interphase supply repair gate             = passed
planet engagement population gate         = passed
planet ownership timeline gate            = passed
```

## V6 prepared after this runtime

New diagnostic:

```text
tools/diagnostics/combat_host_planet_precombat_owner_source_audit.py
```

It inventories the 59 changed planet-turns and checks T-1 source candidates:

- planet T-1 coordinates and owner;
- all T-1 ships co-located with the planet;
- ships owned by the future factual defender;
- positive `clans` cargo on those ships;
- lowest-ID defender clan-carrying ship;
- actual clan/order/target/transfer-related fields present in the T-1 ship object.

This is a source-candidate inventory only. Exact cargo-drop orders, ground-combat kill ratios, Imperial Assault conditions, Horwasp exceptions and sequential multi-ship effects remain separate until corpus-supported.
