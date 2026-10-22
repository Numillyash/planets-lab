# PR #282 — real PPQ starbase source ownership/freshness observability

Date 2026-10-22. Independent published runtime evidence:
`runtime-logs/pq-window-selection-g620917-p1-from1/20261022T185133Z_412db3d34b32/artifacts/pq/selection/game-620917-p1-from1.json` on branch `runtime-logs`. Source commit `412db3d34b3276c778a7f530a8426441e74685c5`.

## What was actually seen

User ran `bash tools/run-pq-window-selection-with-evidence.sh` in the corpus Docker host. The published sanitized report states `actually_checked_pairs=7`, `admissible_consecutive_embedded_pairs=5`, `EMBEDDED_TURN_REPEATED=1` and `EMBEDDED_TURN_SKIPPED_FORWARD=1`. All five accepted filename+embedded pairs are **3→4, 4→5, 5→6, 6→7 and 7→8** for frozen approved game 620917, perspective slot 1. The five reports carry array shapes with visible 80 planets and one visible starbase, while the *direct* starbase `ownerid+infoturn==embedded_turn` classification found **zero** bases in that perspective. Visible ship row counts change; that is not evidence of regular builds, since contacts/visibility/confounders are uncontrolled.

The canonical `src/planets_lab/data/nu_loadturn.py::_starbase` importer already legitimately falls back to the owner of the base's anchored planet when the starbase record itself has no owner. The old shape-only probe did **not** distinguish such a link. Without additional provenance, reporting zero *direct owner-current* bases is true but may hide structurally linked bases; reporting all visible bases as current would also be unjustified.

## New strict field gate

`src/planets_lab/corpus/pq_starbase_observability.py` adds independent `starbase_owner_provenance`, plugged into `pq_window_field_sufficiency.py` as `starbase_provenance.before/after` (thus automatically present in #281 bounded selector's per-window reports).

For a planet-to-starbase link to qualify as current-owner evidence, demand all of:
- one unambiguous **typed** base `planetid`/alternate `planet_id` and unique visible base with that planet ID;
- one unambiguous visible planet record with the same typed ID and positive typed `ownerid` or `owner_id`, plus `infoturn == embedded turn`;
- planet's owner equals caller-approved perspective; any explicit base owner must not contradict the planet's owner;
- to count the **base record itself as fresh**, typed base `infoturn == embedded turn`. If absent, record separately **linked ownership but unverified base freshness**, not as a current buildable base. If stale or malformed, record in another failure bucket.

Also count owner conflicts, duplicate planet/base mappings, missing arrays and unresolved aliases as UNKNOWN/ABSTAIN rather than assigning owner/default. A fixed allowlist of **key presence counts only** (`planetid`, `ownerid`, `infoturn`, `buildhullid`, tech-level names, `hulls`/`engines`/`beams`/`torpedoes`) clarifies observed source shape; never include any values, IDs, names, codes, secret keys or private orders. Field presence is not proof of a filled warehouse or command.

`fresh_owned_planet_linked_bases` is thus **only a conditional source-row temporal/link qualification**, never authenticated global fleet/base completeness, accepted build intentions, Priority Point arithmetic, build rights, warehouse availability or real NuHost selection. Both `warehouse_and_queue_complete` and `independent_host_owner_freshness_verified` are always false.

Synthetic adversarial tests include known fresh linked bases, base owner omission, missing/stale base infoturn, contradictory owner, duplicate planet/base identifiers, malformed types, missing arrays, private field injection and real two-member synthetic integration. This tests the *gate*, not yet the actual missing-field explanation in game 620917.

## Next operator run and proof boundary

After exact-head PR CI success, merge and post-merge main push CI, the **same** tracked one-command automatic evidence launcher suffices:

```bash
git pull --ff-only origin main
bash tools/run-pq-window-selection-with-evidence.sh
```

This is a rerun, not an invitation to publish any raw `.trn` or copies of private owner orders. The wrapper saves only sanitized report and log to `runtime-logs` under a source-SHA-bearing immutable run. The assistant retrieves that report using connected GitHub without asking the user to copy terminal output.

Interpret actual new counters: if own-planet-linked bases without base infoturn are nonzero, they are owner-linked **not current**; if raw base `buildhullid` key appears, it means key presence only, not a confirmed queued order. If no compatible planet link appears, record explicit insufficiency; do not weaken owner tests.

The existing selection of 6 approved PPQ games is frozen. No broad public100 rebuild, M2 sealed heldout32 records, alteration of `CURRENT` public68, unrelated C5/production IntelBoard or signed V1/V2 orders. Real accepted Host orders/PP/component inventories and causal phase attribution remain blocked by issue #247.

Per PR #262, the current PR must rewrite the entire continuation prompt, add its own changelog, substantive handoff and roadmap before exact HEAD green CI, merging and checking main push CI.
