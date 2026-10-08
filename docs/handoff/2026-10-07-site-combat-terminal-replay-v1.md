# Site combat terminal replay v1 — implementation handoff

Date: 2026-10-07

## Scope

This stage replaces the target-window precomputed terminal-appearance injection
with an explicit reusable current-VCR replay adapter.

Base main checkpoint:

    52c9ba4ccbbbabc05c631e53d9173e82ee1658fa

The previously closed input-adapter runtime remains:

    runtime-logs/site-combat-input-adapter-v1/
    20261007T001314Z_4278c0a8caa9

    SITE_STATE_EXACT 3/3
    SITE_INPUT_ADAPTER_EXACT

## Important correction to the previous boundary description

The old site differential called the target-window terminal vector "factual".
Tracing the producer shows that appearance["terminal"] is itself built by
deterministic NuHost Classic replay from the factual current VCR.

Therefore the remaining injection was a precomputed replay result, not an
independent post-combat oracle.

This stage makes that replay explicit in the carried-state pipeline.

## New reusable modules

Compact current-VCR reader:

    src/planets_lab/corpus/combat_vcr_runtime.py

It exposes only replay-relevant current-VCR inputs:

- VCR payload;
- minimal beam catalog fields;
- minimal torpedo catalog fields;
- combat RNG setting.

It does not expose ships/planets or other post-state member fields through the
returned case. Duplicate perspective observations must agree on all retained
replay inputs or the case fails closed.

Terminal replay adapter:

    src/planets_lab/rules/combat/site_terminal_adapter.py

The adapter:

1. checks that carried mutable state exactly matches the factual current-VCR
   start vector for owner/race/hull, shield, damage, crew, torpedoes, fighters
   and effective weapon counts;
2. overlays those mutable values from SiteCombatState onto the current VCR
   combat setup;
3. invokes the existing deterministic NuHost Classic resolver;
4. converts replay output into terminals_by_ship_id;
5. derives capture transfer owner/race/crew-bonus state from the carried captor,
   not from a post-combat appearance.

Fail-closed boundaries remain explicit.

## Site differential modes

tools/diagnostics/combat_site_state_differential_v1.py now supports:

    --terminal-source appearance
    --terminal-source replay

appearance is the backward-compatible historical checkpoint mode.

replay uses site_terminal_adapter for every target-window terminal mutation.

The pre-window history remains history-anchored through the existing appearance
path solely to establish the starting SiteCombatState before V592.

## Held-out N+1 boundary

In replay mode:

- current VCR N is opened before resolving its terminal state;
- N+1 pair/sides are not opened until after the executor predicts N+1;
- N+1 raw VCR start state is also not consulted by the loop until after the
  prediction;
- after prediction, N+1 start state is used only as a comparator against the
  carried active state.

Thus N+1 remains comparator-only.

## Remaining factual/current-VCR injections

This stage does not claim a fully free-running battle generator.

The current VCR still supplies:

- pair/sides already elapsed at N;
- deterministic combat seed;
- static combat setup fields that SiteCombatState does not yet model, including
  equipment/mass and several combat-rate parameters.

Mutable state is no longer taken from precomputed replay terminal appearances.

## Runtime gate

Tracked gate:

    tools/run-site-combat-terminal-replay-v1.sh

Evidence wrapper:

    tools/run-site-combat-terminal-replay-v1-with-evidence.sh

The gate requires:

    SITE_STATE_EXACT
    3/3 pair + side transitions

and additionally:

    current_vcr_start_exact_transitions 3
    next_vcr_start_exact_transitions    3
    terminal_source current_vcr_replay_carried_overlay

Successful marker:

    SITE_TERMINAL_REPLAY_EXACT

Runtime evidence publishes under:

    runtime-logs/site-combat-terminal-replay-v1/

## Evidence boundaries preserved

- O remains fail-closed with o_branch_not_independently_covered.
- Immediate-C LEFT/RIGHT projection remains research-only.
- No N+1 pair/side/start/terminal is used to produce N+1 selection.
- Same-turn diplomacy cutoff remains <= current VCR.
- Unresolved current-VCR replay/setup/state mismatches fail closed.
- Current-VCR static combat setup and seed remain explicit inputs.

## Next step after successful runtime

If public100 V592->V595 is exact in replay mode, the large target-window
precomputed-terminal dependency is removed.

The next generative boundary is no longer "terminal outcome" itself. It becomes
construction of the current combat VCR setup from executor-selected ships:

    carried SiteCombatState
      + selected pair/sides
      + game combat rules
      + RNG/seed policy
      -> combat payload
      -> deterministic replay
      -> terminal mutation

The largest remaining factual pieces are static/effective combat payload fields
and seed/RNG progression.

## Runtime closure — 2026-10-08

Verified public100 server evidence (source branch main, clean worktree):

    runtime-logs/site-combat-terminal-replay-v1/
    20261008T024042Z_421360cf07b7

    source_commit 421360cf07b76a794c85300983af7fcae26a5a93
    exit_code 0

    SITE_STATE_EXACT
    SITE_TERMINAL_REPLAY_EXACT
    expected_transitions 3
    evaluated_transitions 3
    exact_transitions 3
    current_vcr_start_exact_transitions 3
    next_vcr_start_exact_transitions 3

    V592 -> V593 capture_immediate_C   predicted [140,170] exact pair/sides
    V593 -> V594 capture_parent_resume predicted [170,184] exact pair/sides
    V594 -> V595 capture_immediate_C   predicted [170,382] exact pair/sides

All current/next VCR start comparisons exact. This closes the
target-window precomputed terminal-result dependency for the studied chain.

Scope limitation: pre-window queue/state history is still anchored to observed
VCRs, and the **current** VCR N still supplies the known combat encounter's
pair/sides, seed, static/effective combat setup, weapon catalog and RNG mode.
N+1 pair and start state are held out until after predicting N+1. O remains
unpromoted and fail-closed. This is not a general free-running NuHost.

Next evidence work: decompose factual current-VCR combat setup into values
recoverable from T-1 ship data, known catalog/settings, carried state, and
unresolved seed/combat-rate/other host-dependent fields. Do not promote a
static setup rule or seed progression without independent validation.
