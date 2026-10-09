# Combat mass temporal catalog / ship ID audit V2

Date: 2026-10-09.

## Verified prior evidence

Clean V1 runtime:
`runtime-logs/combat-mass-catalog-owner-provenance-v1/20261009T191531Z_cd6255e8873d`;
source `cd6255e8873d23e435e487c670f9c1c16bb0fe5b`, exit 0.

G217591 T75 V756 ship758 D19c hull1039:
- first source member T0 hulls[1039].mass=96
- owner T−1 T74 hulls[1039].mass=46
- last source member T149 hulls[1039].mass=46
- VCR mass346; T−1 owner ship has engine9=300MC and owner
  ship recorded D19c. Rulebook numeric candidate 46+2*150=346.
- archived owner T74 ship at (1226,2910) has waypoint
  (1234,2974); VCR site (1234,2977), 3 ly offset.
  Not proof of precombat generator movement.

G325434 T149 V1075 ship274 D19c hull1039:
- first T0 hulls[1039] mass96
- owner T−1 T148 hulls[1039] mass46
- last T229 hulls[1039] mass46
- owner T−1 engine1=1MC, two same-owner Sabers at VCR site,
  factual mass48, numeric 46+2*1=48.

**Key lesson:** The archival `hulls` array itself changes from
96 to 46. `hullsall` was absent from both first/last
snapshots. The existing `_independent_hull_specs` takes FIRST
member static; that source is stale by T−1 for these two
historical games. Do not globally override NuStaticSpecs,
because the Host effective time-indexed static selection
and implications for other hulls have not been validated.

G617883 T201 V1017 Rush hull94 ship27:
- factual VCR owner4, hull94, mass795 vs source base645
- owner4 T200 source exists but ship27 does not appear
- foreign player1 T200 observes ID27 *owner5* Rush hull94
  with engineid=0 **masked** (not a real engine0).
- at T201 owner4 source shows ID27 as **Victorious hull35**,
  engine9, co-located with Saber #406; player1 independently
  sees ID27 owner4 hull35 at that point.
- at T202 owner4 source sees same ID27 owned by player5,
  still hull35. The factual Rush VCR ID27 and T-owner
  Victorious ID27 must NOT be stitched together as one
  physically continuous vessel. A T201 Victorious engine9
  is not evidence that the earlier Rush carried engine9.

## New V2 gate

`tools/diagnostics/combat_mass_temporal_static_identity_v2.py`
`tools/run-combat-mass-temporal-static-identity-v2.sh`
`tools/run-combat-mass-temporal-static-identity-v2-with-evidence.sh`

Reads pinned immutable public100 only. For each of the two
D19c games, walks every archived turn T0..combat T in
the SAME owner perspective, reconstructing one or
more matching source members and retaining the exact
source SHA/mass, plus change segments and any conflicts.
This locates the earliest **observed** change from
96 to 46, not an invented Host update timestamp.
The tool explicitly rejects contradictory owner T−1
catalog values.

For Rush ID27, collects ALL unique factual VCR
appearances on turns 200, 201 and 202, preserving
observed hull, owner, combat mass, site, other side
and VCR ID. Correlates with V1 archival owner/foreign
snapshots but does not presume a single physical ship
across hull/owner changes. If VCR IDs are not Host
chronological sequence, the report keeps that
ordering uncertainty explicit.

No production changes, no Host rule promotion.
Missing archive source is unknown, not zero.

## Server execution

    cd ~/projects/planets-lab
    git fetch origin && git switch main && git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-temporal-static-identity-v2-with-evidence.sh

Report:
`artifacts/combat/mass-temporal-static-identity-v2/published/report.json`

Evidence:
`runtime-logs/combat-mass-temporal-static-identity-v2/`

Next: test a *time-indexed* hull snapshot resolver on held-out
games/hulls before replacing any current Classic mass source;
recover Rush identity lineage via combat results, not
unverified T archived engine continuity.
