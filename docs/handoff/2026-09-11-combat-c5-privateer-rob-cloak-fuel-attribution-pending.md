# C5 Host combat — Privateer Rob cloak/fuel attribution gate — COMPLETE

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

This gate has been completed successfully on source:

```text
16f9253b92f7e48f7f2179f9c3b704469de4128a
```

Runtime result:

```text
tests rc=0
audit rc=0
```

Full durable result:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-runtime.md
```

Headline findings:

```text
stable prior-true rows=1413
clean stationary/no-visible-fuel-mutation rows=12
clean exact-reference-debit=2
clean zero-debit=7
clean other-debit=3

threshold rows fuel <= reference cost=14
ordinary-cloak threshold rows=13
ordinary threshold true_to_false=13/13
advanced-cloak threshold true_to_true=1/1
```

The clean subset therefore rejects the simple universal interpretation `Rob Ship consumes ordinary cloak reference fuel`: the broad exact-debit correlation collapses from the earlier 72.2% quiet-bucket share to only 2/12 in the stricter visible-input subset.

The low-fuel controls instead expose a strong threshold correlation: every ordinary-cloak hull row with archived prior `iscloaked=true` and `fuel_before <= reference_cost` transitions `true_to_false` in this population. The sole below-threshold `true_to_true` row is an advanced-cloak hull and has confounded fuel acquisition / foreign-origin context.

This threshold is `CORPUS_OBSERVED + TESTED`, but is **not yet a canonical combat blocker predicate**. All 13 ordinary threshold controls have nonzero requested Warp, so phase/order attribution is still required.

The next gate is an explicit fail-closed effective-cloak candidate differential:

1. partition ordinary-cloak vs advanced-cloak Privateer mission9 prior-true rows;
2. model fuel margin around `fuel_before - reference_cost`;
3. control requested Warp / transfer / ion / Loki / Glory context;
4. apply the candidate helper only in diagnostics;
5. rerun initial-target opportunities and test whether the three skipped Meteors are blocked while `620694/T64/ship118` remains eligible;
6. keep Bird `511506/T94/ship202` separate.

No canonical `selection.py`, `queue.py`, STANDARD priority or FC parser changes are justified yet.
