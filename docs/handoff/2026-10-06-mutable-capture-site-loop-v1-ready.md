# Mutable capture site loop v1 — ready

Date: 2026-10-06

## Purpose

The one-step capture and parent-resume gates have now established the following
bounded sequence on game 400330 / turn 141 / site (1674, 2363):

    V592 capture140 by184
      -> immediate C continuation
      -> V593 pair140/170

    V593 capture140 by170
      -> immediate O/C exhausted
      -> parent queue resume
      -> V594 pair170/184, LEFT184 RIGHT170

    V594 capture170 by184
      -> immediate C continuation
      -> V595 pair170/382

The next step is to compose those transitions in one site-level loop rather
than maintain separate one-off runtime gates.

## Implementation

Diagnostic:

    tools/diagnostics/combat_capture_mutable_site_loop_v1.py

Runner:

    tools/run-mutable-capture-site-loop-v1.sh

Evidence wrapper:

    tools/run-mutable-capture-site-loop-v1-with-evidence.sh

Default window:

    game 400330
    turn 141
    site (1674, 2363)
    V592 .. V595

## Evidence discipline

This is a history-anchored compositional loop, not yet a fully generative Host
executor.

For each transition VCR N -> N+1:

1. factual VCR N may supply terminal/mutation state;
2. immediate capture continuation is reconstructed with diplomacy controls
   truncated through N;
3. if immediate continuation resolves on the independently covered C branch,
   the predicted opponent comes from the O/C selector and the prize side uses
   the post-prospective C-order side-flip candidate;
4. if immediate continuation exhausts with no unresolved dependency, the
   parent-resume gate invokes production select_next_plain_standard;
5. only after a prediction exists is factual VCR N+1 opened as comparator.

Immediate O-branch selection fails closed in v1 because the prospective fresh32
population did not contain an independently qualified O case.

The C-order side flip remains a research candidate rather than independently
promoted canonical mechanics. Therefore a successful site-loop result is
compositional evidence, not a promotion of every contained sub-rule.

## Temporal diplomacy boundary

The immediate continuation gate is strengthened in this checkpoint.

Within the target battle turn, diplomacy calibration now permits only factual
VCR rows with id <= the current capture VCR. Future same-turn rows are removed.

The parent-resume gate already applies the same temporal cutoff.

This ensures that no future engagement in the loop can establish directed
permission for an earlier prediction.

## Acceptance

Expected transitions:

    3

Expected mode sequence:

    capture_immediate_C
    capture_parent_resume
    capture_immediate_C

Pass:

    SITE_LOOP_EXACT

with:

    exact_transitions = 3
    pair_exact = true for all three transitions
    side_exact = true for all three transitions

## Next step after pass

Do not add another one-off gate for this site.

Replace repeated factual-history reconstruction with a carried internal state,
for example:

    SiteCombatState
      active_ships
      standard_queue_state
      capture_cursor / temporary capture order
      parent queue membership
      elapsed pair history

The terminal result of each factual VCR may still be injected initially while
the new state object is validated. After that, terminal outcome generation can
be connected to the already reconstructed combat-resolution layer.

This is the intended transition from diagnostic composition to an actual
mutable NuHost site executor.
