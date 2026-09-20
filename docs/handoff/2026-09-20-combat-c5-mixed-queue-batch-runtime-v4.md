# C5 mixed ship / planet-base queue — batch runtime v4

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
f48e39ee46ce5a9f8d7605adbb320d61b3e5883f
```

PR #28 remained open + draft. Game `591478` remained isolated from ordinary promotion.

## Batch result

All eight stages passed:

```text
REGRESSION TESTS                         rc=0
FACTUAL QUEUE SHAPE                      rc=0
PLANET CARRY                             rc=0
SHIP NEXT-PAIR REGRESSION                rc=0
POST-CAPTURE INITIATOR REGRESSION        rc=0
SHIP->PLANET INTERPHASE STATE            rc=0
ALL PLANET ENGAGEMENT POPULATION         rc=0
MIXED SHIP/PLANET DISCOVERY V4           rc=0
```

## Ordinary ship-vs-planet initiator population

The new all-planet sweep covered every ordinary ship-vs-planet VCR:

```text
ordinary_ship_vs_planet_vcrs = 2406
payload_conflicts             = 0

explanation:
  ship_only    = 1981
  planet_only  = 86
  both         = 337
  unresolved   = 2
  hard_residual= 0

T-1 unresolved context:
  planet = 29
  ship   = 3
```

Acceptance:

```text
ordinary_planet_population_present=True
payload_conflicts_absent=True
pair_projection_resolved=True
owner_repair_population_if_observed_is_resolved=True
explained_population_present=True
no_hard_initiator_residuals=True
planet_engagement_population_gate_passed=True
```

This is a strong **population attribution** closure, not yet a fully independent production targetability closure. The diagnostic uses factual VCR combat-owner identity for the planet side when T-1 ownership is stale relative to earlier Host ownership changes.

## Correction to v3 owner interpretation

The v3 handoff described five residuals as an apparent same-owner VCR shape. That interpretation was wrong.

The field named `planet_owner_id` in the v3 residual printout came from the T-1 planet projection, not the factual VCR owner field.

V4 explicitly printed owner resolution for all 2406 ordinary planet VCRs:

```text
owner_resolution:vcr_owner_foreign = 2406
same_owner_vcr_rows                 = 0
race-map owner repairs              = 0
```

Therefore:

- there is no observed same-owner ship-vs-planet VCR population in this ordinary corpus;
- the five v3 residuals were caused by using a stale T-1 planet owner as the hostility target;
- factual VCR owner already identifies a foreign defender;
- the real remaining production problem is reconstructing **planet owner at combat time** after earlier Host ownership-changing phases and before ship-vs-planet combat.

Do not preserve the v3 same-owner hypothesis.

## Capture-generated planet priority

Population:

```text
capture-containing repeated planet groups = 9
capture-reset priority comparable          = 8
capture-reset exact                       = 8
capture-reset mismatch                    = 0
capture-reset unresolved                  = 1
```

The one unresolved group is:

```text
622476/T13 planet55
ship68 T-1 state unresolved
```

It is an evidence gap, not a contradiction.

The exact rule supported by all comparable groups is:

```text
captured entrant:
  preserve Friendly Code priority
  clear old Mission / Primary Enemy aggression priority
  evaluate ordinary STANDARD Combat Priority
```

This explains both ordinary-after-capture and interleaved capture cases, including numeric FC controls.

Status before production wiring:

```text
CORPUS_OBSERVED + TESTED
8/8 comparable differential exact
1 fail-closed evidence gap
```

## Other stable regressions

Still unchanged:

```text
ordinary mixed sites                        = 391
ship block before planet block              = 391/391
planet on RIGHT                             = 435/435
ordinary repeated planet production order   = 27/27
ship post-mutation next pair                = 22/22
post-capture independent initiator           = 23/23
interphase supply repair gate               = passed
```

## Production work started after this runtime

Production selector is being advanced so that `PlanetAttackCandidate.post_capture_generated_order=True` means:

```text
priority mission       = None
priority primary_enemy = None
priority friendly_code = preserved candidate FC
```

This changes only priority. Engagement eligibility/targetability remains an independent upstream input and therefore stays fail-closed when unknown.

The mixed differential is also being routed through the production selector for capture-containing groups. The next runtime must turn the 8/8 experimental capture-reset result into a production differential closure.
