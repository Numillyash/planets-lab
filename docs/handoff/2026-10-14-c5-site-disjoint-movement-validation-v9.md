# C5 movement-validation V9 — site-disjoint metadata-only cohort

Repository: `Numillyash/planets-lab`; branch `main`.
Not an executor promotion, not new standalone Host mechanics.
Separate external-engine research, production `planets-intel`, and
draft PR #28 must remain untouched.

## Frozen V8 source and observational result

Published evidence: `runtime-logs/combat-c5-posthost-endpoint-controls-v8/20261014T134303Z_fc4f26521768`.

Confirmed GitHub metadata: exit_code=0, original main
`fc4f26521768bb1473d81d2f98bae185ad0d1fa3`.
V8 uses pinned immutable public100 DB read-only, 27 sites, 21 windows.
Owner-current post-Host position comparator:

- `NORMAL_MINE_RISK_CONDITIONAL_NO_HIT`: 401 matches, 2 mismatches;
  9 owner-current absent, 9 owner drift; 10 game-turn clusters.
- `NORMAL_MODEL_NO_INDEXED_MINE_RISK`: 2598 matches,
  24 mismatches, 20 owner-current absent, 20 owner drift and
  3 hull drift; 12 game-turn clusters.
- Original frozen V7: 3 matches, 7 owner drift, 2 unknown.
  These seven owner changes are NOT automatically assigned to capture.
- Four windows had missing T-1 site-context reconstruction and must
  be carried as an explicit denominator loss.

V8's scores are conditional on existence of a stable owner-current T
record. T state is post-Host, not necessarily precombat; no causal
mine-hit or site-arrival conclusions.

## V9 preregistered selection

Source metadata `source_members(game_id,archive_turn)` from pinned
public100 only. First exclude **every game** in frozen V6 27-site
C5 census. Among remaining games with >=2 adjacent archive pairs,
choose 8 evenly across sorted game IDs. Select 2 archived adjacent
turn pairs per game at deterministic 1/3 and 2/3 positions.
Selection reads NO VCRs, ship coordinates, T results, or outcomes.
Freeze this list before loading T-1 ship observations.

For each window, build exact T-1 owner-current ship roster.
Exact T-1 static hull and engine catalog must agree between
available perspectives; missing/conflicting catalogs are abstentions.
Map topology, warp wells, fuel movement, storms, minefields, race,
friendly code and Tow/Chunnel guards come only from T-1.
No post-T snapshot, current/future archive setting or VCR is input
to forecast construction.

Reuse the existing normal-movement planner. If its normal endpoint
exists, split into two cohorts based on the independent T-1 foreign
mine-route intersection risk:

1. `NORMAL_MINE_RISK_CONDITIONAL_NO_HIT`: mine-risk route with normal
   planner endpoint *conditioned on the absence of mine interference*.
2. `NORMAL_MODEL_NO_INDEXED_MINE_RISK`: resolved normal planner
   endpoint with no registered foreign-mine route risk. This is NOT
   guaranteed mine-free.

Other movement types (Tow, Sphere, Chunnel, special, unresolved)
are excluded with explicit source/reason counts; no claim is made
about them.

After calculating ALL T-1 window forecasts, read owner-current T
archives strictly for endpoint comparison and preserve abstentions
for absent/stale records, identity/hull changes, missing endpoint,
etc. Report per-game and game-turn denominators rather than counting
every ship as an independent replication.

This V9 is **site-game-disjoint** from C5, but uses the SAME earlier
studied public100. It is not a freshly collected independent corpus
and is not prospectively validated. There is no mine-hit RNG or
precombat Host-position oracle. Exact endpoint match does not
prove the absence of combat or a mine hit.

## Command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-site-disjoint-movement-validation-v9-with-evidence.sh
```

Report: `artifacts/combat/c5-site-disjoint-movement-validation-v9/published/report.json`.
Evidence: `runtime-logs/combat-c5-site-disjoint-movement-validation-v9/`.

## Acceptance

- SHA256-pinned external DB, never edit `CURRENT`.
- 8 games / 16 metadata-only windows, no overlap with frozen C5 games.
- At least 4 windows and 100 independent precomputed normal endpoints
  survive uncertainty gates, otherwise no success report.
- All T-1 predictions frozen before ANY post-Host T comparison.
- Per-game/per-window match, mismatch, unavailable, identity drift counts.
- No VCR N+1 use or combat executor promotion.

Further work: if cross-game independent (site-disjoint) evidence
remains supportive, select a truly new unstudied external game set,
pre-register mechanic tests and evaluate mine-hit evidence separately
rather than interpreting counterfactual no-hit concordance as a
reconstruction of NuHost's random mine-hit behavior.
