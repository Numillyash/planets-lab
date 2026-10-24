# PR #316 — exact minefield observational joint source counts (v6)

## Context

Parent live main before this PR: `500192c1f950f0012ee61820c4f3b378bc14188d`; #315 merged and verified final PR CI #1752, main push CI #1753 completed SUCCESS. Source of truth remains live main, not this historical SHA.

## Verified state

Existing actual 2026-10-24 v5 server run: 8550 frozen observer T−1/T pairs across exactly baseline68 games selected from explicit public100 metadata-only population; public100 SHA `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`; frozen selection digest `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659`; trusted server-local baseline manifest `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9`. v5 cross-archive minefield matching ID 887224, own-current 138864, same-owner/centre changed numeric units 536703, previously unknown actual joint 0..138864.

PR #316 introduces a per-row conjunction in `profile_source_identity_pairs` of **both exact observer-owned `ownerid` and matching `infoturn` on T−1 and T**, strict numeric (non-bool, nonnegative) units on both, exact integer `x/y` unchanged and matching owner. It counts the joint denominator, increased, decreased, unchanged, and changed, with algebraic conservation and synthetic tests. Existing v5 independent marginals and source classifier remain unchanged. These are still repeated observation pairs, not unique mines/turns or causal Host phases.

New dedicated `bash tools/run-public100-baseline68-mine-joint-v6-with-evidence.sh` reuses exact `tools/run-with-runtime-evidence.sh`, runs full Docker tests, SHA and exact cohort verification, frozen 8550 sample, baseline68-only read-only reconstruction, generic sanitized report validator and v6 stricter joint validator. It publishes only count-only aggregate/status/JUnit sanitized summary and complete outer log to orphan `runtime-logs`, even on ABSTAIN. No raw .trn, orders, entity IDs, HAR, private logs or heldout32 sampling. This change is `TESTED` only after actual PR CI, **not yet an empirical v6 run**. No v6 joint count is known until a real authorized server run is published.

## Next actions

1. Check exact final #316 head CI SUCCESS; squash merge with expected head SHA, then verify merged main HEAD and completed successful main push CI; never assume green.
2. On existing corpus server, only after merge and pull to main: `bash tools/run-public100-baseline68-mine-joint-v6-with-evidence.sh`. This is a **new experimental corpus reconstruction**, requires actual operator host execution. Read safe JSON from `runtime-logs` via GitHub; do not request raw logs.
3. Compare actual joint count with 0..138864 bound; report increased/decreased/unchanged separately. Even a nonzero count is only `CORPUS_OBSERVED`, not `DIFF_VERIFIED` accepted mine decay/sweep. Issue #247 parked for independently accepted orders and phase receipts.
4. Every future PR rewrites full standalone CONTINUE_HERE using its OWN PR number and updates numbered changelog + substantive documents, final PR and main CI.

## Boundaries

Read-only explicit public100 generation, `CURRENT=public68`, immutable databases, sealed heldout32 records never sampled, frozen #289 PPQ, unrelated C5/Horwasp and IntelBoard production untouched. All 8550 archive pairs are observer-relative and nonindependent. No Host phase/diff claims. `DOCUMENTED`, `TESTED`, `CORPUS_OBSERVED`, `DIFF_VERIFIED` always separate.
