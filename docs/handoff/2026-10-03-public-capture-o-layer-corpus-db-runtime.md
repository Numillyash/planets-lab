# Public capture O-layer Corpus DB runtime — 2026-10-03

Source main:

    4482e6ab8f4b962aff552aa2c98de4321d0c6054

Runtime evidence:

    runtime-logs/public-capture-o-layer-discovery/20261003T150910Z_4482e6ab8f4b

The discovery-only O-layer probe is now running against the active exact-parity
compact Corpus DB rather than whole-game ZIP decoding.

Operationally the migration closes the previous memory blocker. In particular,
game 233558 completed from 22 targeted snapshots instead of approaching the WSL
memory ceiling through full-game archive/Python materialization.

Discovery population:

    ship capture continuations     50
    globally adjacent rows         31
    resolved                       31
    not comparable                 19
    unresolved                      0

External original-order pair reachability split:

    O pair reachable                5
      factual LEFT                  2
      factual RIGHT                 3

    O pair not reachable           26
      factual LEFT                 23
      factual RIGHT                 3

The external c2ng candidate that forces a captured prize to RIGHT is not a
NuHost side rule:

    external O exact                3 / 31
    external O mismatch            28 / 31

However pair reachability exposes a stronger discovery-only structure.

For all five O-reachable rows, the factual post-capture prize side equals the
prize side in the capture VCR:

    reachable + sticky capture side = 5 / 5

For the 26 non-reachable rows, the existing neutral-orders + fresh nonmatching
symbolic FC priority control is exact:

    non-reachable + neutral fresh FC = 23 / 26

A provisional split candidate therefore scores:

    O reachable     -> retain capture side
    O not reachable -> neutral-orders fresh-FC priority

    exact             28 / 31
    mismatch           3 / 31

The three residual adjacent rows are:

    game 224849 turn 141 capture VCR 311 ship 533 -> factual RIGHT
    game 224849 turn 162 capture VCR 473 ship 258 -> factual RIGHT
    game 597910 turn 189 capture VCR 1176 ship 510 -> factual RIGHT

Do not freeze or test this rule on held-out yet.

Important dependency caveat: O pair reachability uses independently reconstructed
post-capture active/candidate state. The expanded public discovery population is
larger than the original eight-row capture checkpoint. A pair marked not
reachable may therefore reflect a candidate-graph/active-membership residual
rather than a distinct side-assignment layer.

Immediate next gate:

1. report whether the factual N+1 opponent is active after the mutation replay;
2. report whether it is a resolved candidate;
3. report requests-new-owner and strict-permission status/ranks;
4. evaluate the provisional 28/31 split candidate only after those dependency
   statuses are explicit;
5. keep held-out sealed until the discovery rule and dependency boundary are
   frozen.

No NuHost side mechanic is promoted by this checkpoint.

## Dependency-qualified discovery checkpoint

Runtime evidence:

    runtime-logs/public-capture-o-layer-discovery/20261003T154738Z_94186008f694

The dependency audit separates the 31 adjacent rows into:

    factual N+1 opponent active/candidate/request/strict resolved   15
    factual N+1 opponent absent from reconstructed active graph     16

On the dependency-qualified subset, the provisional split side candidate is:

    exact       15 / 15
    mismatch     0 / 15

On the dependency-blocked subset:

    exact       13 / 16
    mismatch     3 / 16

All three discovery mismatches are dependency-blocked:

    game 224849 turn 141 capture VCR 311 ship 533 -> factual RIGHT
    game 224849 turn 162 capture VCR 473 ship 258 -> factual RIGHT
    game 597910 turn 189 capture VCR 1176 ship 510 -> factual RIGHT

Therefore the current blocker is upstream of side assignment for these rows.
The factual ship really fights next, so a reconstructed active=false /
candidate=false result is evidence of an incomplete active/movement/history
model, not evidence that the ship is actually inactive.

The next discovery gate records whether each missing factual opponent was
predicted at the site, history-anchored, removed by mutation replay, or
owner-changed. Held-out remains sealed.

No NuHost side mechanic is promoted by this checkpoint.

## Side-only identity-anchored discriminator

The 16 dependency-blocked adjacent rows all fail before active membership because
the conservative movement predictor intentionally returns no exact position.
Observed sources are:

    pre_move_mkt_mass_change        5
    intercept_movement              3
    hyperjump_movement              3
    normal_mine_route_risk          2
    tow_target                      2
    potential_chunnel_source_stack  1

All 16 have predicted_position=None. None are history-anchored, mutation-removed,
or owner-changed by the current replay.

This is a heterogeneous special-movement/risk uncertainty population, not a
coherent post-capture side residual.

The next discovery comparator therefore conditions on one additional factual
input already proven by VCR N+1: the next opponent identity is active and
strictly eligible at that step. It injects only that identity/eligibility into
the external frozen-order diagnostic. It never uses the factual LEFT/RIGHT side.

This comparator is explicitly a conditional side discriminator, not an
independent queue predictor. Held-out remains sealed until its discovery result
is frozen.

