# PR #319 — frozen baseline68 starbase→planet owner-link source qualification

## Context

PR #318 merged into actual `main` `c9c452e5c79eb24ada355ae9c46b14c705d24c6f`; final PR CI #1789 and postmerge push-main #1790 both SUCCESS. Follow repository process from `AGENTS.md`, `docs/WORKFLOW.md` and standalone `docs/CONTINUE_HERE.md`; verify new HEAD/CI live, historical SHA never assumed current.

Existing published v6 `runtime-logs/public100-baseline68-mine-joint-v6/20261025T002616Z_cd6140b03aa5` established exact frozen 8550 observer archive T−1/T pairs across 68 baseline games out of explicit public100 100 metadata/224014 member snapshots; standard nonplanet source identity audit counted **346222 same-ID starbase observation occurrences, all 346222 lacking generic direct `ownerid` typed evidence**. This is NOT a proof that bases have no owner. Historical #282 `docs/handoff/2026-10-22-pq-starbase-owner-planet-link-v1.md` already correctly distinguished linking through owning planet from actual base infoturn freshness in a small frozen PQ setting.

## Implementation

- `src/planets_lab/corpus/starbase_archive_link_readiness.py`: strict, count-only **same-ID T−1/T** classifier. Atomic abstain for invalid/duplicate starbase IDs. Require unambiguous positive typed base planet anchor (`planetid` / `planet_id`) unchanged in both archives; unique base per anchor and unique typed planet ID per snapshot; planet `ownerid`/`owner_id` must be unambiguous positive int of exact observer, with typed `infoturn == before/after embedded turn`, separately; any explicitly typed base owner must not contradict linked planet. No default owner inference when aliases conflict or base owner explicitly invalid. Link-current-on-both **does not mean the starbase row is current**.
- Distinguish three **mutually exclusive** source subsets of own-current planet-linked same-ID bases: (a) base `infoturn` typed/current BOTH archive turns, (b) missing at least one base `infoturn` but no stale/invalid value, (c) base `infoturn` stale/invalid. Missing direct base infoturn stays **ABSTAIN_BASE_FRESHNESS**, not `fresh`, no construction/queue/warehouse/phase claims.
- Require conservation: linked-own plus distinct unresolved/owner-conflict/anchor failure buckets equals qualified same-ID occurrence count; three base timestamp categories sum to linked-owned. **All counters fixed-schema aggregate integers; no entity IDs/planet IDs/coordinates/owner names or raw archive rows exported**.
- Opt-in `starbase_planet_link_readiness=True` in `src/planets_lab/corpus/m2_economy_coverage.py`; default historical schema/output unchanged. `tools/diagnostics/m2_public_corpus_economy_coverage_v1.py --starbase-linked-provenance` enables exactly this field after independent population freeze. Generic safe nested-int aggregate gate extended by one fixed sample field, the separate starbase validator requires all exact expected counter keys/partition conservation **and pinned original 346222 same-ID starbase occurrences**, SHA/manifest/metadata and false Host flags.
- New dedicated `bash tools/run-public100-baseline68-starbase-link-v1-with-evidence.sh` reuses **EXACT** `tools/run-with-runtime-evidence.sh`; checks Docker Git/Bash, pinned CURRENT=public68 and explicit read-only public100 SHA, independent baseline68 cohort ID attestation, **frozen previous 8550 adjacent source-pair digest `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659` BEFORE any reconstruction**, full Docker pytest, standalone isolated host source gate preflight, fixed-schema source aggregate validation. Only sanitized status/aggregate/log/exit SHA on `runtime-logs` EVEN ABSTAIN. No private local logs/JUnit/raw member rows published.
- `tests/test_starbase_archive_link_readiness.py`: synthetic malformed/duplicate IDs, ambiguous planet anchors/owner, stale/missing base infoturn, owner conflict, successful positive case, frozen selection integration (default schema parity), independent host `python -I -S` synthetic validator without DuckDB/installed packages, runner safety and Bash syntax.
- Work in this PR is **DOCUMENTED+TESTED** once exact CI passes. **New real starbase empirical linked counts are UNKNOWN until actual server execution**; no Host accepted order/turn phase receipt and no new `DIFF_VERIFIED`.

## Next actions

1. Verify final **exact HEAD** PR #319 Actions `completed/success`; fix failed tests while maintaining privacy/source gates; merge squash **with exact expected HEAD SHA**, verify live main and postmerge main CI `completed/success`.
2. After #319 merge, on actual corpus server from `~/projects/planets-lab` run:
```bash
git pull --ff-only origin main
bash tools/run-public100-baseline68-starbase-link-v1-with-evidence.sh
```
It is a NEW source-only corpus study, **not run during this coding PR**, and must publish sanitized runtime evidence even ABSTAIN. No user log copy; assistant retrieves the published GitHub safe JSON directly.
3. Real future counters: compare `same_id_planet_linked_current_own_both_archives` and `same_id_planet_linked_base_current_both_archives` against total 346222 repeated same-ID observational starbase occurrences, with missing/stale/ambiguous source buckets. They remain repeated observer/archive occurrences, **not unique base construction, authenticated owner intents, or Host phases**.
4. If evidence shows missing base infoturn dominates, maintain missing-freshness gate. Further independently accepted Host orders/phase-specific evidence remains issue #247 PARKED. The next independent VCR correlation key may need a distinct study; generic cross-turn VCR `id` has zero historical continuity, not proof of no battles.

## Boundaries

No raw/sensitive `.trn`, HAR, API credentials, game/player/planet/base identities, accepted orders, private captured traffic. No mutable DuckDB writes, `CURRENT` switches or sealed32 entity access, no resampling frozen PPQ #289, C5/Horwasp, or unrelated production IntelBoard changes. Preserve `DOCUMENTED` / `TESTED` / `CORPUS_OBSERVED` / `DIFF_VERIFIED` separation. Starbase being anchored to a planet ≠ new Host construction or current inventory/queue, even if a base row is fresh.
