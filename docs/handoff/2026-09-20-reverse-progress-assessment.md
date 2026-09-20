# NuHost reverse progress assessment — 2026-09-20

This is an engineering planning estimate, not a mechanics evidence label and not a percentage derived from test count.

GitHub is the source of truth.

Checkpoint inputs:

```text
main:
  2cfad9f5de83e052afc420179f45ab22557cec4f

active C5 branch before this assessment:
  bb474c66ca7b9987f326334c758add3400c60a85

PR #28:
  open
  draft
  unmerged
```

Game `591478` remains isolated from ordinary-mechanic promotion.

## Executive estimate

```text
combat mechanics reconstruction (C1-C5 knowledge):       ~85-90%
ordinary ship-combat independent candidate coverage:      ~20-25%
movement ordinary-core reconstruction:                    ~80-90%
warfare subsystem overall:                                ~70-80%
historical corpus / compatibility pipeline (M5A/M5B):     ~75-85%
whole NuHost reverse across the roadmap:                  ~45-55%
```

These percentages answer different questions and must not be collapsed into one number.

The combat knowledge estimate asks how much of the mechanic/order/state model is already understood.

The independent-coverage number asks how much of the historical factual ship-combat population can currently be reached from independently reconstructed pre-Host inputs without using factual outcomes as selector inputs.

The whole-NuHost estimate includes economy, production, minefields, missions, diplomacy, race mechanics, visibility and full-turn Host ordering, not only combat.

## Progress since the 2026-09-11 assessment

The 2026-09-11 estimate was:

```text
combat knowledge: ~70-80%
whole NuHost:     ~40-50%
```

Since then the C5 branch closed most of the previously listed immediate blockers.

### Initial selector / targetability

Closed:

- ordinary Privateer Rob effective targetability;
- ordinary Bird Super Spy targetability;
- directional STANDARD targetability wiring;
- canonical initial plain-STANDARD selector.

Runtime differential:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

### Mutable queue and repeated pairs

Closed:

```text
ordinary mutable membership:
  survivor membership=1146/1146
  capture fail-closed control=23/23
  destroyed predecessor reappearances=0
  gate passed

second STANDARD occurrence:
  repeated controls=2
  production exact=2/2
  gate passed
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Post-mutation next-pair prediction

Held-out factual next-VCR differential:

```text
strict:
  23 exact-set multi-VCR sites
  22 compared transitions
  22/22 exact

conditional:
  same result

transitions_with_inactive_filter=22/22
```

This validates a real mutable queue transition:

```text
VCR N terminal
  -> active membership mutation
  -> inactive pair filtering
  -> occurrence history
  -> canonical selector
  -> predicted factual VCR N+1
```

within the bounded exact-set ordinary scope.

### Production capture state

Closed production transition:

```text
capture continuations=23

owner/race/hull/shield/crew/torpedoes/fighters:
  23/23 exact

damage:
  22/23 exact

known isolated replay residual only:
  621253/T17 ship84 VCR39->45 damage 11->7
```

Capture state status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Production now supports explicit `ShipCaptureTransfer` while remaining fail-closed without explicit captor attribution.

### Post-capture combat continuation

The first attempted invariant:

```text
next opponent is always the pre-capture owner
```

was correctly rejected:

```text
pre-capture owner=22/23
third party=1/23
captor=0/23
```

The sole third-party residual was explained by independent Kill! aggression from the next opponent.

Population-wide initiator gate then closed:

```text
capture continuations=23

independent opponent initiator=23/23
  ship Kill!/PE=8/8
  planet NUK/ATT=15/15

explanation:
  opponent_only=21
  both=2
  captured_old_orders_only=0
  neither=0

required unresolved=0
optional captured-old-order history gaps=2

gate passed
```

Status:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

No current corpus row requires persistence of the captured ship's old mission/Primary Enemy.

## Why combat knowledge is now ~85-90%

The ordinary ship-combat stack now has evidence-backed implementations for:

1. deterministic pairwise combat replay;
2. combat phase classification;
3. Priority Intercept ordering;
4. scoped Cloak & Intercept / Galactic Power / matching-FC behavior;
5. precombat position reconstruction for the supported ordinary scope;
6. pair candidate composition;
7. directional STANDARD targetability;
8. canonical initial STANDARD active ship and target ordering;
9. mutable survivor/destruction membership;
10. repeated-pair occurrence state and second-pass side reversal;
11. post-mutation next-pair selection on held-out VCR transitions;
12. capture state transfer and prize-crew continuation;
13. post-capture continuation explained by independently attributable opponent aggression.

The remaining C5 work is no longer a broad unknown queue model. It is concentrated in narrower boundaries.

## Remaining combat/C5 work

### 1. Mixed ship / planet-base queue ordering — immediate next target

Fifteen of the twenty-three observed prize-ship continuations go directly into planet/base combat.

We still need to reconstruct:

- when ship-vs-ship queue work yields to planet/base combat;
- ordering among multiple eligible ships attacking/defending the same planet/base;
- interaction between ship battle priority and planet/base participation;
- survivor/captured-ship re-entry around planet combat;
- exact LEFT/RIGHT and ordering semantics in mixed queues.

This is the largest immediate C5 mechanics gap.

### 2. Specific planet/base participation and C4 -> C5 integration

C4 is checkpointed, but full integration with the generated Host queue is not yet closed end-to-end.

### 3. Capture-generated target list

Documentation says capture creates a new target/order list.

The current corpus does not identify its contents because every observed post-capture continuation already has an independent opponent-side initiator.

Do not invent this list.

It becomes a priority only when a corpus/scenario contains a post-capture battle that cannot be explained by opponent aggression alone.

### 4. Advanced Cloak production predictor

The decisive historical Advanced Cloak rows are explained, but a generic precombat production predictor remains deliberately unpromoted.

### 5. Independent candidate coverage

Current historical candidate boundary remains:

```text
factual unique ship pairs=1986
candidate-covered=428
coverage=21.6%

conditional:
  factual eligible=427
  unresolved=1
  hard blocked=0

strict:
  factual eligible=420
  unresolved=8
  hard blocked=0
```

Position reconstruction remains:

```text
factual ship occurrences=3204
predicted=1810
exact=1806
mismatch=4
uncovered=1383
```

Thus many factual battles are still outside independent reconstruction because upstream position/effective-state/special-case inputs fail closed.

This coverage expansion is a substantial remaining research task even though the mechanics inside the covered scope are increasingly exact.

### 6. Isolated game 591478

Keep separate until its identity/lifecycle anomalies are explained. It must not contaminate ordinary-mechanic promotion.

### 7. Full end-to-end combat-turn differential

The final C5 closure should predict a complete mixed ship/planet VCR queue for a turn/site from independent pre-Host state, not only bounded subpopulations.

## How much remains for combat

Planning estimate:

```text
mechanics knowledge remaining:
  ~10-15% of C1-C5

engineering / coverage work remaining before robust full-combat replay:
  materially more than 10-15%
```

The distinction matters.

The remaining mechanic unknowns are narrow, but raising independent coverage from ~21.6% to broad historical coverage requires reconstructing many upstream state/special-case branches.

A useful way to phrase the current state:

```text
"we mostly know how the ordinary combat machine works,
 but we cannot yet independently feed that machine for every historical case."
```

## Wider NuHost roadmap

Large subsystems still remain beyond combat.

### M2 — economy / planetary Host

Current planning estimate:

```text
~35-50%
```

Still requires broad end-to-end work in economy, planet updates, starbases and ship production.

### M3 — warfare overall

Current planning estimate:

```text
~70-80%
```

Combat is advanced, but minefields and several integrated special/race interactions keep warfare below the combat-only knowledge estimate.

### M4 — race-specific mechanics

Current planning estimate:

```text
~35-50%
```

Many race mechanics are individually known or partially reconstructed but not vertically integrated through the whole Host order.

### M5A/M5B — corpus and Nu compatibility

Current planning estimate:

```text
~75-85%
```

The corpus/differential infrastructure is now mature enough to repeatedly promote or reject narrow mechanics with held-out validation.

### Observer / visibility / intel

Still a major later subsystem:

- fog of war;
- shared intel;
- stale observations;
- visibility timing;
- observer-state reconstruction.

### General missions and special abilities

Need Host-order integration rather than isolated rule implementations.

### Diplomacy

Pair-level combat diplomacy controls exist, but full Safe Passage / alliance / team behavior must be integrated across movement, combat, planets and other subsystems.

### Minefield lifecycle

Still a large warfare subsystem requiring end-to-end Host ordering.

### Full-turn Host differential

The ultimate completion criterion is not a collection of local rules. It is:

```text
pre-Host complete state
  -> reconstructed Host phases
  -> post-Host complete state
  == factual archived turn
```

over sufficiently broad historical populations.

## Whole-NuHost estimate

Current engineering estimate:

```text
~45-55% complete
~45-55% remaining
```

This is intentionally only modestly higher than the 2026-09-11 `~40-50%` estimate despite major C5 progress.

Reason: combat was already one of the strongest subsystems. Closing a large fraction of C5 materially improves warfare fidelity but does not automatically complete economy, minefields, production, missions, diplomacy, race integration or visibility.

## Practical milestone interpretation

### To a strong ordinary-combat simulator

Remaining effort is relatively bounded:

1. mixed ship/planet ordering;
2. planet/base integration;
3. broaden candidate coverage;
4. close remaining special-state branches;
5. complete-site/complete-turn combat differential.

### To a credible general NuHost simulator

Roughly half the roadmap remains.

The largest future blocks are:

1. economy / planets / starbases / production;
2. minefield lifecycle;
3. missions and special abilities in Host order;
4. cross-subsystem diplomacy;
5. vertical race-specific mechanics;
6. observer/visibility/fog/shared intel;
7. full-turn differential closure.

### To training/AI

Do not shortcut simulator fidelity merely to reach M6.

Training becomes useful after the reconstructed simulator and observer surfaces are sufficiently faithful that an agent is not learning artifacts of an incomplete Host model.

## Immediate next step

After the green post-capture initiator v2 runtime, move C5 to:

```text
mixed ship / planet-base queue ordering
```

while keeping:

```text
capture-generated old-order persistence:
  unproven and unnecessary for current corpus

game 591478:
  isolated
```
