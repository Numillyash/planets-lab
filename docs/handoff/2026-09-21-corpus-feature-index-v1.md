# Corpus Game / Host Feature Index v1

Date: 2026-09-21

Repository: `Numillyash/planets-lab`
Branch: `main`

This handoff closes the first implementation stage described in
`2026-09-21-corpus-feature-index-workstream.md`.

The feature index is **corpus-selection infrastructure only**. It does not create
a new evidence source or evidence status.

```text
feature-index match
!= mechanic observation
!= discriminator
!= DIFF_VERIFIED
```

## Source-of-truth boundary

Immutable historical evidence remains:

```text
validation/corpus/cache/loadall/game-<id>.zip
```

The index does not rewrite those files.

Factual game/Host settings come from the tracked privacy-safe corpus manifest,
which was produced from public Planets.nu `/game/loadinfo`. Archive/evidence
counters are derived directly from the immutable loadall ZIPs when they are
locally present. Existing movement transition counts are read only from the
already compiled per-game movement metadata when available.

Third-party analyzers are not runtime inputs.

## Schema

```text
planets-lab.game-feature-index.v1
```

Storage model: normalized typed Parquet table, exposed in DuckDB as:

```text
game_features
```

Columns:

```text
schema_version
game_id
feature
value_type
known
bool_value
int_value
double_value
text_value
source_kind
source_location
```

Exactly one typed value column is populated for a known feature.

Unknown is explicit:

```text
known = false
value_type = unknown
all value columns = NULL
```

Therefore:

```text
unknown != false
missing != disabled
not present != zero
```

The schema is normalized rather than wide so that new factual settings can be
added without table migrations while retaining per-feature provenance.

## Compiled locations

Default outputs:

```text
validation/corpus/compiled/v1/metadata/game_features.parquet
validation/corpus/compiled/v1/metadata/game_feature_build.json
validation/corpus/compiled/v1/corpus.duckdb
```

These remain gitignored deterministic compiled artifacts.

The existing DuckDB catalog is augmented with `game_features`; existing
movement views are not replaced.

## Current factual manifest inventory

Tracked manifest:

```text
validation/corpus/manifests/accounts-recent-finished.jsonl
```

Current records:

```text
games = 12
manifest schema = planets-lab.corpus-game.v2
```

The current manifest has factual `loadinfo.settings` values for all 12 games
for the major v1 selector families.

Coverage observed in the tracked manifest:

```text
setting / feature              known   observed values

sphere                         12/12   false=11, true=1
productionqueue                12/12   false=4, true=8
planetaryproductionqueue       12/12   false=4, true=8
combatrng                      12/12   0=12
cloakandintercept              12/12   false=4, true=8
campaignmode                   12/12   false=10, true=2
shiplimittype                  12/12   0=6, 1=6
plsminships                    12/12   0=5, 20=7
teamsize                       12/12   0=1, 1=11
cloningenabled                 12/12   true=12
groundattackadjustments        12/12   ""=12
nowarpwells                    12/12   false=12
nuionstorms                    12/12   false=10, true=2
unlimitedfuel                  12/12   false=5, true=7
Horwasp presence               12/12   false=11, true=1
```

Additional allowlisted v1 settings include diplomacy limits, Galactic Power,
Super Spy Advanced, hardened mines, web/diplomacy settings, race-specific
switches and other mechanical configuration values already factual in
`loadinfo.settings`.

## Explicit UNKNOWN fields

The current tracked evidence does not expose an attributable:

```text
engine.host_version
engine.engine_version
```

These are emitted as UNKNOWN for every game. No version is inferred from dates,
sector names or third-party sites.

The current manifest also predates allowlisting:

```text
game.short_description
```

The manifest builder now allowlists that public field for future refreshes, but
the current 12 records correctly index it as UNKNOWN.

Official Planets.nu API documentation establishes `/game/loadinfo` as a public
source for game settings/player metadata, and `/games/list?ids=...` as a public
source for the Game object including `shortdescription`.

No documented public Host/engine-version field has been established, so version
features remain UNKNOWN rather than guessed.

## Archive-derived feature families

When `game-<id>.zip` is available, the compiler derives:

```text
coverage.archive_present
coverage.archive_sha256
coverage.archive_bytes
coverage.turn_member_count
coverage.player_stream_count
coverage.first_archive_turn
coverage.last_archive_turn
coverage.archive_turn_count
coverage.missing_grid_cells
coverage.rectangular_grid_complete

evidence.archive_transition_count
evidence.vcr.raw_observation_count
evidence.vcr.unique_count
evidence.vcr.ship_vs_ship_count
evidence.vcr.ship_vs_planet_count
evidence.vcr.payload_conflict_count

evidence.relations.members_available
evidence.relations.complete_across_members
evidence.relations.record_count

evidence.movement_transition_count
```

VCR identities are deduplicated by factual:

```text
(game_id, battle_turn, vcr_id)
```

with canonical-payload hashes used to count conflicting duplicate observations.

If an immutable ZIP is absent:

```text
coverage.archive_present = known false
archive-derived counters = UNKNOWN
```

If `relations` is absent on any turn member, the total relation-record count is
UNKNOWN rather than silently treated as zero.

## Population features

Manifest player slots compile into:

```text
population.player_slot_count
population.races_present
population.race.<1..12>.present
population.horwasp_present
```

Player/race slot metadata remains privacy-minimal.

## Selector API

Production API:

```python
FeaturePredicate
select_games(...)
selected_game_ids(...)
load_feature_rows(...)
```

CLI:

```bash
python -m planets_lab.corpus.feature_index_cli select \
  --index validation/corpus/compiled/v1/metadata/game_features.parquet \
  --profile ordinary-classic
```

Additional factual filters are reusable, for example:

```bash
--known settings.combatrng
--eq settings.combatrng=0
--eq settings.cloakandintercept=true
--ge evidence.vcr.ship_vs_ship_count=100
```

UNKNOWN required predicates fail closed and are printed as UNKNOWN with their
source/provenance.

## ordinary-classic profile

Official Planets.nu `gametype=2` combines Classic / Standard / Custom, so the
profile does not equate `gametype=2` with Classic.

The v1 profile requires a factual Classic-rule signature:

```text
game.status == 3
game.game_type == 2
game.is_custom == false
game.scenario_id == 0
settings.campaignmode == false
settings.sphere == false
settings.productionqueue == false
settings.planetaryproductionqueue == false
settings.shiplimittype == 0
settings.plsminships == 0
settings.cloakandintercept == false
settings.galacticpower == false
settings.superspyadvanced == false
settings.fascistdoublebeams == false
settings.unlimitedfuel == false
settings.combatrng is known
population.horwasp_present == false
```

Current tracked-manifest selection:

```text
included:
  360690
  511506
  620694

excluded:
  591478
  620636
  620917
  621103
  621253
  621896
  622476
  680435
  680910

UNKNOWN profile predicates:
  none
```

Examples of factual exclusion causes:

```text
591478:
  game_type=4
  campaignmode=true
  sphere=true
  Production Queue=true
  Cloak+Intercept=true
  Horwasp present=true

620636:
  is_custom=true
  campaignmode=true
  plsminships=20

newer Standard-style population:
  Production Queue=true
  Planetary Production Queue=true
  Cloak+Intercept=true
  Galactic Power=true
  Super Spy Advanced=true
  unlimitedfuel=true
```

This profile is a selection contract, not a mechanic conclusion.

## Integration proof

Existing diagnostic converted:

```text
tools/diagnostics/combat_classic_corpus_parity_audit.py
```

New optional arguments:

```text
--feature-index
--feature-profile
```

With no feature index the diagnostic is unchanged.

The `all-indexed` profile is used as an integration control: baseline and
feature-selected runs must match on all evidence-bearing report fields.

Checker:

```text
tools/diagnostics/corpus_feature_index_integration_check.py
```

## Reproducible gate

Tracked one-command runner:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

It performs:

1. targeted feature-index + combat-integration tests;
2. full 12-game archive-enriched build from immutable local ZIPs;
3. a second rebuild and byte/SHA equality check;
4. `ordinary-classic` selector output;
5. baseline Classic combat parity;
6. all-indexed feature-selected combat parity;
7. exact evidence-bearing result comparison.

GitHub Actions additionally builds the current 12-game **manifest layer** twice
without local archives, compares Parquet byte-for-byte, and runs the
`ordinary-classic` selector. In that environment archive-derived features are
correctly UNKNOWN because gitignored evidence ZIPs are intentionally absent.

## Existing archive corpus checkpoint

The last independently recorded archive corpus checkpoint remains:

```text
archives                 12
raw VCR observations  22256
unique VCRs            6469
ship-vs-ship           2750
ship-vs-planet         3719
```

Those counts predate the v1 feature-index runtime and are not relabeled as a
fresh feature-index differential result.

## Evidence boundary

Do not use index membership to promote mechanics.

The normal pipeline remains:

1. select attributable population;
2. identify mechanic observations;
3. compare competing hypotheses;
4. control confounders;
5. deterministic tests;
6. historical differential gate;
7. evidence promotion using the existing labels only.


## GitHub Actions validation

Push CI after the completed v1 implementation ran the normal repository workflow successfully.

```text
full pytest: 384 passed
feature-index CLI/import checks: passed
tracked 12-game manifest build: passed
second deterministic manifest rebuild: passed
Parquet byte comparison: exact
ordinary-classic selector CLI: passed
```

The CI build deliberately points archive/compiled source directories at empty
temporary paths. This proves that the current 12 tracked games still compile
deterministically while archive-derived and compiled-derived features fail
closed to UNKNOWN instead of zero/default values.

The archive-enriched gate remains:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

and requires the gitignored immutable ZIP cache that exists on the corpus host.


## Local gate portability repair

The first corpus-host execution of:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

failed during pytest collection with:

```text
ModuleNotFoundError: No module named 'planets_lab'
```

The host was using system Python 3.10 against a `src/` layout checkout with no
editable package installation. GitHub Actions did not expose this because CI
installs `-e '.[dev]'` under Python 3.12 before running tests.

This was a runner portability defect, not a feature-index or corpus failure.

Repair commit:

```text
d2b3195a03711852f5f5769aaecf50a43da65a96
  fix: run corpus feature index gate in project container
```

The gate now follows the mature historical-gate convention:

```text
docker compose run --rm -T
-e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics
lab
```

The project image is Python 3.12 and already contains `.[dev]` dependencies.
The repository is bind-mounted at `/workspace`, so source is always taken from
the checked-out revision even if the image itself was built earlier.

The gate now additionally verifies:

- current branch is `main`;
- the checkout is clean;
- HEAD exactly matches freshly fetched `origin/main`;
- container Python is >= 3.11;
- `planets_lab` imports from `/workspace/src`;
- tracked working-tree state remains unchanged after the gate.

No evidence or selector result was taken from the failed host attempt.


## Archive-enriched v1 runtime — PASSED

Durable runtime:
`docs/handoff/2026-09-21-corpus-feature-index-v1-runtime.md`

Runtime source HEAD:

```text
68ed7006732c22273b47a5e915d7c2ed9b4e1f74
```

Result:

```text
12/12 archives present
games=12
feature rows=1152
known=1116
unknown=36
deterministic rebuild SHA exact
ordinary-classic included=3
ordinary-classic excluded=9
UNKNOWN selector predicates=0
combat integration exact=true
combat integration mismatches=[]
```

Compiled Parquet SHA:

```text
cb72f539775d22726d8d7f225fc7b3deeb8f936312873df12db59340e1dd7735
```

The feature-index workstream v1 acceptance target is therefore met on the actual immutable archive corpus.


## Mechanics integration profile

Feature Index v1 now includes a separate:

```text
combat-planar-no-horwasp
```

profile for continuity with existing C3/C4 diagnostics.

Predicates:

```text
game.status == 3
settings.sphere == false
population.horwasp_present == false
```

This is intentionally not called Classic. It preserves the current historical
11-game clean combat scope while the stricter `ordinary-classic` profile
continues to select only three Classic-signature games.

The first migrated diagnostics and archive continuity gate are documented in:
`docs/handoff/2026-09-21-combat-feature-scope-selector-pending.md`.
