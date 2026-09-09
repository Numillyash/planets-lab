# Finite-fuel Tow classic storm membership runtime — 2026-09-09

## Runtime checkpoint

Candidate commit:

`6f1252832b72b1fb2a93c435e2cb71ad9313db9d`

Collected server log directory:

`logs/finite-fuel-tow-classic-storm-20260909T193531Z-6f125283-18812`

All gate stages completed with `command_rc=0`, `tee_rc=0`:

- `inputs`
- `tooling`
- `classic-storm-membership`
- `summary`

The gate reused the preserved external-context checkpoint and did not rebuild the corpus or rerun the expensive warp-well phase-fuel envelope.

## Population accounting

- clean Tow residual input: `53`
- after-turn root-storm drag-vector exact rows: `44`
- no after-turn root-vector match: `9`
- root-vector matches: `49`
- ambiguous root-vector rows: `5`

Game split for the 44 vector-matched rows:

- game `360690`: `33`
- game `511506`: `4`
- game `620694`: `7`

## Historical storm-mode setting

The archived mechanics payload did **not** contain a resolvable `nuionstorms` value in any of the three games:

- `tow_classic_mode_rows=0`
- `tow_nu_mode_rows=0`
- `tow_unknown_mode_rows=53`
- `tow_unknown_mode_after_root_vector_rows=44`

For each game the archive diagnostic reported:

- `nuionstorms_archive=None`
- `archive_raw_values=()`

Therefore classic-vs-Nu storm mode is still unknown from the preserved loadall/prepared snapshots alone.

## Classic constant-voltage membership result

For the 44 rows whose factual residual exactly equals an after-turn root-storm drag vector, the classic root-circle model gives:

- `tow_any_classic_origin_qualifies=44`
- `tow_any_classic_geometry_qualifies=11`
- `tow_any_classic_causal_point_qualifies=44`
- specifically `tow_classic_after_raw_origin_qualifies=44`
- `tow_classic_before_translated_after_strength_origin_qualifies=44`

This is a perfect **geometry + membership lead** at the Tow origin under the classic constant-voltage root-circle model.

It is **not yet mode-consistent evidence**, because the historical `nuionstorms` setting is unresolved. The result must not be promoted to a Host rule merely because the classic model closes all 44 rows.

## Relation to the prior transient Nu-cloud audit

The immediately preceding transient-state gate showed:

- `tow_after_root_vector_rows=44`
- `tow_any_transient_origin_qualifies=0`
- `tow_any_transient_geometry_qualifies=0`
- `tow_any_transient_causal_point_qualifies=0`

and the ordinary direct storm control baseline remained valid (`236/236` under current after-state origin classification).

Combined evidence therefore says:

1. the 44-row family has an exact factual after-turn root-storm drag vector;
2. tested Nu-cloud local-voltage states do not qualify the Tow origin/geometry;
3. the classic constant root-circle model qualifies the Tow origin in all 44 rows;
4. the missing discriminator is now the historical game storm mode, not another geometric fit.

## Decision

Finite-fuel Tow remains **OPEN**.

No nominal-vs-rasterized Tow fuel discriminator has been found.

No simulator rule is promoted from this diagnostic.

No `planets-intel` change is justified.

The 44 rows should continue to be treated as strong storm-confounded candidates, but not removed from the Tow evidence population as proven classic-storm cases until game mode is resolved.

## Next bounded step

Resolve `nuionstorms` for the three affected historical games from public `game/loadinfo`, using the repository's existing **proxy-only** `PlanetsNuPublicApi` path. The next diagnostic must:

- query only the three games present in the clean Tow residual population;
- recursively inventory every `nuionstorms` occurrence/path in `loadinfo` rather than assuming one fixed schema location;
- keep `true`, `false`, conflicting, missing and request-error results separate;
- print relevant storm settings such as `maxions` and `maxioncloudsperstorm` when present;
- avoid direct-network fallback on the server;
- make no Host-rule or production change.
