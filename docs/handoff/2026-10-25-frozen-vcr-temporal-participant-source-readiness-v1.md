# PR #321 — strict frozen VCR temporal and participant source-readiness (2026-10-25)

## Context

Source of truth LIVE GitHub main, historical pre-PR commit `de582c74151aff30840a00fea3b30310803a2130`; #320 fully merged with verified exact final PR-head CI #1811 and postmerge main CI #1812 both `completed/success`. PR #321 https://github.com/Numillyash/planets-lab/pull/321; verify its eventual own actual PR SHA and CI before merge. Do not substitute handoff history for live Github.

## Verified existing source evidence

Last real starbase survey: `runtime-logs/public100-baseline68-starbase-link-v1/20261025T110236Z_7fd6ded29b14`, 27m38s, exit0, 3789 Docker test cases/0 failures/errors/26 skipped, exact pinned generation/cohort/8550 selection, sealed32 false/CURRENT unchanged. Starbase archive observer occurrences same-ID 346222; own current planet-link both turns 138711; base itself fresh typed `infoturn` both 138708, stale 3, missing 0; unqualified own-current planet link 207511. These are repeated `CORPUS_OBSERVED` source data, not Host construction/battle proof. #320 strictly reanalyzed already-published safe source with scorecard and full previous v6 parity.

VCR generic archive identity on frozen 8550 T−1/T **before 21918 VCR ID rows, after 22414**, direct same-ID across adjacent turns **0** (v5–starbase historical report). This does NOT mean that there were no combats, or that `vcr.id` isn't valid within a single battle turn. Existing `src/planets_lab/corpus/combat_vcr_runtime.py` already keys replay input cases by **`(battle_turn, vcr_id)`**, looks at typed raw `vcr.turn`, falls back to embedded archive turn in adapter for missing battle turn, and fails closed when same-game/same-turn/same-VCR-ID observations from distinct perspective members disagree on replay inputs. **We are NOT changing that adapter or claiming a cross-turn physical combat ID.**

## Implementation

- New `src/planets_lab/corpus/vcr_archive_temporal_readiness.py` strictly requires positive integer unique VCR row IDs on EACH archive independently, otherwise atomically `ABSTAIN`. For each archive turn T−1 and T, separate raw `vcr.turn` strictly typed positive and equal embedded archive turn vs earlier vs future vs missing/invalid, plus availability of both typed positive `left.objectid`/`right.objectid` and separately both positive `leftownerid`/`rightownerid`. Only count exact-archive-turn AND both participant IDs; optionally both owners. Missing typed fields do not default to valid. All fixed count-only counters and partition/monotonicity invariants; **no game/player/VCR/ship/battle IDs, positions, seeds or raw payload values leave module**.
- **Opt-in** `m2_economy_coverage.analyze_corpus_coverage(..., vcr_temporal_readiness=True)` and `tools/diagnostics/m2_public_corpus_economy_coverage_v1.py --vcr-temporal-input-provenance`. Default report and existing M2 source behavior unchanged; 8550 pair population selection SHA verified BEFORE entity reconstruction.
- `tools/diagnostics/validate_vcr_archive_temporal_readiness_v1.py` host-side standalone stdlib-only `python -I -S` synthetic validator preflight, strict all-key integer/no-extra-data aggregate verification, exact previous real frozen VCR source 8550 pair, 21918 before, 22414 after, zero cross-turn-ID matching, fixed SHA and manifest. Require raw turn partition and typed IDs/owner monotonicity without assuming any empirically observed new result.
- New independently tracked `bash tools/run-public100-baseline68-vcr-temporal-v1-with-evidence.sh` calls unchanged `tools/run-with-runtime-evidence.sh` with sanitized JSON/status/log/exit/source commit EVEN ABSTAIN. Underlying read-only Docker runner repeats existing SHA pinned explicit public100 metadata-only 100 games/224014, EXACT baseline68 entity set, 8550 frozen T−1/T pairs, full pytest and preflight and generic+new validator. 32 sealed heldout entity games NOT decoded, `CURRENT=public68` unchanged.
- `tests/test_vcr_archive_temporal_readiness.py`: malformed bool/duplicate ID atomic refusal, source-time categories, typed left/right owner/full combinations, no inference from same cross-turn ID, opt-in integration preserving default report, standalone no-site-packages preflight, frozen dedicated publisher and bash syntax.
- **This PR adds `TESTED` source diagnostic capability after final actual CI, not new `CORPUS_OBSERVED` VCR contents until an on-host run, and certainly no `DIFF_VERIFIED` Host battle.** C5/Horwasp code untouched.

## Next actions

1. Complete exact final PR #321 CI SUCCESS, squash merge with expected HEAD SHA, verify actual live merged main SHA and postmerge push-main Actions `completed/success`. Update full own-numbered `docs/CONTINUE_HERE.md`, numbered PR_CHANGELOG, roadmap/progress map within this PR.
2. AFTER merge, the operator on the existing corpus server runs:
```bash
cd ~/projects/planets-lab
git pull --ff-only origin main
bash tools/run-public100-baseline68-vcr-temporal-v1-with-evidence.sh
```
The assistant reads sanitized `runtime-logs` on GitHub, without needing user to copy logs. A future report must distinguish which raw VCR rows specify same embedded archival turn vs historical/future/missing `turn`, and both participants/owners readiness; never treat observed cross-turn same ID as authenticated combat continuity.
3. For independent accepted Host combat/ship-building/mining phase verification need independently authenticated accepted orders and phase-specific receipts; issue #247 OPEN/PARKED. No change to combat queue/C5; if future real VCR temporal source proves sufficient, a separate independently justified same-**turn** battle input correlation gate may be researched.

## Boundaries

Immutable public100 SHA `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c` (only metadata all 100); `CURRENT=public68` SHA `5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a`; baseline68 verified independent manifest digest `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9`, frozen original 8550 SHA `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659`, 32 heldout entity games SEALED, frozen PPQ #289, issue #247 PARKED, C5/Horwasp and IntelBoard production untouched. No raw orders/IDs/private .trn/HAR. Code `TESTED`, archive readout `CORPUS_OBSERVED` only after actual run, Host `DIFF_VERIFIED` unchanged.
