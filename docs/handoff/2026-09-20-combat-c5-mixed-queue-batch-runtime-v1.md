# C5 mixed ship / planet-base queue — batch runtime v1

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
209abdad14682cfab8d9bc4729f2b63b4ad9a5a4
```

PR #28 remained open + draft. Game `591478` remains isolated from ordinary promotion.

## Batch execution

All stages completed successfully:

```text
REGRESSION TESTS                         rc=0
FACTUAL QUEUE SHAPE                      rc=0
PLANET CARRY                             rc=0
SHIP NEXT-PAIR REGRESSION                rc=0
POST-CAPTURE INITIATOR REGRESSION        rc=0
MIXED SHIP/PLANET DISCOVERY              rc=0
```

## Ordinary factual queue shape

Across ordinary games:

```text
combat sites=3132
multi-VCR sites=639
ship-only sites=829
planet-phase sites=2303

ship-vs-ship VCRs=1988
ship-vs-planet VCRs=2406

phase-order violations=0
```

Mixed-site batch:

```text
mixed sites=391
mixed VCRs=1161

ship-vs-ship VCRs=726
ship-vs-planet VCRs=435

S->S transitions=335
S->P transitions=391
P->P transitions=44
P->S transitions=0

sites with all ship combat before planet block=391/391
```

This is independently consistent with the documented Host phase order:

```text
ship-vs-ship
-> repair / MKT
-> ship-vs-planet
```

The interphase repair/MKT transition is not yet reconstructed.

## Ship / planet orientation

Every ordinary mixed-site planet engagement observed:

```text
planet RIGHT=435/435
planet LEFT=0/435
```

This matches the existing bounded planet-sequence production shape where attacking ships are LEFT and one fixed planet/base is RIGHT.

## Planet participation

```text
distinct planets per mixed site:
  1 = 391/391

planet attack-code rows:
  NUK/ATT=87
  non-NUK/ATT=343
  T-1 planet unresolved=5

planet attacker priority:
  resolved=434
  unresolved=1
```

Most mixed-site planet battles therefore cannot be explained by planet NUK/ATT alone; ship-side Kill!/Primary Enemy initiation must be measured explicitly in the next batch.

## Ship history before planet combat

```text
planet rows where ship already fought ship at same site=397
fresh planet attackers=38

immediate previous VCR is ship combat containing same ship=385
post-capture planet rows=15
post-ship non-capture planet rows=382
```

The gap between 397 prior-ship participants and 385 immediate same-ship handoffs is expected under the phase boundary: other ship-vs-ship VCRs may finish before the planet block begins.

## Repeated attacks against one planet/base

```text
planet engagement groups=391
repeated planet groups=36
repeated planet VCRs=80

naive STANDARD-priority comparable groups=35
exact=34
mismatch=1
unresolved=1
```

The sole comparable mismatch:

```text
game 511506
turn 48
planet 131

factual planet attacker order:
  ship489
  ship480

T-1 ordinary STANDARD priority would predict:
  ship480
  ship489
```

Context:

```text
ship489:
  owner3
  ordinary non-capture attacker
  priority [3,489,0]

ship480:
  T-1 owner6
  captured into owner3 during the preceding ship-combat block
  post-capture planet row
  old T-1 priority [1,480,0]
```

Therefore the only observed failure of naive T-1 planet priority is exactly a post-capture candidate whose documented capture-generated target/order list is not represented by its old T-1 priority.

Do not encode this row as an exception to ordinary Combat Priority.

Next differential must partition ordinary and post-capture planet attackers and make production fail closed on capture-generated order semantics.

## Planet carry regression

Ordinary same-turn repeated planet/base transitions:

```text
transitions=103
match=102
not comparable=1
mismatch=0

shield carry=103/103
```

Ordinary no-starbase exact reconstruction:

```text
11 transitions
10 exact
1 start-reconstruction not comparable
0 exact mismatches
```

Ordinary starbase:

```text
92 transitions
92/92 shield carry match
```

Hidden persistent starbase state remains fail-closed.

## Previously closed regressions

Ship post-mutation next-pair:

```text
strict 22/22 exact
conditional 22/22 exact
```

Post-capture initiator:

```text
23/23 independent opponent initiators
required unresolved=0
gate passed
```

## Evidence promoted by this runtime

Factual phase ordering:

```text
all ordinary ship-vs-ship combat precedes planet/base combat:
DOCUMENTED + CORPUS_OBSERVED
```

Factual mixed VCR orientation:

```text
ship LEFT / planet-base RIGHT:
CORPUS_OBSERVED
435/435
```

Ordinary repeated planet attacker priority is strongly supported after excluding post-capture generated-order rows, but production promotion waits for the v2 capture-aware differential.

## Next large batch

The next one-command batch must cover all of:

1. production phase state machine;
2. production ordinary planet-attacker selector;
3. ship-side Kill!/PE vs planet-side NUK/ATT initiator population;
4. ordinary-only repeated planet ordering;
5. capture-containing repeated planet groups kept fail-closed;
6. ship->planet interphase state differential for damage/ammunition/shield changes;
7. existing ship queue, capture and planet carry regressions.

The documented repair/MKT boundary must be measured before full mixed queue orchestration is promoted.
