# PR #312 — расширенный 128-парный baseline68 corpus-pass + безопасная диагностика пяти pytest ошибок

24 октября 2026; PRE-PR `main` SHA `c692f00e8adf2406ab6ef4f5f9b14fd9ba0f02be`, PR #311 merged, final PR CI #1718 and postmerge main #1719 SUCCESS. Этот SHA исторический; live GitHub — единственный источник будущего HEAD.

## Обоснование по НАСТОЯЩЕМУ серверному запуску

В run `runtime-logs/public100-baseline68-deep-v2/20261024T171245Z_c692f00e8adf`:
- start `2026-10-24T17:12:45Z`, end `2026-10-24T17:20:41Z`: **7 мин 56 сек**;
- immutable explicit public100 full SHA256 verified `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`; all100 games / 224014 members; all metadata qualified adjacent 221091. Baseline68 ID exact-identity cohort guard PASS against independently SHA-pinned public68; current unchanged, sealed32 excluded from all entity reconstruction.
- existing M2 source-bounded owner-current `16 pairs/game × 68 = 1088` frozen selected; successful aggregate report and strict validation. 39402 same-owner current planet pairs, 7059 archival planet windows any mineral surface residual, 885 windows with any cargo-match **candidate**, 5 stale/no-infoturn owner planet record ABSTAIN. These are **observed T−1/T** changes, not demonstrated Host actions, no accepted orders.
- Complete server pytest: `3692` cases, `5` failures, `0` errors, `26` skipped. Five test-case details are private-local JUnit, safely not published. Root cause of these 5 test failures **NOT established yet**. CI green on synthetic environment and on-host failures can coexist. Do not invent cause.

The user expects a significantly larger corpus pass, not just a quick `COUNT`/metadata summary. The previous `m2_economy_coverage.py` explicitly bounded `MAX_PAIRS_PER_GAME=16`, so increased Docker runtime cannot increase coverage without code changes.

## Implemented in PR #312

- `src/planets_lab/corpus/m2_economy_coverage.py`: increase **bounded maximum** per-game metadata-frozen adjacent observations from **16 to 128**, total guarded `MAX_SELECTED_PAIRS=16384` (approved baseline68 selection at most 68×128=**8704**). Preserve original census of **ALL 100 game metadata**, apply `allowed_games` exact published baseline68 allowlist, freeze deterministic game/perspective/turn selection **before** reconstructing any member; process each pair with existing owner-current planet/mineral/mass-balance/cargo-context model, no reordering or causal advancement. Add aggregate **nonplanet_section_observability_not_host_phase** for 5 sections `minefields`, `ships`, `starbases`, `vcrs`, `ionstorms`: each selected archive pair counts typed list presence, non-empty both, raw before/after row totals, row-count difference. This is ONLY perspective archive source availability and may be stale; not exact Host mine placement/sweep/ship combat. `evidence_limits["nonplanet_section_counts_prove_sweeping_or_combat"]=False` explicit. Strict `tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py` now allows the new nested numeric aggregate key; forbids raw objects/lists/strings.
- `tools/run-public100-baseline68-expanded128-v4.sh`: NEW separate tracked full host-run command, cloned from prior v2 guard path, retaining exact CURRENT baseline SHA pinned public68 cohort manifest identity guard #311, full public100 SHA, **read-only** Docker lab, complete pytest, existing strict aggregate validator, actual attested local manifest hash binding to M2, no heldout32 decoding. Uses `--max-games 68 --pairs-per-game 128`, a new separate `artifacts/corpus/public100-baseline68-expanded128-v4/` report directory and status. No reconstruction of extra game IDs. Real 8704 is upper bound; selected actual pairs recorded.
- `tools/diagnostics/public100_pytest_failed_modules_v4.py`: interprets local private JUnit but only maps *Git-tracked allowlisted* paths `tests/test_*.py` to **counts** of failed/errored testcases; all test names, parameters, failure messages, internal traces, source file paths not in tracked test subset are suppressed and only counted as `unmapped_failures_or_errors`. Needed to diagnose earlier 5 server-only pytest failures without unmasking source/private test arguments. Outputs `pytest-failed-modules.json` (safe filenames of public repo tracked test modules only), alongside preexisting `pytest-counts.json` and separate aggregate report. Detailed `private-local/pytest.xml`, `pytest.log`, `deep-m2.log` remain untracked/unpublished.
- `tools/run-public100-baseline68-expanded128-v4-with-evidence.sh`: ONE short command invoking EXACT `tools/run-with-runtime-evidence.sh`, run_name `public100-baseline68-expanded128-v4`, only fixed allowlisted stage/cohort/test/module/M2 JSON copied to `runtime-logs` with sanitized stdout/status/exit/source SHA EVEN ABSTAIN.
- `tests/test_public100_expanded128_multifamily_v4.py`: generated fake 100-game metadata, tests 8704 deterministic selected pairs across baseline68 and none in heldout32, rejects >128 pairs/game; adversarial injected private JUnit strings excluded, maps only tracked filenames, bash -n both runners and launcher evidence include scopes.

## After green exact-head PR CI and postmerge main CI

ONE server command:
```bash
cd ~/projects/planets-lab && git pull --ff-only origin main && bash tools/run-public100-baseline68-expanded128-v4-with-evidence.sh
```

Assistant fetches REAL GitHub runtime artifacts from `runtime-logs/public100-baseline68-expanded128-v4/<actual stamp_SHA>` itself. Do not fabricate report before run and do not ask user to manually share private logs. Duration depends on 26.65GiB SHA + large entity reconstruction, potentially substantially longer than prior 8min; no fixed-duration guarantee and user may interrupt. No `CURRENT` switching, public100 rebuild, .trn/HAR, 32 sealed game entity access, or private accepted orders; no source-independent Host `DIFF_VERIFIED`.

## Remaining boundaries and next research

Despite larger sample, 8704 is still **not** all 221091 archival adjacent pairs and not 100-game content validation; 32 heldout remain sealed. M2 archive T−1/T and nonplanet section lists do NOT isolate any single Host phase, accepted player order, defensive mine sweep stage or battle engine result. `DOCUMENTED` + `TESTED` + `CORPUS_OBSERVED` separate from `DIFF_VERIFIED`. Frozen public PPQ #289 stays CLOSED, issue #247 actual accepted orders OPEN/PARKED, C5/Horwasp and production IntelBoard untouched. Independent true Host witness before stage/order needed for causal claims.

Mandatory **every PR**: full own-numbered `docs/CONTINUE_HERE.md`, numbered `docs/PR_CHANGELOG.md`, substantive handoff/ROADMAP/project map, exact FINAL PR-head CI SUCCESS, squash merge only then, actual main SHA and push CI success. All user-facing chat Russian.