# PR #320 — validated starbase planet-link observational scorecard (2026-10-25)

## Context

Live previous main before this PR: `7fd6ded29b14462a367f96a6871b6dc37c533356` (#319 merged; exact PR CI #1801 and postmerge push-main #1802 `completed/success`). Branch `research/starbase-real-link-source-scorecard-v2`, PR https://github.com/Numillyash/planets-lab/pull/320. PR #320 CI/merge **must be verified live**, do not assume success from documentation.

## Verified real runtime source

Independently fetched from GitHub orphan `runtime-logs/public100-baseline68-starbase-link-v1/20261025T110236Z_7fd6ded29b14`, `metadata.json`, `stage-status.json`, baseline cohort attestation, `pytest-counts.json`, entire published sanitized aggregate. Started UTC **2026-10-25 11:02:36**, completed **11:30:14 = 27m38s**, outer exit **0**, `PASS_NONCAUSAL_READONLY`, `PASS_VALIDATED_AGGREGATE`, Docker Git/Bash PASS, exact baseline68 IDs SHA pinned public68 PASS, host isolated validator self-test PASS, pytest **3789 tests, 0 failures/errors, 26 skipped**. Explicit immutable public100 metadata exactly 100 games/224014 source member observations and source SHA `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`; baseline68 exact manifest digest `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9`, **8550** selected T−1/T pairs pre-frozen SHA `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659`, heldout32 entity records NEVER read, `CURRENT` unchanged.

**Exact repeated observer-archive starbase same-ID source counts (not unique bases, turns or independent Host actions):**

- 346222 same-ID occurrences across T−1/T.
- 138711 have one unambiguous owned-current **planet link** in both archives. Among these, 138708 additionally have current typed **base infoturn** on BOTH sides; **3** have a stale/invalid base `infoturn`; **0** lack an `infoturn` on either side under this classifier.
- 207511 cannot be certified as own-current through both planet links (mixed foreign/stale/unknown; **NOT** necessarily missing bases or hostile owners). Ambiguous anchors: **0**, changed/missing anchors: **0**, explicit base owner conflict: **0** in this frozen sample.
- `138708 + 3 + 0 = 138711` and `138711 + 207511 = 346222`. Direct generic base `ownerid` alone qualified **0/346222**, so the planet link resolves an important **observability blind spot**, not an earlier ownership error.
- All previous real v6 source projection values (including five minefield joint counts) were compared against the real new starbase report and **identically replayed**. `CORPUS_OBSERVED` for qualified source records only. Not proof of a buildable starbase, warehouse stocks, construction queues, Host accepted orders or a Host phase.

## What PR #320 implements

- `tests/fixtures/public100_baseline68_starbase_link_v1_safe_projection.json`: exactly allowlisted (no game/player/planet/base IDs, coordinates, orders, HAR, raw member rows) projection of already-published successful report, plus explicitly pinned real stage/test/run metadata. Entire previous v6 safe source projection and all source limits reused without changing a value, one new ten-count `starbase_planet_archive_link_not_host_phase` section.
- `src/planets_lab/corpus/starbase_link_v1_observation_readout.py`: *offline* exact previous v5+v6 source/selection/Host gate replay; exact real #319 runtime identity/success/checks, unchanged old projection byte-equivalent decoded data; strictly ten allowlisted nonnegative integer starbase counters, both conservation equations, original 346222/8550 pins and never a causal Host flag. Existing pure-stdlib strict source reviewer reused without requiring installed DuckDB.
- `tools/diagnostics/review_starbase_link_v1_observations.py`: standalone `python3 -I -S` offline replay from v5 + v6 + starbase safe JSON, write only if destination absent, print no untrusted source content on ABSTAIN. Output `validation/research/public100-baseline68-starbase-link-v1-source-scorecard.json` checked into repo.
- `tests/test_starbase_link_v1_observation_readout.py`: exact live safe scorecard replay, origin/marginal, stale/count partition and malicious injection tests, host Python isolated CLI and no overwrite.
- This is **only offline analysis of already-published safe reports**. No new Host or corpus experiment; no dedicated runtime evidence runner needed beyond existing already-run PR #319 launcher. Work is `TESTED` after actual CI, empirical source results are `CORPUS_OBSERVED`, Host mechanics not `DIFF_VERIFIED`.

## Next actions

1. Verify exact final PR #320 head Actions success, merge with expected SHA, verify actual new main SHA and completed successful push-main Actions; do not invent CI or commit.
2. Next substantive evidence direction, not another broad unspecific sample: investigate **VCR cross-turn correlation structure** from documented public archive schema in baseline68, because generic `vcrs.id` matched ZERO across 8550 adjacent T−1/T archives. Zero means ID is not a cross-turn link here, **NOT** no battles. Perform read-only local code/schema analysis before proposing signatures; if a NEW on-host experiment is needed, dedicated tracked `bash tools/run-*-with-evidence.sh` calling unchanged `tools/run-with-runtime-evidence.sh` and publishing sanitized JSON/exit/log even ABSTAIN. No heldout32, no frozen PPQ #289 resampling.
3. Any actual NuHost construction, mine sweep/decay or battle phase `DIFF_VERIFIED` still needs authenticated accepted orders and phase receipts; issue #247 OPEN/PARKED. No user-private HAR/orders or production IntelBoard changes.

## Boundaries

Repeated 8550 T−1/T perspective snapshots across baseline68 games are NOT independent objects/actions. 100 games metadata only, 32 heldout entity games sealed, immutable public100 SHA pinned, `CURRENT=public68` SHA `5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a`, frozen PPQ #289, C5/Horwasp and separate IntelBoard untouched. Distinguish `DOCUMENTED`, `TESTED`, `CORPUS_OBSERVED`, `DIFF_VERIFIED`.
