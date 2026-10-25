# PR #318 — validated successful v6 same-row minefield observation readout

## Verified existing runtime evidence

Source of truth: GitHub orphan `runtime-logs/public100-baseline68-mine-joint-v6/20261025T002616Z_cd6140b03aa5`; actual `metadata.json`, `stage-status.json`, `pytest-counts.json` and complete **already published sanitized** `m2-deep-coverage.json` independently inspected. Source commit `cd6140b03aa5be714f9245a9a4966f97a9fbbf5a` (PR #317 squash merged, final PR CI #1777 and main CI #1778 SUCCESS). Actual run 2026-10-25 UTC **00:26:16–01:01:24 (35m08s)**, outer exit0, no missing artifacts, `PASS_NONCAUSAL_READONLY`, `PASS_VALIDATED_AGGREGATE`, Docker Git/Bash PASS, baseline68 exact attestation PASS, **3746 tests / 0 failures / 0 errors / 26 skipped**, host joint self-test PASS. Immutable explicit public100 verified SHA `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`, 100 metadata games / 224014 source members; exact frozen baseline68 (68 content games), 32 sealed entity games untouched, `CURRENT` unchanged. Frozen same 8550 observer-perspective T−1/T archive pairs SHA `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659`, local manifest SHA `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9`.

**Exact observed v6 minefield source joint** across repeated observer pairs (not unique minefield IDs or Host actions):

| Source-only count | Real v6 |
|---|---:|
| Same ID across archives | 887224 |
| Fresh own `ownerid+infoturn` T−1 and T | 138864 |
| Also stable numeric `x/y` and numeric units both turns | **138833** |
| Fresh own excluded from joint qualification | **31** |
| Within qualified joint: numeric units decreased | **134693** |
| Units increased | **3746** |
| Units unchanged | **394** |
| Units changed (increase + decrease) | **138439** |

`134693 + 3746 + 394 = 138833` and `134693 + 3746 = 138439`. The previous #315 only knew that the intersection of 138864 fresh own and 536703 stable owner-centre changed-unit source rows was bounded **[0,138864]**; here the actual same-row intersection is **138439**. Missing 31 cannot be attributed specifically to centre movement versus malformed/missing position based on these aggregates alone. Repeated archive perspectives mean the observations are **not independent unique minefield transitions**.

## Implementation in PR #318

- `tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json` derived programmatically from the **actual** live sanitized v6 report, copying exactly the already committed v5 source projection and adding **only the five v6 joint count keys**. Every previous field was compared for equality against real v5 fixture before committing (zero differences). Only fixed count-only runtime attestation included; raw IDs and player/game/coordinates/orders excluded.
- `src/planets_lab/corpus/minefield_v6_observation_readout.py`: separate offline fail-closed check that validates the reference via the existing strict v5 reviewer, pins real v6 successful source SHA/run/status/heldout/current flags, demands exact equality of *all* previous v5 safe source/marginal/metadata fields, permits only the five joint source counters, verifies directions/conservation/marginal bounds, and emits a small noncausal scorecard with explicit false Host-causality/uniqueness flags.
- `tools/diagnostics/review_minefield_v6_observations.py`: offline **stdlib-only** `python3 -I -S` CLI for original v5 fixture + frozen v6 safe projection → count-only `validation/research/public100-baseline68-minefield-v6-joint-observations.v1.json`. Refuses overwrites and suppresses untrusted file contents on failure; no DuckDB, Host API, database, private .trn/HAR or remote connector.
- `tests/test_minefield_v6_observation_readout.py`: deterministic exact replay against checked-in scorecard, source/marginal/range/conservation/Host-provenance adversarial cases, no third-party host site-packages and safe CLI failure behavior.
- This is **an offline analysis of already-published safe aggregates, NOT a new on-host experiment**, so no new dedicated server runner is needed; do not rerun 35-minute v6 just to produce the readout.

## Evidence interpretation

**Code/test evidence**: `TESTED` only after passing actual final PR CI. **Archive observation evidence**: `CORPUS_OBSERVED`, exact joint signs as count-only descriptive provenance. **NuHost Host phase/mine causality**: none. The large downward count must NOT be labelled observed decay, beam/fighter/starbase sweep, MSC, ship hit or direct Host action. No accepted phase-specific Host receipts or paired authenticated orders; issue #247 remains **OPEN/PARKED**.

## Next engineering directions

1. Check #318 exact final HEAD PR Actions SUCCESS, expected-SHA squash merge, live main commit and postmerge push-main Actions SUCCESS; update standalone `docs/CONTINUE_HERE.md` (this PR itself) and numbered changelog/roadmap/map.
2. Do not resample sealed32 or revisit #289 frozen PPQ. Without user-private captures, next independent **source-structure** direction: inspect canonical starbase→planet correspondence and provenance paths, since generic `starbases.ownerid` is untyped in all 346222 old paired observations; alternatively inspect combat VCR links, since generic `vcrs.id` matches cross-turn zero times. Any NEW on-host or corpus experiment must have a dedicated tracked short `bash tools/run-*-with-evidence.sh` reusing `tools/run-with-runtime-evidence.sh`, auto-publishing sanitized status/JSON/log/exit on `runtime-logs` even ABSTAIN.
3. Independent accepted orders plus *phase-specific* Host receipt are necessary before upgrading isolated mine mechanics to `DIFF_VERIFIED`; issue #247 remains PARKED. M0–M6 project overall completion not assigned invented percentages.

## Boundaries

Read-only exact `public100` generation, `CURRENT=public68` pinned SHA `5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a`, heldout32 entity content SEALED, frozen PPQ #289, C5/Horwasp, IntelBoard production untouched. Treat any percentages across observations as repeated correlated samples, not unique independent events or causal rates.
