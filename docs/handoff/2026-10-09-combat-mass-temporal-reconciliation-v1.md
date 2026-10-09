# Time-indexed mass reconciliation and Rush capture candidate — V1

Date: 2026-10-09.

## Frozen inputs

Clean successful run:
`runtime-logs/combat-mass-capture-phase-controls-v1/20261009T203109Z_2d7fbf7cb8fa`, source main `2d7fbf7cb8fa910a7d992e79b9f4ca02e4f58dd7`. It checked 14 game/turn pairs, 6 with changed hull masses versus the earliest `hulls` array. Across all 14, T−1 player perspectives agreed on changed hull IDs/values.

All 67 residual identities preserved at
`runtime-logs/combat-mass-complete-residuals-v1/20261009T164712Z_614b20e04efe`.

Independent T−1 static changes across 14 controlled game/turns:
- hull1039 D19c: 96 → 46 KT (G217591, G325434, and additional G341336, G310054)
- hull117 Brood: 125 → 145 KT (G217591)
- hull119: 165 → 185 KT (G217591)

In the complete 67-residual corpus, exactly **7 individual VCR sides** intersect a changed hull catalog row:
- D19c G217591 T75 V756: 46+2×150=346
- D19c G325434 T149 V1075: 46+2×1=48
- Brood G217591 T149 V2405,2406,2422,2423 mass290=2×145, with owner T−1 clans900/900
- Brood G217591 T149 V2421 mass650=2×145+360, but owner T−1 clans unknown.

These *numeric* matches use independently archived T−1 hull mass and, where present, owner engine/clan data. The number of working generators and random +360 branch are still selected retrospectively from factual VCR data; they are not independent Host predictions.

## New code

`tools/diagnostics/combat_mass_temporal_reconciliation_v1.py`
`tools/run-combat-mass-temporal-reconciliation-v1.sh`
`tools/run-combat-mass-temporal-reconciliation-v1-with-evidence.sh`
`tests/test_combat_mass_temporal_reconciliation_v1.py`

The report fail-closed checks: source status/schema, all 14 controls, untruncated all-perspective agreement, full 67 VCR-side uniqueness, exactly 6 changed game-turn controls and seven intersecting cases. In particular, 4 Horwasp start states are corroborated by *independent* T−1 full clan capacity, and the fifth is clearly marked unknown instead of guessed.

### Rush #27: strong within-turn capture + new-owner Saber hypothesis

G617883 T201:
- T200 owner5 source ship27 Rush hull94 has engine9 Transwarp, crew28;
- V1016 owner5 Rush#27 hull94, mass645, crew28, fighters200;
- V1017 owner4 same ID/hull94, mass795, crew10, fighters148;
- owner4 owned Saber#406 exactly at shared combat site [1455,2615] in T200 and T201;
- candidate calculation: **645 + 150 = 795** using independent prior engine9 and owner4 Saber T−1 position.
- V1016 terminal outcome is NOT provided in the initial VCR records; capture + SG activation is a highly constrained hypothesis, not completed independent postcombat replay.
- T201 same ID27 Victorious hull35 is a different archival identity; do NOT project its engine9 backward into Rush. The candidate Rush engine9 is grounded in ORIGINAL owner5 T200.

Source: https://help.planets.nu/abil-shield-generator

## Run

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    bash tools/run-combat-mass-temporal-reconciliation-v1-with-evidence.sh

Output: `artifacts/combat/mass-temporal-reconciliation-v1/published/report.json`.
Evidence: `runtime-logs/combat-mass-temporal-reconciliation-v1/`.

No DuckDB rerun required. No changes to probabilistic.py, a Host executor, canonical game database, or production client.

## Scientific next steps

1. Build a READ-ONLY time-indexed static provider from T−1 owner-perspective archives, with independent checks on multiple distinct game settings; do not silently replace all earliest `hulls` catalogs yet.
2. Obtain actual terminal battle result/crew capture from combat engine replay or other independent Host outcome records, then test owner-recompute of generator bonuses on N+1 ships.
3. Resolve Horwasp mutable clans and ordering without oracle VCR masses, separately from static-drift artifacts.
