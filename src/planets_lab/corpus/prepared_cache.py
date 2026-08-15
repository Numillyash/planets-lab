from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass
from pathlib import Path

from . import field_reconstruction as field_reconstruction_module
from . import readiness as readiness_module
from .field_reconstruction import FieldReconstructionSummary, reconstruct_fields
from .normalizer import ArchiveTurnSnapshot, load_archive_snapshots
from .readiness import MOVEMENT_GEOMETRY, ReadinessSummary, evaluate_readiness


PREPARED_GAME_CACHE_SCHEMA = "planets-lab.prepared-game-cache.v1"


@dataclass(frozen=True, slots=True)
class PreparedGameCache:
    """Trusted local cache for expensive deterministic corpus preparation.

    The cache deliberately lives under validation/corpus/cache and is never a
    portable/public artifact. It contains normalized private-perspective state,
    reconstructed entities and readiness results, so callers must treat it with
    the same privacy constraints as the source /loadall archive.

    Bump PREPARED_GAME_CACHE_SCHEMA whenever normalizer, reconstruction or
    readiness semantics change in a way that invalidates stored objects.
    """

    schema: str
    game_id: int
    archive_sha256: str
    snapshots: tuple[ArchiveTurnSnapshot, ...]
    reconstruction: FieldReconstructionSummary
    movement_geometry_readiness: ReadinessSummary


def _archive_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seed_process_caches(prepared: PreparedGameCache) -> None:
    """Seed the existing one-game identity caches from a trusted prepared file."""

    # These are intentionally the exact tuple objects stored in PreparedGameCache.
    # The existing caches are identity-based, so seeding them avoids another full
    # reconstruction/readiness pass while keeping all downstream APIs unchanged.
    field_reconstruction_module._LAST_RECONSTRUCTION_RECORDS = prepared.snapshots
    field_reconstruction_module._LAST_RECONSTRUCTION_SUMMARY = prepared.reconstruction
    readiness_module._LAST_READINESS_RECORDS = prepared.snapshots
    readiness_module._LAST_READINESS_BY_PROFILE = {
        MOVEMENT_GEOMETRY.name: prepared.movement_geometry_readiness,
    }


def build_prepared_game_cache(
    archive_data: bytes,
    *,
    game_id: int,
) -> PreparedGameCache:
    snapshots = load_archive_snapshots(archive_data)
    if not snapshots:
        raise ValueError(f"game {game_id} archive has no snapshots")
    observed_game_ids = {snapshot.game_id for snapshot in snapshots}
    if observed_game_ids != {game_id}:
        raise ValueError(
            f"prepared cache game mismatch: expected {game_id}, got {sorted(observed_game_ids)}"
        )

    reconstruction = reconstruct_fields(snapshots)
    movement_geometry_readiness = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    prepared = PreparedGameCache(
        schema=PREPARED_GAME_CACHE_SCHEMA,
        game_id=game_id,
        archive_sha256=_archive_sha256(archive_data),
        snapshots=snapshots,
        reconstruction=reconstruction,
        movement_geometry_readiness=movement_geometry_readiness,
    )
    _seed_process_caches(prepared)
    return prepared


def _valid_cached_object(
    value: object,
    *,
    game_id: int,
    archive_sha256: str,
) -> PreparedGameCache | None:
    if not isinstance(value, PreparedGameCache):
        return None
    if value.schema != PREPARED_GAME_CACHE_SCHEMA:
        return None
    if value.game_id != game_id:
        return None
    if value.archive_sha256 != archive_sha256:
        return None
    if not isinstance(value.snapshots, tuple):
        return None
    return value


def load_or_build_prepared_game_cache(
    archive_data: bytes,
    *,
    game_id: int,
    cache_path: Path,
    rebuild: bool = False,
) -> tuple[PreparedGameCache, bool]:
    """Return prepared state and whether it came from the persistent cache.

    Pickle is used only as a local trusted performance cache. Never load a cache
    file received from an untrusted source. Archive SHA-256 plus an explicit
    schema version prevents accidental reuse after input/schema changes.
    """

    archive_sha256 = _archive_sha256(archive_data)
    if not rebuild and cache_path.is_file():
        try:
            with cache_path.open("rb") as stream:
                cached = pickle.load(stream)
        except (OSError, EOFError, pickle.PickleError, AttributeError, ImportError):
            cached = None
        prepared = _valid_cached_object(
            cached,
            game_id=game_id,
            archive_sha256=archive_sha256,
        )
        if prepared is not None:
            _seed_process_caches(prepared)
            return prepared, True

    prepared = build_prepared_game_cache(archive_data, game_id=game_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
    try:
        with temporary.open("wb") as stream:
            pickle.dump(prepared, stream, protocol=pickle.HIGHEST_PROTOCOL)
        temporary.replace(cache_path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return prepared, False
