# C5 post-capture third-party residual — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains isolated.

## Population result that opened this gate

The immediate post-capture opponent audit over the 23 production-validated capture continuations found:

```text
capture_continuations=23
next_combat:planet=15
next_combat:ship=8

next_owner_relation:pre_capture_owner=22
next_owner_relation:third_party=1
next_owner_relation:captor=0

post_capture_opponent_gate_passed=False
```

The sole third-party row is:

```text
game 622476
turn 17
position 1973,1734
captured ship 7
pre-capture owner 5
captor ship 44 / owner 3
next VCR 38 opponent ship 48 / owner 8
```

Therefore "immediate next opponent is always the pre-capture owner" is rejected and must not be promoted.

## Documentation context

Primary Planets.nu Order Of Battle documentation says:

- ships fight if either side has Kill!/Primary Enemy aggression, and attacked ships defend themselves;
- every ship proceeds through its target list while alive/uncaptured;
- a captured ship may fight for its new owner;
- capture adds an additional target/order list which is set anew when captured;
- any pair can fight at most twice.

This makes an independently aggressive third-party ship a plausible explanation for the residual, but the corpus case must be inspected before encoding anything.

## Active targeted diagnostic

```text
tools/diagnostics/combat_host_post_capture_third_party_residual_audit.py
```

Test:

```text
tests/test_combat_host_post_capture_third_party_residual_audit.py
```

Implementation:

```text
79b997e96cbcde490c87fa9f7c4454e78bad6347
  combat: add post-capture third-party residual audit

b37f6ded0981dc052eab30eb2cba8ac0fc665b5e
  test: cover post-capture third-party residual audit
```

## What the diagnostic extracts

For `622476/T17 @ 1973,1734`:

1. complete factual VCR queue at the site;
2. T-1 owner-current state for every ship participating at that site:
   - owner/race;
   - mission;
   - mission target;
   - Primary Enemy;
   - Friendly Code;
   - fuel/cloak/damage;
   - static battle-priority key;
3. T-1 request matrix for every site ship against owners 3/5/8 using the already-tested `orders_request_ship_combat(...)`;
4. raw relation signatures among all involved owners;
5. focused booleans:
   - did old ship7 orders request owner8;
   - did captor ship44 request owner8;
   - did ship48 independently request combat against new owner3;
   - did ship48 instead request old owner5.

## Decision boundary

If ship48 independently requests owner3, the third-party residual is explainable without assuming that captured ship7 retained its old orders: ship48 can attack the newly transferred prize ship, which then defends.

If ship48 does not independently request owner3, inspect ship7's old orders and the full queue before inferring any capture-reset rule.

Do not promote a generic post-capture hostility rule from this one case until the initiator is identified.

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
echo "===== THIRD-PARTY RESIDUAL TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_host_post_capture_third_party_residual_audit.py \
  tests/test_combat_host_post_capture_opponent_audit.py \
  tests/test_combat_host_capture_continuation_audit.py

echo
echo "===== THIRD-PARTY RESIDUAL CORPUS ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_post_capture_third_party_residual_audit.py \
  --output /workspace/artifacts/combat-host-post-capture-third-party-residual.json

echo
echo "===== STATUS ====="
git status --short
```

The most important runtime field is:

```text
focus.third_party_orders_request_post_capture_owner
```

Do not assume its value before runtime.
