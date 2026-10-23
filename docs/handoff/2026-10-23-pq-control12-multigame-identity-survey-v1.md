# PR #284 — multi-game frozen public PPQ owned-current identity survey

Date: 2026-10-23. New source `src/planets_lab/corpus/pq_control_multigame_observation.py`, CLI `tools/diagnostics/pq_control_multigame_observation.py`, tests `tests/test_pq_control_multigame_observation.py`, host launcher `tools/run-pq-control-multigame-with-evidence.sh` and its Docker gate `tools/run-pq-control-multigame-gate.sh`.

## Independent corpus checkpoint and reason to expand

The on-host source `runtime-logs/pq-window-selection-g620917-p1-from1/20261023T115343Z_705f8398f517/artifacts/pq/selection/game-620917-p1-from1.json`, source main SHA `705f8398f517bd85c6284a33d31810f2d9dc0f5b`, records five **embedded-consecutive** public game 620917 player1 windows (3→4 through 7→8) out of seven inspected adjacent filenames; one embedded repeat and one forward skip were refused. Unique typed fresh own-planet IDs per snapshot: 2→3→4→6→6→6. Precisely TWO unique fresh own-ship IDs remain in all six per-turn snapshots, with ZERO newly visible or no-longer-visible owned fresh ship IDs in the five windows. Precisely ONE unique planet-linked current starbase remains in all snapshots. This is **CORPUS_OBSERVED owner-identity persistence**: it neither proves shipyard inactivity nor validates PQ/PPQ construction (invisible ships and unrecorded accepted orders remain possible). All five are no-ship-appearance windows, so one must not extrapolate from them to an algorithmic building success rate.

## Strict bounded data collection

From the exact pre-existing `validation/corpus/manifests/pq-public-control12-frozen-cohort.v1.json` (12 public finished games, eight PPQ and four Classic controls), the existing prebuilt feature-index Parquet gate selects exactly the six `PPQ` `observational_candidate` games known from real metadata: `591478, 620917, 621253, 621896, 680435, 680910`. Nothing outside the frozen cohort can be accessed. Up to eight game IDs are allowed by the implementation cap, and the default host command has a fixed perspective=1, first filename turn=1, max 48 pairs/game, max 8 **strictly admitted consecutive embedded windows**/game, giving at most 288 examined filename pairs and at most 48 admitted windows. Other perspectives and turns are not opened beyond this bound. ZIP central-directory listing is not reading all members; only two preselected bounded `.trn` payload members at a time get decoded by the existing #279/#280 source identity verifier. The immutable ZIPs, game cache, public100 and CURRENT are untouched.

A per-game and aggregate report contains only the number of archive-adjacent windows checked, actually admitted embedded-consecutive windows, source-qualified owner-fresh entity windows, counts of owner-fresh ships/planets/bases present on both turns, newly visible and no longer visible IDs, unknown/unqualified source row counts, base-planet owner provenance counts, aggregate refusal reasons, and explicitly missing/unreadable game archive buckets. It does **not** emit individual ship/planet/base identifiers, private values, messages, codes, emails or raw orders. The same in-memory entity ID may appear across multiple *overlapping windows*, so sums across windows are **counts of per-window identity transitions**, not unique ships built over an entire game.

All security/evidence sentinels are fixed false: `independently_complete_owner_ship_roster`, `ship_appearance_is_construction_verified`, `ship_disappearance_is_loss_verified`, `planet_gained_is_colonization_verified`, `queue_component_warehouse_and_pp_verified`, `server_accepted_orders_verified`, `host_causal_verified`. A newly visible owned fresh ship is a *candidate for investigating actual transition events*; without authenticated accepted shipyard order/BOM, full fleet snapshots, hidden contacts, PP/warehouse and Host boundary it is NEVER labeled a constructed vessel. Real DIFF_VERIFIED Host parity still needs issue #247. All source structural ambiguity is classified/abstained rather than reinterpreted as zero effects.

## One-command on-host run, automatic GitHub evidence

**After** exact final-head PR CI success, squash merge and post-merge main CI success:

```bash
cd ~/projects/planets-lab
git pull --ff-only origin main && bash tools/run-pq-control-multigame-with-evidence.sh
```

The tracked launcher invokes existing `tools/run-with-runtime-evidence.sh` to execute the tracked bounded Docker gate using the **prebuilt** `lab` image (no dependency rebuild) and publish only the privacy-minimal JSON + full sanitized capture/stdout/status into the separate immutable `runtime-logs` branch, including a failure/ABSTAIN run. The report is local `artifacts/pq/surveys/control12-ppq-p1-first48-max8.json`, GitHub remote evidence prefix `runtime-logs/pq-control12-ppq-multigame-p1-first48-max8/`. The user is never asked to paste stdout or files manually; assistant reads evidence via connected GitHub.

Unit/integration tests include an actual small synthetic ZIP + precreated feature-index/frozen cohort, one fresh ship identity appearance that **must not** become a claimed build, privacy suppression, explicit missing archives, invalid scope, deterministic serialization and shell syntax. These tests are `TESTED conditional` until the on-host six-game report is actually published. No claim of full corpus-parity or verified PPQ formula is made merely from green CI.

## Next research once runtime evidence exists

1. Read the newest `runtime-logs` report after the host's single command, count observed ship appearance candidate windows *per game*. Select bounded, predeclared candidate windows with nonzero fresh ship identity additions and plan exactly what additional server-supported evidence would distinguish a build from a contact, capture, recycle or rebuilt ID.
2. For each candidate, run a source **field sufficiency gate** on unique fresh-owned starbases/planets/ships: which planet cargo stock, current `buildhullid` intent, own PP, component warehouse and constructed ship build specs are actually available in the immutable public archives? Presence does not authenticate accepted orders. Unknown → explicit ABSTAIN and persist aggregate evidence via a new one-command wrapper.
3. Attributable PPQ external Host behavior (fractional Stage2/Stage3 randomness, actual chosen queued base, accepted order, phase placement) cannot be claimed without independent Host data per #247. Keep public68 CURRENT, public100 26+GiB prepared immutable, M2 heldout32 sealed; do not touch unrelated C5/combat, IntelBoard production or signed V1/V2 PlayerOrders.

**Per PR #262:** In every subsequent PR, fully rewrite the entire `docs/CONTINUE_HERE.md` with the real PR number, append `docs/PR_CHANGELOG.md`, modify substantive handoff/roadmap, check exact-head PR CI, merge on success, then verify actual main and post-merge CI.
