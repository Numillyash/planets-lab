# Post-v5 generic movement residual rebaseline — pending

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **mine/web context v5 fully runtime-verified and repository test suite green; generic residual triage is now moving to the post-mine final layer.**

This handoff supersedes `2026-08-24-mine-context-v5-diff-verified.md` for the active movement investigation. Chunnel v4, classic ion storms, scoped sphere topology, Red Mite closure and strict mine/web v5 remain closed unless new evidence appears.

## Verified current accounting

```text
move_most_candidates              227468
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
mine_strong_explained                 37
post_mine_strong_residual           2240
label_issues                           0
```

Mine split:

```text
normal_mine_hit_nearest_damage  19
web_mine_hit_nearest_damage     18
```

Overlap guards were all zero:

```text
mine_and_chunnel              0
mine_and_horwasp_strong       0
mine_horwasp_hulls            0
mine_not_post_horwasp_source  0
```

The normal v5 build also verified cache behavior:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

## Test state

After correcting the stale Chunnel shared-schema sentinel, both requested test runs are green on clean `main`:

```text
targeted v5 regression: 17 passed
full pytest suite:       all passed
```

No corpus rebuild followed the test-only schema-sentinel fix and none is required.

Mine/web context v5 is therefore fully:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Generic triage source layer

The old broad clustering script still historically referenced the pre-mine view:

```text
movement_post_horwasp_strong_residual
```

That would reintroduce the 37 strict mine/web rows into the next prioritization pass.

`tools/diagnostics/post_sphere_generic_residual_clustering_audit.py` has therefore been updated so its default source is now:

```text
movement_post_mine_strong_residual
```

For reproducibility, the old v4/pre-mine endpoint remains available explicitly:

```text
--residual-view movement_post_horwasp_strong_residual
```

The script prints the selected `residual_view` at runtime.

Historical focused Warp-0 and fuel diagnostics are intentionally left unchanged because they encode their original stage-specific populations. Do not use them as the next broad prioritization source without first checking their residual layer.

## Immediate next step

Run the generic clustering against the new default post-mine endpoint:

```bash
cd ~/projects/planets-lab
set -o pipefail

git pull --ff-only origin main

echo "===== HEAD ====="
git rev-parse --short HEAD

echo
echo "===== STATUS ====="
git status --short

echo
echo "===== SYNTAX CHECK ====="
docker compose run --rm -T lab \
  python -m py_compile \
  tools/diagnostics/post_sphere_generic_residual_clustering_audit.py

echo
echo "===== POST-V5 GENERIC CLUSTERING ====="
docker compose run --rm -T lab \
  python -u tools/diagnostics/post_sphere_generic_residual_clustering_audit.py \
  --limit 40 \
  | tee /tmp/post_v5_generic_residual_clustering.log

echo
echo "===== STATUS AFTER ====="
git status --short
```

Sanity checks:

```text
residual_view = movement_post_mine_strong_residual
final_residual_rows = 2240
```

The previous post-v4 generic population was:

```text
final_residual_rows       2277
generic_rows               820
generic_hulls               81
generic_games               12
```

Do not assume `generic_rows = 783` merely from `820 - 37`: strict mine rows are non-Horwasp by construction, so that arithmetic is a useful expectation, but the clustering script must provide the authoritative post-v5 count and hull/game distribution.

## What to inspect in the new output

Priority sections:

```text
GENERIC HULL COUNTS
GENERIC GAME COUNTS
BASELINE CATEGORIES
WARP BUCKETS
TARGET RELATION
DIRECTION RELATIVE TO TARGET
COARSE SIGNATURES SHARED BY >=3 HULLS / >=2 GAMES
DETAILED MECHANIC SIGNATURES SHARED BY >=2 HULLS / >=2 GAMES
```

Compare specifically with the old post-v4 leads:

- short same-line movement;
- Warp-0 target-at-origin external movement;
- stationary Warp 7-9 rows;
- above-nominal target-at-origin rows;
- oblique / >3x rows.

The main question is which families survive after removing the 37 strict mine/web transitions. Prefer a cross-game/cross-hull mechanic lead over hull-specific clustering.

## Evidence guardrails

- Do not broaden mine labels to repair-bracket rows until repair reconstruction is separately validated.
- Do not reopen Chunnel route-equivalent ambiguity; it is TESTED + DIFF_VERIFIED.
- Do not reopen Red Mite without fresh evidence.
- Do not generalize game `591478` effective 2170 topology globally.
- Exact/canonical displacement repetition is a lead, not a mechanic by itself.
- Historical focused diagnostics may intentionally represent an older residual stage; always check their source view before using them for current prioritization.
