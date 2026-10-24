# PR #313 — 8550 baseline68 T−1/T read-only observations + five Docker-only pytest failures, Git prerequisite

Дата: 2026-10-24. PRE-PR immutable `main`: `3f539501db2af038b751c94b228c4609c5d565f5` (#312 merged, exact PR CI #1725, postmerge main #1726 SUCCESS). This SHA is historical; re-query GitHub after merge.

## Verified on-host runtime #312

**Actual source**: `runtime-logs/public100-baseline68-expanded128-v4/20261024T185839Z_3f539501db2a`, `metadata.json`, `gate.log`, safe `stage-status.json`, `pytest-counts.json`, `pytest-failed-modules.json`, `m2-deep-coverage.json` and `baseline-cohort-attestation.json`. Assistant read them itself directly from GitHub rather than asking user for local logs.

- Started **2026-10-24T18:58:39Z**, finished **2026-10-24T19:26:33Z**, duration **27m54s**; exit code1 because pytest failed; **M2 did not fail**.
- Explicit `public100` SHA256 `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c` verified, metadata **100 games**, **224014** perspective snapshots; 222536 valid member turn identities, 1478 invalid/mismatch; 221091 potentially adjacent same-perspective archive pairs in all 100; 32 sealed games excluded from ANY entity sampling. Independently SHA-pinned `public68` 68-game cohort exact-ID metadata gate PASSED; `CURRENT` not changed.
- Deterministic frozen **8550 T−1/T archive pairs from all 68 approved baseline games** (upper bound 8704 = 68×128, some games have fewer distinct eligible turns). **8550/8550** sampled payload identity valid; owner-current fresh planet matching **317255** matched IDs, 320638 before/322857 after owner-current records. Five `ABSTAIN_OWNER_PLANET_STALE_OR_NO_INFOTURN` recorded.
- Observational archive row count sums across sampled *perspectives*, NOT unique ships/fields nor proven NuHost events: after ship rows **1025238** across 8550 pairs (6126 pairs with different ship row count); minefields after **916892** (4459 row-count difference); starbases after **351652** (2774 difference); VCRs after **22414** (4267 difference); ionstorms after **101318** (2314 difference). All five source sections arrays present on both sides of all 8550 sampled pairs, but archival perspective may be stale.
- M2 owner-current material: **58938** planet windows with any surface mineral residual, **6870** planet windows with any exact opposite cargo candidate, **2282** windows with base tech change, **39387** windows with planet-linked bases. These are *descriptive* stock changes/source candidates, not proof of Host cargo transfer, mineral mutation cause, construction or combat/sweeping phase. M2 status `PASS_VALIDATED_AGGREGATE` and `CORPUS_OBSERVED` descriptive source coverage; actual accepted Host orders, phase chronology and `DIFF_VERIFIED` remain FALSE.
- Complete Docker pytest: `tests=3697`, `failures=5`, `errors=0`, `skipped=26`, **passed=3666** (3697-5-26). New safe module classifier `PASS_SAFE_FAILURE_COUNTS_ONLY`, `unmapped_failures_or_errors=0`: exactly **4 failures** `tests/test_runtime_evidence_wrapper.py`, **1** `tests/test_site_combat_state_runtime_fallback.py`. These are infrastructure/runtime integration regressions, NOT mine formula comparison failure. No raw pytest/JUnit/parametrized test names/traces published.

## Root cause and fix (verification levels explicit)

Comparing actual `Dockerfile` to failing tests revealed **missing OS Git binary in lab Docker image**:
- Dockerfile `FROM python:3.12-slim`, previously only pip-installed Python requirements, did not install `git`. Ubuntu GitHub Actions runner has Git preinstalled; its green pytest had **not** exercised the lab Docker image.
- All four tests in `test_runtime_evidence_wrapper.py` use `git init`, `git commit`, push/worktree/ls-tree/show subprocesses in artificial tmp git repositories. Without `git` in the image, subprocess fails.
- `test_site_combat_state_runtime_fallback.py` host runtime script includes `HEAD: $(git rev-parse HEAD)` and a test asserts absence of `: command not found`, so missing Git also explains one failure. This is a strongly source-supported root-cause **hypothesis until the real-image CI smoke passes**, then validated on CI container; re-run on actual server for definitive closure.

PR #313 changes:
1. Install `git` via `apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*` in Dockerfile (Python3.12 image otherwise unchanged).
2. Update `.github/workflows/tests.yml` to **build actual Dockerfile inside Ubuntu GitHub CI** and run targeted `tests/test_runtime_evidence_wrapper.py` and `tests/test_site_combat_state_runtime_fallback.py` INSIDE that image with the real workspace volume, ensuring environment parity, not just native Ubuntu Python pytest.
3. Update `tools/run-public100-baseline68-expanded128-v4.sh` after Docker image build with early read-only `docker compose ... lab sh -ec 'command -v git; git --version; command -v bash'` preflight. Missing prerequisites → fixed safe `ABSTAIN_LAB_GIT_OR_BASH_MISSING`, ahead of the 27-minute data reconstruction. No raw logs exposed, no weakening source guards.

## Operational note

CI must be SUCCESS on **exact final PR HEAD**, then squash merge #313 and verify push main CI SUCCESS for exact live main SHA. No new Host/corpus experiment in this PR; synthetic/docker CI only, thus no new runtime wrapper (v4 already has dedicated exact publisher). Once merged and both CIs green, the next SINGLE server command to retest entire workload (no new data scope):
```bash
cd ~/projects/planets-lab && git pull --ff-only origin main && bash tools/run-public100-baseline68-expanded128-v4-with-evidence.sh
```
Or, if the user wants JUST the pytest failures verified without re-running large corpus, use **one dedicated tracked short `tools/run-*-with-evidence.sh`** in future PR. Avoid asking user to repeat 27-minute run unnecessarily; Docker CI proving both targeted suites passes already indicates likely fix. Do not claim local green pytest before user runs.

Boundaries preserved: `CURRENT` public68 unchanged, public100 immutable full100 metadata only, 68 exact baseline entities only, sealed heldout32 NEVER decoded, frozen six-game PPQ #289 CLOSED, issue #247 real order witness OPEN/PARKED, C5/Horwasp PAUSED and unrelated production IntelBoard untouched. Never promote archival T−1/T differences to actual Host accepted orders or DIFF_VERIFIED. Every next PR own fully rewritten `docs/CONTINUE_HERE.md`, numbered changelog, docs handoff/ROADMAP, exact PR and postmerge main CI, all user-facing chat Russian.
