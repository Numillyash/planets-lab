# Post-heldout capture-side candidate

Date: 2026-10-03

Status:

    POST_HELDOUT_CANDIDATE_NOT_CANONICAL

The original frozen pre-heldout candidate failed independent validation:

    27 / 29 exact
     1 mismatch
     1 unresolved

The failure is preserved in:

    docs/handoff/2026-10-03-public-capture-side-heldout-result.md

This document records the replacement research candidate only. It must not be
promoted without a new independent validation population.

## Open-corpus result

After opening both the former discovery and held-out partitions, there are 60
globally adjacent ship-capture continuations.

A bounded candidate explains all 60:

    reachable sticky                    20 / 20
    nonreachable neutral/fresh-FC       38 / 38
    second-occurrence reversal           1 / 1
    reachable numeric-opponent override  1 / 1
                                       --------
                                        60 / 60

This is fitting evidence, not validation evidence.

## Candidate

Evaluate the following branches in order.

### 1. Prior same-pair occurrence

If the same prize/opponent pair already fought once in the current combat
phase, apply the already verified ordinary second-occurrence side reversal.

For the only adjacent repeated-pair row:

    game 257776
    turn 230
    VCR 1644: ship71 RIGHT vs ship153 LEFT
    VCR 1646: ship71 LEFT  vs ship153 RIGHT

The intermediate VCR1645 captures ship71 again. No T-1 state for the temporary
owner is required to decide the second occurrence.

### 2. Identity-anchored original-order pair reachable

Ordinary controls retain the captured prize's side.

The single currently observed exception is:

    game 476380
    turn 223
    VCR 903 -> 904
    captured ship157
    capture side LEFT
    factual next side RIGHT
    next opponent ship514
    opponent STANDARD priority [0, 24, 514]

All other captured-LEFT reachable controls in the open corpus have the next
opponent in priority group 3 and remain LEFT.

The narrow candidate is therefore:

    reachable + next opponent priority group 0 -> prize RIGHT
    otherwise reachable -> retain capture side

Priority group 0 is the documented numeric-Friendly-Code STANDARD group.
Official Nu documentation says numeric Friendly Codes 001..999 have the
earliest ordinary ship-combat priority, but it does not document this specific
post-capture side transition. Therefore the group-0 override remains a
corpus-derived hypothesis.

### 3. Original-order pair not reachable

Use the already tested neutral-captured-orders + fresh nonmatching symbolic FC
side control.

## Evidence boundary

The 60/60 result is not a held-out gate. The former held-out rows directly
informed branches 1 and 2.

A replacement rule may be promoted only after independent evidence that was not
used to derive this candidate.

Preferred sources:

1. prospective controlled private-game turns, especially game 686764;
2. newly acquired public games not present in the public36 Corpus DB;
3. deliberately constructed capture/re-capture experiments.

The most valuable prospective discriminators are:

- captured prize LEFT + next opponent numeric FC (001..999);
- matched controls with the same stack but symbolic-FC group 3 opponent;
- same-turn repeated capture followed by the original captor/opponent pair;
- captured RIGHT + numeric-FC opponent controls.

Do not modify the canonical combat rules from this document alone.
