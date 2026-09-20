# C5 mixed ship / planet-base queue — batch runtime v2

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
3db42c59439226f249e19615197e75582de10590
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
MIXED SHIP/PLANET DISCOVERY V2           rc=0
```

## Stable queue/planet regressions

Ordinary queue phase shape remains:

```text
mixed sites=391
ship block before planet block=391/391
P->S transitions=0
planet RIGHT=435/435
```

Planet carry remains:

```text
ordinary transitions=103
match=102
not comparable=1
mismatch=0

ordinary starbase shield carry=92/92
ordinary no-starbase exact=10/10 comparable
```

Ship next-pair remains:

```text
strict=22/22 exact
conditional=22/22 exact
```

Post-capture initiator remains:

```text
23/23 independent opponent initiators
required unresolved=0
gate passed
```

## Ship -> planet interphase state population

Ordinary game population, excluding game 591478:

```text
ship->planet same-ship transitions=397

ordinary exact carry=374
ordinary damage-change transitions=8
defeated/captured predecessor reappearances=15
```

For the 382 ordinary surviving-ship transitions:

```text
crew:      382 same
torpedoes: 382 same
fighters:  382 same
```

Damage changes occur in exactly 8 rows:

```text
360690/T84  ship41   88 -> 72   T-1 supplies=155
360690/T169 ship184  12 -> 3    T-1 supplies=45
360690/T177 ship451  82 -> 62   T-1 supplies=100
620636/T71  ship60   51 -> 40   T-1 supplies=58
620694/T46  ship224   2 -> 0    T-1 supplies=100
620694/T83  ship83   54 -> 46   T-1 supplies=41
620694/T127 ship201  60 -> 57   T-1 supplies=16
621253/T17  ship24   24 -> 17   T-1 supplies=36
```

Seven rows exactly consume the full repair budget implied by the T-1 supply count:

```text
repair = min(damage, floor(supplies / 5))
```

The first row repairs only 16 points despite T-1 supplies permitting 31. This is not a contradiction because T-1 supplies are not necessarily the supplies remaining at the post-ship-combat repair step. Host has earlier automatic repair opportunities, so supplies may already have been consumed.

The production rule must therefore use the current interphase cargo state, not T-1 cargo.

Official documentation independently states:

```text
5 KT supplies repair 1% ship damage automatically.
repair does not restore lost crew or recharge shields.
Mass check / repair / MKT occurs after ship-vs-ship and before ship-vs-planet.
```

Production supply repair is promoted as a documented pure primitive in:

```text
src/planets_lab/rules/combat/interphase.py
```

MKT torpedo construction remains separate.

## Ordinary repeated planet attacker ordering — CLOSED in bounded scope

V2 production-aware repeated groups:

```text
repeated planet groups=36
without post-capture entrant=27
with post-capture entrant=9

ordinary production-comparable=27
ordinary production-exact=27
ordinary production-mismatch=0
```

Therefore the ordinary planet attacker selector based on standard Combat Priority is:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

for the current repeated-group scope.

Post-capture groups remain fail-closed.

## Capture-containing repeated planet groups

```text
groups=9
post-capture entrants after all ordinary attackers=8
post-capture entrant interleaved before ordinary attacker=1
```

Therefore:

```text
"post-capture planet attackers are always appended after ordinary attackers"
```

is false and must not be promoted.

The known interleaving case is:

```text
621896/T25 planet5
factual: ship34(post-capture) -> ship67(ordinary)
```

All nine groups must be compared together before reconstructing capture-generated order insertion.

## Planet engagement initiator inventory

For 435 mixed-site planet engagements:

```text
ship_only=338
planet_only=17
both=69
neither_basic_order=5

planet T-1 unresolved=5
ship T-1 unresolved=1

NUK/ATT rows=87
non-NUK/ATT rows=343
matching ship/planet FC rows=5
```

The five `neither_basic_order` rows are not yet contradictions. V2 only modeled the eleven-race ordinary Kill!/PE and NUK/ATT request surface.

V3 must add explicit race-aware residual classification, especially Horwasp:

- Horwasp ships function as though Kill! is always set;
- Horwasp planets function as though NUK is set.

It must also report factual/current owner versus T-1 owner so capture-history rows are not mistaken for ordinary orders.

## Production committed after this runtime

### Supply repair

```text
src/planets_lab/rules/combat/interphase.py
tests/test_combat_interphase.py
```

Pure documented rule:

```text
repaired = min(damage, floor(current_supplies / 5))
damage -= repaired
supplies -= 5 * repaired
```

Crew, shield and ammunition are preserved; functional weapon counts are re-derived from the repaired damage state.

### V3 mixed residual diagnostics

The mixed audit now:

- emits all initiator residual rows;
- emits all capture-containing repeated planet groups;
- records factual VCR race IDs;
- applies Horwasp Kill!/NUK-equivalent initiator classification;
- records T-1 owner versus VCR owner;
- remains fail-closed for capture-generated ordering.

### V2 interphase repair differential

The interphase audit now separates:

- exact full T-1 supply-budget rows;
- rows compatible only if earlier Host steps already consumed supplies;
- hard contradictions where observed repair exceeds T-1 supply budget;
- crew/ammunition preservation;
- shield non-recharge;
- MKT candidate inventory.

## Next large batch

Use the same one-command runner.

The next run should answer together:

1. whether production supply repair matches every row where current supply budget is independently usable;
2. whether any ship->planet damage change contradicts the documented 5:1 rule;
3. how many T-1 supply rows require earlier Host consumption;
4. whether Horwasp closes the five basic initiator residuals;
5. exact details of any initiator rows still unexplained;
6. full shape of all nine capture-containing repeated planet groups;
7. whether any simple capture-order insertion invariant survives;
8. MKT candidate behavior in the ship->planet population;
9. all prior queue/capture/planet regressions.
