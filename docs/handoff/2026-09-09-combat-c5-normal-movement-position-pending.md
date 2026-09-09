# C5 Host combat — T-1 normal-movement position gate — pending runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains open/draft. Game `591478` remains excluded from ordinary promotion.

## Why this gate follows candidate-set v1

Candidate-set v1 was clean but covered only:

```text
1 / 1986 factual unique ship pairs
```

because its position scope admitted only intrinsically stationary Warp-0 ships. The dominant exclusion was:

```text
self_movement_possible=1606
```

Therefore the next dependency is movement-derived precombat position, not weaker combat eligibility.

## Committed diagnostic

```text
tools/diagnostics/combat_host_normal_movement_position_audit.py
tests/test_combat_host_normal_movement_position_audit.py
```

Schema:

```text
planets-lab.combat-host-normal-movement-position-audit.v2
```

## Evidence boundary

This audit is site-conditioned but does not use factual `T` ship state as predictor input.

Factual ship-vs-ship VCRs provide only:

- ordinary `(game, battle_turn, x, y)` comparison coordinates;
- factual pair membership used to define which combatant occurrences must be explained.

For every factual ship occurrence, the predictor starts from owner-current `T-1`.

### Stationary branch

The conservative v1 stationary policy is retained for direct position proofs:

- Warp 0;
- not Tow / Intercept / C&I;
- not HYP;
- not a visible Tow target;
- not an obvious Firecloud Chunnel-source stack.

### Normal self-movement branch

Only rows initially classified as `self_movement_possible` are considered for ordinary self-movement, but v2 **rechecks special movement before normal geometry**. This is required because the older stationary helper reports non-zero Warp before testing special movement state.

A moving ship remains uncovered if any of these apply:

- mission Tow (`6`);
- mission Intercept (`7`);
- mission Bird Cloak and Intercept (`20`);
- FC `HYP`;
- the ship is a visible Tow target;
- its origin is an obvious Firecloud Chunnel-source stack;
- its T-1 position is unknown.

Only after those guards does the ordinary normal-movement branch use:

- owner-current `T-1` position, waypoint and requested warp;
- owner-current `T-1` engine/components/cargo fields;
- raw T-1 `mass` as the movement-mass input;
- canonical `plan_full_normal_move(...)` Host major/minor geometry;
- Gravitonic doubling for known gravitonic hulls;
- the existing strict raw-damage maximum-warp rule where its fail-closed prerequisites hold;
- known ordinary warp-well setting and eligible warp-well planets.

### Warp-well fail-closed rule in v2

The audit obtains **all factual planets** for the turn, not only the already-recognized warp-well-eligible subset.

- `warp_wells_enabled=False`: ordinary endpoint is retained.
- `warp_wells_enabled=True`: eligible planet ids must be known; otherwise endpoint is unresolved. Known eligible wells are applied using canonical warp-well geometry.
- `warp_wells_enabled=None`: if the predicted endpoint could be affected by any factual planet's warp well, the result is `warp_well_setting_unknown`; only an endpoint for which warp wells are geometrically irrelevant is accepted.

This prevents unknown settings from being silently treated as disabled.

### Other deliberate first-pass exclusions

This first movement expansion does **not** guess:

- sphere movement;
- explicit inbound/outbound cargo-transfer cases;
- MKT pre-movement mass mutation;
- fuel-prorated movement when raw T-1 fuel is insufficient.

If one of these can materially change the endpoint, the occurrence stays uncovered.

Partial ordinary movement to the canonical Host major/minor endpoint is allowed only when raw T-1 fuel is sufficient for that movement at raw T-1 mass.

## Why fuel proration is excluded here

Nu waypoint fuel proration itself is already differential-verified in a strict movement scope, but introducing it into this first combat-position gate would mix two questions:

1. whether ordinary self-movement endpoint composition is correct;
2. whether all pre-movement fuel/mass mutations have been reconstructed for combatants.

The first gate therefore requires raw-fuel sufficiency. Explicit transfer cases are removed. Repair-related mass reduction can only make a raw-fuel-sufficient movement cheaper; it cannot create a shorter endpoint unless it changes the effective damage-limited warp, which is separately fail-closed.

## Pre-runtime hardening regressions

The targeted tests now pin the specific v2 boundaries:

- moving Intercept does not fall through to ordinary movement;
- moving Tow target does not fall through;
- moving `HYP` does not fall through;
- moving ship in an obvious Chunnel-source stack does not fall through;
- unknown warp-well state plus a potentially relevant factual planet remains unresolved;
- explicit transfer remains unresolved;
- raw-fuel-insufficient movement does not guess fuel proration;
- canonical full and partial normal endpoints remain covered.

These tests are committed but are not `TESTED` until the user runtime reports success.

## Runtime interpretation

After tests/audit return `rc=0`, require:

```text
payload_conflicts=0
```

Then inspect:

```text
ship_occurrences.position_predicted
ship_occurrences.position_exact
ship_occurrences.position_mismatch
ship_occurrences.position_uncovered

factual_pairs.position_exact
factual_pairs.position_mismatch
factual_pairs.position_uncovered

sites.all_factual_pairs_position_exact
sites.has_position_mismatch
normal_prediction_reasons
```

### Strong result

A useful gate has:

- materially higher factual-pair coverage than v1;
- zero or very few movement-position mismatches;
- any mismatch explainable by a bounded missing movement mechanic rather than by changing combat rules.

### Mismatch policy

Every predicted factual-combatant endpoint that differs from the factual battle site is a movement-position residual. Do not feed that occurrence into candidate-set v2 until explained or explicitly moved back to uncovered.

Do not use factual `T` survivor position to patch the predictor.

## Next step after runtime

If the normal-movement position scope is clean enough, integrate only the exact/validated position sources into candidate-set v2 and remeasure factual-pair coverage plus pair-level `eligible / blocked / unresolved`.

If mismatches are material, cluster them first by movement source/context (damage, transfer, warp well, mine/web, ion storm, topology, etc.) and close only attributable branches.
