# C5 V8 — T−1 plans versus AFTER-Host T owner-current endpoint observations

**Research only, no production promotion.** Source of truth
`Numillyash/planets-lab` `main`; do not switch to
`research/external-engine-analysis`, modify corpus CURRENT, or merge draft PR #28.

## Provenance and V7 result

Server evidence: `runtime-logs/combat-c5-pre-mine-route-counterfactual-v7/20261014T131437Z_f4e4ee81f93a`.
Verified source `f4e4ee81f93ab0ec170bed62636fb4c9f235a004`;
`exit_code=0`, SHA256-pinned public100 read only.

V7's twelve conditional no-hit T−1 routes all end at (2178,1105),
G421276 T115, owner 10. This is **one game-turn/site** and 12 model
evaluations; there was no independent comparison against Host's T owner
ship positions. The existing default risk still produces
`position=None` for all twelve. Zero new C5 pair forecasts.
219 same-window ordinary routes ended elsewhere and zero at the
site; these controls were model-internal only, not actual observations.

Pinned report Git blobs: V6
`51d21132e4db89511be59805ebe2be14014b3e7a`,
V7 `f551fc83b1725f7170aae210238ebae68c0e6eee`.

## Question and experimental cohort

We want to know whether the T−1 conditional no-hit endpoints agree with
the separately reconstructed T **post-Host** owner-current positions.
This is a differential, **NOT** proof of site-arrival membership before
combat or a mine-hit classifier.

Selection: the EXACT pre-published V6 frozen 27 combat sites / 21
game-turn windows, without choosing games or ships by T outcomes.
The 12 V7 risk witnesses are frozen by ship id and T−1 owner/site.
Control populations within EACH frozen game-turn window are selected
from all independent T−1 position estimates:

- `NORMAL_MINE_RISK_CONDITIONAL_NO_HIT`: original T−1
  `normal_mine_route_risk` position is None. The opt-in existing
  normal planner destination before the mine-risk mask is only
  *conditional on no mine interference*.
- `NORMAL_MODEL_NO_INDEXED_MINE_RISK`: existing resolved
  `normal_move*` T−1 position. This is a model-internal risk
  categorization, not proof that every foreign mine was excluded.

One ship per game/turn, regardless of how many battle sites occur in
that turn. Model outputs are frozen in memory before accessing T
owner-current observations. Afterward read only owner-current T archive
ships from the immutable compact public100 DuckDB. Keep missing/stale,
owner-changed, hull-conflict, missing endpoints and absent coordinates
as explicit abstentions.

The T archive represents a **later state after Host**. Movement,
capture, destruction, combat and other processing can intervene. An
exact endpoint match is `POSTHOST_ENDPOINT_MATCH` only. A mismatch
is not mine-hit proof, even on mine-risk paths. No factual N+1
VCR opponent or next-battle pair enters case selection or comparison.

Report denominators per cohort, per game and by game/turn clusters;
do not claim independence from per-ship counts. Record all twelve
V7 target post-host outcomes separately. Fail closed if the pinned
target cases are missing.

Known limitation: existing site builder uses the game's first static
catalog and topology reconstructed from archived settings; V8 is NOT
time-indexed static validation or a fresh holdout. Positional concordance
does not warrant promotion of combat executor or mine mechanics.

## Server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-posthost-endpoint-controls-v8-with-evidence.sh
```

Output:
`artifacts/combat/c5-posthost-endpoint-controls-v8/published/report.json`.

Evidence:
`runtime-logs/combat-c5-posthost-endpoint-controls-v8/`.

If the after-turn owner-current records are missing, report their
availability and stop short of causal conclusions. If there are
cross-game controls with positive observations, the next distinct
research task is pre-registered, held-out *movement* validation with
separate T−1 feature freeze and post-Host outcomes, not another
site-conditioned replay or an assumed mine-hit RNG rule.
