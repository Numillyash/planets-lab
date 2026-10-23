# PR #285 — public six-game PPQ ship-appearance source-field sufficiency

Date: 2026-10-23. Source `src/planets_lab/corpus/pq_ship_appearance_fields.py`; integration in `pq_window_field_sufficiency.py` and `pq_control_multigame_observation.py`; tests `tests/test_pq_ship_appearance_fields.py`; server command `tools/run-pq-ship-candidate-fields-with-evidence.sh`.

## What actually happened in the public archives

The authorized frozen control12 multi-game operator run was published successfully as `runtime-logs/pq-control12-ppq-multigame-p1-first48-max8/20261023T121122Z_333a480ed93b/artifacts/pq/surveys/control12-ppq-p1-first48-max8.json`, originating from source `333a480ed93bd9f9ebcb95fa9bb5f9f1b2c173e3` on `main`.

The run genuinely tested six authorized completed PPQ games (591478, 620917, 621253, 621896, 680435, 680910), all player perspective 1, within a **predeclared** allowed control12 cohort. Exactly 58 filename-adjacent pairs inspected, ten refused (five embedded repeated, five embedded skipped-forward), 48 validated as strictly consecutive embedded turns and qualified for typed owner-current ID observations. Five games have newly visible owned fresh ship IDs; 620917 has none. Per-game observed ship identity **appearance event counts**, in the bounded eight accepted windows per game, are 591478:8, 620917:0, 621253:3, 621896:2, 680435:4, 680910:5 — 22 total, with four disappearance events. These are **not 22 Host ship builds**. Per-turn appearance IDs may be old IDs becoming newly visible or otherwise discontinuous. Global own-fleet completeness not proven. `ship_appearance_is_construction_verified=false` and `host_causal_verified=false`.

## New exploratory source-field audit

For a strict, source-qualified T−1→T archived pair, `source_fields_for_ship_appearance` derives private-in-memory typed fresh-owned ship IDs and their observed set difference, plus typed fresh-own planets and uniquely owned current starbases per the already conservative #282–283 gates. For each known fixed, allowlisted mechanical source key it reports ONLY counts of selected rows where the key is present and whether the value is typed nonnegative int, null or other/negative. Source values, ship/site IDs, names, coordinates, email, friendly codes, API/HMAC keys, raw orders and raw archival JSON are never emitted.

Field groups are:
- `before_owned_current_planets`, `after_owned_current_planets`: e.g. `megacredits`, `duranium`, `tritanium`, `molybdenum`, each tied to explicitly fresh-own planets.
- `before_owned_current_bases`, `after_owned_current_bases`: e.g. `buildhullid`, several possible build-part names, tech levels and `hulls/engines/beams/torpedoes`. **Key existence ≠ authenticated accepted queue order, and part field existence ≠ full warehouse contents**.
- `newly_visible_owned_current_ships`: `hullid`, `engineid`, beam/torp/fuel fields on strictly fresh owned new-to-observation ship IDs; this does **not** certify new construction.
- `before_perspective_player`, `after_perspective_player`: candidate PP field names (e.g. `prioritypoints`, `prioritybuildpoints`, `pbps`). No global owner PP audit or authenticity; player profile may omit those fields.

Fields with unknown/missing input are `null/missing/other`, not a default zero. Missing source arrays or duplicate own ship identity records yield `ABSTAIN_SOURCE_SHAPE_OR_IDENTITY`. The strict underlying archive parser still demands public game, frozen allowlist, exact perspective, typed embedded game/turn/player identity, consecutive embedded turns, bounded selected gzip/ZIP size; the new audit never relaxes any of these.

`pq_control_multigame_observation.py` now emits bounded `exploratory_ship_appearance_windows` per approved game, each with archive/embedded T−1/T, observed fresh own ship-appearance count and the source-field-presence counts. Only up to eight accepted windows per game can appear, and only those with nonzero additions get candidate records. **This is discovery on the same observations, not independent confirmation**, so `selection_type=EXPLORATORY_POSTHOC_OBSERVED_IDENTITY` and `posthoc_window_selection_not_independent_validation=true`. The per-window candidate reports remain bounded and free of entity IDs and private values.

All indicators remain FALSE for complete independent own ship roster, authenticated accepted shipyard build command, full component inventories, PP ledger, independent Host order acceptance, or NuHost build execution. Evidence remains `CORPUS_OBSERVED` for actual public source shape when the runtime run occurs, not `DIFF_VERIFIED` for PPQ formula/Host causal outcome. Independently accepted orders and full snapshots are still human-dependent issue #247. In particular, a typed `player.prioritypoints` field does not establish an independently validated PP ledger.

## How to run; no manual chat log copying

After PR #285 exact final-head green CI, squash merge and successful main push CI, the corpus host operator executes:

```bash
cd ~/projects/planets-lab
git pull --ff-only origin main && bash tools/run-pq-ship-candidate-fields-with-evidence.sh
```

This new **one-command** entrypoint reuses existing `tools/run-pq-control-multigame-gate.sh` and `tools/run-with-runtime-evidence.sh`, preserving exact same six games/48-adjacent-pairs max/8-admitted per game/prebuilt Docker lab, but publishes a new immutable evidence run under `runtime-logs/pq-ship-candidate-fields-control12-p1-first48-max8/<timestamp>_<SHA>/`. The sanitized report and logs go to separate `runtime-logs` even on ABSTAIN, never into `main`. The user need only say it ran; assistant reads GitHub evidence. No new archive downloads or public100 rebuild.

**Next research stage:** Use the real emitted source-key presence and qualified candidate turn windows to determine whether any authentic accepted queue orders and component warehouses/PP can be reconstructed from archived owner-current snapshots. If no independently attributable accepted orders exist, report explicit `ABSTAIN` and design narrowly controlled Host experiment under #247, rather than claiming a quantitative PPQ build-solver parity result. Avoid reading M2 sealed heldout32, altering public68 CURRENT or any production IntelBoard/C5.

Every next PR must fully rewrite `docs/CONTINUE_HERE.md` with its real PR number, append `docs/PR_CHANGELOG.md`, update technical handoff/roadmap, verify exact PR-head CI and postmerge main CI.
