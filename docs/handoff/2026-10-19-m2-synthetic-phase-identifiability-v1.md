# M2 synthetic phase-identifiability preflight — 2026-10-19

## Why this follows PR #241

PR #241 (merged `84489f213d866fd12372098b426d3304d3e47d28`,
main CI #1356 success) enumerates the six mathematical permutations
of cargo transfer, the fixed fourteen-phase planetary economy block,
and standard-price starbase technology purchase. Enumeration alone
does not mean six outcomes are **distinguishable** at a real Host
boundary. Some sequences commute and produce identical complete T
states. A synthetic internal event trace is not a Host observation.

V3 archival public68 remains a descriptive baseline:
915 surface-stock residual mineral comparisons occupy 315 planet
transition windows, 108 distinct opposite ship-cargo mineral
candidates and 65 cargo-associated planet windows; only one
observed transition combines a weak-linked base-tech change with
a cargo candidate. They are not Host-order proofs.

## Model-side preflight (no user work required)

`planetary_phase_identifiability.evaluate_six_phase_signatures`
compares all six outcomes against one supplied complete synthetic
prestate and *explicit technology/transfer orders*. It uses the
existing fingerprint of each *complete modeled state* internally,
never returning it, and groups placements with indistinguishable
end states. Any model ABSTAIN is assigned a **single unobservable
bucket**, not a fake server-rejection outcome.

The bounded `search_synthetic_phase_discrimination` enumerates 96
fixed, artificial economic configurations: synthetic planet MC,
ship MC, local cargo transfer, factory controls and technology
7→10 under an asserted level-10 cap. It selects the best candidate
with all six model paths supported separately from the best candidate
where some model paths abstain. A partially supported scenario is
**not** evidence that NuHost rejects those orders. Cases with no
explicit tech order or no asserted eligibility cap ABSTAIN rather
than produce false ranking or inferred phase order.

Run an entirely local, source-pinned aggregate-only diagnostic:

```bash
cd /root/projects/planets-lab
git pull --ff-only origin main
bash tools/run-m2-phase-identifiability-v1-with-evidence.sh
```

The existing evidence wrapper publishes a dated log and metadata
to `runtime-logs/m2-phase-identifiability-synthetic-v1/`. No raw
state, private player name/ID, signed order record, HMAC key,
network URL, hash fingerprint, HAR capture, or historical corpus
entity is loaded or emitted. The tool uses the fixed *fake*
`planetary_order_aware_scenarios_v1.fixture()`.

## Interpretation and next boundary

The tool demonstrates **identifiability limitations of our incomplete
research model**, not Host ordering, rule causality, submission
acceptance or external time provenance. Even a uniquely modeled final
state does not grant `DIFF_VERIFIED` without independently accepted
pre-Host orders, complete T−1 and T owner state, externally witnessed
execution time and no unmodeled interference.

No corpus rescan, CURRENT modification, heldout32 entity sampling,
canonical C5/combat changes, or IntelBoard production changes.
