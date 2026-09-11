# C5 Host combat — Bird Advanced Cloak decisive-context runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Runtime

Source HEAD:

```text
838aca3a931d16f7cb46e28350271b34a1cacf8c
```

Targeted tests:

```text
16 passed
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_advanced_cloak_decisive_context_audit.py
```

Artifact:

```text
artifacts/combat-bird-advanced-cloak-decisive-context.json
```

## Summary

```text
focus_rows=3
expected_blocked_rows=2
expected_eligible_rows=1
stable_t_identity_rows=2
postmove_active_glory_possible_rows=0
postmove_loki_possible_rows=0
t_cloak_false_rows=0
t_cloak_true_rows=2
```

The diagnostic found no visible post-movement Glory, Loki or mine-route separator between the factual Advanced-Cloak control and the two skipped Advanced-Cloak targets.

## Factual control — 680435/T31 ship68 vs ship26

```text
expected_blocked=False
factual_outcome=pair_vcr
initial_classification=initial_pair_vcr
start_position=(1996,2287)
full_position_prediction=(1984,2266)
position_source=normal_move_warp_well
visible_mine_route_risk=None
prior_iscloaked=True
damage=0
fuel=480
postmove active Glory candidates=[]
postmove Loki candidates=[]
T stable identity=False
```

The simple reference normal-move projection from the preceding population gate ends at `(1986,2268)`, while the full position-v3 predictor correctly resolves the factual site `(1984,2266)` through the warp-well branch. Any further cloak attribution for this row must therefore use the full Host movement context rather than the simple normal-move endpoint.

Because the target participates in the factual VCR, no stable T identity survives for attribution. T cannot be used as a precombat state input.

Canonical mission constants also confirm attacker ship26 mission `3` is `Kill!`, not Intercept or another pre-standard mission. The pair therefore remains a valid ordinary-STANDARD negative control for a blanket Advanced-Cloak target blocker.

## Skipped controls — 620694/T119 ships26 and69 vs ship74

Both rows are:

```text
expected_blocked=True
factual_outcome=attacker_fought_other
initial_classification=initial_skip_target_outranks_factual
start_position=(1574,1872)
full_position_prediction=(1590,1837)
position_source=normal_move_warp_well
visible_mine_route_risk=None
prior_iscloaked=True
damage=0
postmove active Glory at site=False
postmove Loki within 10 ly=False
```

T attribution remains stable for both physical ships:

```text
ship26:
  T owner=3
  T damage=0
  T fuel=1
  T iscloaked=True

ship69:
  T owner=3
  T damage=0
  T fuel=396
  T iscloaked=True
```

This is consistent with the skipped ships remaining cloaked, but T remains attribution-only.

## Interpretation

The tested visible post-movement decloak hypothesis did **not** separate the factual ship68 row from the skipped ship26/69 rows:

```text
ship68 visible mine route risk: none
ship68 postmove active Glory:   none
ship68 postmove Loki <=10 ly:   none

ship26/69 visible mine route risk: none
ship26/69 postmove active Glory:   none
ship26/69 postmove Loki <=10 ly:   none
```

Therefore do not promote either of these blanket rules:

```text
Bird Super Spy + Advanced Cloak => untargetable
Bird Super Spy + Advanced Cloak => targetable
```

Population-wide Advanced Cloak targetability remains `UNRESOLVED`.

## Remaining high-value hypotheses

The next gate should inspect raw Host reports/events and game/race configuration around the three rows, especially the factual ship68 case:

1. system messages/events referring to ship68/ship26 or the battle site around T31;
2. mine/web-hit reports not represented by the visible minefield route context, including hidden-mine possibilities;
3. active race/campaign advantages for Bird owner3 and the relevant opponents, especially Hidden Minefields and Loki Immunity;
4. mechanical message/event schemas which may expose cloak failure, mine hit, Glory, Loki or other wake-up causes;
5. matched raw-event/message controls for the two skipped 620694/T119 ships.

Absence of a visible minefield in owner-visible state is not proof that no hidden/unobserved mine interaction occurred. Message absence likewise is not proof of no event unless perspective completeness is independently established.

## Evidence status

```text
Advanced Cloak decisive-context audit:
  CORPUS_OBSERVED + TESTED

visible postmovement Glory/Loki separator:
  NOT OBSERVED

visible candidate-set mine-route separator:
  NOT OBSERVED

population-wide Bird Advanced Cloak targetability:
  UNRESOLVED
```

Canonical `selection.py` and `queue.py` remain unchanged.
