# Corpus DB v1 implementation checkpoint

Status: code-complete first prototype path; archive-host runtime on `game-233558` is still required before the prototype gate can be called green.

## Storage boundary

Corpus DB v1 is a third storage entity. It must live outside every checkout and outside project-scoped Docker volumes.

Host contract:

```text
PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
```

Container contract:

```text
/corpus-db
```

Published readers mount the shared host root read-only. Only the dedicated importer service mounts it read-write, and the importer writes a new file under `staging/`; it never opens the active generation for write.

The committed Compose overlay is:

```text
compose.corpus-db.yaml
```

It is intentionally reusable with both the normal `planets-lab` checkout and the `research/external-engine-analysis` checkout because both expose the research service as `lab`.

## Trust/privacy boundary

The database is a lossless mirror of raw `.trn` semantics, not the privacy-minimized `mechanics_projection` used by existing compiled/prepared layers. It can therefore contain source fields such as messages, account-facing fields, save keys or other private turn data when those fields exist in the archive.

Consequences:

- DB generations are trusted local research artifacts;
- DB files/manifests containing source-derived metadata are not committed to Git;
- they are not public/export artifacts;
- raw ZIP/TRN remains the immutable evidence source;
- the DB is reproducible derived storage with source provenance, not a replacement for evidence.

## Physical schema

Schema id:

```text
planets-lab.corpus-db.v1
```

Tables:

```text
corpus_metadata
source_archives
zip_members
source_members
member_fields
entity_rows
```

Provenance chain:

```text
source_archives
  -> zip_members
  -> source_members
  -> member_fields / entity_rows
```

`source_archives` records the game id, source path, source ZIP byte size and SHA-256.

`zip_members` records every ZIP member in archive order, including name, CRC32, compressed/uncompressed sizes, directory/turn-member flags and payload SHA-256 for non-directory members.

`source_members` records every canonical `playerN-turnM.trn`, including:

- game id;
- archive/member relation;
- member name/ordinal/CRC/sizes;
- raw member payload SHA-256;
- decoded JSON payload SHA-256;
- plain/gzip transport;
- perspective player id;
- archive turn;
- embedded turn;
- decoded JSON byte count.

`member_fields` records every top-level field and its ordinal, semantic JSON type and storage representation. Field absence is represented by row absence. Explicit JSON null is a present row whose payload decodes to null.

`entity_rows` stores object-array elements as separate perspective-scoped rows. It preserves the full object as canonical JSON and additionally projects query keys when they are type-compatible:

```text
source_entity_id
owner_id
player_id
x
y
```

These projected columns are never used to reconstruct semantic truth. They exist only for indexed selection.

## Lossless fallback

The importer does not require a complete field schema before accepting a source member.

Known object-array sections and unknown non-empty arrays consisting entirely of objects are stored as ordered `entity_rows`. All other top-level values are stored as canonical JSON in `member_fields`.

This preserves:

- missing vs present-null;
- bool vs integer vs float;
- zero, false and empty string;
- nested unknown fields;
- array ordering;
- separate observations of the same entity id from different perspectives;
- unknown future top-level fields.

Object-key byte ordering and JSON whitespace are intentionally not evidence semantics and are not parity requirements.

## Import memory model

`src/planets_lab/corpus/corpus_db.py` opens the ZIP from its path and consumes one member at a time. It does not call `load_archive_snapshots()` and never creates a whole-game `ArchiveTurnSnapshot` tuple.

Entity/field inserts use bounded PyArrow batches rather than Python-to-SQL row-by-row `executemany`. The default Arrow batch threshold is 20,000 rows and transaction checkpoint is 128 turn members.

This bounds Python object retention to approximately one decoded turn plus a finite row batch instead of the full game object graph.

## Indexed access

Indexes cover:

```text
source_members(game_id, perspective_player_id, archive_turn)
source_members(game_id, source_member_name)
member_fields(member_id, field_name)
entity_rows(member_id, section_name, ordinal)
entity_rows(game_id, section_name, archive_turn, source_entity_id)
entity_rows(game_id, section_name, archive_turn, x, y)
```

Convenience views expose common source sections without changing the row model:

```text
players
planets
ships
starbases
ionstorms
minefields
vcrs
relations
messages
notes
```

and top-level object views:

```text
game_fields
player_fields
settings_fields
```

## Semantic parity gate

For each canonical TRN member:

```text
A = existing _decode_member_json(original member)
B = reconstruct_member(DB member)
```

The comparator is recursively type-sensitive and validates exact field presence, scalar type/value and array order. On the first divergence it reports the exact source member and JSON path.

The same validation pass also rechecks:

- whole archive SHA-256/size;
- every ZIP member ordinal/name/CRC/compressed size/uncompressed size/type/payload SHA-256;
- source-member game id;
- raw and decoded payload SHA-256;
- perspective player id;
- archive turn;
- embedded turn.

Any failure leaves the file in `staging/`; publication is refused.

## Publication protocol

A successful build is:

```text
source ZIP
  -> /corpus-db/staging/<temporary>.duckdb
  -> archive-integrity validation
  -> full TRN semantic parity
  -> close writer
  -> os.replace() into generations/<build-id>.duckdb
  -> chmod read-only where supported
  -> write manifests/<build-id>.json
  -> atomic os.replace() of CURRENT
```

Existing generations are never overwritten. `CURRENT` is validated to point directly to one `.duckdb` file under `generations/`.

## Prototype commands

On the archive host:

```bash
export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
bash tools/run-corpus-db-game233558-prototype.sh
```

The runner performs, in order:

1. one-time direct import of `validation/corpus/cache/loadall/game-233558.zip`;
2. full archive integrity + TRN semantic parity;
3. immutable publish + `CURRENT` update;
4. published DB size/source JSON size report;
5. fresh-process indexed T-1/T benchmark;
6. fresh-process indexed VCR/site benchmark;
7. simultaneous read-only open of the same `CURRENT` generation from the normal and external research containers.

The external checkout defaults to:

```text
$HOME/projects/planets-lab-external
```

Override with `PLANETS_EXTERNAL_CHECKOUT` when needed.

Do not scale to the 36-game corpus until the runtime measurements in `BENCHMARK_GAME_233558.md` are filled from a green run.

## Storage attribution diagnostic

After the first archive-host runtime showed the direct v1 generation was 24.06%
larger than decoded semantic JSON, the branch added a bounded physical-layout
diagnostic rather than immediately scaling to 36 games.

Tracked entry point:

```text
tools/run-corpus-db-storage-attribution.sh
```

The diagnostic:

1. resolves the immutable published generation;
2. creates a fresh scratch DB directly under `/corpus-db/staging`;
3. attaches the published generation `READ_ONLY`;
4. copies only the six v1 base tables;
5. checkpoints and records file size for data-only storage;
6. adds the current secondary indexes in groups, checkpointing after each;
7. runs `ANALYZE` and records the final size;
8. removes the scratch DB by default.

It uses a configurable DuckDB memory limit (default `4GB`) and two threads so
the attribution pass cannot casually recreate the earlier ~11 GiB peak merely
because the host has spare RAM.

This is still v1 direct-mirror work. It does not add delta encoding, RLE,
state-version dedup or cross-perspective dedup.


### Deep attribution after the first physical-size run

The first attribution proved that secondary indexes account for about 1.16 GB,
while the data-only copy is already 10.71 GB. The same tracked command now also
reports:

- cumulative and incremental bytes after each base table is copied;
- a disposable `entity_semantic_min` layout containing only
  `member_id, section_name, ordinal, payload_json`;
- a disposable `entity_query_slim` layout that adds only the typed query
  projection (`source_entity_id, owner_id, player_id, x, y`) and deliberately
  omits repeated game/perspective/archive/embedded-turn columns.

The two entity-layout databases are deleted inside the diagnostic itself. This
lets the next runtime distinguish lossless JSON payload cost, typed projection
cost and repeated per-entity context cost before any physical-schema change.
