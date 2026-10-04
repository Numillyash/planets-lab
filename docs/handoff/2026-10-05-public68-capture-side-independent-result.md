# Public68 independent capture-side result and post-independent candidate

Date: 2026-10-05

## Independent gate result

Frozen post-heldout candidate commit:

    592607b07efa0f857521da05fe0651127ed8be2d

Canonical runtime evidence:

    runtime-logs/public-capture-side-independent-validation/
    20261004T165819Z_051e365210be

Independent population boundary:

    short32 manifest games      32
    short32 index games         32
    overlap with public36        0
    ship capture continuations  37
    globally adjacent rows      22

Frozen post-heldout candidate result:

    exact                       21
    mismatch                     1
    unresolved                   0

Independent branch coverage:

    reachable sticky                     9
    nonreachable neutral/fresh-FC        6
    second-occurrence reversal           1
    reachable numeric-opponent override  6

Therefore:

    independent_validation_status = FAILED_MISMATCH
    candidate_gate_passed         = false
    promotion_ready               = false

This is a real independent failure. Do not relabel the frozen post-heldout
candidate as validated.

## Independent counterexample

Game 341336, turn 75:

    capture VCR             338
    next VCR                339
    captured ship           211
    captor ship              12
    next opponent ship      369

Observed side transition:

    capture side            LEFT
    factual next side       LEFT

The frozen post-heldout candidate predicts RIGHT because the identity-anchored
original-order pair is reachable and the opponent has STANDARD numeric priority
group 0.

T-1 order context:

Captured prize ship 211:

    mission                 1
    primary enemy           0
    friendly code           gs3
    priority                [4, 211, 0]

Opponent ship 369:

    mission                 3  (Kill)
    primary enemy           5
    friendly code           004
    priority                [0, 4, 369]

The identity-anchored comparator reaches the factual pair, so this is not a
false mismatch caused by missing opponent identity/eligibility. The old sticky
capture-side control is exact on this row.

## Numeric LEFT discriminator comparison

There are now three genuinely discriminating reachable first-occurrence rows
where the captured prize enters the continuation on LEFT and the next opponent
has numeric group-0 priority.

Two flip LEFT -> RIGHT:

    game 476380 T223 VCR903 -> 904
    opponent 514
    opponent mission 1
    opponent FC 024
    opponent priority [0, 24, 514]

    game 421949 T49 VCR91 -> 92
    opponent 451
    opponent mission 1
    opponent FC 870
    opponent priority [0, 870, 451]

One remains LEFT:

    game 341336 T75 VCR338 -> 339
    opponent 369
    opponent mission 3 (Kill)
    opponent FC 004
    opponent priority [0, 4, 369]

Thus numeric priority group 0 alone is not the side discriminator.

## Open-population Kill interaction

After the short32 gate is opened, the combined adjacent population is:

    old discovery           31
    old heldout             29
    independent short32     22
                            --
    total                   82

Across reachable first-occurrence observations, every currently observed Kill
opponent preserves the capture side, including:

    mission 3 / group 1
    mission 3 / group 2
    mission 3 / group 0

The two observed numeric LEFT -> RIGHT flips are both non-Kill mission-1
opponents.

A bounded Kill-sensitive candidate therefore fits all open 82 / 82 adjacent
rows:

1. second same-pair occurrence -> ordinary pair-side reversal;
2. reachable first occurrence:
   - captured prize already RIGHT -> RIGHT;
   - captured prize LEFT + nonnumeric opponent -> LEFT;
   - captured prize LEFT + numeric group 0 + Kill opponent -> LEFT;
   - captured prize LEFT + numeric group 0 + observed non-Kill branch -> RIGHT;
3. nonreachable original-order pair -> neutral captured orders + fresh
   nonmatching symbolic FC side.

Implementation:

    tools/diagnostics/combat_public_capture_side_postindependent_candidate.py

Status:

    POST_INDEPENDENT_CANDIDATE_NOT_CANONICAL

The independent short32 evidence directly informed the Kill-sensitive split.
The 82/82 open-population fit is therefore fitting evidence, not validation.

## Interpretation

The evidence now rejects the idea that numeric Friendly Code priority by itself
forces the captured prize to RIGHT.

A more plausible mechanism is that STANDARD ordering priority and combat
aggression/initiator semantics are separate inputs to post-capture side
assignment. Numeric FC determines the opponent's early STANDARD priority, while
Kill versus non-Kill combat request state appears to affect which side the
captured prize retains or receives.

This interpretation is still a hypothesis. No production combat rule should be
changed yet.

## Next independent evidence

The highest-value next discriminators are predeclared:

1. captured prize LEFT + reachable numeric group-0 opponent + Kill;
2. captured prize LEFT + reachable numeric group-0 opponent + non-Kill/PE;
3. captured prize LEFT + numeric group-0 opponent with another non-Kill mission
   if such a factual continuation exists;
4. additional second-occurrence capture rows as continuity controls.

A future validation population must not overlap public68 and must be selected
without using these outcomes.

Prospective private game 686764 remains especially valuable because its orders
can be controlled deliberately, but private/live Corpus DB ingestion is still a
separate work item.

Do not reuse the now-open short32 population as validation for the
post-independent candidate.
