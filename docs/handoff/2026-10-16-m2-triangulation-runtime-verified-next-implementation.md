# M2 V1 historical economy + triangulation — verified runtime; handoff to implementation

> Repository: `Numillyash/planets-lab`. Canonical branch: `main`.
> Verified latest implementation source before this handoff:
> `ab80e84d4c23ca4190f1a73c5d071e65cc8aa5e5`.
> PR #206 (Planetary Cross-Family Evidence Gates) was merged,
> PR CI #1259 and main CI #1260 passed.
> Never switch to `research/external-engine-analysis` in this workflow.
> Do not merge draft PR #28 or modify production `Numillyash/planets-intel`.

## Verified evidence and exact provenance

The three-report batch ran on the server and **succeeded**.

- Run: `planetary-evidence-triangulation-v1`
- Source commit/branch: `ab80e84d4c23ca4190f1a73c5d071e65cc8aa5e5` / `main`
- Evidence branch: `runtime-logs`
- Evidence path:
  `runtime-logs/planetary-evidence-triangulation-v1/20261016T180738Z_ab80e84d4c23`
- Evidence metadata: `exit_code=0`, `source_dirty=false`,
  `missing_artifact_paths=[]`, published requested artifacts.
- Published data source:
  `artifacts/planetary/evidence-triangulation-v1/published/`
- Published Git blobs:
  - `manifest.json` `2cb21baad9a78bf9422149dedac66a946484e4d3`
  - `joint_controls.json` `17644f51d00c0954e446eea3d6c4dfdf89dd2189`
  - `resource_balances.json` `d090a4e1f080fbb773dadee119c832b843121c4b`
  - `population_balances.json` `f22d70105cd9bb9a2b5d04b2af6239436f887af0`
- `manifest.json` pins all three report SHA256 hashes.
  Never replace exact Git blobs with mere unverified filenames.

These reports consume previously published M2 archive comparison JSONs:
`runtime-logs/planetary-historical-differential-v1/20261016T175520Z_f2f70dc46528`;
original historical comparison was successful after strict archive
identity fail-closed handling (source `f2f70dc46528ccc3695b62bd8fd0b39fa60067dc`,
`exit_code=0`). This triangulation makes **no additional corpus
scan**, no new T-1/T prediction and no new independent Host measurement.

## What was established (OBSERVATIONAL, not causal)

Same 8 newly acquired public archival games and 32 metadata-selected
adjacent T−1/T windows. Original comparison: 650 T−1 owner-current
planet rows, 617 conditionally qualified, 33 abstentions per family
(16 unsupported models, 5 owner changes, 11 identity-untrusted
G608293/T2 T-archive rows, 1 T owner-current missing).
There are 31 surviving source game-turn clusters in the triangulation;
not every one of 32 windows yielded a trusted T comparison.

The four original conditional net-stock comparison counts:

| Family | Full-field exact | Full-field mismatch | Denominator |
| --- | ---: | ---: | ---: |
| Supplies | 312 | 305 | 617 |
| MegaCredits | 358 | 259 | 617 |
| Surface + underground minerals (8 fields) | 440 | 177 | 617 |
| Colonist + native clans (2 fields) | 481 | 136 | 617 |

After joining the EXACT same game, turn, planet, owner and race
identities across all four published source reports:

- `215 / 617` conditional whole-planet matches on **all four families**
  simultaneously; `402 / 617` differ in at least one family.
  `26` distinct game/turn windows contain at least one full match.
- Mineral quadrants: `440` all eight fields exact,
  `152` surface-only difference, `3` ground-only difference,
  `22` both surface and ground differ. Thus `592/617`
  have all four underground mineral fields matching.
- Supply vs MC cross-class: both exact `241`; supply exact/MC
  mismatch `71`; supply mismatch/MC exact `117`; both mismatch `188`.
- Supply observed-minus-modeled residual: `0:312`, `-1:42`,
  `-2:22`, `-4:20`, `-200:14`, etc. Values are **net-stock
  residuals**, not independently observed factory events/transfers.
- MC observed-minus-modeled residual: `0:358`;
  remaining differences include both small and large magnitudes.
  Not evidence of a specific tax formula error.
- Population quadrants: both clan fields exact `481`,
  colonists-only differ `101`, natives-only differ `29`,
  both differ `6`.
  Individual signed colonist residual `0:510`, `-1000:20`,
  `-100:7`, `-200:5`; native residual `0:582`, `+1:28`.
  Exact families can coexist with individual field differences.
- **No** causes of differences have been conclusively attributed to
  explicit player orders, cargo transfers, purchases, building,
  reproduction, production, racial mechanics, or Host phase order.
  No new formulas or mechanisms have been promoted into production.

Scientific status: `M2_HISTORICAL_STOCK_RESIDUALS_ATTRIBUTION_UNPROVEN`.
Do NOT describe the ratios above as four components being causally
verified against NuHost. Do NOT choose examples *after* seeing T results
and call them new holdout predictions.

## Code checkpoint

Completed, merged and CI-green PR #206 added:

- `src/planets_lab/sim/planetary_evidence_gates.py`:
  strict four-way evidence join by historical identity, stock delta
  reconciliation, fail-closed incompleteness checks and partitioned
  residuals.
- `tools/diagnostics/planetary_evidence_triangulation_v1.py`:
  read-only comparison of pinned published JSON reports.
- `tests/test_planetary_evidence_triangulation_v1.py`.
- `tools/run-planetary-evidence-triangulation-v1.sh` and
  `tools/run-planetary-evidence-triangulation-v1-with-evidence.sh`.
- `docs/handoff/2026-10-16-m2-archive-evidence-triangulation.md`:
  original pre-runtime method/interpretation.

Canonical M2 simulation is **already present**:
`src/planets_lab/sim/planetary_host_pipeline.py`
(`PlanetaryHostPipeline`, implemented relative order of 13
planetary phases; incomplete NuHost coverage). Avoid rewriting or
duplicating those phases for a second implementation.

Also **already present**:
`src/planets_lab/sim/planet_cargo_transfer_phase.py`
(`PlanetCargoTransferPhase`, includes guarded bidirectional
ship↔planet transfers, cargo and fuel capacity, some colonization),
`src/planets_lab/sim/orders.py` (`TurnOrders`,
`ShipOrder`, `PlanetCargoTransferOrder`), and
`tests/test_planet_cargo_transfer.py`.
This transfer phase is presently **separate** from the
`PlanetaryHostPipeline` phase tuple and requires static hull specs.
Extend/integrate what exists; DO NOT invent a parallel transfer
implementation. Do not assume precise NuHost chronology solely from
current code structure.

## NEXT TASK (implementation, NOT another residual-only run)

Deliver the smallest **order-aware planet transition slice**,
starting with existing `PlanetCargoTransferPhase` and its explicit
`TurnOrders`, then scope building/purchases as separate order models
only when evidence warrants their real Host phase boundary.

Recommended sequence:

1. Inspect current main HEAD, pending PRs and code;
   keep `main` sole source of truth.
2. Implement a **composable research-only HostEngine pipeline** that
   integrates existing cargo-transfer phase with the existing ordered
   `PlanetaryHostPipeline` without changing canonical production
   combat or silently claiming exact NuHost phase timing. Make
   any phase placement an explicit tested assumption, not a fact.
3. Add **deterministic, multi-turn scenario tests** with real
   `TurnOrders`: planet→ship load, ship→planet unload, cargo
   conservation, capacity/fuel/ownership failure, interactions
   with mining, factory supplies and taxation, input-state immutability,
   and explicit fail-closed unsupported transfers.
4. Add explicit pre- and post-transfer balance snapshots/event
   accounting. HostEvents and independently identifiable inventory
   deltas should separate modeled transfers from economy-phase
   production; do not infer undisclosed player orders from T residuals.
5. Build one server wrapper and one evidence report, with reproducible
   scenario results and limitations. Use PR → CI → merge main →
   main CI, then provide **one exact server command**.
6. Only AFTER the vertical slice, plan a bounded new historical
   comparison where independent source orders can be authenticated.
   Unknown orders/transfers/phase order = abstain, not heuristic match.
   Stop after acceptance; do not start another V2–V27 diagnostic loop.

Important scope: no mission to explain every one of 402 mismatches
immediately. The priority is real inter-phase integration and an
end-to-end runnable partial Host state transition.

## Technical environment and safety

Server checkout `~/projects/planets-lab`.
Existing immutable public8 DuckDB:
`/root/projects/planets-corpus-db/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb`
SHA256 `af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a`.
Corpus root `/root/projects/planets-corpus-db`.
Research Python `/root/.cache/planets-lab/site-state-v1/bin/python`.
If used: hash once, open read-only, never modify `CURRENT`.

C5 combat and Chunnel research remain **frozen at bounded checkpoint**;
no new C5 investigation unless it blocks end-to-end progress.
No changes to `Numillyash/planets-intel`, production combat executor,
the `research/external-engine-analysis` branch or draft PR #28.
Facts, hypothetical phase assumptions, and supported mechanics remain
separate, with unsupported conditions failing closed.

## New-chat opening guidance

Read THIS handoff together with
`docs/handoff/2026-10-16-m2-archive-evidence-triangulation.md`,
`docs/ROADMAP.md`, existing `PlanetaryHostPipeline` and
`PlanetCargoTransferPhase`. First verify actual `main` HEAD, PRs
and CI on GitHub. Then **implement order-aware vertical integration**
instead of performing another archival histogram/diagnostic iteration.
