# M2 V3 verified: disjoint cargo candidates and bounded standard base-tech purchases

Date: 2026-10-19.

## Runtime evidence (the corrected V3, not the failed earlier run)

Published source: `runtime-logs/m2-public100-surface-context-v1/20261019T143058Z_1f0721ca1186/`, with `metadata.json: exit_code=0`, both aggregate artifacts, clean source commit `1f0721ca11866dfe0500c1277af67e098b248f2b`, unchanged corpus `CURRENT`. Generation SHA256 `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`, frozen selection SHA256 `b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f`. Only 68 baseline games, 136 selected perspective transitions, **no heldout32 entity sampling**.

Among 915 qualified ground-exact/surface-residual planet×mineral observations:
- 65 exact opposite **single-only** ship cargo candidates;
- 36 matches **both** single ship and full co-site multiship cargo sum;
- 7 **multiship-only** full-co-site cargo sums;
- 807 neither;
- union = **108** unique mineral comparisons, 11.80% of the residual cohort.

Thus the old 101 single and 43 multi marginals overlap by 36, not independent observations. At the more defensible planet-window aggregation level, 915 mineral residuals occupy only **315** planet transition windows: 60 with one mineral, 29 with two, 107 with three, 119 with four. Of 315 transitions, 65 have *any* cargo candidate (not 108 independent transfers), 267 have a weak starbase planet-link, 15 have observed base-tech changes, and just 1 combines base-tech change with any cargo candidate. The mineral-comparison weak-base tech-change count 52 is not 52 distinct upgrades. The 65 candidate planet windows span 15 baseline games. All categories are **descriptive and not proof of NuHost orders, phase ordering or causal attribution**.

## Implemented next Host-simulator step

Introduces `StarbaseTechUpgradePhase` and explicit `StarbaseTechUpgradeOrder` within `TurnOrders`. The phase uses the already tested `published_standard_tech_upgrade_cost_mc()` from the published Planets.nu technology-level table: e.g. engine level 7→10 costs 700 + 800 + 900 = **2400 MC**. It applies several explicitly selected upgrades at one existing, known-owned starbase atomically against its known-owner planet MC, with strict 1..10 range, no downgrades, owner check, duplicate-order rejection, a **caller-specified eligible max level** for the owner, and no unsupported automatic base construction or free-native upgrade inference.

Opt-in composition with existing `PlanetCargoTransferPhase`, `PlanetaryHostPipeline` and `HostEngine` uses an explicit `tech_before_planetary` or `tech_after_planetary` assumption. A separate technology-phase resource ledger checks that its total net inventory is **exactly the stated negative MC cost**, with no ship, ground, or non-MC debits. Older non-starbase slices retain the original 15 phases and default unsupported-starbase ABSTAIN. `HostEngine` refuses tech orders if the technology phase is omitted, rather than silently ignoring them.

The bounded full-state `reconcile_explicit_orders` can now opt into known-identity starbases, assert a chosen tech phase placement and player-specific level caps, and compare end-state technology alongside cargo and phase ledgers. Without an opt-in, missing eligibility assertion, or intact base roster/owner/defense/fighter evidence it **ABSTAINS**. Historical V3 starbase rows with missing ownerid are still ineligible for this full-state comparison.

The V1 operator order-capture and owner-observation serializers cannot encode `StarbaseTechUpgradeOrder`. They now explicitly reject it to avoid stripping an order from a signed capture, until a separately versioned provenance schema exists.

## Scientific boundaries and pending validation

The standard table is `DOCUMENTED` at https://help.planets.nu/tech-levels. The implementation's behavior is locally `TESTED` by synthetic scenarios, not `DIFF_VERIFIED` against a known NuHost execution. Operator assertions of cap 7 or 10 are not verified Premium/homeworld conditions; special custom-host prices, free native-tech upgrades, receipts and the Host execution time remain unknown. Signed owner captures cannot yet authenticate this order family. Explicit technology orders with full state are never inferred from 15 archival base-tech changes.

No C5, canonical combat, production IntelBoard, corpus `CURRENT`, raw generations or heldout entity records changed. The existing V3 report is sufficient to motivate this phase; **no new 26.65-GiB corpus pass is needed** for these deterministic model changes.


## Optional no-corpus server smoke if GitHub Actions is queued

The new `tools/diagnostics/m2_starbase_tech_synthetic_gate_v1.py` runs
six deterministic, dependency-light assertions (documented cost;
two purchase placements; cross-phase explicit money transfer;
eligibility rejection; conditional state comparison). It prints
aggregate-only status without game/ship/starbase IDs or any private
material. No DuckDB, no public corpus, and no heldout data.

From an updated clean checkout:

```bash
cd /root/projects/planets-lab
git pull --ff-only origin main
bash tools/run-m2-starbase-tech-synthetic-v1-with-evidence.sh
```

The existing evidence wrapper stores an immutable `gate.log` and source
metadata in a new `runtime-logs/m2-starbase-tech-synthetic-v1/<run-id>/`.
If the smoke fails, it still publishes exit!=0 and must not count as a
successful evidence gate. Passing it demonstrates **local modeled behavior**
only, never independently observed NuHost acceptance or execution.
