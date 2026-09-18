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
