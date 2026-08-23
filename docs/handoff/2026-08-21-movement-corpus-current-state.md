# Movement corpus — current state

Date: 2026-08-21

Repository: `Numillyash/planets-lab`

Status: **movement differential pipeline is current through classic ion-storm mode validation; sphere topology integration is the next active item.**

This handoff is the source-of-truth snapshot for the current movement/corpus work. Do not reconstruct project state from old chat logs when this document and `docs/ROADMAP.md` are available.

## Runtime-verified corpus baseline

Current validation manifest:

- 12 recent unique finished games across four configured accounts;
- tracked manifest: `validation/corpus/manifests/accounts-recent-finished.jsonl`;
- manifest schema: `planets-lab.corpus-game.v2`;
- compiled database: `validation/corpus/compiled/v1/corpus.duckdb`;
- movement schema: `planets-lab.compiled-movement.v2`;
- storm-context semantic schema: `planets-lab.compiled-movement-storm-context.v1`;
- context-label schema: `planets-lab.compiled-movement-context-labels.v3`.

Latest successful runtime build/accounting:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13444
post_external_residual         4450

chunnel_explained              1387
post_chunnel_residual           3063
horwasp_strong_explained         310
post_horwasp_strong_residual    2753
```

The production semantic-cache invalidation for the classic-storm change was verified by a normal build without `--rebuild`:

```text
compiled_cache_hits:    0
compiled_cache_misses: 12
prepared_cache_hits:   12
```

The following context-label rebuild produced:

```text
compiled_label_cache_hits:   5
compiled_label_cache_misses: 7
label_issues:                0
```

Targeted movement tests and the full pytest suite both pass after the classic-storm integration.

## Manifest privacy hardening

The first attempt to promote `validation/corpus/manifests/accounts-recent-finished.jsonl` into Git exposed `game.password` on all 12 rows. That v1 file was **not committed**.

Root cause: manifest v1 copied the complete public `loadinfo.game` object into the durable manifest. Even if the observed password values were empty, wholesale copying was an unsafe persistence contract because future API fields could silently enter Git.

Production fix:

- manifest schema bumped from `planets-lab.corpus-game.v1` to `planets-lab.corpus-game.v2`;
- `game` metadata is explicit-allowlist only;
- `player_slots` remains explicit-allowlist only;
- full `settings` remains preserved because exact Host settings and `settings_hash` are part of the ruleset/provenance contract;
- `sanitize_manifest_record()` migrates an existing v1/v2 record offline into the current privacy-safe schema and recomputes its settings hash;
- regression coverage lives in `tests/test_manifest_privacy.py`.

Runtime migration/validation is complete:

```text
targeted privacy/corpus tests: 18 passed
manifest rows:                 12
unique games:                  12
schema:                        planets-lab.corpus-game.v2
forbidden fields found:        0
```

The privacy-safe v2 manifest was committed to `main` in `57c0e57` (`Track privacy-safe finished-game corpus manifest`). The local working tree was clean immediately after that commit/push. Manifest cleanup is therefore **closed** and is no longer an active roadmap item.

## Closed / verified movement mechanics

### Warp-well classifier ordering

Status: **TESTED + DIFF_VERIFIED**.

Warp-well matches must be tested before `above_nominal`; the old ordering hid legitimate planetary pulls. The production ordering fix reduced the historical movement residual set and is covered by regression tests.

### Red Mite tracking/fallback

Status: **research stage closed**.

Use:

- `docs/rules/red-mite-tracking.md`;
- `docs/handoff/2026-08-18-red-mite-tracking-final.md`;
- `src/planets_lab/corpus/movement_horwasp_mite_context.py`.

Do not restart one-off Mite research without new evidence. Remaining hull-213 final residuals are intentionally left fail-closed.

### Horwasp ballistic topology for game 591478

Status: **TESTED + DIFF_VERIFIED**.

For game `591478`, raw metadata reports a 2150×2150 sphere map, but independent seam evidence shows an effective wrap period of 2170×2170. The 2170 period is evidence-scoped to this game and is already used by the Horwasp ballistic classifier. Do not generalize it as `mapwidth + 20`.

### Classic ion storms (`nuionstorms = false`)

Status: **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

The old external-context implementation always used the cloudy ion-storm local-voltage model. Historical classic-mode games instead use the published storm voltage throughout the circular storm area.

The authoritative `loadinfo.settings.nuionstorms` split produced a perfect corpus differential on the audited final residual set:

```text
classic constant-voltage matches: 1724
cloudy constant-voltage matches:      0
```

Production integration is in `src/planets_lab/corpus/movement_storm_context.py` and is driven offline from manifest settings. There is no additional network dependency during corpus compilation.

Observed runtime effect:

```text
post_external_residual:          6174 -> 4450  (-1724)
post_horwasp_strong_residual:    4477 -> 2753  (-1724)
hull 79 final residual:           495 ->   20  (-475)
```

Hull 79 is therefore no longer an active high-volume mechanic investigation.

## Rejected / deprioritized hypotheses

### Multi-waypoint queue as the hull-79 cause

Rejected for the current corpus.

On the old 4477-row final residual set, raw `waypoints` existed as a field on every row but contained coordinate points on only four rows; zero queued candidates explained movement and hull 79 had zero queue explanations.

### Fuel-limited freighter movement

A real minor mechanic exists and is represented by the documented fuel-proration formula, but the current corpus signature is too small to justify priority over the large generic residual clusters.

## Active finding: sphere geometry outside Horwasp

Diagnostic:

```text
tools/diagnostics/final_residual_sphere_geometry_audit.py
```

This audit reruns the existing ordinary movement classifier on the current final residual while comparing:

- raw sphere period 2150×2150;
- evidence-scoped effective period 2170×2170 for game `591478`.

Latest runtime result:

```text
final_residual_rows                       2753
sphere_rows                               2059
raw_period_explains                          0
effective_period_explains                  442
effective_period_explains_non_horwasp      394
effective_only_explains                    442
raw_only_explains                            0
```

The strongest non-Horwasp closure is hull 46:

```text
hull 46 sphere rows          235
effective-period explains   213
raw-period explains            0
```

Other large effective-period closures include hull 119 (`27/28`), hull 36 (`26/28`), hull 118 (`16/20`), hull 117 (`15/19`) and hull 17 (`14/20`) within sphere game `591478`.

Interpretation: this is strong evidence for a **generic sphere-aware ordinary movement geometry gap**, not a hull-46-specific ability. Production integration has **not** been done yet. The raw topology facts must remain unchanged; an effective/evidence-scoped topology layer should be applied only where independently validated.

## Immediate priorities

1. Integrate evidence-scoped effective sphere topology into ordinary movement/external-context classification for game `591478`, reusing `sphere_adjusted_sample()` and wrapped-planet geometry rather than adding a parallel classifier.
2. Add regressions proving that the same seam-crossing samples are explained under 2170 and remain unexplained under raw 2150.
3. Invalidate the relevant compiled movement semantic cache without changing raw topology columns.
4. Rebuild movement and context labels without `--rebuild` and verify the expected residual delta. A first-order expectation is up to 442 additional final closures, including 394 non-Horwasp rows, but the exact production delta must be measured rather than assumed.
5. Re-rank `movement_post_horwasp_strong_residual` after sphere integration. Ignore hull 213 as a closed Mite research cluster and do not re-prioritize hull 79 unless new evidence appears.
6. Continue generic/high-volume movement mechanics before small one-off hull signatures.

## Working rules

- GitHub `main` is the source of truth.
- Preserve raw facts and effective/evidence-scoped overrides separately.
- Do not infer global settings from one historical game.
- Promote mechanics only with explicit evidence labels.
- Prefer generic fixes that close many hulls/games over per-hull overfitting.
- Raw corpus/cache artifacts remain local and gitignored; only privacy-safe compact manifests, code, compact evidence, schemas and summaries belong in Git.
