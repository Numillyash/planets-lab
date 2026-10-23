# PR #283 — frozen public PPQ owner-current observed transition signatures

Date: 2026-10-23. Actual independent evidence: `runtime-logs/pq-window-selection-g620917-p1-from1/20261023T103725Z_15f627933064/artifacts/pq/selection/game-620917-p1-from1.json`, reported by existing `tools/run-pq-window-selection-with-evidence.sh` at source `15f6279330645f4883453d9e34f8d2fa854236a3`. Source branch `main`; immutable evidence branch `runtime-logs`.

## Actual archived finding, not a synthetic prediction

Five accepted archive filename/embedded game.turn windows in the frozen approved game 620917, slot 1: 3→4, 4→5, 5→6, 6→7 and 7→8. Of seven inspected filename pairs, one embedded turn repeated and one skipped forward. Each before/after snapshot contains 80 visible planet rows and one visible starbase. In **all ten distinct per-turn base observations** (the five overlapping pairs share intermediate snapshots), `fresh_owned_planet_linked_bases=1`, `linked_owned_planet_bases_without_base_infoturn=0`, `owner_conflicts_with_planet=0`; direct base `ownerid` presence is ZERO but `infoturn` is present. Thus ownership via the unique fresh owning-planet link is **CORPUS_OBSERVED** and provides a real local source-field fix for previously unclassified bases.

`buildhullid` and hull/engine/beam/torp tech-level key names are present on the visible base; source-key **presence alone** does not reveal/verify actual accepted queue intention, typed component counts, PP ledgers or the server's selected base. Changing visible ship-row counts between turns may reflect other players/contacts and MUST NOT be interpreted as ship creation.

## Implementation

New `src/planets_lab/corpus/pq_observed_transition.py` exports `observed_owned_transition_signature`, used automatically in the current bounded source reader `src/planets_lab/corpus/pq_window_field_sufficiency.py` under `observed_owner_transition`; no new user command.

For each selected pair with already authenticated same game/player and consecutive typed **embedded turns**:

- Select planet/ship IDs only from visible rows carrying a unique, positive integer ID, owner exactly the approved perspective and a typed `infoturn` equal to each snapshot's embedded turn. Missing/stale/foreign owner, boolean IDs, duplicate IDs and unknown owner fields never fabricate owned fresh identity. Preserve an explicit unqualified/duplicate count.
- Select base site IDs via a unique positive typed `planetid` row anchored to one unique typed owned-current planet ID, with no contradictory base owner and **independent fresh base infoturn**. This is the same conservative provenance rule introduced by #282; a base's absent/stale `infoturn` cannot be promoted. Duplicated base/planet IDs make the source ambiguous.
- Intersect the two **private in-memory typed ID sets** to report only three counters for planets, bases and ships: `observed_in_both`, `newly_visible_owned_fresh_ids`, `no_longer_visible_owned_fresh_ids`, along with bounded source shape/qualification counters. Never include individual ship/planet/base identifiers, resource values, email, names, orders, buildhullid value, API secrets or source JSON.
- If a group array is missing or an identity is duplicated, report `ABSTAIN_AMBIGUOUS_OR_MISSING_SOURCE_ARRAYS`; otherwise `OBSERVED_OWNER_CURRENT_IDENTITY_INTERSECTION_ONLY`. These are *limited public perspective observed signatures*, not fleet completeness or Host causal event signatures. All `appearance_is_ship_construction_verified`, `disappearance_is_ship_loss_verified`, accepted orders, PP, warehouse, phase/Host parity and global completeness flags remain explicitly FALSE. Unknown/unqualified rows never get zero-as-a-fact.
- Reuse the exact frozen-control12 feature-index/allowlist gate and bounded 48-pair/5-window scanner, only reading the corresponding two selected .trn ZIP members per pair and no sealed M2 heldout32. Public100 26+ GiB is NOT rescanned or rebuilt, CURRENT remains public68.

Negative/synthetic tests: one ship visible on T but not on T−1 (not a build), stale ship `infoturn` (not fresh), ambiguous duplicate identifiers, missing arrays, absent/stale base freshness, boolean identifiers, nonconsecutive embedded turns, and payload secret-suppression. Those tests are `TESTED` only until the next real on-host run.

## How to obtain the first real T−1→T observational signatures

Once #283 passes exact final-head PR CI, merges and passes post-merge main CI, the corpus operator runs the already-installed **one-command** launcher:

```bash
git pull --ff-only origin main && bash tools/run-pq-window-selection-with-evidence.sh
```

Only public-safe JSON and logs are automatically published via `tools/run-with-runtime-evidence.sh` into the separate `runtime-logs` branch. User must not paste raw archival data or private fields. Assistant reads the newly published report from GitHub and reports actual ship/planet/base observed identity changes (not construction).

Next work should be a predeclared multi-game PPQ observational coverage aggregate and source-field sufficiency of *owner-current* starbase/ship/planet per-turn data, not an ungrounded queue mechanic parity claim. If the public archive has no independently accepted owner orders, full component warehouse/PP before/after and hostile effects, record ABSTAIN and park exact causal comparison in issue #247. Do not touch unrelated C5, production IntelBoard, signed V1/V2 orders or sealed M2 holdout.

Every PR must rewrite all `docs/CONTINUE_HERE.md`, append its PR-specific entry to `docs/PR_CHANGELOG.md`, update substantive handoff/ROADMAP, and verify exact-head PR CI, merge and post-merge main CI.
