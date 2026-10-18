# M2 conditional observed-transition reconciliation

Date: 2026-10-18.

## Verified V2 baseline evidence and scope

The published `runtime-logs/m2-public100-surface-context-v1/20261018T173827Z_f7bbb283e93c` has metadata exit_code=0, source f7bbb283e93c1d11ade3cf91c008a690421cf99a, immutable corpus hash 3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c, frozen selection b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f, published report.json and triage.json. The V2 outcome counts are 11,813 both exact, 915 surface-only residual, 33 ground-only residual, and 262 neither exact. Among the 915, 101 single-ship and 43 multiship cargo matches overlap; 802 have a weak ownerless planet-linked base in both snapshots; 52 report base-tech changes on mineral-comparison rows. These are observational, not independent Host-order proof. PR #236 already adds disjoint and planet-window-deduplicated measurement for the next V3 runtime.

## New functionality

`sim/planetary_conditional_reconciliation.py` adds a full-state comparison around existing `PlanetaryOrderAwareSlice`, `PlanetCargoTransferPhase`, `PlanetaryHostPipeline`, `TurnOrders` and `HostEngine` without modifying the production combat executor or default planetary formulas.

It requires explicit complete pre/post states, adjacent identity, unchanged roster, bounded ship noncargo state, and declared complete orders. It runs both hypothetical transfer placements, validates that the per-phase resource ledger telescopes to the modeled inventory, and records signed observed-minus-model residuals separately by planet, ship and ground. It distinguishes complete match, resource-only match, incomplete/mismatching transition and unsupported/ABSTAIN. A separate entry point requires authenticated *operator-owned* pre-Host order bundles via the existing strict owner-capture admission, with every player represented and a separately supplied Host-start boundary.

A model match does not establish the authenticity of the observed snapshot, order submission acceptance, or NuHost phase ordering. Model compatibility is explicitly **conditional**, never DIFF_VERIFIED. No orders may be inferred from residuals or replaced by absent orders. Full, closed-world observation is a caller obligation, never inferred from public loadall.

Synthetic tests cover conservation and phase comparison, signed mismatches, source absence, malformed/unmatched turn and ship data, and owner-scoped completeness. Future validation requires independent sealed pre/post observations and independently time-witnessed order submissions; historical public archives alone do not meet the admission criteria.

## Pending external verification

CI and merge status are recorded by the GitHub PR. The already published V2 historical evidence does not need to be rerun for this code-only phase. The separate V3 instrumentation from PR #236 requires its own one-pass runtime after main sync; no V3 numerical claims are made here. Holdout32 entity sampling remains sealed.
