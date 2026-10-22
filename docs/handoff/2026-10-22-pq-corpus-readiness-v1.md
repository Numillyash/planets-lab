# PR #278 — PQ/PPQ historical corpus readiness without rescanning

Date: 2026-10-22. Source: `src/planets_lab/corpus/pq_historical_readiness.py`, CLI `tools/diagnostics/pq_historical_readiness.py`, tests `tests/test_pq_historical_readiness.py`.

## Why start historical validation now?

The queue/economy stack through #277 has reached a **bounded executable TESTED conditional** checkpoint, but its PQ/PPQ shipyard selection, warehouses, PP ledgers, chosen Ship IDs and Host phase ordering are not authenticated by real NuHost before/after states. More synthetic sequence PRs alone cannot promote those claims. Existing public archives have already supported numerous observational/differential *other* movement/combat/economy studies; they are not yet an independently attributable queue-order test set. The feature-index's trusted public `/game/loadinfo` and archive coverage metadata can pre-screen promising games **without** reading raw game members again.

## Input and exact interface

`python -m tools.diagnostics.pq_historical_readiness --feature-index validation/corpus/compiled/v1/metadata/game_features.parquet --frozen-cohort path/to/explicit-cohort.json --output artifacts/pq/readiness/report.json`

Required, predeclared cohort JSON is:
```json
{"schema":"planets-lab.pq-historical-frozen-cohort.v1","game_ids":[123456,654321]}
```
IDs above are illustrative only; **do not silently use these exact IDs** as study subjects. Build a genuine allowlist separately from the already designated permitted baseline/public cohort. Do not copy fresh32/heldout32 into the allowlist without explicit independent pre-registration. The CLI consumes an **existing** feature-index Parquet (no rebuild), demands strict schema/typed values, and hashes the exact cohort bytes and Parquet index bytes for reproducible provenance.

Strict classification:
- `game.status=3` and typed queue booleans determine completed PQ (`productionqueue=true`, `planetaryproductionqueue=false`) or PPQ (both true). Both false is excluded; PPQ true and PQ false is treated as contradictory/unsupported, never guessed.
- Archive coverage requires `archive_present=true`, `rectangular_grid_complete=true`, and positive `archive_transition_count`; absent metadata, incomplete grid and no transitions are separately reported. TRUE coverage means only **historical adjacent-member availability candidate** — not that all starbase orders/owner PP warehouses are visible.
- Missing feature or null, malformed/int-as-bool, source outside the **explicit** cohort, duplicate rows or malformed cohort never silently promotes. Non-indexed requested IDs are explicitly `NOT_INDEXED`. Report includes per-game dispositions, counts, actual excluded/missing predicates, observational candidate IDs and global **host_causal_verified_games=0**.

The report contains NO private orders, raw archives, player personal data, synthetic Host “evidence”, or archived turn entities. It does NOT open heldout32, `CURRENT`, runtime-logs, public100 ZIPs or game turns.

## What corpus can/cannot answer

**Already feasible without the user:** metadata selection in a predeclared allowed cohort, availability of adjacent public turns and contradictions between documented rules and historical *visible outcomes* when actual relevant ship/base fields are shown. A positive match is `CORPUS_OBSERVED` or qualified observational support, not Host-executed-order proof. Existing 12-game feature-index archive-enriched checkpoint can be used as a small control. public68 and public100 are larger corpora but need existing appropriate indexes/manifests; don't assume the old 12-game index covers all 68/100.

**Requires additional data/authorised intervention later for `DIFF_VERIFIED`:** independently authenticated server-accepted specific ship/planet/base orders for affected owners, genuine T−1/T Host timing, complete provenance-qualified owner PP/bank/component/shipyard/fleet and cargo snapshots before and after, and absence of confounding external actions. Archived public visible-state changes, client `/game/save` 2xx, signed local V1/V2 capture or an asserted ship-loss snapshot are NOT sufficient. All such controlled live experimentation is parked in [issue #247](https://github.com/Numillyash/planets-lab/issues/247), not requested now.

## Immediate next science (without altering holdouts)

1. Run this metadata gate on **already available index** with a frozen allowed/public cohort. If only the tracked 12-game index is present, label that scope 12, NOT 68. The current PR adds machinery, synthetic and Parquet tests, **not a claim that the 26+ GiB corpus was actually rescanned**.
2. Predeclare candidate windows and an independent field-sufficiency gate for actual T−1→T planet owner/base/ship/warehouse/PP facts before opening any game payloads. Try to recover counts/coverage from existing compiled metadata or published aggregate reports first. If required fields absent, record `ABSTAIN_MISSING_*_FIELD` and report observational feasibility instead of asserting Host parity.
3. Compare boundedly on nonsealed, predeclared slices only. A documented host selection/random/deterministic queue step must be interpreted according to evidence tier.

## Maintenance

Per #262 **each PR** must completely rewrite `docs/CONTINUE_HERE.md` with its actual PR number, update `docs/PR_CHANGELOG.md`, and change substantive topic docs. Check exact final HEAD CI success, merge and successful push `main` CI before declaring completion. Keep public68 `CURRENT` unchanged, public100 immutable, M2 heldout32 entity sampling sealed, C5 and production IntelBoard untouched.
