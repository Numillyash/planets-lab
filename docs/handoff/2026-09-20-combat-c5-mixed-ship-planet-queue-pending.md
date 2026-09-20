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


## 2026-09-20 large-batch workflow

Per user workflow preference, C5 research now groups several related hypotheses into one longer batch rather than requiring one command per micro-gate.

New broad first-pass diagnostic:

```text
tools/diagnostics/combat_host_mixed_ship_planet_queue_batch_audit.py
```

Unit coverage:

```text
tests/test_combat_host_mixed_ship_planet_queue_batch_audit.py
```

One-command runner:

```text
tools/run-combat-c5-mixed-queue-batch.sh
```

Implementation commits:

```text
1e9a455c6b3dd1b93baff88150119636e7486424
  combat: add mixed ship-planet queue batch audit

e6f19ee1352d45da9f7afc2238a740569f195d3d
  test: cover mixed ship-planet queue batch audit

c40bc44eaca7551f5dfe25b17bca613d1c3f1394
  tools: add one-command C5 mixed queue batch

8e32455dbc40556283fdc1ff043ce1766e400a3a
  tools: keep mixed queue batch running after failures

a3b24234b07055ef1d3edbf6353ccad00cc47344
  tools: save full mixed queue batch log
```

### What the mixed diagnostic measures in one pass

1. mixed-site population and full factual queue profiles such as `SSPP`, `SPP`, etc.;
2. transition counts:
   - ship->ship;
   - ship->planet;
   - planet->planet;
   - planet->ship;
3. whether all ship combat forms a block before the planet/base block;
4. factual LEFT/RIGHT orientation of planet/base combat;
5. T-1 planet Friendly Code distribution and NUK/ATT population;
6. whether each planet attacker already participated in ship combat at the same site;
7. immediate same-ship ship->planet handoff counts;
8. capture->planet handoff counts;
9. repeated engagement groups against the same planet/base;
10. number of distinct planets per mixed site;
11. a deliberately naive comparison of repeated planet-attacker order against ordinary STANDARD ship Combat Priority.

The three ordering ideas are reported independently under `hypotheses`; a false hypothesis does not invalidate the batch and is expected to identify the next focused mechanic.

### One-command batch contents

The runner continues after individual stage failures and prints a final stage/RC summary.

It executes:

```text
pytest:
  mixed queue audit
  factual queue-shape audit
  planet mechanics + planet-chain audit
  ship post-mutation next-pair regression
  post-capture initiator regression
  host queue / mutable queue regressions

corpus:
  factual queue shape
  planet carry differential
  ship next-pair differential
  post-capture initiator differential
  mixed ship/planet discovery audit
```

Full output is automatically captured to:

```text
artifacts/combat-c5-mixed-queue-batch.log
```

JSON artifacts are written under `artifacts/`.

### Runtime

Use only:

```bash
cd ~/projects/planets-lab
git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

bash tools/run-combat-c5-mixed-queue-batch.sh
```

After completion, the full log file is sufficient for review. No need to manually run each diagnostic separately.
