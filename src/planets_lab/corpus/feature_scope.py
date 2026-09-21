from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .feature_index import load_feature_rows, profile_selection_summary


DEFAULT_FEATURE_INDEX_PATH = Path(
    "validation/corpus/compiled/v1/metadata/game_features.parquet"
)


@dataclass(frozen=True, slots=True)
class FeatureScope:
    index_path: Path
    profile: str
    predicate_count: int
    included_game_ids: tuple[int, ...]
    excluded_game_ids: tuple[int, ...]
    unknown_game_ids: tuple[int, ...]

    @property
    def selected_ids(self) -> frozenset[int]:
        return frozenset(self.included_game_ids)

    @property
    def excluded_ids(self) -> frozenset[int]:
        return frozenset(self.excluded_game_ids)

    @property
    def unknown_ids(self) -> frozenset[int]:
        return frozenset(self.unknown_game_ids)

    @property
    def indexed_ids(self) -> frozenset[int]:
        return frozenset(
            (*self.included_game_ids, *self.excluded_game_ids, *self.unknown_game_ids)
        )

    def classify(self, game_id: int) -> str:
        if game_id in self.selected_ids:
            return "selected"
        if game_id in self.unknown_ids:
            return "unknown"
        if game_id in self.excluded_ids:
            return "excluded"
        return "unindexed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": str(self.index_path),
            "profile": self.profile,
            "predicate_count": self.predicate_count,
            "included_game_ids": list(self.included_game_ids),
            "excluded_game_ids": list(self.excluded_game_ids),
            "unknown_game_ids": list(self.unknown_game_ids),
        }


def load_feature_scope(
    index_path: Path,
    *,
    profile: str,
) -> FeatureScope:
    rows = load_feature_rows(index_path)
    summary = profile_selection_summary(rows, profile=profile)
    return FeatureScope(
        index_path=index_path,
        profile=str(summary["profile"]),
        predicate_count=int(summary["predicate_count"]),
        included_game_ids=tuple(int(value) for value in summary["included_game_ids"]),
        excluded_game_ids=tuple(int(value) for value in summary["excluded_game_ids"]),
        unknown_game_ids=tuple(int(value) for value in summary["unknown_game_ids"]),
    )


def optional_feature_scope(
    index_path: Path | None,
    *,
    profile: str,
) -> FeatureScope | None:
    if index_path is None:
        return None
    return load_feature_scope(index_path, profile=profile)
