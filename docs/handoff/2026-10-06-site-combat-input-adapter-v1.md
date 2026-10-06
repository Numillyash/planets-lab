# Site combat input adapter v1 — implementation handoff

Date: 2026-10-06

## Scope

Mainline branch:

    research/site-combat-input-adapter-v1

Base main verified before work:

    d19606c902448e606cda5d7452738342fdcc08fd

This change extracts evidence-safe executor input assembly from:

    tools/diagnostics/combat_site_state_differential_v1.py

into reusable mainline code:

    src/planets_lab/rules/combat/site_input_adapter.py

## Extracted responsibilities

The adapter now owns:

- same-turn diplomacy cutoff through the current VCR;
- current physical owner + T-1 order-state assembly;
- post-capture candidate-state recomposition;
- parent STANDARD pair-input construction from carried parent membership.

The site-state differential is reduced toward:

    corpus reader
      -> site_input_adapter
      -> SiteCombatState / site_executor
      -> comparator

## Dependency boundary

The new src module does not import tools/diagnostics.

Eligibility-specific evidence primitives are injected as callbacks by the
diagnostic harness.  This is deliberate: the currently validated implementations
for relation signatures, independent diplomacy permission, interference state
and FC-bounded pair disposition are still research evidence code and have not
all been promoted as canonical rules.

## Preserved evidence boundaries

- No VCR N+1 pair, side or terminal state is consumed by adapter prediction.
- Same-turn diplomacy evidence is truncated at <= current VCR.
- Current-owner / T-1 owner mismatch fails closed.
- Parent inputs come from parent_queue_active_ship_ids(state), so a physically
  active captured prize remains excluded from the parent queue.
- O remains fail-closed in site_executor with
  o_branch_not_independently_covered.
- Immediate-C LEFT/RIGHT projection remains in the research harness and is not
  promoted into canonical executor/adapter logic.
- Terminal combat outcome remains the major factual injection after this
  extraction.

## Tests

Added:

    tests/test_combat_site_input_adapter.py

Coverage includes:

- temporal diplomacy cutoff;
- current-owner/T-1 candidate assembly;
- owner-change fail-closed behavior;
- parent membership exclusion;
- parent current-owner/T-1 mismatch fail-closed behavior.

The existing site-state differential test also asserts that input assembly is
delegated to site_input_adapter and that the old inline candidate/parent helper
paths are absent.

## Validation status

GitHub PR/CI and the public100 runtime regression are to be recorded after this
implementation commit is exercised.


## Runtime regression gate

Added dedicated server-side entrypoints:

    tools/run-site-combat-input-adapter-v1.sh
    tools/run-site-combat-input-adapter-v1-with-evidence.sh

The adapter gate deliberately reuses the canonical carried-state differential
instead of creating another one-off VCR diagnostic. It defaults to local runtime
selection so a broken Docker/containerd daemon does not mask mechanics:

    PLANETS_SITE_INPUT_ADAPTER_RUNTIME_MODE=local

The underlying site-state runner still enforces Python >=3.11 and prepares its
cached host venv when required.

After the differential completes, the adapter gate additionally requires:

    SITE_STATE_EXACT
    expected_transitions 3
    evaluated_transitions 3
    exact_transitions 3

and the mode sequence:

    capture_immediate_C
    capture_parent_resume
    capture_immediate_C

It also verifies that the generated report evidence boundary names
site_input_adapter, proving the extracted path was the path under regression.

The with-evidence wrapper publishes under:

    runtime-logs/site-combat-input-adapter-v1/
