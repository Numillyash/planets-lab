# Public capture side held-out result and residual split

Date: 2026-10-03

Frozen pre-heldout candidate commit:

    cd87f9505472e5e396db28a7d6f7c67c561f9c64

Held-out runner source:

    b02438605422b650ce7bbed2e9afcd55c76f335b

Runtime evidence:

    runtime-logs/public-capture-side-heldout-validation/
    20261003T165327Z_b02438605422

## Gate result

The frozen candidate did not pass held-out.

Held-out population:

    capture ship rows                   43
    adjacent rows                       29
    resolved                            29
    not comparable                      14
    unresolved                           0

Frozen identity-anchored side gate:

    exact                               27
    mismatch                             1
    unresolved                           1
    gate passed                       false

This result must not be rewritten as a pass. The pre-heldout formula remains
frozen and failed its independent validation.

## True held-out side counterexample

Game 476380, turn 223:

    capture VCR                         903
    next VCR                            904
    captured ship                       157
    factual next opponent               514
    capture prize side                  LEFT
    factual next prize side             RIGHT

The identity-anchored original-order pair is reachable.

The frozen candidate therefore predicts sticky LEFT and is wrong.

Important detail: the external reference cursor itself reaches the factual pair
with prize on RIGHT, but that external cursor is not a NuHost side authority.
Using its predicted side globally would regress multiple discovery controls.

The T-1 STANDARD keys are:

    captured ship 157    [4, 157, 0]
    opponent ship 514    [0, 24, 514]

This is the first reachable captured-LEFT observation in the tested population
where the factual side flips to RIGHT. It remains an open NuHost queue/side
residual.

## Held-out unresolved is a repeated-capture mutation chain

Game 257776, turn 230:

    VCR 1644:
        ship 71 owner 2 -> captured by owner 8
        ship 71 appears again in VCR 1645

    VCR 1645:
        ship 71 owner 8 -> captured by owner 2
        ship 71 appears again in VCR 1646

The second capture continuation is adjacent (1645 -> 1646), but there is no
valid T-1 ship-71 state owned by owner 8 because owner 8 acquired the ship during
VCR 1644 in the same combat phase.

Therefore:

    captured_ship_tminus1_missing

is not a corpus/parity failure. The neutral/fresh-FC side input for the second
capture must come from mutable state produced by the first capture, not directly
from the pre-turn archive.

This is a post-capture mutable-order-state/repeated-capture dependency.

## Consequences

The previous single LEFT/RIGHT blocker has split again:

1. ordinary/identity-conditioned side behavior is strongly constrained but has
   one genuine held-out reachable flip residual;
2. repeated capture requires carrying the captured prize's mutated combat-order
   state across same-turn captures;
3. conservative movement fail-closed cases remain a separate predictive-queue
   problem and must not be folded into side assignment.

The next candidate is necessarily held-out-informed. It may be explored against
the now-open corpus, but it requires a new independent validation population
before canonical promotion.

Suitable future independent evidence includes:

- newly acquired public games not present in public36;
- prospective turns from controlled private games such as game 686764;
- deliberately constructed capture/repeated-capture experiments.

## Immediate diagnostic

The external original-order comparator now emits a compact cursor trace for each
candidate encountered when the captured prize is considered on RIGHT:

    left/right order indices
    left/right ship ids
    active membership
    strict-attacker membership
    accepted/rejected

Use this trace to compare game 476380/T223 against reachable LEFT-sticky
controls. Do not alter the frozen pre-heldout rule.

No canonical NuHost side mechanic is promoted by this checkpoint.
