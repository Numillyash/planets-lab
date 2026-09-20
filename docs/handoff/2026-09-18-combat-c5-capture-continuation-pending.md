# C5 capture continuation — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains excluded from ordinary promotion.

## Closed queue prerequisite

Runtime:

```text
docs/handoff/2026-09-18-combat-c5-post-mutation-next-pair-runtime.md
```

Bounded exact-set post-mutation next-pair selection is now:

```text
22 / 22 held-out next VCR transitions exact
7 capture-predecessor sites excluded
strict + conditional acceptance passed
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

All 22 compared transitions exercised inactive-pair filtering after prior combat.

## Why capture is next

The exact-set next-pair population contains seven multi-VCR sites per profile that could not be continued solely because the predecessor replay marked a participant as captured.

Across the ordinary 11-game chain audit there are 23 same-turn same-location `reappearance_after_defeat` transitions after the `591478` isolation fix; the mutable membership runtime already showed these are capture predecessors rather than ordinary destroyed-ship reappearances.

Production therefore remains deliberately fail-closed on capture until the continuation state is measured.

## Active diagnostic

```text
tools/diagnostics/combat_host_capture_continuation_audit.py
```

Unit test:

```text
tests/test_combat_host_capture_continuation_audit.py
```

Implementation:

```text
4b52a987a5edf6bcc91e74925a75ca0f9dd471eb
  combat: add captured-ship continuation audit

8ee250f30a6dfcd38b3e80b40f874a85217b5e8e
  test: cover capture continuation attribution
```

## Questions measured

For every ordinary same-turn same-location ship chain where deterministic replay of VCR N returns `captured=True` and the same ship id appears later:

1. is the hull id preserved;
2. does factual next-VCR `raceid` change from the captured ship's old race to the previous opponent/captor race;
3. does the next opponent equal the captor again or a third ship;
4. which LEFT/RIGHT side the captured ship occupies next;
5. how `damage / crew / torpedoes / fighters` compare from capture terminal to next VCR start;
6. whether shields are exact carry or, for a Federation captor, match the existing +25 Federation between-fight recovery candidate.

The diagnostic is descriptive in this first pass. Only hull preservation and race-to-captor attribution are acceptance fields. Dynamic carry distributions are reported but not promoted until runtime is reviewed.

## Evidence boundary

- game `591478` excluded;
- deterministic Classic replay provides capture terminal state;
- factual next VCR of the same ship id provides continuation observation;
- no post-Host T state is used;
- previous opponent's factual VCR `raceid` is used only as the captor-race attribution comparator;
- no production capture mutation is changed yet;
- post-capture mission, PE, diplomacy and pair ordering remain unresolved until the population shape is known.

## Runtime

Run:

```bash
cd ~/projects/planets-lab

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

echo "===== HEAD ====="
git rev-parse HEAD
git status --short

echo
echo "===== CAPTURE TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_host_capture_continuation_audit.py \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py

echo
echo "===== CAPTURE CONTINUATION CORPUS ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_capture_continuation_audit.py \
  --output /workspace/artifacts/combat-host-capture-continuation.json

echo
echo "===== STATUS ====="
git status --short
```

Do not assume the dynamic carry model before reading the runtime. In particular, captured-ship crew state and Federation-after-capture shield behavior are empirical questions for this pass.


## 2026-09-20 descriptive runtime result

Runtime source:

```text
9d7f974feee3f77e5b3ddf1382fd72567e5cfa8d
```

Durable descriptive runtime:

```text
docs/handoff/2026-09-20-combat-c5-capture-continuation-descriptive-runtime.md
```

Observed:

```text
capture reappearances=23
hull preserved=23/23
race changes to captor=23/23
crew terminal 0 -> next start 10=23/23
torpedoes carry exact=23/23
fighters carry exact=23/23
damage carry exact=22/23
shield raw carry exact=22/23
```

The crew transition is also officially documented as the 10-person prize crew.

The single shield residual is:

```text
621896/T14 ship36
pre-capture race1
terminal shield0
captor race3
next race3 shield25
```

and matches the documented NuHost rule that Federation shield recovery occurs at the end of the battle, before the observed ownership transfer.

The single damage residual remains:

```text
621253/T17 ship84 VCR39->45 damage 11->7
```

and is not encoded as capture repair.

## Production v2 gate

Production commits:

```text
d7db90e5849dbadf4fde93482e85459f95b57bb9
  combat: add captured ship carry transition

fbeddd8c317b1424c90caf11919b314daab7a08c
  combat: support explicit capture transfer mutation

b018f664df901ef68b48d6fbc248751c1f0b60d9
  diagnostics: retain VCR owner attribution in ship chains

c5f0302f0cce68e09a58cbf05690349ed7dec5d3
  test: cover captured ship sequence carry

82343768924e230b2246f5200d9981176038d1b7
  test: cover explicit capture queue mutation

8ca9e11f134494507a764cf08281b5d5c110aa52
  combat: export capture transfer primitives

9c97e6267506e57e359cd8b58716b174d21b9f02
  combat: wire capture continuation into production mutation

b67dff010dfb35a587ee3648f4edb32e408720e0
04b3e958ebd6eb2def21e274447c24e24ec7cdc5
  tests: align capture gate with production ordering

4fb09d32ac344a68c7f41e41e02eb51cb62ca030
  combat: fail capture gate on new damage residuals
```

New production API:

```python
CAPTURE_PRIZE_CREW = 10

carry_captured_ship_to_next_engagement(...)

ShipCaptureTransfer(
    new_owner_id=...,
    new_race_id=...,
    new_federation_crew_bonus=...,
    new_lizard_crew_bonus=...,
)

apply_ship_terminal_batch(
    ...,
    capture_transfers_by_ship_id={...},
)
```

Backward compatibility is deliberate:

```text
captured=True + no explicit ShipCaptureTransfer
  -> unresolved / fail closed
```

With explicit transfer metadata:

```text
terminal vector
 -> pre-capture Fed end-of-battle shield recovery
 -> prize crew 10
 -> owner/race transfer
 -> new-owner race bonus flags
 -> next-engagement weapon preparation
 -> captured ship remains active
```

The v2 diagnostic now compares production state against the next factual VCR and classifies one-sided next encounters as planet/base continuation rather than unknown.

Required acceptance:

```text
capture_reappearance_population_present=True
no_capture_transition_adapter_errors=True
hull_preserved=True
owner_changes_to_captor=True
race_changes_to_captor=True
production_capture_state_exact_excluding_damage=True
no_new_damage_replay_residuals=True
capture_transition_gate_passed=True
```

The only permitted damage residual is the already observed
`621253/T17 ship84 VCR39->45 11->7`; zero residuals is also valid. Any additional residual fails the gate.

## Updated runtime command

```bash
cd ~/projects/planets-lab

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

echo "===== HEAD ====="
git rev-parse HEAD
git status --short

echo
echo "===== CAPTURE PRODUCTION TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_sequence.py \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_host_capture_continuation_audit.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py

echo
echo "===== CAPTURE PRODUCTION CORPUS ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_capture_continuation_audit.py \
  --output /workspace/artifacts/combat-host-capture-continuation-v2.json

echo
echo "===== STATUS ====="
git status --short
```
