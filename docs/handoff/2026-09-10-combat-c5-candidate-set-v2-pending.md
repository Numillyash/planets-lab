# C5 Host combat — candidate-set v2 pending runtime

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains excluded from ordinary promotion.

## Dependency now closed

Repaired storm-aware position v3 runtime is recorded in:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
```

Runtime source `14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c` passed tests/audit with:

```text
ship occurrences: factual=3204 predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs: total=1986 exact=678 mismatch=4 uncovered=1304
sites: total=1220 fully exact=346 mismatch=4
storm modes: false=10 true=1
payload_conflicts=0
```

The six attributable classic-storm residuals are now exact and no new mismatch appeared. Two of the four remaining rows are specific DIFF_VERIFIED stochastic normal-mine hits; two remain bounded unresolved. None is patched with factual coordinates.

## New diagnostic

```text
tools/diagnostics/combat_host_candidate_set_v2_audit.py
tests/test_combat_host_candidate_set_v2_audit.py
```

Schema:

```text
planets-lab.combat-host-candidate-set-audit.v2
```

This is still a **site-conditioned differential**, not a full-turn battle-site predictor and not a mutable Host queue.

For each factual ordinary ship-combat site it:

1. reconstructs all owner-current T-1 ships for that battle turn;
2. independently predicts each ship's precombat position with the repaired position-v3 layer;
3. fails closed any otherwise deterministic normal-movement route that visibly crosses a foreign T-1 normal/web minefield, because hit occurrence is stochastic;
4. admits only ships whose independently predicted position equals the site;
5. enumerates all cross-owner physical candidate pairs at that independently reconstructed stack;
6. evaluates the canonical pair-selection layer in strict leave-pair-out diplomacy and conditional aggression profiles;
7. compares only afterward against the factual VCR pair set.

The mine guard is deliberately conservative: foreign-field crossing means *position unresolved*, not "a mine hit occurred". Battle-turn-created fields and other same-Host-turn state that is absent at T-1 can still produce position residuals and must not be copied from factual VCR/T state.

## Important output

Summary keys:

```text
factual_unique_pairs
factual_pairs_candidate_covered
factual_pairs_candidate_uncovered
factual_pair_position_status
factual_ship_position_status
factual_position_reasons
candidate_pairs
candidate_position_sources
mine_route_risk
strict
conditional
sites
```

Interpretation:

- `factual_pair_position_status.exact` is the population whose two ship positions independently resolve to the factual site before pair eligibility is considered.
- a candidate-covered factual pair with `conditional.engagement_eligible=False` is a real pair-eligibility contradiction and must be investigated individually;
- `strict unresolved` is not a mismatch: leave-pair-out diplomacy intentionally remains conservative;
- `eligible_nonfactual` is not yet a queue error: target selection, survival/capture mutation and repeated-pair history are not applied by this diagnostic;
- position `unresolved`/`mismatch` rows remain movement coverage boundaries, not combat blockers.

## Runtime gate

Run the targeted canonical combat/position/candidate tests and then the full v2 candidate-set diagnostic over all 11 ordinary archives.

Success for advancing to mutable target-list reconstruction does **not** require every factual pair to be position-covered. It requires:

- tests rc=0;
- audit rc=0;
- payload_conflicts=0;
- materially larger factual candidate coverage than v1's `1/1986`;
- no candidate-covered factual pair conditionally hard-blocked by the canonical pair layer, or every such row individually explained before promotion;
- remaining movement uncertainty kept explicit.

If coherent, checkpoint candidate-set v2 and move next to mutable target selection / queue mutation on the fully position-covered sites. Do not reopen closed Galactic Power, reciprocal PIA, matching-FC or repeated-pair gates absent contradiction.
