# Corpus Game / Host Feature Index v1 — archive-enriched runtime

Date: 2026-09-21

Repository: `Numillyash/planets-lab`
Branch: `main`

Runtime source HEAD:

```text
68ed7006732c22273b47a5e915d7c2ed9b4e1f74
```

This is the first successful full archive-enriched runtime of:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

## Gate result

All stages completed successfully.

Environment:

```text
Python 3.12.14
planets_lab imported from /workspace/src/planets_lab/__init__.py
targeted tests: 12 passed
```

## Feature-index build

```text
schema:        planets-lab.game-feature-index.v1
build schema:  planets-lab.game-feature-index-build.v1
games:         12
rows:          1152
known rows:    1116
unknown rows:  36
missing archives: []
```

Primary Parquet:

```text
validation/corpus/compiled/v1/metadata/game_features.parquet
```

Deterministic rebuild Parquet:

```text
artifacts/corpus-feature-index-v1/rebuild/game_features.parquet
```

Both builds produced:

```text
sha256:
cb72f539775d22726d8d7f225fc7b3deeb8f936312873df12db59340e1dd7735
```

Byte/SHA comparison passed.

Therefore the v1 compiler is deterministic for the current 12-game archive corpus.

## ordinary-classic selector

Included:

```text
360690
511506
620694
```

Excluded:

```text
591478
620636
620917
621103
621253
621896
622476
680435
680910
```

Profile predicate count:

```text
17
```

UNKNOWN profile predicates:

```text
0
```

The selector reports the factual matching/mismatching predicate values and manifest provenance for every game.

## Historical combat integration proof

Baseline replay:

```text
archives:                 12
raw_vcr_observations:  22256
unique_vcrs:            6469
replay_supported:       6469
replay_unsupported:        0
payload_conflicts:         0
replay_result_conflicts:   0
partially_supported:       0
malformed_members:         0

ship_vs_planet:         3719
ship_vs_ship:           2750
```

Per-game unique VCR population:

```text
360690  1529
511506   791
591478  2075
620636    97
620694   945
620917   186
621103   113
621253   176
621896    78
622476   205
680435   125
680910   149
```

The same diagnostic was then rerun through:

```text
--feature-index validation/corpus/compiled/v1/metadata/game_features.parquet
--feature-profile all-indexed
```

The integration checker compared all evidence-bearing fields and returned:

```json
{
  "exact": true,
  "mismatches": []
}
```

Selected IDs were all 12 indexed games.

Therefore feature-index preselection does not alter the current Classic combat parity evidence result.

## Acceptance

Feature Index v1 infrastructure acceptance is complete for the current corpus:

```text
12/12 immutable archives present
deterministic compiler rebuild exact
ordinary-classic selector reproducible
predicate provenance emitted
UNKNOWN semantics retained
combat parity integration exact
no mechanics conclusion changed
```

The feature index remains selection infrastructure only:

```text
feature-index match
!= mechanic observation
!= discriminator
!= DIFF_VERIFIED
```

## Runtime outputs

```text
validation/corpus/compiled/v1/metadata/game_features.parquet
validation/corpus/compiled/v1/metadata/game_feature_build.json
validation/corpus/compiled/v1/corpus.duckdb

artifacts/corpus-feature-index-v1/ordinary-classic.json
artifacts/corpus-feature-index-v1/combat-baseline.json
artifacts/corpus-feature-index-v1/combat-all-indexed.json
artifacts/corpus-feature-index-v1/combat-integration.json
```

The compiled/runtime artifacts remain gitignored and rebuildable from the tracked manifest plus immutable local archives.
