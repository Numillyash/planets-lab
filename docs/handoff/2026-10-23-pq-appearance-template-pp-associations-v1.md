# PR #286 — exploratory public PQ/PPQ ship-template and PP trend associations

Date: 2026-10-23. Current source of independent, already published runtime facts: `runtime-logs/pq-ship-candidate-fields-control12-p1-first48-max8/20261023T123217Z_cfc651f1106c/artifacts/pq/surveys/control12-ppq-p1-first48-max8.json` on separate `runtime-logs` branch. Origin code SHA `cfc651f1106c5150d7917a5e9709f7d92e4313f7`, source branch main. Published metadata `exit_code=0`, `interrupted_signal=null`, `missing_artifact_paths=[]`; the user's extra `^C` after the JSON line did NOT truncate the published gate/artifact and **the previous command must not be rerun to repair anything**.

## Actual field evidence from published JSON

Frozen 12-game public control cohort only; six approved PPQ games, perspective 1, 58 filename-adjacent pairs inspected, 48 owner-current typed embedded consecutive pairs, 10 refused (5 embedded repeated turns, 5 forward skips), and 22 appearance windows (one new own-fresh ship identity event per candidate window in this sample) across five games: game 591478=8, game 620917=0, game 621253=3, game 621896=2, game 680435=4, game 680910=5. Selection is *exploratory and posthoc* on these same T−1→T windows, not an independent blinded test or a proof of 22 completed builds.

Across these 22 candidate windows (source rows may be counted repeatedly where archives overlap):
- 22 of 22 observed new current-owned ship rows have **typed nonnegative integer `hullid` and `engineid`**.
- 22 of 22 have **typed nonnegative integer `player.prioritypoints`** at both endpoints. That is a visible source field, NOT an independently validated PP ledger.
- The 22 windows collectively observe 25 current-owned qualified starbase rows BEFORE the turn; **all 25** have typed nonnegative `buildhullid` and `buildengineid`. These are snapshot configuration fields, NOT authenticated server-accepted build orders. Multiple current bases in one perspective make selecting the exact building base ambiguous.
- Direct candidate base source keys `hulls`, `engines`, `beams`, `torpedoes` are present in **0 of these 25 source rows**. This is *absence of four checked key names*, not proof that true source component warehouses are universally absent (other structures/schema may hold them). Pre-turn current-owned planets have typed `megacredits`, `duranium`, `tritanium`, `molybdenum` in 112/112 source row observations. Values of resource/PP/ship IDs never left the corpus host.
- Prior runtime report `runtime-logs/pq-control12-ppq-multigame-p1-first48-max8/20261023T121122Z_333a480ed93b` established 48 qualified windows and 22 fresh-own ship appearance events; the new report proves the source-key availability of the *posthoc* cases, not Host event attribution.

## New conservative conditional *correlate*, not a Host solver

New `src/planets_lab/corpus/pq_ship_appearance_correlates.py` exposes `appearance_correlates` on the already validated pair. It builds only private ephemeral source-qualified owner-current own-ship ID sets; compares **one** newly visible current-owned ship (if and only if exactly one exists) against **one uniquely qualified fresh owned starbase** from the BEFORE snapshot. If exactly one base was independently fresh with no extra visible competing starbase and typed positive hull/engine IDs, report one of categorical `OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH`, `OBSERVED_HULL_ONLY_ENGINE_MISMATCH`, `OBSERVED_ENGINE_ONLY_HULL_MISMATCH`, or `OBSERVED_HULL_AND_ENGINE_MISMATCH`. If multiple/newly-visible ships or possible base sites, stale/unknown/missing order keys, or duplicated ship identities, report an explicit `ABSTAIN_*` or `NO_NEW_OWN_CURRENT_IDENTITY`. This does not imply the base is the historical actual builder. Its `buildhullid`/engineid may be stateful UI settings, no server acceptance is authenticated.

Independently compare the already permitted embedded perspective `player.prioritypoints` typed nonnegative integer **before vs after** and output ONLY category `PP_INCREASED`, `PP_DECREASED`, `PP_UNCHANGED`, or `UNKNOWN_PRIORITYPOINTS_SOURCE`/`ABSTAIN_PLAYER_IDENTITY`. No actual points/deltas or owner names/ship IDs are emitted. PP direction alone cannot attribute any spending because other events/awards are unobserved.

Integration:
- `src/planets_lab/corpus/pq_window_field_sufficiency.py` adds `ship_appearance_noncausal_correlates` to the already frozen, approved two-member source reader.
- `src/planets_lab/corpus/pq_control_multigame_observation.py` attaches `observed_before_base_template_and_pp` to ONLY existing exploratory candidate windows, adds per-game and aggregate categorical histograms. Retains `posthoc_window_selection_not_independent_validation=true` and all causal verification flags FALSE.
- `tests/test_pq_ship_appearance_correlates.py` unit and archive synthetic integration tests check compatibility states, stale/missing/multiple IDs or bases, PP sign and no raw output. `tools/run-pq-appearance-correlates-with-evidence.sh` provides one short on-host bash command, reusing unchanged `tools/run-pq-control-multigame-gate.sh`, prebuilt Docker lab, frozen allowlist/index and existing `tools/run-with-runtime-evidence.sh`, publishing safe JSON + log/status to separate `runtime-logs`. Existing six-game scope maximum 48 filename pairs / 8 accepted per game remains; never touch sealed M2 heldout32, public100 or CURRENT public68.

All flags **always remain false** for accepted orders, Host build execution, component warehouse / BOM completeness, unique own fleet coverage, phase ordering, and PP spending attributable to that ship. A dual hull/engine match + decreased PP is only an **exploratory association**, NEVER a causal proof. This new code is `TESTED` on synthetic data until the host publishes a real #286 run; actual field counts above are `CORPUS_OBSERVED` from the previous #285 run.

## Operator command after exact-head PR CI success, merge, and post-merge main CI

```bash
cd ~/projects/planets-lab
git pull --ff-only origin main && bash tools/run-pq-appearance-correlates-with-evidence.sh
```

Do not re-run the #285 command, or paste terminal logs manually. The new run is immutably published in `runtime-logs/pq-appearance-correlates-control12-p1-first48-max8/<timestamp>_<sha>/`, and the assistant reads the sanitized aggregate from GitHub itself. No private ship/base/planet IDs or raw values are saved.

## Next scientific choices

Evaluate the *actual observed categorical associations* from the #286 run and identify whether any before-template/ship match with PP decreases exists in source-qualified windows. If no warehouse/source accepted orders, stop at `CORPUS_OBSERVED` associations; controlled independently authenticated Host input under issue #247 is still required for `DIFF_VERIFIED` PQ/PPQ build selection. Next code can be a bounded source identity collision/temporal construction feasibility gate that emits only count categories without releasing raw data; do not label match + PP spend as a Host build. Maintain per-PR full continuation, PR_CHANGELOG and topical docs, exact final PR CI, then merge and verify postmerge push-main CI.
