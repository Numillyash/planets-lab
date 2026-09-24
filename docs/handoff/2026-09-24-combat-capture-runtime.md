# Combat capture reintegration — archive runtime checkpoint

Date: 2026-09-24

Repository: `Numillyash/planets-lab`

Archive-host source commit:

```text
256d8de7604685afcc62da2a672edf7b6865c641
```

Published runtime evidence:

```text
runtime-logs/combat-capture-reintegration/20260924T151626Z_256d8de76046
```

## Full reintegration gate

The full capture reintegration gate completed successfully on the archive host.

Final integration checker:

```text
exact=true
failures=[]
capture_continuations=23
ship_continuations=8
planet_continuations=15
initiator_continuations=23
independent_opponent_attack=23
```

The non-capture predictive queue checkpoint remained closed:

```text
strict      22/22 held-out next VCR exact
conditional 22/22 held-out next VCR exact
mismatch=0
```

FeatureScope continuity remained exact and game 591478 remained excluded by the
shared profile rather than by any hardcoded game-id exception.

## Capture-state continuity

Observed capture continuations:

```text
23 total
owner -> captor exact: 23/23
race  -> captor exact: 23/23
hull preserved:        23/23
shield exact:          23/23
crew exact:            23/23
torpedoes exact:       23/23
fighters exact:        23/23
damage exact:          22/23
```

The only damage replay residual remains the previously known bounded case:

```text
621253 / turn 17 / ship 84 / VCR 39 -> 45 / predicted 11 / factual 7
```

No new damage residual appeared.

## Post-capture initiator result

Every observed same-turn continuation has an independently attributable
opponent-side initiator:

```text
capture continuations=23
independent opponent attack candidate=23
required unresolved=0
ship opponents=8
planet opponents=15
post_capture_initiator_gate_passed=true
```

Owner relation of the factual next opponent:

```text
pre-capture owner=22
third party=1
```

The third-party case also has an independently reconstructed attack against the
new prize-ship owner.

Captured-ship old orders are not needed to explain continuation:

```text
old orders attack candidate=2
old orders no attack candidate=19
old orders unresolved=2
opponent-only explanation=21
both=2
```

Therefore old mission/Primary Enemy persistence through capture must not be
invented as a production rule.

## Candidate-discovery v1 result and diagnostic boundary

The first descriptive post-capture ship-candidate inventory reported:

```text
ship capture sites=7
resolved observations=4
unresolved observations=3
```

All four resolved observations had:

```text
factual opponent independently predicted at site=true
requests combat against prize ship's new owner=true
strict diplomacy permission=true
requester rank=1
strict rank=1
```

One informative multi-candidate site had requester order:

```text
48, 53, 57
```

and factual opponent ship 48 ranked first.

The three unresolved rows were not NuHost counterexamples. They were caused by
a diagnostic assumption requiring the prize ship itself to appear in the
owner-current T-1 position reconstruction even though the validated capture
event already proves the prize ship's presence in the combat chain.

A second diagnostic issue collapsed two capture observations at the same
`(game, turn, x, y)` site, producing seven site targets from eight factual
ship continuations.

Both diagnostic issues are fixed after this runtime:

- the validated capture event now anchors prize-ship presence;
- multiple capture observations at the same site remain distinct;
- all *other* candidate ships remain independently reconstructed from T-1 state;
- factual next VCR remains comparator-only.

## Next archive-host gate

Use the narrow candidate-only gate; rerunning the full FeatureScope and
predictive queue checkpoint is unnecessary for this diagnostic change:

```bash
bash tools/run-combat-post-capture-candidate-with-evidence.sh
```

Expected evidence branch prefix:

```text
runtime-logs/combat-post-capture-candidate/
```

The next decision boundary is whether all eight ship capture observations now
resolve and whether the factual next opponent remains rank 1 after rebuilding
the post-capture foreign candidate set.
