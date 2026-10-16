# M2 differential completed — cross-family evidence gate (bounded posthoc)

## Full M2 server evidence verified

`runtime-logs/planetary-historical-differential-v1/20261016T175520Z_f2f70dc46528`
source `f2f70dc46528ccc3695b62bd8fd0b39fa60067dc`,
clean, `exit_code=0`, no missing artifacts, all 4 reports + manifest.

Pinned exact published Git blobs:
- manifest `c2d95b1c50d89895a30497f0008c0e0f486d12ef`
- supplies `984f481fdafcd797aa388fb14557d22962021675`
- taxes `fd28daed75e486f3f9c19e125009c589f03ac9a5`
- minerals `638de25e2417e07bcd3a8ab8be3cf0acb3b046d4`
- populations `e3dcc585ca5d00617136069e8d8060e2618296a1`.

Provenance game-disjoint public8 corpus SHA256
`af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a`.
32 metadata-frozen adjacent windows; 650 source owner-current
planet observations; same 33 abstentions in every family
(16 unsupported models, 5 owner changed, 11 G608293/T2
identity-untrusted T rows, 1 owner-current missing);
617 qualified conditional comparisons each. Exact T **net stocks**
by family: supplies 312, MC 358, eight mineral fields 440,
two population fields 481. These are NOT causally isolated
production, taxation, extraction or growth observations.

## Why this step is limited and useful

Independent read-only join of all four original outcomes by
exact game/turn/planet/owner/race, NOT separate per-family accuracy
cherry-picking. Two important previously unseen joint facts:

- Of 617 qualified planet observations **215 match all four
  stock families together** across 26 game-turn windows, not
  215 independent Host mechanical proofs.
- Underground mineral stocks match all four on **592/617**
  observations. Mineral stock divergence is mostly **surface only**
  (152), compared with 3 ground-only, 22 both surface and ground.
  This indicates surface cargo/production/order balance is a
  high-value integration gap; it does NOT prove the exact cause.

`src/planets_lab/sim/planetary_evidence_gates.py` provides a
reusable integration-safe, fail-closed evidence join:
- no silently dropped or duplicate planet IDs,
- immutable source Tminus1 and archive T delta arithmetic reconciled,
- exact/mismatch labels checked against numeric model/archived states,
- fully abstained cases never counted as mechanism failures,
- separate stock residuals and causal claims (always false).

`tools/diagnostics/planetary_evidence_triangulation_v1.py`
checks complete pinned Git blobs, original published manifest
SHA256 membership and exact 650/617 and 32-window denominators.
Outputs THREE independent measures in ONE evidence invocation:
- `joint_controls.json`: four-family exact and mismatch signatures,
  same 650 planet/time IDs and game-turn clusters, 215 full matches;
- `resource_balances.json`: mineral surface vs ground quadrant,
  MC/supply coupled divergences and frequent signed net-stock
  residual magnitudes, NOT assumed transfers or purchases;
- `population_balances.json`: colonist/native residual categories,
  common signed discrepancies, NOT assumed growth/tow/assimilation.

`manifest.json` includes SHA256 each report.

No new corpus, no extra NuHost archives, no Host rule promotion.
This is bounded posthoc analysis for planning the **next implementation
slice**, not a new validation experiment and not an excuse for
30 more micro-experiments.

## Subsequent implementation priorities

1. Preserve owner-current input and error model; avoid fitting
   arithmetic constants to confounded net-stock residuals.
2. Integrate explicit building/ship-cargo orders into deterministic
   state transitions when source orders are trustworthy.
3. Add real filtered subcohort tests that can exclude such
   operations, then validate extraction/growth formulas externally.
4. Stop M2 diagnostics after this bundled attribution checkpoint
   and make changes to the actual planetary simulation or full
   Host inter-phase integration.

C5 remains frozen, and production `planets-intel`,
original public100/new public8 DB, CURRENT, PR #28 and
external-engine branch are unchanged.

## One exact server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-evidence-triangulation-v1-with-evidence.sh
```

No database hash/disk IO: read only the published four M2 JSONs
and manifest, then output
`artifacts/planetary/evidence-triangulation-v1/published/`
with evidence under
`runtime-logs/planetary-evidence-triangulation-v1/`.
