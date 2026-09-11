# Finite-fuel Tow same-line stop-context gate: incomplete runtime

## Scope

This note records one failed server run of the bounded same-line stop-context gate. It is a tooling-contract failure only and is **not** evidence about Tow, mine/web, damage, hull specials, or fuel semantics.

Source reconciliation gate:

```text
logs/finite-fuel-tow-same-line-reconcile-20260911T083834Z-661f9d97-15295
```

Failed stop-context gate:

```text
logs/finite-fuel-tow-same-line-stop-context-20260911T085822Z-5049a7cb-20987
candidate=5049a7cbddbb72aa0c266dc78894211ad4c72f48
```

The `inputs` and `tooling` stages completed. `same-line-stop-context` failed before archive/corpus classification with:

```text
ValueError: same-line reconciliation log has no CASES block
```

## Root cause

`tools/diagnostics/tow_finite_fuel_same_line_reconciliation_audit.py` emits the three case dictionaries inline before `===== SUMMARY =====`.

The first implementation of `tools/diagnostics/tow_finite_fuel_same_line_stop_context_audit.py` assumed those dictionaries were under a `===== CASES =====` marker. The counters were compatible (`3 same-line`, `3 neither_model`), but the producer/consumer log contract was not.

Therefore the failed run contains no completed stop-context result and must not be used as evidence.

## Correction

The runner now preserves the immutable source log and creates a gate-local normalized copy. If the source already contains `===== CASES =====`, it is passed through unchanged. Otherwise the runner recovers exactly three inline dictionaries before `===== SUMMARY =====` and fails closed unless all of these invariants hold:

```text
cases = 3
game = 360690
turns = {41, 44, 185}
envelope_class = neither_model for all rows
```

Only the normalized gate-local copy is supplied to the stop-context diagnostic. The original completed reconciliation log remains the provenance source.

## Evidence status

No Tow mechanic is promoted or rejected by this failed run.

```text
finite-fuel Tow = OPEN
planets-intel = unchanged
```
