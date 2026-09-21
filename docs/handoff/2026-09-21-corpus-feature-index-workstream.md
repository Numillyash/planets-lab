# Corpus feature index / historical-game selector workstream

Date: 2026-09-21

Repository: `Numillyash/planets-lab`
Branch: `main`

This is a planning record for corpus infrastructure discovered while reviewing external Planets.nu tools. It does not promote any new Host mechanic.

## Motivation

The current corpus already uses immutable cached `/game/loadall` ZIPs and deterministic compiled layers. External historical analyzers demonstrate a useful additional capability: browsing/filtering historical games by Host/game settings before analysis.

Our diagnostics currently often discover confounders after selecting candidate transitions. A deterministic game-feature index should allow earlier bounded selection of cleaner populations.

## Source boundary

Authoritative inputs remain this repository's own immutable/cached Planets.nu evidence and manifests.

External references:

- T-Continuum Analyser: useful as a UX/concept reference for filtering historical games by settings;
- `derblondehans/player-affinity-tool`: useful only as a reference that public event history can encode joins/drops/replacements;
- chmeee.org: no direct mechanics role for this workstream.

Do not ingest third-party calculated metrics as evidence. If a third-party tool claims a setting/statistic, independently recover it from Planets.nu evidence before indexing it.

## Proposed artifact

Add a deterministic compiled table/file, for example conceptually:

```text
game_features
-------------
game_id
field_name / normalized columns
value
known
source_kind
source_location
schema_version
```

A wide DuckDB table is also acceptable if it better matches the existing compiled corpus. The important contract is that unknown is not silently converted to false/zero and provenance remains recoverable.

## Candidate factual feature families

Only index fields that can be recovered attributable from existing archives/manifests or explicit Planets.nu game metadata.

### Game identity / coverage

- game id;
- game type/status;
- first/last available turn;
- archive completeness;
- host/engine/version identifiers when exposed.

### Host/game settings

Examples to investigate, not assumptions that every field exists in current archives:

- Production Queue;
- Sphere / topology;
- ship-limit / PLS variants;
- combat RNG;
- cloak/intercept and other option flags;
- ground-attack/combat options;
- cloning/build options;
- diplomacy/team format;
- campaign/special feature switches;
- relevant race-specific toggles.

The T-Continuum filtering vocabulary is a discovery checklist only. Exact names/semantics must come from Planets.nu factual metadata, not copied labels.

### Population / evidence availability

- races present;
- Horwasp/special population presence;
- VCR count and battle-shape counts;
- movement transition count;
- availability of relation/diplomacy records;
- evidence counts useful for preselecting candidate games.

## Intended consumers

Diagnostics should be able to ask for bounded populations before expensive analysis, for example:

```text
ordinary Classic + planar + no Horwasp
combat RNG = known value
games with enough ship-vs-ship VCR chains
games with a particular documented option enabled
exclude campaign/special games for a Classic discriminator
```

Prefer a small reusable selector/API over repeated ad-hoc parsing in individual diagnostics.

## Evidence semantics

This workstream does not create a new evidence status.

```text
feature-index match
!= mechanic observation
!= discriminator
!= DIFF_VERIFIED
```

The normal workflow still applies:

1. select attributable population;
2. identify candidate observations;
3. compare competing hypotheses;
4. control confounders;
5. run deterministic tests/differential gates;
6. promote only with existing evidence labels.

## Integration constraints

- Preserve `validation/corpus/cache/loadall/game-<id>.zip` as immutable evidence.
- Do not mutate prepared-cache semantics merely to add convenient settings.
- Prefer a versioned compiled schema.
- Add tests for unknown-vs-false semantics and deterministic rebuilds.
- If source metadata varies by game/version, fail open at the index level as UNKNOWN but fail closed in any mechanic diagnostic requiring the value.
- Keep external URLs/notes in documentation; do not introduce runtime dependency on external analyzer sites.

## Suggested implementation order

1. Inventory which relevant game/Host settings are already present in `loadall`, manifests and prepared caches.
2. Define a minimal v1 schema with known/unknown semantics.
3. Compile the current 12-game corpus and inspect feature coverage.
4. Add a selector/query helper for diagnostics.
5. Re-run one existing diagnostic using explicit corpus predicates to prove the integration without changing its evidence result.
6. Only then expand the indexed setting vocabulary where it demonstrably helps discriminator search.

The first acceptance target should be reproducible selection of an "ordinary Classic" subset with explicit reasons each game was included or excluded.
