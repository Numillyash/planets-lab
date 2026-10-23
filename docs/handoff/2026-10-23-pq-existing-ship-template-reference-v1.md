# PR #287 — within-window existing-ship base-template reference (exploratory)

Date 2026-10-23. Actual live evidence source from corpus host:
`runtime-logs/pq-appearance-correlates-control12-p1-first48-max8/20261023T124858Z_4dd63aa4cf59/artifacts/pq/surveys/control12-ppq-p1-first48-max8.json` on the separate GitHub `runtime-logs` branch, from main commit `4dd63aa4cf59cee05fa4be750e4953c2761f1b6b`, successful gate `exit_code=0`, no interrupted signal or missing artifacts.

## Confirmed results

Six preapproved completed public PPQ games of the frozen 12-game control set, player perspective1, first bounded eight source-qualified adjacent embedded turns per game: 58 archive-name-adjacent member pairs inspected, 48 strictly embedded delta +1 windows, 10 refused (5 repeats and 5 forward skips), 22 windows with one newly visible fresh own-ship ID each across five games. **17/17 eligible single-uniquely-fresh-base windows** have previous base's `buildhullid` and `buildengineid` equal to new-to-observation own ship's `hullid`+`engineid`; remaining **five** are `ABSTAIN_NO_UNIQUE_CURRENT_BASE`. The `player.prioritypoints` direction in the same 22 windows: **16 unchanged**, **6 increased**, **0 decreased**. For game 591478 five template matches and three site abstains, four PP increases; 621253 three template matches; 621896 two; 680435 two matches and two site abstains; 680910 five matches. Game 620917 yields zero eligible ship appearance windows in this bounded scope.

These are **real `CORPUS_OBSERVED` descriptive associations** on posthoc-selected windows, NOT 17 independently attributed Host builds, zero PP spend, or a model success score. PP can increase/hold even when ships genuinely build; unmeasured awards/sources or phase boundaries may explain this. Do not assert a PP spending formula from this observational sample.

## Why a reference group is useful

The 17/17 template match ratio can be a baseline artifact when one base's configured hull/engine is popular, unchanged over many turns, or matches previously built ships. A comparison with **existing persistent ships** on the same archive windows is required before treating it as specific evidence even at an observational level.

New `src/planets_lab/corpus/pq_existing_ship_template_reference.py` computes a privacy-minimal reference from two already approved `.trn` members:
- Only positive typed unique owner-current ship IDs in BOTH embedded consecutive snapshots qualify as persistent. The ship's *BEFORE snapshot* typed positive `hullid`/`engineid` is compared with the same BEFORE snapshot's single uniquely fresh planet-linked own starbase `buildhullid`/`buildengineid`. It does not compare a new ship with itself or require after-base configured templates.
- Both strata are included: window has new own fresh ship identity **or** does not have one, using all up to eight qualified existing survey windows per game, not only positive appearance ones. Counts per stratum: windows, typed persistent-ship template comparisons, matches, mismatches and persistent ships with untyped specs; fixed-category refusals for missing/duplicate ship source IDs, missing/ambiguous base, no persistent ship, untyped base or ship fields.
- **Within-game repeated ships can be counted on multiple overlapping windows.** These are counts of ship–window comparisons, not independent individual ships nor randomly selected negative controls. Some persistent ships may have been built previously and share the same template. Explicit `persistent_ships_are_independent_negative_samples=false` and `existing_ship_reference_is_independent_negative_control=false`.
- Immutable source owner scope, typed embedded ID+T delta gates and the six-game frozen control12/index remain unaltered. No raw ship/site/planet IDs, PP values, order values, ship templates, private strings or raw ZIP members emitted. Host-accepted order/phase/warehouse and causal flags remain false.
- Integrated under `existing_owned_ship_template_reference` in `src/planets_lab/corpus/pq_window_field_sufficiency.py`, and per-game+aggregate `existing_ship_template_reference_by_stratum` in `src/planets_lab/corpus/pq_control_multigame_observation.py`. Previous source-field and PP/template candidate reports unchanged.
- `tests/test_pq_existing_ship_template_reference.py` covers both strata, matched/unmatched persistent ship comparison, source/duplicate/no base/no stable ship/untyped abstentions, full synthetic archive+frozen-cohort pipeline and absence of private source data. Only `TESTED synthetic` until the corpus host publishes a real run for PR #287.

## One command on existing Docker corpus host

After exact final-head PR CI green, squash merge, verified `main` and successful postmerge CI:

```bash
cd ~/projects/planets-lab
git pull --ff-only origin main && bash tools/run-pq-existing-ship-reference-with-evidence.sh
```

This tracked launcher reuses the existing `tools/run-pq-control-multigame-gate.sh` and `tools/run-with-runtime-evidence.sh` for the exact same prebuilt Docker `lab` six-game frozen source and immutable privacy-minimal JSON/log publication on separate `runtime-logs`. It will publish to
`runtime-logs/pq-existing-ship-template-reference-control12-p1-first48-max8/<timestamp>_<mainSHA>/artifacts/pq/surveys/control12-ppq-p1-first48-max8.json`. User sends **no manual logs**, the assistant retrieves the immutable published report through GitHub.

## Next decision

Compare true observed existing-ship match/reference rates by stratum to the already verified 17/17 appearance-match ratio; avoid naive p-values/independence claims because overlapping windows and ship identity re-use violate iid. If existing-ship template matches are common, note the discovery is not discriminative. If rare, still only observational specificity, not Host accepted-order/PPQ mechanic proof. Field-name absence of direct hull/engine/beam/torp warehouses in 25 earlier base-row observations is not global warehouse absence. Independently authenticated NuHost orders, full before/after warehouses/PP/fleet and execution phase remain deferred in [issue #247](https://github.com/Numillyash/planets-lab/issues/247). Never open sealed M2 heldout32 or rebuild public100; `CURRENT` stays public68.

Every future PR must completely rewrite `docs/CONTINUE_HERE.md`, append own entry to `docs/PR_CHANGELOG.md`, update meaningful topic docs, verify exact PR CI/merge/post-merge main CI, and supply a one-command automatic `runtime-logs` publisher for new server research.
