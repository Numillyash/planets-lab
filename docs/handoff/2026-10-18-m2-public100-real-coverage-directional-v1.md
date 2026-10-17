# M2 public100 coverage V1: actual baseline68 server result and directional V1.1

Date: 2026-10-18. This handoff records an *actual* owner-run
read-only public100 corpus check, NOT just CI fixtures.

## Verified server invocation

The player ran the published runner at HEAD
b55b29751dae8d5b6225c11e41ea2050794170bb
using explicit public100 corpus generation
corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb.

The corpus SHA256 matched
3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c.
The authorized 68-game baseline manifest SHA256 matched
942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9.
CURRENT remained unchanged at the published public68 generation.

The first attempt failed *before* connecting to DuckDB due to a missing
export of PLANETS_CORPUS_DB_ROOT in the shell wrapper, subsequently
fixed in PR #226. The owner manually exported the path for the
successful run. No corpus database or CURRENT was modified.

## Full 100-game metadata census

| Measure | Actual value |
|---|---:|
| Games with source members | 100 |
| All source perspective-turn members | 224,014 |
| Qualified identity-valid members | 222,536 |
| Invalid/embedded-turn mismatch | 1,478 |
| Ambiguous duplicate game/player/turn metadata identities | 0 |
| All qualifying adjacent same-perspective T-1/T pairs | 221,091 |
| Games with qualifying adjacent pairs | 100 |
| Games permitted for entity sampling | 68 |
| Sealed heldout games excluded from entity sampling | 32 |

This *metadata census* is across the full public100. It does not
claim we reconstructed the 541-million entity rows.

## Exactly frozen baseline68 content sample

Selection fingerprint:
b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f.

| Measure | Actual value |
|---|---:|
| Baseline games sampled | 68 |
| Preselected same-perspective adjacent T-1/T pairs | 136 |
| Archive payload identity-valid pairs | 136 |
| Owner-current planet records at T-1 | 3,819 |
| Owner-current planet records at T | 3,867 |
| Same-owner matching planet-ID pairs | 3,769 |
| Owner planet rows stale or missing infoturn (aggregated) | 5 |

All 3,769 same-owner planet pairs qualified credits/supplies,
surface minerals, underground minerals, colonist/native clans and
structures. 3,767 qualified the combined tax family.

Family with **at least one observed net change**:

| Family | Changed / qualified |
|---|---|
| MC + supplies | 3,670 / 3,769 |
| Surface N, D, T, M | 3,631 / 3,769 |
| Underground N, D, T, M | 1,467 / 3,769 |
| Colonist/native clans | 2,605 / 3,769 |
| Mines/factories/defense | 1,795 / 3,769 |
| Combined tax+native happiness fields | 716 / 3,767 |

**Key caution:** "tax_inputs" in the V1 family groups
colonisttaxrate, nativetaxrate AND nativehappypoints. It does
NOT mean 716 owner-issued tax-rate changes. A happiness change
alone can qualify as a family difference. Similarly, net mineral
or stock changes do not uniquely prove production/mining,
player orders or Host phase sequencing.

The previous M2 public8 T-1/T conditional simulator differential
included 617 qualified owner-current rows. It is a different
sample/cohort, using conditional model predictions, not an additional
617 independent instances that can be blindly pooled with these
3,769 observational field pairs.

## Next: field-level directional coverage (this PR)

The actual V1 report aggregates by broad field *families* and
thus cannot answer how often individual fields increase, decrease,
or remain fixed. Rather than fit formulas prematurely, extend the
same bounded *already frozen* source selection with additive,
aggregate-only, per-field counts.

The new fields in the sample report are:

- individual_numeric_field_directions: per-field qualified,
  increased, decreased and unchanged counts; unlike the broad
  tax family this separates tax rate from happiness changes;
- surface_ground_joint_signs_not_mining_attribution: the
  nine ground-vs-surface sign combinations for each mineral,
  plus a transparent subset where mines themselves did not
  change; this is a **candidate for later mining research**,
  not an extracted Host mining trace;
- observable_structure_and_tax_controls: counts of pairs
  with fully observed structure and tax rate fields, split
  into all-unchanged vs some-changed.

The output contains no game/player identity, planet IDs, notes,
raw stock values, or inferred orders. It never reads a sealed
heldout entity. All metrics carry explicit noncausal claims.

### Next server run (after merge)

The previous report must remain immutable. Use a distinct
output path with the existing runner; no new arguments or
corpus generation are required:

~~~bash
cd /root/projects/planets-lab &&
git fetch origin &&
git switch main &&
git pull --ff-only origin main &&
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-economy-directional-v1/report.json \
bash tools/run-m2-public100-economy-coverage-v1.sh
~~~

This repeats SHA256 verification of the immutable published
26.65-GiB input. The source selection is deterministic, so its
metadata_frozen_selection_sha256 MUST equal the hash above.
Any change in this fingerprint invalidates direct comparison
between the V1 and directional follow-up reports.

## Scientific boundaries

T-1/T archive net changes do not identify the player's original
instructions, complete client purchases or Host execution phase.
Only successful user-authorized client save captures can supply
some pre-Host order witnesses; Host comparison additionally needs
an independently authenticated boundary. Do not treat repeated
perspectives from one game as independent samples. Do not use the
sealed 32-game heldout for posthoc tuning.

Keep C5, combat, public corpus CURRENT, production IntelBoard,
external engines and draft PR #28 frozen.
