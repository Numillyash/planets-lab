# Mainline handoff — temporal mass reconciliation runtime failure and next research

Updated: 2026-10-10. Repository: Numillyash/planets-lab. Correct development branch: main. The parallel research/external-engine-analysis branch is **not** the mainline.

## Current issue and fix

PR #161 (commit b48eb0972c99ed259057b3271c33138ac5225907) merged, PR CI #1153 and main CI #1154 success. On the real server, command

    bash tools/run-combat-mass-temporal-reconciliation-v1-with-evidence.sh

FAILED with ValueError `cannot assert all-perspective agreement when truncated`; error handler then FAILED AGAIN with NameError because `sys` was not imported. Failure evidence:

    runtime-logs/combat-mass-temporal-reconciliation-v1/20261009T212402Z_b48eb0972c99

The source report `artifacts/combat/mass-capture-phase-controls-v1/published/report.json` has 14 selected pairs. Four game-turns (441148/T236, 653272/T132, 658427/T73, 658427/T87) have 30 source perspectives checked by original collector, but only 12 per-perspective details saved. In all four, the original, full-perspective `max_mass_changed_hulls` is 0 and summary status is `SAME_CHANGE_SET_ACROSS_AVAILABLE_TMINUS1_PERSPECTIVES`. These are valid *zero-change controls with upstream aggregate support*, not full per-perspective records. Treat truncation as safe ONLY with full aggregate zero, exact 12-detail cap, valid positive perspective count and all serialized rows empty. Nonzero truncated changes remain fail closed.

The fix adds `import sys`, guarded support for these four zero-change controls and an explicit output category `truncated_zero_change_static_controls`. Tests verify positive, negative and invalid source cases. This patch is observational only, not a static resolver, and DOES NOT prove all omitted per-perspective hull lists were independently rechecked in the postprocessor.

## Proven project research

Immutable public100 DuckDB:

    /root/projects/planets-corpus-db/generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb
    SHA256 3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

Never alter DB CURRENT. Server main checkout: `~/projects/planets-lab`. SSH GitHub via ssh.github.com:443. Research runtime Python: `/root/.cache/planets-lab/site-state-v1/bin/python`.

The 80-game 320-turn long mass survey covered 3912 ship-versus-ship VCRs / 7821 sides. Frozen digest recovered 67 residual VCR sides (40 unique game-turn-ship groups, 27 repeated). Original 52 non-Horwasp sides: 49 match official Shield Generator numeric bonuses (engine1 +1, engine5 +13, engine6 +27), two D19c cases need time-indexed 46KT instead of first-member 96KT, one Rush ship27 +150. The other 15 are Horwasp/clan cases; after temporal Brood hull117 125→145, five specific records have conditional full-load arithmetic. Never describe oracle-assisted mass fitting as genuinely generative Host prediction.

In 14 selected static-control game-turn pairs, six have changed hull mass compared with earliest static snapshot. Changes involve D19c hull1039 96→46, Brood hull117 125→145 and hull119 165→185. First D19c catalog change is seen at game217591 T1 and game325434 T33. Source T−1 owner perspectives agree in these investigations. Exactly seven of 67 original residual VCR sides intersect a changed hull: two D19c and five Brood. Four Brood sides have independent T−1 clans900/900, one has missing owner clans.

Rush #27 G617883 T201 same-site V1016 owner5 hull94 mass645 crew28, V1017 owner4 hull94 mass795 crew10. Original T200 owner5 snapshot engine9 Transwarp; owner4 T200 Saber#406 co-located at VCR site. 645+150=795. Capture and recompute of SG bonus are strongly supported candidates but terminal capture/result from independent battle replay has NOT been proven. T201 archive ship ID27 is Victorious hull35; do not attribute its engine9 to Rush. No production code changed.

Relevant source and evidence:
- `tools/diagnostics/combat_mass_capture_phase_controls_v1.py`
- `tools/diagnostics/combat_mass_temporal_reconciliation_v1.py`
- `tests/test_combat_mass_temporal_reconciliation_v1.py`
- `docs/handoff/2026-10-09-combat-mass-temporal-reconciliation-v1.md`
- `artifacts/combat/mass-capture-phase-controls-v1/published/report.json`
- `artifacts/combat/mass-residual-complete-v1/published/residuals.json`
- `runtime-logs/combat-mass-capture-phase-controls-v1/20261009T203109Z_2d7fbf7cb8fa`
- `runtime-logs/combat-mass-complete-residuals-v1/20261009T164712Z_614b20e04efe`

## Onboarding next chat and exact next steps

1. FIRST independently fetch GitHub main HEAD and latest PRs. Never blindly trust SHAs in this handoff. Confirm current fixes merged and GitHub CI green. User expects autonomous GitHub changes, PR, CI, fast-forward main and verification, not permission-seeking. Ensure actual implementation, not merely suggested diffs.
2. On server run:
   
       cd ~/projects/planets-lab
       git fetch origin && git switch main && git pull --ff-only origin main
       bash tools/run-combat-mass-temporal-reconciliation-v1-with-evidence.sh

   This reads existing local published JSON; no DuckDB scan. Check `runtime_evidence` *actual command success*, expected seven cases and six changed controls, and four audited truncated zero-change controls.
3. After V1 succeeds on real evidence, implement experimental **read-only time-indexed static resolver** at game/turn/owner perspective, strict no future leakage, explicit missing/conflicting states. Test held-out independent mass prediction with separate shields/capture/horwasp boundaries; do not promote to canonical database or production until evidence is sufficient.
4. Separately reconstruct Horwasp mutable clans and site combat terminal outcomes on a held-out path, never predicting from VCR N+1 mass.

Project rules: VCR current mass is a comparator, not model input. Facts/inferences must remain separate. Current site executor captures some branches observationally, other O/C and RNG mechanics fail-closed. No unverified full NuHost claim.
