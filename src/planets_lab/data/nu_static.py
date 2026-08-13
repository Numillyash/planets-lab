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

    Records remain raw dictionaries on purpose. The public API documents which
    collections exist but not every record field, so typed component/hull
    projections are added only after their observed schema is validated.
    """

    hulls: dict[int, dict[str, Any]] = field(default_factory=dict)
    beams: dict[int, dict[str, Any]] = field(default_factory=dict)
    engines: dict[int, dict[str, Any]] = field(default_factory=dict)
    torpedoes: dict[int, dict[str, Any]] = field(default_factory=dict)
    races: dict[int, dict[str, Any]] = field(default_factory=dict)
    advantages: dict[int, dict[str, Any]] = field(default_factory=dict)
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


def import_static_all(payload: Mapping[str, Any]) -> NuStaticCatalog:
    """Import the documented core collections from `/static/all` losslessly."""

    if not isinstance(payload, Mapping):
        raise NuStaticDataError("payload must be an object")

    # The API documentation names `torpedos` and `torpedosall`; prefer the
    # all-components collection when present, while accepting the default set.
    torpedo_records = payload.get("torpedosall")
    if torpedo_records is None:
        torpedo_records = payload.get("torpedos")

    # Some documentation revisions describe both default and all-hull sets.
    # Keep support for `hullsall` if the live endpoint exposes it.
    hull_records = payload.get("hullsall")
    if hull_records is None:
        hull_records = payload.get("hulls")

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
        hulls=_index_records(hull_records, "hulls"),
        beams=_index_records(payload.get("beams"), "beams"),
        engines=_index_records(payload.get("engines"), "engines"),
        torpedoes=_index_records(torpedo_records, "torpedos"),
        races=_index_records(payload.get("races"), "races"),
        advantages=_index_records(payload.get("advantages"), "advantages"),
        extra_collections={
            str(key): deepcopy(value)
            for key, value in payload.items()
            if key not in known
        },
    )
