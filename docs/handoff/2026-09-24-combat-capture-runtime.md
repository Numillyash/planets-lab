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


## Candidate discovery v2 archive runtime

Runtime source:

```text
041772b543e322aa906dfdbd46f8e2c3a33d00cb
```

Published evidence:

```text
runtime-logs/combat-post-capture-candidate/20260924T162521Z_041772b543e3
```

The repaired diagnostic preserves all factual ship continuations:

```text
ship_capture_observations=8
ship_capture_sites=7
status:resolved=8
target_sites_missing=0
```

Prize-ship presence is independently reconstructed at five observations and
anchored by the already-validated capture event at three observations.

For six of the eight observations, the ordinary T-1 position adapter also
reconstructs the factual next opponent at the battle site. Every such opponent:

```text
requests the prize ship's new owner=6/6
strict permission=true=6/6
requester rank 1=6/6
strict rank 1=6/6
```

The informative multi-requester site remains:

```text
622476/T17 @1973,1734
requester order: 48, 53, 57
factual opponent: 48
rank: 1
```

Two observations remain outside the ordinary per-ship movement adapter:

```text
511506/T26 @2514,1772 opponent ship119 mission=6 (Tow)
511506/T33 @1491,2315 opponent ship268 mission=7 (Intercept)
```

These are not capture-state or candidate-order counterexamples. The ordinary
position helper deliberately fails closed on Tow and Intercept movement, while
the independent initiator audit already resolves T-1 aggression for all eight
ship opponents.

A dedicated residual differential now runs existing production movement phases
in Host order:

```text
Tow -> Move Most -> Intercept
```

from owner-current T-1 state and compares the resulting special-movement
opponent position with the held-out factual combat site. This keeps movement
mechanics out of the combat diagnostic and will determine whether candidate
reconstruction can consume a common post-movement state for these two rows.


## Special-movement bridge runtime

Runtime source:

```text
3e416007021f7eb26ba48750c4f63a34b13ad3a1
```

Published evidence:

```text
runtime-logs/combat-post-capture-candidate/20260924T212428Z_3e416007021f
```

Population:

```text
ordinary ship opponents=6
special-movement opponents=2
Tow=1
Intercept=1
```

The Tow residual closes exactly through the existing production movement
pipeline:

```text
511506/T26
opponent ship119
mission=6 Tow
target ship102
origin=(2565,1729)
waypoint=(2516,1770)
warp=9

TowMovementPhase:
  from=(2565,1729)
  to=(2514,1772)
  fuel_used=95
  movement_mass=1523
  warpwell_planet_id=112

predicted=(2514,1772)
factual=(2514,1772)
exact=true
```

The remaining Intercept row is not a movement mismatch. It remains fail-closed
before simulation because the Intercept target has a submitted outbound transfer:

```text
511506/T33
opponent ship268
mission=7 Intercept
target ship174
factual site=(1491,2315)
preflight issue=target_outbound_transfer
```

Therefore the remaining bridge gap is specifically pre-movement transfer state
for ship174, not capture ownership/state, candidate aggression, Tow geometry or
generic Intercept ordering.

The v2 residual diagnostic now tests only a bounded transfer hypothesis before
Move Most: a current-visible, co-located, same-owner ship receiver with
sufficient sender cargo and receiver capacity. Foreign or ambiguous transfers
remain fail-closed. No generic ship-transfer production rule is promoted by
this diagnostic.


## Transfer-target namespace residual

Runtime source:

\`\`\`text
c5d2a777dc22f8e15d0e7c1581570c826a3b6cba
\`\`\`

Published evidence:

\`\`\`text
runtime-logs/combat-post-capture-candidate/20260924T220519Z_c5d2a777dc22
\`\`\`

The remaining Intercept case still fails closed, but the reason is now more
specific:

\`\`\`text
511506/T33
interceptor ship268
Intercept target ship174
submitted transfer:
  target_id=224
  target_type_raw=1
  clans=30

ship174 position=(1491,2368)
ship id 224 position=(2576,1469)
\`\`\`

Therefore the earlier assumption that \`transfertargetid=224\` identifies ship
224 is not supported by T-1 geometry. The numeric \`transfertargettype\` value
must not be interpreted by guesswork.

The next differential resolves the submitted transfer target by actual T-1
co-location across both ship and planet namespaces. The raw numeric target type
is retained as evidence only. If exactly one object namespace with the target
ID is co-located with the sender, receiver-side transfer semantics remain
unpromoted and movement is tested under both no-transfer and sender-reduced
bounds.

This keeps the combat/Intercept geometry question independent from full
ship/planet transfer reconstruction.
