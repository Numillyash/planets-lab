# C5 mixed ship / planet-base queue — batch runtime v6

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
370ecaf5de029fadfd0acafd1107e1fb35c9cb54
```

PR #28 remained open + draft. Game `591478` remained isolated from ordinary promotion.

## Batch execution

All ten stages completed successfully:

```text
REGRESSION TESTS                         rc=0
FACTUAL QUEUE SHAPE                      rc=0
PLANET CARRY                             rc=0
SHIP NEXT-PAIR REGRESSION                rc=0
POST-CAPTURE INITIATOR REGRESSION        rc=0
SHIP->PLANET INTERPHASE STATE            rc=0
ALL PLANET ENGAGEMENT POPULATION         rc=0
PLANET OWNERSHIP TIMELINE                rc=0
PLANET PRECOMBAT OWNER SOURCE            rc=0
MIXED SHIP/PLANET DISCOVERY V6           rc=0
```

## Stable production closures

Still green:

```text
ordinary mixed sites=391
ship block before planet block=391/391
planet RIGHT=435/435

ordinary repeated planet order:
  27/27 exact

production repeated planet order:
  comparable=35
  exact=35
  mismatch=0
  unresolved=1

capture-reset subset:
  comparable=8
  exact=8
  mismatch=0
  unresolved=1

ship post-mutation next pair:
  22/22 exact

post-capture independent initiator:
  23/23

interphase supply repair:
  gate passed

all ordinary planet initiators:
  2406 factual VCR
  hard residuals=0
  unresolved=2
```

Capture-generated planet priority remains:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Ownership timeline

The independent attribution sweep remains:

```text
ordinary ship-vs-planet VCRs=2406
unique planet-turn combat timelines=2303

precombat owner unchanged=2334 VCR rows
precombat owner changed=60 VCR rows
T-1 owner unresolved=12 VCR rows

unique precombat owner-change timelines=59
unique changed from attacking ship owner to factual defender=42
```

All factual VCR defenders are foreign and race-owner consistent:

```text
vcr_defender_foreign_to_ship=2406/2406
vcr_race_owner_exact=2406/2406
```

## Precombat owner source inventory

The v6 source inventory intentionally resolved only the positive-owner reversal class that can be reconstructed with the current T-1 owner adapter:

```text
changed_planet_turn_timelines=42
source_class:tminus1_attacker_owned=42

future-defender ship co-located at T-1=42/42

future-defender ship with onboard clans > 0=33/42
without onboard clans > 0=9/42

candidate count:
  exactly one positive-clan defender ship=32
  multiple positive-clan defender ships=1
  zero positive-clan defender ships=9
```

Important correction:

The v5 handoff described V6 as an inventory over all 59 changed timelines. The actual v6 adapter covers 42 positive-owner reversal timelines. The remaining 17 unique owner-change timelines are outside this adapter and must remain separate until neutral/other ownership state is explicitly represented.

## Strong new transfer evidence

Every co-located ship projection exposes the actual Nu cargo-transfer fields:

```text
transferclans
transfertargetid
transfertargettype
```

The v6 examples show that rows counted as `defender_positive_clan_ship_count=0` can still have direct clan-transfer orders to the planet.

Examples include:

```text
360690/T51 planet88:
  defender ship281
  clans=0
  transferclans=172
  transfertargetid=88
  transfertargettype=1

360690/T68 planet192:
  defender ship54
  clans=0
  transferclans=87
  transfertargetid=192
  transfertargettype=1

360690/T177 planet450:
  defender ship183
  clans=0
  transferclans=10
  transfertargetid=450
  transfertargettype=1

511506/T42 planet490:
  defender ship393
  clans=0
  transferclans=280
  transfertargetid=490
  transfertargettype=1

620636/T12 planet86:
  defender ship14
  clans=0
  transferclans=65
  transfertargetid=86
  transfertargettype=1
```

Therefore `clans > 0` on the T-1 ship object is not the correct source criterion by itself.

The next ownership gate should evaluate **directed clan transfer order**:

```text
transferclans > 0
transfertargettype == planet
transfertargetid == planet_id
```

and then reconstruct sequential cargo-drop / ground-combat ownership effects in Host Ship-ID order.

No generic ground-combat production rule is promoted by v6 yet.

## Evidence status after v6

Closed / stable:

```text
ordinary mixed phase ordering:
  CORPUS_OBSERVED + TESTED

ordinary repeated planet attacker priority:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

capture-generated planet priority:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

interphase supply repair:
  DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

all-planet initiator population:
  CORPUS_OBSERVED + TESTED
  production targetability still depends on precombat owner reconstruction

planet ownership timeline:
  CORPUS_OBSERVED + TESTED

precombat owner source:
  CORPUS_OBSERVED inventory only
```

## Remaining immediate C5 boundary

The dominant mixed queue gap is now upstream of queue ordering:

```text
T-1 planet/ship cargo state
  -> cargo transfer / ground combat / ownership mutation
  -> actual precombat planet owner
  -> planet combat targetability
  -> already-verified planet queue ordering
```

Other remaining C5 work:

- broaden independent candidate/position coverage beyond the current historical 21.6% ship-pair candidate boundary;
- generic Advanced Cloak production predictor;
- complete-site / complete-turn mixed combat differential;
- keep `591478` isolated.
