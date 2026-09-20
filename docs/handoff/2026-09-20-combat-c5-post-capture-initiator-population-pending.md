# C5 post-capture initiator population — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains isolated.

## Residual that motivated this gate

The immediate-opponent population after capture was:

```text
23 continuations
22 -> pre-capture owner
1  -> third party
0  -> captor
```

The sole third-party case:

```text
622476/T17 @ 1973,1734
ship7 owner5
  -> captured by ship44 owner3
  -> next VCR38 against ship48 owner8
```

Targeted runtime showed:

```text
ship7 old T-1 orders:
  mission=1
  PE=8
  requests owner8=True

ship48 T-1 orders:
  mission=3 (Kill!)
  PE=0
  requests owner3=True
  requests owner5=True
```

Therefore VCR38 is fully explainable by ordinary one-sided aggression after the capture transfer: ship48 independently attacks the new owner3 and ship7 can defend. Old ship7 orders also point at owner8, so this row cannot determine whether old-order aggression survives capture.

Do not promote old-order persistence from this case.

## Documentation constraint

Primary Planets.nu Order Of Battle documents that:

- a ship-vs-ship battle occurs if either side has Kill!/Primary Enemy aggression;
- attacked ships defend themselves;
- captured ships may fight for their new owner;
- captured ships receive an additional target/order list set anew when captured.

The refined evidence question is therefore not "is the next opponent always the old owner?" but "can the observed next combat be independently initiated under ordinary attack/defense semantics?"

## Active diagnostic

```text
tools/diagnostics/combat_host_post_capture_initiator_population_audit.py
```

Test:

```text
tests/test_combat_host_post_capture_initiator_population_audit.py
```

Implementation:

```text
6ffdb66b287edda1d04384d9374e600de8260f45
  combat: add post-capture initiator population audit

9b7df923a47d1371a8b0378b446487c043eb7bb1
  test: cover post-capture initiator population adapter

3c5eb4f3a2584ed929adad63f487a34c3ef7b64c
  combat: normalize post-capture initiator order inputs
```

## Population logic

For every production-validated capture continuation:

### Ship opponent

Read owner-current T-1 orders of the factual next ship opponent and evaluate:

```python
orders_request_ship_combat(
    mission=...,
    primary_enemy=...,
    opponent_owner_id=post_capture_owner,
)
```

This asks whether the opponent independently requests combat against the captured ship's new owner.

### Planet/base opponent

Read owner-current T-1 planet Friendly Code and classify:

```text
NUK / ATT -> independent planet attack candidate
other     -> no independent planet attack-code candidate
```

This is deliberately only the documented attack-code trigger. Diplomacy/matching-FC suppression remains separate.

### Captured ship old orders

The captured ship's T-1 Kill!/PE request toward the factual next opponent owner is also reported, but only as a historical alternative. It is never assumed to survive capture.

Rows are classified:

```text
opponent_only
captured_old_orders_only
both
neither
unresolved
```

## Acceptance / interpretation

Hard structural acceptance:

```text
capture_continuation_population_present=True
payload_conflicts_absent=True
no_adapter_unresolved=True
third_party_population_present=True
all_third_party_have_independent_attack=True
ship_and_planet_continuations_present=True
```

Do NOT require all 23 rows to have independent opponent aggression. The runtime distribution is the evidence for whether reconstruction of the capture-generated target list is needed for some rows.

Particularly inspect:

```text
independent_opponent_attack_candidate
captured_old_orders_attack_candidate

explanation:opponent_only
explanation:captured_old_orders_only
explanation:both
explanation:neither
```

If every row has an independent opponent initiator, the observed corpus does not require production reconstruction of captured-ship aggression to reproduce these continuations.

If some rows are `captured_old_orders_only` or `neither`, capture-list/order reconstruction becomes immediately necessary.

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
echo "===== POST-CAPTURE INITIATOR TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_host_post_capture_initiator_population_audit.py \
  tests/test_combat_host_post_capture_third_party_residual_audit.py \
  tests/test_combat_host_post_capture_opponent_audit.py \
  tests/test_combat_host_capture_continuation_audit.py

echo
echo "===== POST-CAPTURE INITIATOR CORPUS ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_post_capture_initiator_population_audit.py \
  --output /workspace/artifacts/combat-host-post-capture-initiator-population.json

echo
echo "===== STATUS ====="
git status --short
```
