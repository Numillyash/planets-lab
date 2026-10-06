# SiteCombatState v1 — ready for carried-state differential

Date: 2026-10-06

## Closed prerequisite

Runtime evidence:

    runtime-logs/mutable-capture-site-loop-v1/
    20261006T182353Z_af60578ecaed

Result:

    SITE_LOOP_EXACT

Transitions:

    V592 -> V593  capture_immediate_C   exact pair + sides
    V593 -> V594  capture_parent_resume exact pair + sides
    V594 -> V595  capture_immediate_C   exact pair + sides

This closes the history-reconstructed orchestration loop for the target chain.

## New carried state

Module:

    src/planets_lab/rules/combat/site_state.py

State:

    SiteCombatState
      active_ships
      StandardQueueState
      parent_queue_excluded_ship_ids
      temporary_capture_order

The model deliberately separates:

1. physical activity;
2. parent STANDARD queue membership;
3. temporary post-capture continuation order.

A captured prize remains physically active while being excluded from the parent
queue for the site. Opening or exhausting its temporary capture order does not
change physical activity. Exhausting the temporary order also does not
reinsert the prize into the parent queue.

This is still evidence-scoped research state, not a claim that every NuHost
capture configuration follows this rule.

## Atomic state transitions

The module delegates physical terminal mutation to the already tested:

    apply_ship_terminal_batch

and wraps it as:

    apply_site_terminal_batch

On a resolved capture:

- physical captured state is carried;
- ownership/race transfer is applied;
- captured prize is added to parent_queue_excluded_ship_ids.

Destroyed ships are removed from both physical activity and any stale parent
exclusion.

Pair history is carried with:

    record_factual_site_pair

Temporary order lifecycle is explicit:

    open_temporary_capture_order
    clear_temporary_capture_order

Parent queue membership is projected by:

    parent_queue_active_ship_ids

## Differential v1

Diagnostic:

    tools/diagnostics/combat_site_state_differential_v1.py

Runner:

    tools/run-site-combat-state-v1.sh

Evidence wrapper:

    tools/run-site-combat-state-v1-with-evidence.sh

Target:

    game 400330
    turn 141
    site (1674, 2363)
    V592 .. V595

Unlike mutable-site-loop v1, site history is reconstructed only once before
V592.

From V592 onward:

- factual pair N is recorded into SiteCombatState;
- factual terminal result N is applied atomically;
- capture opens/replaces TemporaryCaptureOrder;
- immediate O/C selection uses current carried active ownership and carried pair
  occurrence history;
- exhausted capture order is explicitly cleared;
- parent resume uses parent_queue_active_ship_ids(state) and
  state.standard_queue_state;
- factual N+1 is opened only after prediction.

Terminal combat outcomes are still injected from factual VCRs. This checkpoint
validates carried orchestration state, not yet combat-outcome generation.

## Acceptance

Pass:

    SITE_STATE_EXACT

Expected:

    exact_transitions = 3

Mode sequence:

    capture_immediate_C
    capture_parent_resume
    capture_immediate_C

If this passes, the next refactor is to move more selection orchestration from
diagnostics into an evidence-scoped production module operating directly on
SiteCombatState, while leaving terminal outcome injection as the remaining
factual dependency.
