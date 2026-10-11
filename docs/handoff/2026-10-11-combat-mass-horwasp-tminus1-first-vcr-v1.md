# Horwasp: independent T−1 clan-component hypothesis, by VCR-ID occurrence

## Frozen evidence

Source main: 45a3eaf8d1435117a169b530221a54027f626ed9
Evidence branch: runtime-logs
Source: runtime-logs/combat-mass-late-residual-prestate-audit-v1/20261011T141334Z_45a3eaf8d143/
Published report Git blob SHA-1: f4650a6cdb612f750970385d762af0d486894c6e

424 original independently held-out ship/VCR sides, including 26 Horwasp race12 sides. All 26 have T-1 owner-ship clans and hull cargo observed independently; 423/424 global sides have T-1 ship records. Carrier +360 control: 35 of 60 right-hand standard sides facing nonzero left bays had precisely +360, versus 0/140 when left bays absent. Those are retrospective VCR bay measurements, not T-1 predicted random rolls. No exact-site T-1 SG candidates observed, which does NOT prove SG absent at battle.

## Falsifiable non-Host formula

Hypothesis computed only from independently archived T-1 mass/clans/capacity:

    hypothetical_mass = hull_mass + floor(hull_mass * clans_Tminus1 / hull_cargo_capacity)

NO factual VCR mass is used in the formula. Explicitly fail closed when clans/cargo/mass are absent, invalid, contradictory or archived hull/catalog mass disagree. Formula is unverified; do not claim host code reconstruction.

Manual cross-check against frozen JSON before adding code:

- 26 Horwasp sides from 21 distinct (game, turn, owner, ship) identities.
- Of 21 first-by-VCR-ID occurrences, 20 equal the T-1 hypothesis without extra effect.
- One first occurrence (G350094 T153 V1781 right, ship1037 hull210) differs by exactly +360KT; current VCR left bays support a retrospective carrier condition, but no RNG prediction.
- Of five repeated-by-VCR-ID appearances, one remains equal to unchanged T-1 candidate; the other four differ by −4, −34, −57, −225KT.
- G350094 T153 ship513 hull115, clans 24000/24000 at T-1: V1778 950KT, V1779 893KT, V1780 725KT. This does NOT prove VCR-ID ordering equals NuHost combat execution ordering, nor does it independently prove exact clan-loss counts.
- Fractional control: G449095 T134 hull204 (31KT, clans100, cargo1600) gives floor(31*100/1600)=1KT. Ceiling would yield 2KT; this is evidence for floor in this example, not general proof.
- Partial load: G371631 T41 V313 hull118 200KT with T-1 clans228/capacity300 gives 200+152=352KT.

## Implementation

Research-only diagnostic: tools/diagnostics/combat_mass_horwasp_tminus1_first_vcr_v1.py
Tests: tests/test_combat_mass_horwasp_tminus1_first_vcr_v1.py
Executable runner: tools/run-combat-mass-horwasp-tminus1-first-vcr-v1.sh
Evidence wrapper: tools/run-combat-mass-horwasp-tminus1-first-vcr-v1-with-evidence.sh

Input is the exact frozen 1.1MB published observational JSON, verified byte-for-byte via Git blob SHA1. The DuckDB is NOT opened, preserving read-only scientific boundaries. Output preserves all 26 Horwasp-side identities, separates first-by-ID and repeated-by-ID cohorts and lists same-ship mass transitions solely as observations. Current VCR left fighter bays enter only AFTER T-1 clan candidate calculation, and any +360 is an evaluated counterfactual, NOT a predicted random branch.

## Next crucial engine phase tasks

1. Obtain independent evidence for VCR chronological execution ordering before converting first-by-ID into pre-first-combat predictive guarantee.
2. Independently reproduce terminal damage/crew/clan attrition through combat replay rather than solving clans backwards from later observed mass.
3. Validate floor interpolation on additional games/hulls including partially-loaded Horwasp, negatives, and changed catalog masses, without calibrating on VCR residuals.
4. Keep carrier random +360 and SG phase separate; no production combat executor promotion.

## Single server command

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-mass-horwasp-tminus1-first-vcr-v1-with-evidence.sh

Report: artifacts/combat/mass-horwasp-tminus1-first-vcr-v1/published/report.json
Evidence: runtime-logs/combat-mass-horwasp-tminus1-first-vcr-v1/
Do not modify planets-intel, corpus CURRENT, or host executor.
