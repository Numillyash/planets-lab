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
