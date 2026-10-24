# PR #315 — verified v5 archive-source capability review without a new server scan

Date: 2026-10-24 UTC (local early 2026-10-25). Historical PRE-PR main `0c527a79cc53d874cb0d867241d08840ec78a4c2`, PR #314 merged, exact PR CI #1739 and postmerge push-main CI #1740 SUCCESS. Re-fetch actual live GitHub after PR merge.

## Independent on-host provenance actually read

Existing separate orphan GitHub branch `runtime-logs`:
`runtime-logs/public100-baseline68-identity-v5/20261024T215211Z_0c527a79cc53`.
Read directly via GitHub `metadata.json`, `gate.log`, status, cohort attestation, pytest JUnit count-only summary, anonymized failing-module counts, and full sanitized `m2-deep-coverage.json`.

- Source main commit `0c527a79cc53d874cb0d867241d08840ec78a4c2`; started 2026-10-24 **21:52:11Z**, finished **22:24:33Z** → **32 min 22 sec**, exit0, outer `PASS_NONCAUSAL_READONLY`.
- Lab Git and Bash preflight PASS, exact SHA-pinned current public68 baseline game ID cohort **68 of public100 100** passed. Full public100 DuckDB SHA256 `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`, immutable read-only, CURRENT untouched, no sealed32 entity reconstruction. `224014` members metadata. The actual local manifest SHA from published attestation is `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9`. Do NOT use earlier historically incorrect SHA (without final `9`).
- Population is EXACT prior #312 frozen observational T−1/T 8550 pairs across 68 baseline games, sha `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659`. Source payload IDs 8550/8550 valid, strict M2 aggregate validator PASS.
- Full server pytest `3707` reported cases, failures=0, errors=0, skipped=26, hence **3681 executed/pass** if total includes skipped (vs CI typically reports `3707 passed` plus skips separately). Previously 5 failing Docker Git-dependent tests are now absent; this host run confirms the #313 Git dependency fix in real local environment.
- Across 8550 archived perspective pairs: each of the five sections has **8550 identity-qualified unique-ID list pairs**, zero malformed section rejections. These counts span repeated observers/turns; they are neither 8550 independent games nor unique entities.

| Source section | Same ID observed in both archives | Strict current-own `ownerid+infoturn` both | Owner unavailable | Other bounded observations |
|---|---:|---:|---:|---|
| minefields | 887224 | 138864 | 0 | 536849 same-ID `units` changes, **536703** with owner and x/y center stable |
| ships | 916904 | 347831 | 609 | 6891 observed owner changes; NOT Host capture |
| starbases | 346222 | 0 | 346222 | Generic `ownerid` gate cannot work on source schema; no assumption base has no owner |
| vcrs | 0 | 0 | 0 | 22414 rows in after archives; no cross-turn ID overlap, so ID continuity invalid in this cohort |
| ionstorms | 95130 | 0 | 95130 | Owner check not relevant for storms; ID persistence only |

**Crucial mathematical pitfall (new #315):** 138864 own-current minefield occurrences and 536703 unchanged owner/center + changed units occurrences are separate marginals over N=887224 same-ID minefield archive occurrences. We have **NO published joint cross-tab**. Their actual intersection can be anywhere in tight set bounds `max(0, 138864+536703-887224) = 0` up to `min(138864,536703)=138864`. Do not multiply percentages or claim 138864 fresh mine sweep/decay observations. Even an observed intersection would still be archival movement/source changes, not isolated Host phase.

## Implementation and machine-auditable evidence artifacts

New `src/planets_lab/corpus/nonplanet_v5_evidence_review.py`:
- Examines ONLY allowlisted already sanitized v5 aggregate JSON, NOT game DuckDB, raw members, owner orders, server, network. Requires exact provenance: v5 schema/status, public100 canonical name/full SHA/read_only/CURRENT not changed, exact local baseline68 manifest SHA and allowed=68, heldout false, all100 metadata 224014 and 32 excluded, exact frozen selection SHA + 8550 pairs, all payload identity valid and Host causal evidence flags FALSE. Rejects mismatched/malformed inputs before output.
- Atomic per-section conservation and integer/non-bool/allowlisted counter validation. Enforces ID intersection + only before = before rows, ID intersection + only after = after rows, owner typed unchanged+changed+unknown = same ID, own-fresh+stale ≤ typed unchanged, mine units changed ≤ valid numeric ≤ shared, stable-owner/center+changed subset ≤ changed. Rejects untrusted extra raw/ID keys, missing sections and contradictory counts.
- Emits **fixed, noncausal, per-section evidence states**:
  * minefields, ships: `OBSERVED_ID_AND_FRESH_OWN_SOURCE_ONLY`;
  * starbases: `ABSTAIN_OWNER_PROVENANCE_UNTYPED`;
  * vcrs: `ABSTAIN_NO_CROSS_TURN_ID_CONTINUITY`;
  * ionstorms: `ID_ONLY_STORM_NO_OWNER_CAUSALITY`.
  Every `independent_host_mechanism_verified=false`, also global Host orders/phase/diff false. Shows exact *bounds*, not imagined joint evidence, for fresh minefield × stable-owner/center changed units: **[0,138864]**.
- `tools/diagnostics/review_nonplanet_v5_evidence.py`: optional offline deterministic one-line CLI reading count-only source summary; prints only status and known fixed counters, writes exclusive new scorecard, no corpus or internet. Bad source outputs fixed `ABSTAIN` without exception paths.
- `tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json`: exact privacy-allowlisted projection of actually fetched GitHub sanitized v5 aggregate (no IDs, game/player/member entries, raw orders or host paths). `validation/research/public100-baseline68-nonplanet-v5-source-readiness.v1.json`: matching fixed JSON scorecard calculated from *same source*, with evidence tier `CORPUS_OBSERVED_DESCRIPTIVE_SOURCE_ONLY` and cryptographic observed-population provenance. `tests/test_nonplanet_v5_evidence_review.py`: ensures generated scorecard equals committed file, adversarial wrong SHA, wrong manifest, heldout access, changed frozen selection, forged Host causal evidence, counter conservation violations, boolean/negative values, secret ID injections, CLI reproducibility and output no overwrite.
- No NEW on-host experiment/Host worker needed: analysis only of **existing, already automatically published sanitized JSON**. No additional `run-*-with-evidence.sh` because no new corpus/Host experiment. All new CI is deterministic synthetic/replay of count-only safe aggregate, not new NuHost DIFF_VERIFIED.

## Next work

Use new source category matrix to decide data collection:
1. For minefields, only a fresh **per-row JOINT** count of `observer-owned current (ownerid+infoturn)` AND `same-owner+center` AND strict `units` changed could disambiguate actual *source-qualified candidates*; even then decay/sweep not causally established. Do NOT rerun 32-minute sample without new distinct falsifiable source hypothesis and dedicated evidence wrapper.
2. For starbases, inspect canonical source keys/property semantics and verify provenance via planet linkage only if independently sourced; never assume `ownerid` in starbase schema. For VCR, find correct stable alternative correlation (turn, battle participants, actual combat ID if independently source documented); generic `id` is not cross-turn key in these 8550 observations. Ion storms should not use ownership as required criterion.
3. Actual isolated mine sweep, combat or Host phase requires independent accepted orders and authenticated phase receipts (#247 OPEN but PARKED). T−1/T, new-to-observer IDs, `units` stock shifts and owner changes cannot prove any specific Host mechanism. Closed PPQ #289 FROZEN; C5/Horwasp paused, current public68 immutable, public100 whole100 metadata only and baseline68 entities only; sealed32 never opened; production IntelBoard untouched.
4. Every future PR requires own fully rewritten `docs/CONTINUE_HERE.md`, numbered changelog and substantive docs/roadmap, exact green final PR HEAD CI before squash merge, actual completed postmerge main CI; chat always Russian.
