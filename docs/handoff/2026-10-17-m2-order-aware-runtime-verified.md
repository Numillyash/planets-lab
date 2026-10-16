# M2 order-aware planetary V1 — server runtime verified / archive-order provenance gate

## Verified runtime (October 16, 2026)

This is a durable checkpoint for the already implemented, research-only
integration of `PlanetCargoTransferPhase` and `PlanetaryHostPipeline`.

- Canonical source branch: `main`.
- Exact source commit: `894240fad1c42db2cba868de3ec228a72a19fc83`.
- Implementation: PR #208, server pytest-dependency fix: PR #209.
- CI: PR #209, 1175 passing tests; main CI #1268 successful.
- Runtime: `planetary-order-aware-slice-v1`.
- Evidence branch/path:
  `runtime-logs/planetary-order-aware-slice-v1/20261016T211423Z_894240fad1c4`.
- Evidence metadata Git blob (SHA1):
  `9595ec3ea1f34999ef142d93b29f9a62424cd0eb`.
- Published report Git blob (SHA1):
  `ba9ac519c7b7a33c68f0c23dab01cfd746f8ff55`.
- `exit_code=0`, `source_dirty=false`, `missing_artifact_paths=[]`,
  no interrupted signal, evidence successfully published.
- Schema: `planets-lab.planetary-order-aware-slice.v1`.
- Status: `M2_ORDER_AWARE_INTERNAL_TESTED_NOT_NUHOST_DIFFERENTIAL`.
- 3 simulated turns for each of 2 explicitly hypothetical transfer placements;
  15 phase-balance snapshots per turn; 8/8 ABSTAIN controls; all runtime
  self-checks passed.
- Internal trace SHA256:
  `327af515dc6b3f4bf4ea87764469640f4d60c1db47553d38fa494dbf42b40ef1`.
- `actual_NuHost_orders_authenticated=0`,
  `NuHost_phase_order_verified=false`,
  `historical_differential_verified=false`,
  `canonical_combat_changes=0`.

The preceding failed evidence
`runtime-logs/planetary-order-aware-slice-v1/20261016T203739Z_1fadeedbf0a2`
has `exit_code=1` and a missing report, because the original server
runner required an uninstalled `pytest`. **Do not count this failed run
as a successful Host experiment.** PR #209 removed the server dependency
and made the runtime checks deterministic and self-contained.

## Data-evidence boundary: do not infer submitted orders

`src/planets_lab/corpus/normalizer.py::mechanics_projection`
retains archival game/player metadata, planet/ship/starbase/storm/minefield
snapshot records and a small settings subset. It **does not produce
a separately authenticated `TurnOrders` or `PlanetCargoTransferOrder`
submission record**. A ship's position, current cargo, waypoint or
post-Host stock change is NOT proof of a beam-up/beam-down order.

The original 617 qualified public8 T−1/T comparisons have 215 complete
four-family conditional matches and 402 net-stock mismatches; they are
observational, and their causes remain unattributed. In particular:

- `TurnOrders.empty()` means **no supplied orders to this simulation**,
  not factual evidence that no orders were submitted to NuHost;
- observing a surface-mineral or supply residual cannot reconstruct an
  independent transfer event without circular attribution;
- either modeled phase placement can match a conditional outcome without
  proving which placement NuHost used;
- archives missing independent order capture must `ABSTAIN` from
  order-aware *causal* parity/accuracy denominators.

A new archival differential requires **independent pre-Host submitted-order
captures** (with trusted origin, exact game/turn/player identity,
a frozen capture time before the result, completeness and relevant ship/planet
ids), paired with trustworthy owner-current pre/post snapshots.
A `loadall` ship's `targetx/targety` or snapshot cargo is not a substitute.
If the independent record, its completeness, phase boundary, or interference
from unrelated Host mechanics cannot be resolved: `ABSTAIN`; do not
silently turn empty/missing orders into a known-zero transfer.

## Next implementation priorities

1. Obtain or build a narrowly scoped, separately auditable **pre-Host
   order capture** path for an owned test game or controlled scenarios;
   never publish private credentials or source player/account data.
2. Only then wire a strict identity/provenance admission gate and run
   ONE small pre-selected T−1/T attribution test in a fresh, independently
   captured cohort. Keep experimental transfer phase ordering explicit.
3. Independently address missing building/purchase order models and phase
   placement only after trustworthy source orders and rule evidence exist.

**No new C5, Chunnel, Horwasp, or residual-by-residual analysis was
needed to establish this checkpoint.** Canonical combat, public corpus
`CURRENT`, production `planets-intel`, external-engine branch and draft
PR #28 remain untouched.

The already successful runtime requires **no second server rerun** solely
for this documentation checkpoint.
