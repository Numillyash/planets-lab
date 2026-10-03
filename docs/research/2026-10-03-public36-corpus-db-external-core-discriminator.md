# Public36 Corpus DB external-core discriminator — 2026-10-03

## Scope

This note belongs to the dedicated external-core research stream on
`research/external-engine-analysis`.

The canonical mechanics/backend implementation remains on `main`. This branch
uses main-produced discovery/runtime evidence only to test external engine
hypotheses such as c2ng/THost. No external rule is promoted into NuHost mechanics
from this note.

## Runtime consumed

Canonical runtime was executed from the external checkout after temporarily
fast-forwarding it to main, using the accepted compact Corpus DB backend.

Source:

```text
main
4482e6ab8f4b962aff552aa2c98de4321d0c6054
research: run capture O-layer probe from corpus DB
```

Active DB:

```text
generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb
schema: planets-lab.corpus-db.v2.compact1
```

Published runtime evidence:

```text
runtime-logs/public-capture-o-layer-discovery/20261003T151004Z_4482e6ab8f4b
```

The run stayed inside the deterministic discovery partition. Held-out games
remain sealed.

## Discovery result

Population:

```text
ship capture continuations   50
globally adjacent rows       31
resolved external O probe    31
not comparable               19
unresolved                    0
```

External c2ng/THost original-order result:

```text
O pair reachable              5
  factual prize LEFT          2
  factual prize RIGHT         3

O pair not reachable         26
  factual prize LEFT         23
  factual prize RIGHT         3

external O exact              3
external O mismatch          28
```

## Effect on the previous O/C hypothesis

The earlier 8-row corpus contained one exact c2ng-like original-order case,
`511506/T26`, and five adjacent LEFT continuations where the same external
cursor produced no continuation.

The 50-row discovery population rejects the stronger extrapolation that factual
RIGHT is a reliable marker for a c2ng/THost-like original-order continuation:

- external O reachability is rare: 5 / 31 adjacent rows;
- reachable rows are not side-pure: 2 LEFT / 3 RIGHT;
- RIGHT also occurs among O-not-reachable rows: 3 cases;
- exact full pair+side compatibility is only 3 / 31 comparable rows.

Therefore:

```text
c2ng/THost O cursor as a general Nu post-capture rule:
  rejected on discovery

RIGHT => c2ng-like original-order continuation:
  rejected on discovery

LEFT => capture-generated C order:
  not established; also rejected as a simple complement

individual exact rows:
  retained only as local external compatibility observations
```

The primary Nu documentation can still require distinct original-order and
capture-generated-order contexts, but c2ng is no longer a useful classifier for
partitioning the public discovery population into those contexts.

## External-core conclusion

c2ng remains valuable as a historical THost/PCC2 reference for:

- identifying possible queue/cursor structures;
- generating targeted discriminators;
- explaining a small number of individual official-Nu continuations.

It does **not** currently reproduce Nu's post-capture continuation layer at a
rate compatible with adopting its cursor semantics:

```text
exact 3 / 31
mismatch 28 / 31
```

That is a strong negative result for the external implementation, not a NuHost
mechanics closure.

## Next external-core work

Do not spend more time trying to fit one global c2ng capture cursor to the 50
discovery rows.

The next external-reference pass should instead look for implementations or
historical documentation that explicitly model Nu/THost's second
capture-generated order, including:

1. exact trigger and maximum number of post-capture additional fights;
2. how the captured ship's mission/PE/FC state is reset or preserved;
3. how aggressor/opponent roles are assigned in the newly generated order;
4. whether the additional order is inserted immediately, appended, or traversed
   through a separate queue;
5. any historical THost/PHost distinction that can explain the six discovery
   RIGHT rows not classified by the c2ng cursor.

Candidate priority remains primary/near-primary historical Host documentation
and recoverable server implementations. c2ng should now be treated as a bounded
negative comparator for this blocker rather than the leading structural model.
