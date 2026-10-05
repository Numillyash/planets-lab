# Public100 prospective capture-side result and post-prospective candidate

Date: 2026-10-05

## Prospective gate result

Frozen post-independent candidate commit:

    46bcb08c2f0d3f0449b97921edb03ab6647f7d3b

Prospective runtime evidence:

    runtime-logs/public-postindependent-prospective-validation/
    20261005T191923Z_c4952b00ccfa

The fresh population was selected before its capture outcomes were opened:

    fresh games                         32
    overlap with public68                0
    ship capture continuations          43
    globally adjacent rows              20

The gate independently covered both discriminator branches that motivated the
Kill-sensitive post-independent candidate:

    reachable numeric group-0 + Kill        1
    reachable numeric group-0 + non-Kill    1

Frozen candidate result:

    exact                               19
    mismatch                             1
    unresolved                           0

Therefore:

    prospective_validation_status = FAILED_MISMATCH
    discriminator_coverage        = true
    candidate_exact_gate          = false
    promotion_ready               = false

The Kill/non-Kill split itself survived the fresh population. The failure is in
the older O-not-reachable branch.

## Prospective counterexample

Game 597079, turn 19:

    capture VCR             17
    next VCR                18
    captured ship           14
    captor ship            185
    factual next opponent  172

Observed side transition:

    capture side            LEFT
    factual next side       RIGHT

Captured ship T-1 orders:

    mission                  0
    primary enemy            0
    friendly code          999
    priority        [0, 999, 14]

Opponent T-1 orders:

    mission                  1
    primary enemy            3
    friendly code          mkt
    priority        [3, 172, 0]

Identity-anchored existing-order reconstruction:

    external order       [14, 172, 185]
    prize index                     0
    factual opponent index          1
    capture target index            2
    O pair reachable            false

This is exactly the positional shape already identified by the separate
external-engine workstream as C-forward topology:

    prize < factual opponent < capture target

The old nonreachable side proxy predicted:

    neutral captured orders + fresh symbolic FC -> LEFT

and failed. A preserved numeric FC control predicts RIGHT on this row, but that
is not a general rule: preserved-FC controls fail on many earlier C rows.

## Why fresh FC was a proxy rather than a mechanism

Before this prospective population, every open first-occurrence O-not-reachable
adjacent row had:

    capture side RIGHT
    factual side LEFT

Counts before public100 prospective opening:

    discovery      21
    heldout        17
    independent     6
                   --
    total          44

Thus the prior neutral+fresh-FC control was never tested in the opposite capture
orientation. It happened to predict LEFT on all 44 rows and therefore appeared
perfect.

The public100 prospective corpus adds:

    13 more RIGHT -> LEFT C rows
     1 first LEFT -> RIGHT C row

Across all currently open C rows:

    RIGHT -> LEFT       57
    LEFT  -> RIGHT       1
                       --
    total               58

The minimal structural rule is therefore:

    if existing O-order pair is not reachable:
        enter capture-created C-order on opposite(capture side)

This fits all 58 / 58 open C rows.

## Combined open population

Adjacent capture rows now open:

    discovery                     31
    heldout                       29
    independent short32           22
    prospective public100 fresh32 20
                                 ---
    total                        102

A bounded post-prospective candidate fits all 102 / 102:

1. second occurrence of the same pair:
   use ordinary repeated-pair side reversal;
2. first-occurrence O-reachable pair:
   - prize on RIGHT stays RIGHT;
   - prize on LEFT with nonnumeric opponent priority stays LEFT;
   - prize on LEFT + numeric group 0 + Kill stays LEFT;
   - prize on LEFT + numeric group 0 + non-Kill goes RIGHT;
3. first-occurrence O-not-reachable:
   - C-order prize side = opposite capture side.

Open-population branch counts:

    discovery:
        O reachable sticky                10
        C-order side flip                 21

    heldout:
        O reachable sticky                10
        C-order side flip                 17
        second-occurrence reversal         1
        numeric non-Kill LEFT              1

    independent short32:
        O reachable sticky                13
        C-order side flip                  6
        second-occurrence reversal         1
        numeric Kill LEFT                  1
        numeric non-Kill LEFT              1

    prospective fresh32:
        O reachable sticky                 3
        C-order side flip                 14
        second-occurrence reversal         1
        numeric Kill LEFT                  1
        numeric non-Kill LEFT              1

Implementation:

    tools/diagnostics/combat_public_capture_side_postprospective_candidate.py

Status:

    POST_PROSPECTIVE_CANDIDATE_NOT_CANONICAL

The public100 prospective population directly informed the C-order flip rule.
The 102/102 fit is therefore fitting evidence, not independent validation.

## Interpretation with external-engine workstream

This result materially strengthens the O/C state-machine interpretation.

The separately audited external-engine branch had already converged on:

    O = continue the pre-capture existing order/cursor
    C = capture-created new order after O is exhausted/not reachable

The new Nu side evidence now lines up with that topology:

    O continuation:
        preserve/derive side under the existing-order rules

    C new order:
        captured prize changes to the opposite side from the capture VCR

The prospective counterexample is especially informative because its
identity-anchored positional order is [prize, factual opponent, captor], exactly
the C-forward region identified before this side result was observed.

This does not prove implementation identity with any external engine. It is a
NuHost structural hypothesis supported by two previously separate evidence
streams.

## Next validation

Do not download another broad random 32-game corpus merely to chase this rare
branch. The only newly changed discriminator is now:

    capture side LEFT
    first occurrence
    existing O pair not reachable / C-forward continuation
    factual next prize side should be RIGHT

A controlled prospective case in private game 686764 is higher value than
another large random corpus because orders can be deliberately arranged to
force the required topology.

Required next work:

1. implement private/live read-only ingestion or direct exact snapshot adapter
   without mixing it into immutable public100;
2. predeclare a controlled capture-left C-forward scenario in 686764;
3. freeze the post-prospective candidate before observing the result;
4. use the private case only as prospective validation;
5. if exact, consider canonical promotion of the bounded capture-side state
   machine together with the independently audited O/C queue topology.

Public100 remains a valid exact-parity Corpus DB regardless of this mechanics
candidate failure.
