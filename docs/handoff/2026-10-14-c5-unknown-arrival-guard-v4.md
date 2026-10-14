# C5 parent queue: unknown T−1 arrival safety gate V4

Date 2026-10-14. Canonical research repo: `Numillyash/planets-lab`.
Horwasp remains parked. No production changes.

## Reason for this change

Published V3 `runtime-logs/combat-c5-tminus1-site-recall-attribution-v3/20261014T045945Z_0bcb3d247956`
retrospectively found **23/25** V2 `NO_PAIR` failures where both factual
N+1 participants had positions **unresolved** in the independent T−1
movement forecast. The other two had only one predicted at the site.
The V3 sample does **not** establish faulty Host combat selection.

Observed T−1 position sources for these 25 NO_PAIR transitions include
`tow_target` (18 *appearances*, 8 unique target ships),
`normal_mine_route_risk` (11 appearances),
`sphere_topology_not_integrated` (6), `tow_attempt` (5),
`intercept_movement` (5). These counts reflect repeated ships and
must not be interpreted as independent game samples.
The whole 27-site/63-transition population remains a known exploratory
set, not blind Host validation.

In the normal-mine group, eight of eleven current site destinations
match the archived T−1 waypoint; several are 1-ly warp-1 moves.
However that retrospective matching **does not** justify promoting a
mine-immune movement rule or overwriting a previous `UNRESOLVED`.
Tow lock resolution, random mine hits and sphere geometry are
conditionally modelled by existing movement code and must remain
fail-closed where independent state is absent.

## Reusable mainline evidence-safe C5 primitive

`src/planets_lab/rules/combat/site_input_adapter.py` now exposes
`potential_tminus1_site_arrivals(...)`, a pure function depending on
**only T−1 predictions and the site already known from current VCR N**.
It finds independent T−1 owner-record ships whose predicted movement
position is unknown but whose archived start or waypoint is that site.
It verifies owner, race/hull, ship identity; excludes race12, already
active and optionally previously removed ships. A different known
active owner is required; if no active owner exists, at least two
distinct unresolved candidate owners are required.

The result is **possible competitor presence**, never a ship's
predicted position, engagement eligibility, queue priority or capture.
It cannot create a battle and contains no future VCR/N+1 argument.

## Frozen public100 experiment V4

`tools/diagnostics/combat_c5_parent_queue_arrival_uncertainty_v4.py`
pins the existing site census Git blob
`fda92475988d2f7dfbc7b93606de4f8cec909806`
and the successful V2 published report
`dd641864dc3bd541098ea2c21cf21fb8ff03d5ce`,
verifies the explicit public100 DuckDB SHA256 once and opens read-only.

For all preselected 27 sites / 63 adjacent transitions it reads only
the factual current VCR N participants and the independent T−1 site
prediction map. It does not call a future comparator or reselect a
pair. If original V2 returned `NO_PAIR` but a plausible unresolved
competitor exists, it classifies that negative result as
`ABSTAIN_PLAUSIBLE_UNRESOLVED_TMINUS1_ARRIVALS`.
If the limited T−1 index identifies none, result is
`NO_PAIR_NOT_PROVEN_NO_ARRIVALS_IN_LIMITED_TMINUS1_INDEX`;
this is also **not proof of Host site exhaustion**.

Original frozen V2 = **9 conditional predictions, 7 exact**.
Original strict T−1 = **3 predictions, 2 exact**.
V4 explicitly leaves BOTH unchanged: zero new pair predictions.
The purpose is architectural correctness of a future integrated
site executor: do not make the closed-world assumption that the
active site roster contains all ships if movement is unresolved.

Outputs:
`artifacts/combat/c5-parent-queue-arrival-uncertainty-v4/published/report.json`;
evidence branch
`runtime-logs/combat-c5-parent-queue-arrival-uncertainty-v4/`.

## One server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-parent-queue-arrival-uncertainty-v4-with-evidence.sh
```

Tests check start/waypoint risk, non-resurrection, owner/race
fail-closed and no future leak. No production, movement-physics,
combat executor, Horwasp or corpus CURRENT mutations. Draft PR #28
remains intentionally open/unmerged.

**Next high-value implementation after V4:** re-use the already tested
Tow/normal/intercept phase engine to resolve only independently
admissible special-movement cohorts in *whole site contexts*, then
rerun the fixed 63-transition C5 acceptance. Do not add individual
per-game future-opponent rules or treat possible as certain.

## Frozen-transition source-integrity follow-up (2026-10-14)

Before running the still-unpublished V4 corpus gate, a source preflight
now checks **multiplicity** as well as membership/count of the frozen V2
adjacent transitions. Previously, a duplicate serialized transition
could be masked by a nonzero `missing` count in set-only validation.
Duplicate/foreign/malformed transition identities, invalid missing counts,
and duplicate census identities now fail closed. A missing T−1 prediction
index is never interpreted as an empty index with no possible arrivals.
Negative unit controls exercise all these boundaries.

This is a data-integrity fix only; it introduces zero additional Host
predictions and does not establish observed V4 runtime results. Execute
the existing V4 evidence wrapper before attempting any V5 inference.
