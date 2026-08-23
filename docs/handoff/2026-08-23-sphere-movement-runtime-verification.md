# Sphere-aware ordinary movement — runtime verification handoff

Date: 2026-08-23

Repository: `Numillyash/planets-lab`

Status: **production code implemented; runtime corpus verification pending**.

This handoff supersedes the sphere-integration status in `2026-08-21-movement-corpus-current-state.md`. The older file remains the source for the last runtime-verified pre-sphere counts.

## Last runtime-verified baseline

Do not change these numbers until the new production path is rebuilt and measured:

```text
movement_residual                     4450
movement_post_chunnel_residual        3063
movement_post_horwasp_strong_residual 2753
```

Diagnostic evidence before production integration:

```text
final residual rows                         2753
sphere rows                                 2059
raw 2150 closures                              0
effective 2170 closures                      442
effective 2170 non-Horwasp closures          394
hull 46 sphere rows                           235
hull 46 effective closures                   213
```

## Production implementation now in main

New module:

```text
src/planets_lab/corpus/movement_sphere_context.py
```

Contract:

- raw compiled topology remains the factual `2150x2150` sphere topology from the historical archive;
- effective `2170x2170` is an evidence-scoped override only for game `591478`;
- the override requires exact game id, `sphere=True`, stable topology and raw dimensions exactly `2150x2150`;
- it is not generalized to `mapwidth + 20` or to any other game;
- wrapped target, observed destination and eligible warp-well planet images reuse the existing topology helpers and ordinary movement classifier;
- gravitonic hulls keep their movement multiplier when effective sphere geometry is evaluated;
- categories are exported as `effective_sphere_*` or `effective_sphere_gravitonic_*`.

Ordering is deliberately monotonic:

1. existing raw baseline classification;
2. existing tow / gravitonic / ion-storm external context;
3. effective sphere geometry only for rows still marked `post_external_residual=true`.

Therefore existing explanatory categories are not stolen or renamed by the sphere pass.

The existing post-compile external-context cache marker was bumped:

```text
planets-lab.compiled-movement-storm-context.v1
->
planets-lab.compiled-movement-storm-context.v2
```

The symbol name is retained for compatibility with existing metadata, but v2 now marks the ordered post-compile L1 external-context pipeline: authoritative storm-mode correction followed by scoped sphere closure. A normal build without `--rebuild` must therefore invalidate old L1 movement partitions.

Regression coverage:

```text
tests/test_movement_sphere_context.py
```

The deterministic seam fixture proves a transition that remains unexplained under raw `2150x2150` but becomes `effective_sphere_partial_host_major_minor` under the scoped `2170x2170` period. Scope guards cover wrong game id, unexpected raw dimensions and unstable topology.

## Commits in this implementation sequence

```text
e4a1a46  Add scoped sphere movement context
ab6c5ac  Cover scoped sphere movement context
237f7f3  Wire sphere context from compiled row facts
0ea9abc  Apply scoped sphere context after storm resolution
```

## Runtime verification required next

1. Pull current `main`.
2. Run targeted sphere/storm/compiled-label tests and the full pytest suite.
3. Run the compiled movement build normally, without `--rebuild`.
4. Verify semantic cache invalidation occurs automatically and prepared caches remain reusable.
5. Rebuild movement-context labels normally.
6. Query L1/L2 residual counts and `effective_sphere_%` external categories.
7. Verify raw game `591478` topology columns still report `2150x2150`.
8. Re-rank final residual hulls.

Expected final-residual effect from the pre-production differential is a reduction of 442 rows if production and diagnostic paths are equivalent. This is an expectation, not a verified invariant; record the measured result even if it differs.

Do not start another mechanic until this runtime verification is complete and `ROADMAP.md`, `COMPILED_CORPUS.md`, README/current handoff are rebaselined with the measured counts.
