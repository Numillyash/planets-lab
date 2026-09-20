# C5 post-capture opponent attribution — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains excluded.

## Closed prerequisite

Production capture state runtime:

```text
docs/handoff/2026-09-20-combat-c5-capture-production-runtime.md
```

Closed result:

```text
23 capture continuations
23/23 owner transfer exact
23/23 race transfer exact
23/23 hull exact
23/23 shield exact
23/23 crew exact
23/23 torpedoes exact
23/23 fighters exact
22/23 damage exact
known damage replay residual only
capture_transition_gate_passed=True
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Active diagnostic

```text
tools/diagnostics/combat_host_post_capture_opponent_audit.py
```

Test:

```text
tests/test_combat_host_post_capture_opponent_audit.py
```

Implementation:

```text
489032a8a1f0f43d39d848e343c074518f631298
  combat: add post-capture opponent attribution audit

c98cd0825c79f4adb41b9821065a6afbe2d8c346
  test: cover post-capture opponent attribution
```

## Question

The capture runtime split immediate continuation into:

```text
15 planet/base
8 third ship
```

This gate asks only:

```text
who owns the immediate next opponent?
```

For every production-validated capture continuation, the diagnostic opens the factual `to_vcr_id` and reads the owner/type of the side opposite the captured ship.

Possible classifications:

```text
pre_capture_owner
captor
third_party
```

Ship and planet/base continuations are counted separately.

## Evidence boundary

This is opponent-owner attribution only.

The factual next VCR is used as observation, not as selector input. The diagnostic does not yet infer:

- which specific old-owner ship is selected;
- which specific planet/base is selected;
- mission/PE reset semantics;
- diplomacy mutation;
- post-capture battle-priority key;
- full mixed ship/planet queue order.

If all 23 immediate opponents belong to the pre-capture owner, that is a strong corpus invariant supporting a later explicit post-capture hostility rule. It is not yet a full target selector.

## Runtime

```bash
cd ~/projects/planets-lab

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

echo "===== HEAD ====="
git rev-parse HEAD
git status --short

echo
echo "===== POST-CAPTURE OPPONENT TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_host_post_capture_opponent_audit.py \
  tests/test_combat_host_capture_continuation_audit.py \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_sequence.py

echo
echo "===== POST-CAPTURE OPPONENT CORPUS ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_post_capture_opponent_audit.py \
  --output /workspace/artifacts/combat-host-post-capture-opponent.json

echo
echo "===== STATUS ====="
git status --short
```

Required acceptance:

```text
capture_continuation_population_present=True
payload_conflicts_absent=True
no_missing_next_vcrs=True
no_opponent_projection_unresolved=True
next_opponent_always_pre_capture_owner=True
ship_and_planet_continuations_both_present=True
post_capture_opponent_gate_passed=True
```

Do not assume the relation distribution before runtime.
