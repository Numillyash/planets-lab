# Frozen public capture side candidate before held-out

Date: 2026-10-03

Discovery implementation/source commit:

    e80b0e2d1ee5976c4e8c0dac530f8a1216324eb5

Discovery runtime evidence:

    runtime-logs/public-capture-o-layer-discovery/
    20261003T163249Z_e80b0e2d1ee5

Population:

    globally adjacent capture -> next VCR rows   31
    exact                                           31
    mismatch                                         0
    unresolved                                       0

Observed identity-anchored original-order split:

    O pair reachable        10
    O pair not reachable    21

## Frozen candidate

Condition only on the factual N+1 opponent identity/eligibility. Do not use its
factual LEFT/RIGHT side as an input.

Then:

    if identity-anchored original-order pair is reachable:
        predicted prize side = prize side in the capture VCR
    else:
        predicted prize side = side from neutral prize orders
                               + fresh nonmatching symbolic friendly code
                               + existing priority/occurrence rule

This candidate is frozen before held-out is opened.

The factual N+1 opponent identity is an explicit conditioning input, so this is
a side-assignment discriminator, not a complete independent next-pair predictor.

The discovery runtime also showed that all 16 previously dependency-blocked
rows were fail-closed movement-position cases rather than post-capture mutation
residuals:

    pre_move_mkt_mass_change        5
    intercept_movement              3
    hyperjump_movement              3
    normal_mine_route_risk          2
    tow_target                      2
    potential_chunnel_source_stack  1

No held-out result may be used to alter this frozen formula. A held-out mismatch
must be recorded as a mismatch and investigated as a new residual.

This document does not promote the candidate into canonical NuHost mechanics.
Promotion requires a clean held-out gate and an explicit evidence checkpoint.
