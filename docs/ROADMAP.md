# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-20-reverse-progress-assessment.md`](handoff/2026-09-20-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial target-order evidence runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Directional targetability population runtime: [`handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md`](handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md).
- Canonical pair-level targetability runtime: [`handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md`](handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md).
- Canonical initial plain-STANDARD selector runtime: [`handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md`](handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md).
- Production precombat effective-state runtime: [`handoff/2026-09-16-combat-c5-production-effective-state-runtime.md`](handoff/2026-09-16-combat-c5-production-effective-state-runtime.md).
- Mutable ship-queue scope-repair gate: [`handoff/2026-09-16-combat-c5-mutable-ship-queue-pending.md`](handoff/2026-09-16-combat-c5-mutable-ship-queue-pending.md).
- STANDARD queue composition checkpoint: [`handoff/2026-09-18-combat-c5-standard-queue-composition-pending.md`](handoff/2026-09-18-combat-c5-standard-queue-composition-pending.md).
- Post-mutation next-pair runtime: [`handoff/2026-09-18-combat-c5-post-mutation-next-pair-runtime.md`](handoff/2026-09-18-combat-c5-post-mutation-next-pair-runtime.md).\n- Capture descriptive runtime: [`handoff/2026-09-20-combat-c5-capture-continuation-descriptive-runtime.md`](handoff/2026-09-20-combat-c5-capture-continuation-descriptive-runtime.md).\n- Production capture runtime: [`handoff/2026-09-20-combat-c5-capture-production-runtime.md`](handoff/2026-09-20-combat-c5-capture-production-runtime.md).\n- Post-capture opponent population gate: [`handoff/2026-09-20-combat-c5-post-capture-opponent-pending.md`](handoff/2026-09-20-combat-c5-post-capture-opponent-pending.md).\n- Third-party residual runtime: [`handoff/2026-09-20-combat-c5-post-capture-third-party-residual-runtime.md`](handoff/2026-09-20-combat-c5-post-capture-third-party-residual-runtime.md).\n- Post-capture initiator runtime: [`handoff/2026-09-20-combat-c5-post-capture-initiator-runtime.md`](handoff/2026-09-20-combat-c5-post-capture-initiator-runtime.md).\n- Active mixed ship/planet queue handoff: [`handoff/2026-09-20-combat-c5-mixed-ship-planet-queue-pending.md`](handoff/2026-09-20-combat-c5-mixed-ship-planet-queue-pending.md).
- Advanced Cloak decisive historical closure: [`handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md`](handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status: `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED`. Unknown mechanics fail closed. Post-Host `T`, factual VCR outcomes and Host messages may provide historical attribution but must not become production precombat state inputs.

## Engineering progress estimate

Planning estimates only:

```text
combat mechanics reconstruction (C1-C5 knowledge):     ~85-90%
ordinary ship-combat independent candidate coverage:    ~20-25%
movement ordinary-core reconstruction:                  ~80-90%
whole NuHost reverse across the roadmap:                ~45-55%
```

Candidate-set v2 independently covers `428 / 1986 = 21.6%` factual ship-vs-ship pairs, with zero conditionally hard-blocked covered factual pairs. Position v3 predicts 1810/3204 factual ship occurrences, 1806 exact and 4 mismatch.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**. Combat C1-C4 are checkpointed. C5 remains immediate.

Stable C5 layers now include:

- pair composition and factual phase ordering;
- normal/reciprocal Priority Intercept attribution;
- scoped Galactic Power and matching-FC exceptions;
- repaired precombat positions and candidate-set v2;
- directional ordinary-STANDARD targetability at pair level;
- production initial plain-STANDARD stack selector;
- ordinary Privateer Rob and ordinary Bird Super Spy precombat targetability;
- repeated-pair second-occurrence side reversal.

### Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

### Initial plain-STANDARD selector — production closed

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Production differential:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Directional targetability — production closed for ordinary supported scopes

Canonical input:

```python
ShipCombatSideInput.standard_targetable_by_opponent: bool | None
```

Population gate:

```text
supported blocks=10
conflicts=0
blocked factual pairs=0
potential first-selector regressions=0
baseline mismatch profiles fixed=4/4
unrelated mismatches=0
```

Privateer ordinary Rob:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Bird ordinary Super Spy production runtime:

```text
41 targeted tests passed
one-way plain-STANDARD opportunities=8
decisive rows=4
match=1 mismatch=0 unresolved=3
blocked factual-pair regressions=0
focused 511506/T94 ship202 <- 496:
  effective_cloak=True
  standard_targetable_by_opponent=False
```

Status within the conservative ordinary Super Spy scope:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Advanced Cloak remains unresolved in production. The three decisive historical Advanced rows are explained but not promoted into a generic predictor.

### C3 state carry prerequisite

`carry_ship_to_next_engagement(...)` remains the verified between-combat state primitive. Clean owner-certain C3 chain subset:

```text
5 eligible transitions
5/5 exact carry differential
old reset baseline 3/5
```

Captured predecessor transitions are outside this proof because capture may change ownership and hostility.

### Mutable active ship queue — closed

Production module:

```text
src/planets_lab/rules/combat/mutable_queue.py
```

API:

```python
ShipQueueMutationResult
apply_ship_terminal_batch(...)
```

Semantics:

```text
destroyed -> remove from active map
survivor  -> require full C3 carry vector and carry state
captured  -> unresolved / fail closed
```

The batch is atomic: capture, unknown terminal flags, incomplete survivor state or carry error leaves the entire original active map unchanged.

Active diagnostic:

```text
tools/diagnostics/combat_host_mutable_ship_queue_audit.py
```

Tests:

```text
tests/test_combat_mutable_queue.py
tests/test_combat_host_mutable_ship_queue_audit.py
```

Required acceptance:

```text
survivor_population_present=True
survivor_membership_exact=True
capture_fail_closed_if_observed=True
destroyed_removal_if_reappearance_observed=True
no_production_mutation_errors=True
no_terminal_flag_unknowns=True
mutable_ship_queue_transition_gate_passed=True
```

The corpus gate reuses the independent C3 ship-chain replay and tests C5 membership/continuation only. Absence of destroyed-reappearance rows is not treated as standalone corpus proof of destruction ordering.

### Next combat gates

After mutable membership passes:

1. compose membership mutation with the initial selector;
2. track pair occurrence count and apply the already DIFF_VERIFIED second-pass side reversal;
3. differentially validate the second ordinary STANDARD queue step;
4. reconstruct capture ownership/hostility continuation as a separate branch;
5. integrate ship-to-planet / planet-base queue ordering;
6. keep game `591478` separate.

## Wider Host reconstruction order

1. Movement checkpoint — substantially reconstructed.
2. Classic pairwise combat C1/C2.
3. Ordinary ship battle sequences C3.
4. Planet/starbase sequences C4.
5. Full Host combat ordering / engagement selection C5 — current immediate focus.
6. Planet economy + starbases + ship production.
7. Minefield lifecycle.
8. General missions + special ship abilities.
9. Diplomacy / Safe Passage / alliance / team semantics across all subsystems.
10. Race-specific mechanics integrated vertically.
11. Observer / visibility / fog-of-war / shared intel.
12. End-to-end Host-order differential validation over complete turns.
13. Training environment and AI after simulator/observer surfaces are sufficiently faithful.

## Wider milestones

```text
M0 deterministic skeleton:          ~90%+
M1 minimal sandbox/infrastructure: ~80-90%
M2 economy/planetary Host:         ~35-50%
M3 warfare overall:                ~70-80%
M4 race-specific mechanics:        ~35-50%
M5A historical corpus pipeline:    ~80-90%
M5B Nu compatibility/differential: ~70-80%
M6 training/AI:                    intentionally later
```

Do not shortcut unresolved Host rules merely to begin training sooner.


### 2026-09-18 queue composition checkpoint

The first mutable membership runtime included isolated game `591478` and therefore ran 12 archives instead of the ordinary 11. Its survivor and capture behavior was exact, but all printed destroyed-reappearance contradictions were from the isolated game. The diagnostic now excludes `591478` before promotion accounting; rerun is pending.

Production ordinary STANDARD queue history now lives in:

```text
src/planets_lab/rules/combat/host_queue.py
```

It filters inactive/exhausted pairs, delegates pair choice to the canonical selector, records first-pass sides and occurrence count, and applies the already DIFF_VERIFIED second-pass reversal. It fails closed on incomplete occurrence history and never silently reuses pre-mutation pair decisions.

Current runtime gates:

1. rerun mutable membership on the repaired 11-game ordinary scope;
2. validate production occurrence-history composition on the two repeated-pair controls;
3. then build the full post-mutation multi-pair differential: replay VCR N terminal state -> mutate active set -> independently rebuild current pair candidates -> canonical next selector -> compare with factual VCR N+1.

Capture ownership/hostility continuation remains separate.


### 2026-09-18 runtime closure and active next-pair gate

Runtime:

```text
docs/handoff/2026-09-18-combat-c5-mutable-and-second-standard-runtime.md
```

Closed ordinary-scope results:

```text
mutable membership:
  11 archives
  survivor membership 1146/1146
  capture fail-closed 23/23
  destroyed predecessor reappearances 0
  gate passed

second STANDARD occurrence:
  repeated controls 2
  production exact 2/2
  gate passed
```

The active C5 gate is now:

```text
tools/diagnostics/combat_host_post_mutation_next_pair_audit.py
```

It tests held-out next-VCR prediction over exact-set multi-VCR sites by composing independently reconstructed T-1 candidate rows, deterministic replay terminal state for VCR N, production membership mutation, occurrence history and the canonical selector. VCR N+1 is comparator-only.

If this bounded gate is green, the next refinement is dynamic pair-decision recomposition after combat rather than reusing the already verified T-1 pair projections. Capture continuation remains separate.


### 2026-09-18 post-mutation next-pair closure

Held-out next-VCR differential:

```text
strict:
  23 exact-set multi-VCR sites
  16 exact sites
  7 capture exclusions
  22/22 compared next VCR transitions exact

conditional:
  same population/result

transitions_with_inactive_filter=22/22
all_profiles_pass=True
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The active C5 queue gap is now capture continuation. Production still fails closed on `captured=True`.

New capture diagnostic:

```text
tools/diagnostics/combat_host_capture_continuation_audit.py
```

It measures whether a captured ship's factual next-VCR race changes to the captor race, whether hull/combat state carries, whether Federation recovery applies under a Federation captor, and whether the next opponent is the captor or a third ship. No production capture semantics are promoted until runtime is reviewed.


### 2026-09-20 capture transition checkpoint

Descriptive ordinary corpus:

```text
23 capture reappearances
23/23 hull preserved
23/23 owner/race -> captor
23/23 next crew = 10
23/23 torpedoes carry
23/23 fighters carry
22/23 damage carry
22/23 raw shield carry
```

The documented 10-person prize crew and NuHost end-of-battle Federation shield recovery are now wired into a bounded production capture transition.

Production capture requires explicit `ShipCaptureTransfer`; missing transfer metadata still fails closed. The captured ship remains active after transfer.

Active differential:

```text
tools/diagnostics/combat_host_capture_continuation_audit.py
```

It now validates production owner/race/hull/shield/crew/ammunition state against the next factual VCR. The known `621253/T17 ship84 11->7` damage-only replay residual remains isolated and any additional damage residual fails the gate.


### 2026-09-20 production capture closure

Production capture state differential:

```text
owner/race/hull/shield/crew/torpedoes/fighters 23/23 exact
damage 22/23 exact
only known 621253/T17 ship84 11->7 replay residual remains
capture_transition_gate_passed=True
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Active next gate:

```text
tools/diagnostics/combat_host_post_capture_opponent_audit.py
```

It classifies the immediate post-capture opponent owner as pre-capture owner / captor / third party across the observed 15 planet/base and 8 ship continuations. This is intentionally narrower than target ordering.


### 2026-09-20 post-capture opponent residual

Immediate opponent owner distribution after production-validated capture:

```text
pre-capture owner=22/23
third party=1/23
captor=0/23
planet/base=15
ship=8
```

Therefore an "always old owner" rule is rejected.

Focused residual:

```text
622476/T17 ship7
owner5 -> captured by owner3/ship44
next opponent owner8/ship48
```

Active diagnostic:

```text
tools/diagnostics/combat_host_post_capture_third_party_residual_audit.py
```

It determines whether ship48's independent T-1 Kill!/PE request against owner3 already explains VCR38, while also inventorying the complete site queue and relation signatures. Do not encode captured-ship old-order persistence unless this independent initiator hypothesis fails.


### 2026-09-20 post-capture opponent attribution — universal invariant rejected

Observed immediate opponent owner after capture:

```text
pre-capture owner=22/23
third party=1/23
captor=0/23
```

The universal old-owner rule is rejected.

The third-party residual `622476/T17 ship7 -> ship48` is independently explained by ship48's T-1 Kill! aggression against post-capture owner3. This does not prove captured-ship old-order persistence.

Active next gate:

```text
tools/diagnostics/combat_host_post_capture_initiator_population_audit.py
```

It classifies all 23 continuations by independently attributable opponent aggression versus captured-ship old-order aggression candidates.


### 2026-09-20 post-capture initiator population

Observed across all 23 production-validated capture continuations:

```text
independent opponent initiator=23/23

ship opponent:
  Kill!/PE against new owner=8/8

planet/base opponent:
  NUK/ATT=15/15

explanation:
  opponent_only=21
  both=2
  captured_old_orders_only=0
  neither=0
```

The two missing old captured-ship T-1 rows are optional historical observability gaps, not failures of opponent-initiator reconstruction. v2 diagnostic acceptance has been repaired accordingly.

No observed continuation requires old captured-ship aggression to persist. Do not promote old mission/PE persistence from this corpus.

After the v2 acceptance rerun, the next C5 queue target is mixed ship/planet ordering rather than capture-list guessing.


### 2026-09-20 post-capture initiator closure

v2 runtime:

```text
23 capture continuations
23/23 independent opponent initiators
8/8 ship via Kill!/PE
15/15 planet/base via NUK/ATT
21 opponent_only
2 both
0 captured_old_orders_only
0 neither
required unresolved=0
optional old-order history gaps=2
gate passed
```

Status:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

No observed continuation requires captured old mission/PE persistence.

Current C5 focus is now mixed ship/planet-base queue ordering:

```text
docs/handoff/2026-09-20-combat-c5-mixed-ship-planet-queue-pending.md
```

Current engineering estimate:

```text
combat C1-C5 mechanics knowledge: ~85-90%
whole NuHost roadmap:            ~45-55%
```

Independent ship-combat candidate coverage remains ~21.6%; mechanics knowledge is therefore much farther ahead than end-to-end historical coverage.
