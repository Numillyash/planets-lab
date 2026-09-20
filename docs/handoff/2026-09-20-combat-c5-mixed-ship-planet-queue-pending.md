# C5 mixed ship / planet-base queue ordering — pending

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains isolated.

## Closed prerequisites

### Ordinary ship queue

Closed:

- canonical initial STANDARD selector;
- directional targetability;
- mutable active membership;
- repeated-pair occurrence history;
- held-out post-mutation next-pair selection.

### Capture state

Closed production differential:

```text
23 capture continuations

owner/race/hull/shield/crew/torpedoes/fighters:
  23/23 exact

damage:
  22/23 exact
  one isolated known replay residual

capture_transition_gate_passed=True
```

### Post-capture initiators

Closed v2 population:

```text
23/23 observed continuations have an independent opponent initiator

ship opponents:
  8/8 Kill!/PE against the prize ship's new owner

planet/base opponents:
  15/15 NUK/ATT

explanation:
  opponent_only=21
  both=2
  captured_old_orders_only=0
  neither=0

required unresolved=0
optional captured-old-order history gaps=2

post_capture_initiator_gate_passed=True
```

Do not invent persistence of captured old mission/PE. It is not required by the observed population.

## Why mixed ship/planet ordering is next

Fifteen of the twenty-three production-validated prize-ship continuations enter planet/base combat immediately.

The ship-only queue is now substantially reconstructed, so the remaining high-value C5 boundary is:

```text
ship queue state
  +
planet/base attack/defense eligibility
  ->
mixed factual VCR ordering
```

## Questions to answer

1. At a site with both eligible ship-vs-ship and ship-vs-planet/base battles, which class is emitted first?
2. How are multiple attacking ships ordered against one planet/base?
3. How does ship STANDARD Combat Priority interact with planet/base combat?
4. Does a survivor/captured ship re-enter ship combat before or after planet/base combat?
5. How do NUK/ATT planet-initiated battles interleave with ship-initiated planet attacks?
6. What are the LEFT/RIGHT side rules for mixed queue steps?
7. How do planet/starbase destruction/capture-like terminal states affect the remaining queue?
8. Can one planet/base appear multiple times in a site queue, and under what termination rule?

## Evidence construction

Prefer a new read-only population audit before production changes.

The first pass should inventory every ordinary site containing both:

- at least one ship-vs-ship VCR; and
- at least one ship-vs-planet/base VCR.

For each site, record:

- factual VCR order;
- ship IDs / owner IDs;
- planet ID / owner ID;
- T-1 ship mission / PE / FC / static battle priority;
- T-1 planet FC, especially NUK/ATT;
- whether each pair is independently eligible under already-closed ship combat logic;
- survivor/capture history entering each mixed step.

Do not use factual queue rank as an input to the predictor.

## Promotion boundary

Do not promote a mixed-order rule from a small anecdotal sample.

The desired eventual gate is:

```text
independent pre-Host site reconstruction
  -> ship candidate graph
  -> planet/base candidate graph
  -> mutable queue state
  -> predicted next mixed VCR
  -> held-out factual next VCR
```

with factual VCR order comparator-only.

## Separate unresolved branches

Keep separate:

- generic Advanced Cloak predictor;
- capture-generated target list contents;
- isolated game `591478`;
- broad candidate-coverage expansion.

These must not be mixed into the first mixed-queue ordering gate.
