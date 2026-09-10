# C5 Host combat — initial plain-STANDARD target selection

This pending gate is **superseded by completed runtime**.

Read instead:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md
docs/handoff/2026-09-10-combat-c5-initial-standard-target-residual-pending.md
```

Runtime source `d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3` passed tests and audit. Exact-set scope is clean:

```text
conditional: 169/169 first pair exact
strict:      162/162 first pair exact
informative exact-set target ordering: 15/15 target rank 1
```

Two broad residuals remain only because the reconstructed eligible set contains one extra nonfactual target at each site:

```text
360690/T83: extra target 98 for active ship 264; factual target 190
511506/T94: extra target 202 for active ship 496; factual target 332
```

Do not rerun this gate alone and do not invert target ordering. The active gate is the focused post-movement-fuel / missing-blocker audit described in the residual pending handoff.