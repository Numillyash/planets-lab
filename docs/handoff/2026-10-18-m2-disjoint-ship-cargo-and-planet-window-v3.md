# M2 V3: joint ship cargo / starbase tech evidence, deduplicated by planet-window

Date: 2026-10-18.

## Exact provenance and actual V2 observations

The user's successful immutable-public100 V2 runtime evidence is in the
`runtime-logs` branch at
`runtime-logs/m2-public100-surface-context-v1/20261018T173827Z_f7bbb283e93c/`.
Its `metadata.json` confirms `exit_code: 0`, clean main source,
both `report.json` and `triage.json` published, unchanged CURRENT.
The explicit corpus SHA256 is
`3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`.
The SAME 136 baseline68 T-1/T perspective pairs are selected by
`b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f`.
Heldout32 entity records are NOT examined.

Actual V2 conditional mineral outcomes are unchanged:
11,813 both exact; 915 ground exact / surface residual; 33 surface exact /
ground residual; 262 neither exact. Within the 915 residuals:

- 652 had owner ships at the site at both snapshots (71.26%), versus
  3,316/11,813 (28.07%) among both-exact samples.
- 101 single own-ship same-ID opposite cargo change candidates;
  43 multiple-own-ship same-site SUM opposite cargo candidates.
- **DO NOT ADD 101 + 43:** these are overlapping marginal counts.
  A two-ship fleet can have one ship alone match the residual and
  the *whole fleet* also match when the other ship is unchanged.
- 802 have weak ownerless `starbase.planetid` links at both
  snapshots (87.65%), versus 8,125/11,813 (68.78%) among both exact.
  These links DO NOT authenticate starbase ownership.
- 52 show linked starbase tech changes vs 16 in 11,813 both-exact
  observations. These count mineral comparisons, NOT independent
  base technology purchases.
- 641 negative and 274 positive surface residuals (against modeled
  mined output). Five residual magnitudes were over 1,000.
- Baseline68 game-level V2 evidence shows single-ship candidates
  in 15 games and multiship candidates in 12 games. This is
  *descriptive clustering*, not 101 or 43 independent events.

## V3 added measurements in ONE existing read-only corpus pass

Extend `src/planets_lab/corpus/m2_surface_residual_context.py`,
using the exact SAME conditional mining+mutation model and
same preselected owner-current planet pairs. For each
`ground_exact_surface_residual` **mineral comparison**, record
four disjoint cargo categories:

1. `single_only_cargo_candidate`: exactly one own ship matches its
   opposite cargo delta; whole-site >=2-ship sum does not match.
2. `multiship_only_cargo_candidate`: full observed 2+ ship
   unchanged-ID-set sum matches; no exactly-one ship matches.
3. `both_single_and_multiship_candidate`: both methods match
   on the SAME mineral comparison.
4. `no_exact_cargo_candidate`: neither matches.

The sum MUST equal the existing 915 mineral comparison cohort,
and marginal counts MUST remain 101 for single and 43 for
multiship, or abort without publishing misleading derived triage.
Do not confuse matching cargo arithmetic with Host-executed
cargo transfers or proof of a closed universe of ships.

Add joint covariates: observed weak base link at both ends,
observed base technology changes (not purchase orders),
coincidence of base-tech changes with ANY cargo candidate,
and direction of the modeled surface residual.

**Planet-window deduplication:** track the same planet ID
*within one independently authenticated T-1/T perspective
window*. Record the number of such planet transitions with
at least one surface-only mineral residual, the number
with 1, 2, 3, 4 residual minerals, and the union of
single/multiple cargo candidates and weak base tech changes.
A planet with four mineral residuals counts once as a
planet-window event, not four host commands. If the same
planet appears in two different archival windows it is
two planet-window observations; no claim of independence.

Also publish **zero-inclusive 68-game histograms** for
the seven major planet-window categories, without game IDs.

## Fail-closed gates

Aggregate `m2_economy_coverage.py` independently checks the
partition and exact cargo/tech marginals per mineral.
Offline standard-library `m2_surface_context_triage.py`
validates previous source SHA256, frozen sample, heldout
restrictions, category cardinalities and 68-game zero-inclusive
cluster histograms; requires all V3 sections present together.
Synthetic tests explicitly model a two-ship fleet where one
ship alone matches and the sum of both ships also matches,
to prevent treating their count as two independent events.
Tests also cover multiship-only with changed tech and
one planet-window despite four mineral errors.

All output is aggregate-only numeric counts; it is allowed
by the existing strict M2 aggregate runtime publisher.
No ship IDs, planet IDs, game IDs, raw cargo values, API
keys, HARs or raw corpus rows are written. C5, production,
CURRENT, default mineral formula and heldout32 unchanged.

## Next actual server run (after merge and successful CI)

Use a NEW output directory and existing one-pass dual
runtime-evidence wrapper:

~~~bash
cd /root/projects/planets-lab
git pull --ff-only origin main
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-surface-residual-context-v3/report.json \
  bash tools/run-m2-public100-surface-context-v1-with-evidence.sh
~~~

It reads/hashes the already immutable 26.65-GiB public100
once, reconstructs ONLY the frozen 136 baseline68 pairs,
writes strict aggregate report and offline triage, and
automatically publishes both to `runtime-logs`.
No giant pasted JSON and no new user gameplay captures.

Until the V3 server measurement, overlap and distinct
candidate UNION remain **unknown**, despite V2 publishing
the two separate marginals 101 and 43.
