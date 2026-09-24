# Combat capture reintegration — FeatureScope runtime pending

Date: 2026-09-22

Repository: `Numillyash/planets-lab`

The non-capture predictive queue is already archive-runtime closed:

```text
strict      22/22 exact
conditional 22/22 exact
mismatch=0
```

The exact-set residual is capture.

## Reintegrated capture evidence path

The current branch restores the previously production-wired capture
differentials on top of current `main`:

- factual ship appearances expose replay owner id for attribution;
- explicit `ShipCaptureTransfer` mutation is exercised by the capture
  continuation audit;
- capture state is compared with the next same-turn same-location factual VCR;
- post-capture opponent-side initiators are reconstructed independently;
- all clean population selection now uses shared `FeatureScope`.

No clean selector hardcodes a special game id.

## Historical continuity target

The immutable 11-game ordinary corpus previously established:

```text
capture continuations=23

production owner exact=23/23
production race exact=23/23
production hull exact=23/23
production shield exact=23/23
production crew exact=23/23
production torpedoes exact=23/23
production fighters exact=23/23

damage exact=22/23
known replay residual only:
621253/T17 ship84 VCR39->45 11->7

next opponent:
  ship=8
  planet=15

independent opponent-side initiator=23/23
required unresolved=0
```

Old mission/Primary Enemy persistence on the captured ship is not required and
must not be invented.

## One-command gate

Run from a clean current `main` checkout on the archive host:

```bash
bash tools/run-combat-capture-reintegration-gate.sh
```

The runner first revalidates the already-closed predictive queue checkpoint,
then runs capture state and initiator differentials, and finally checks exact
population continuity.

Required final acceptance:

```text
predictive_queue_checkpoint_exact=true
capture_transition_gate_passed=true
post_capture_initiator_gate_passed=true
capture_population_preserved=true
ship_continuation_population_preserved=true
planet_continuation_population_preserved=true
all_continuations_have_independent_opponent_attack=true
capture_required_unresolved_zero=true
exact=true
failures=[]
```

After this passes, the next new mechanics gate is post-capture candidate-graph
reconstruction for the eight ship continuations: owner/race mutation must create
new foreign pairs and remove new same-owner pairs before canonical next-pair
selection. Factual next VCR remains comparator-only.


## New discovery stage in the same run

The runner also emits:

```text
artifacts/combat-capture-reintegration-v1/post-capture-ship-candidates.json
```

For each of the historical ship continuations after capture, it independently
reconstructs the battle-site ship population from owner-current T-1 movement
state, applies the prize ship's new owner for opponent-side request evaluation,
and records:

- whether the factual next opponent was independently predicted at the site;
- whether its T-1 orders request combat against the new owner;
- strict relation permission with the factual pair removed from its own control
  evidence;
- its static Combat Priority rank among independently aggressive foreign ships.

This stage is descriptive and deliberately does not fail the reintegration gate.
It does not yet apply active-membership history from earlier VCRs at the site,
so its output is the evidence input for the next candidate-graph implementation,
not a promoted rule.


## Narrow candidate-discovery rerun

After the full capture reintegration gate has passed once, candidate-graph
diagnostic changes do not need to rebuild/revalidate the entire FeatureScope and
predictive queue checkpoint. The archive host can run:

```bash
bash tools/run-combat-post-capture-candidate-with-evidence.sh
```

This reuses the existing compiled feature index, runs the targeted diagnostic
tests and candidate inventory, and publishes only the new candidate evidence to
the orphan `runtime-logs` branch.
