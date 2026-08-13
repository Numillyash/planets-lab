from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


class NuStaticDataError(ValueError):
    pass


@dataclass(slots=True)
class NuStaticCatalog:
    """Lossless, id-indexed subset of a Planets.nu `/static/all` response.

    The default component collections are indexed by their normal `id` values
    because those ids are referenced by turn data. Optional "all" collections
    are preserved separately without assuming their identifier semantics.
    """

    hulls: dict[int, dict[str, Any]] = field(default_factory=dict)
    beams: dict[int, dict[str, Any]] = field(default_factory=dict)
    engines: dict[int, dict[str, Any]] = field(default_factory=dict)
    torpedoes: dict[int, dict[str, Any]] = field(default_factory=dict)
    races: dict[int, dict[str, Any]] = field(default_factory=dict)
    advantages: dict[int, dict[str, Any]] = field(default_factory=dict)
    hulls_all: tuple[dict[str, Any], ...] = ()
    torpedoes_all: tuple[dict[str, Any], ...] = ()
    extra_collections: dict[str, Any] = field(default_factory=dict)

    def hull(self, hull_id: int) -> Mapping[str, Any] | None:
        return self.hulls.get(hull_id)


def _record_id(raw: Mapping[str, Any], label: str) -> int:
    value = raw.get("id")
    if isinstance(value, bool):
        raise NuStaticDataError(f"{label}.id must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NuStaticDataError(f"{label}.id must be an integer") from exc


def _index_records(value: Any, label: str) -> dict[int, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise NuStaticDataError(f"{label} must be a list")

    result: dict[int, dict[str, Any]] = {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NuStaticDataError(f"{label}[{index}] must be an object")
        record = deepcopy(dict(item))
        record_id = _record_id(record, f"{label}[{index}]")
        if record_id in result:
            raise NuStaticDataError(f"duplicate id {record_id} in {label}")
        result[record_id] = record
    return result


def _copy_records(value: Any, label: str) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise NuStaticDataError(f"{label} must be a list")

    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NuStaticDataError(f"{label}[{index}] must be an object")
        result.append(deepcopy(dict(item)))
    return tuple(result)


def import_static_all(payload: Mapping[str, Any]) -> NuStaticCatalog:
    """Import the documented core collections from `/static/all` losslessly."""

    if not isinstance(payload, Mapping):
        raise NuStaticDataError("payload must be an object")

    known = {
        "hulls",
        "hullsall",
        "beams",
        "engines",
        "torpedos",
        "torpedosall",
        "races",
        "advantages",
    }

    return NuStaticCatalog(
        hulls=_index_records(payload.get("hulls"), "hulls"),
        beams=_index_records(payload.get("beams"), "beams"),
        engines=_index_records(payload.get("engines"), "engines"),
        torpedoes=_index_records(payload.get("torpedos"), "torpedos"),
        races=_index_records(payload.get("races"), "races"),
        advantages=_index_records(payload.get("advantages"), "advantages"),
        hulls_all=_copy_records(payload.get("hullsall"), "hullsall"),
        torpedoes_all=_copy_records(payload.get("torpedosall"), "torpedosall"),
        extra_collections={
            str(key): deepcopy(value)
            for key, value in payload.items()
            if key not in known
        },
    )
