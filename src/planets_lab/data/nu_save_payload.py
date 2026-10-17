"""Read-only Planets.nu /game/save form + legacy '|||'/':::' entity decoder.

Based on an authenticated *client-side observation* of XHR POST saves.
This parses exact source strings and preserves unverified host semantics.
It does not submit orders or convert stock snapshots into causal orders.

IMPORTANT: one /game/save call may contain only selected ShipN/PlanetN/
StarbaseN objects. The absence of a key is NOT a deletion or an empty
order, and first appearance in a capture is NOT entity construction.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

SCHEMA = "planets-lab.nu-save-observation-analysis.v1"
ENTITY_PATTERN = re.compile(r"^(Ship|Planet|Starbase)([1-9][0-9]*)$")
DIGITS = re.compile(r"^[0-9]+$")
MAX_FIELDS = 256
MAX_SERIALIZED_CHARS = 2_000_000
MAX_EVENTS = 10000


class NuSavePayloadError(ValueError):
    """Untrusted or unsupported /game/save capture format."""


@dataclass(frozen=True, slots=True)
class SavedEntity:
    kind: str
    entity_id: int
    fields: dict[str, str]

    @property
    def identity(self) -> str:
        return f"{self.kind}{self.entity_id}"


@dataclass(frozen=True, slots=True)
class SavedRequest:
    game_id: int
    player_id: int
    turn: int
    save_index: int | None
    source_form_field_count: int
    entities: dict[str, SavedEntity]
    http_status: int | None
    response_success: bool | None
    response_save_index: int | None


def _nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, str) or DIGITS.fullmatch(value) is None:
        raise NuSavePayloadError(f"{label} must be an unsigned integer string")
    return int(value)


def _response_optional_int(value: Any) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def parse_legacy_entity(raw: str, *, kind: str, entity_id: int) -> SavedEntity:
    """Parse observed 'Id:::6|||Name:::...|||Waypoints:::' exactly.

    Numeric fields intentionally remain strings: coercion would erase
    distinctions and falsely imply validated NuHost order semantics.
    """
    if kind not in ("Ship", "Planet", "Starbase"):
        raise NuSavePayloadError("unsupported entity kind")
    if type(entity_id) is not int or entity_id <= 0:
        raise NuSavePayloadError("invalid entity identifier")
    if not isinstance(raw, str) or len(raw) > MAX_SERIALIZED_CHARS:
        raise NuSavePayloadError("entity payload must be a bounded string")
    parts = raw.split("|||")
    if not parts or len(parts) > MAX_FIELDS:
        raise NuSavePayloadError("empty or oversized entity record")
    fields: dict[str, str] = {}
    for token in parts:
        if ":::" not in token:
            raise NuSavePayloadError("entity field missing ':::' separator")
        key, value = token.split(":::", 1)
        if not key or key in fields:
            raise NuSavePayloadError("empty or duplicated legacy entity field")
        fields[key] = value
    identity = _nonnegative_int(fields.get("Id"), "serialized Id")
    if identity != entity_id:
        raise NuSavePayloadError("form key and serialized Id disagree")
    return SavedEntity(kind, entity_id, fields)


def parse_save_body(
    body: Mapping[str, Any],
    *,
    http_status: int | None = None,
    response: Mapping[str, Any] | None = None,
) -> SavedRequest:
    """Decode exactly one sanitized or raw form object, without credentials."""
    if not isinstance(body, Mapping):
        raise NuSavePayloadError("request body must be a form-object mapping")
    game_id = _nonnegative_int(body.get("gameid"), "gameid")
    player_id = _nonnegative_int(body.get("playerid"), "playerid")
    turn = _nonnegative_int(body.get("turn"), "turn")
    if game_id <= 0 or player_id <= 0 or turn <= 0:
        raise NuSavePayloadError("game/player/turn must be positive")
    save_index = None
    if "saveindex" in body:
        save_index = _nonnegative_int(body["saveindex"], "saveindex")
    entities: dict[str, SavedEntity] = {}
    for key, raw in body.items():
        if not isinstance(key, str):
            raise NuSavePayloadError("all form field keys must be strings")
        match = ENTITY_PATTERN.fullmatch(key)
        if match:
            kind, id_text = match.groups()
            entities[key] = parse_legacy_entity(
                raw, kind=kind, entity_id=int(id_text)
            )
        elif key.startswith(("Ship", "Planet", "Starbase")):
            # Do not quietly skip a renamed/unsupported entity wire key.
            raise NuSavePayloadError("unrecognized entity form key")
    if "keycount" in body:
        n = _nonnegative_int(body["keycount"], "keycount")
        if n != len(body):
            raise NuSavePayloadError("keycount/form-field count mismatch")
    if http_status is not None and (type(http_status) is not int or not 100 <= http_status <= 599):
        raise NuSavePayloadError("invalid HTTP status")
    if response is not None and not isinstance(response, Mapping):
        raise NuSavePayloadError("response body must be an object")
    resp = response or {}
    success = resp.get("success")
    if type(success) is not bool:
        success = None
    return SavedRequest(
        game_id=game_id, player_id=player_id, turn=turn,
        save_index=save_index, source_form_field_count=len(body),
        entities=entities, http_status=http_status,
        response_success=success,
        response_save_index=_response_optional_int(resp.get("saveIndex")),
    )


def _observed_response(raw: Mapping[str, Any]) -> Mapping[str, Any] | None:
    obj = raw.get("response")
    if obj is None:
        return None
    if not isinstance(obj, Mapping):
        raise NuSavePayloadError("observed response is not an object")
    return obj.get("body") if isinstance(obj.get("body"), Mapping) else None


def parse_capture(payload: Mapping[str, Any]) -> tuple[SavedRequest, ...]:
    """Accept only the exact local passive capture schema; no Host inference."""
    if not isinstance(payload, Mapping) or payload.get("schema") != "planets-lab.save-payload-capture.v1":
        raise NuSavePayloadError("not a V1 passive save payload capture")
    rows = payload.get("observations")
    if not isinstance(rows, list) or len(rows) > MAX_EVENTS:
        raise NuSavePayloadError("missing or oversized observation list")
    result: list[SavedRequest] = []
    identity: tuple[int, int, int] | None = None
    for n, event in enumerate(rows):
        if not isinstance(event, Mapping):
            raise NuSavePayloadError(f"observation {n} is not an object")
        if event.get("method") != "POST" or event.get("transport") not in ("xhr", "fetch"):
            raise NuSavePayloadError("only POST XHR/fetch save requests supported")
        request = event.get("request")
        if not isinstance(request, Mapping) or request.get("encoding") not in ("form", "multipart-form"):
            raise NuSavePayloadError("request is not a decoded form")
        response = _observed_response(event)
        parsed = parse_save_body(
            request.get("body"),
            http_status=event.get("http_status"),
            response=response,
        )
        current_identity = (parsed.game_id, parsed.player_id, parsed.turn)
        if identity is not None and identity != current_identity:
            raise NuSavePayloadError("different games/players/turns in one capture")
        identity = current_identity
        result.append(parsed)
    return tuple(result)


def analyze_save_capture(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Order-aware observational deltas, NEVER delete missing form objects.

    Compare each entity to its most recent earlier included occurrence,
    not to the immediately prior request (which may omit that entity).
    """
    requests = parse_capture(payload)
    latest: dict[str, tuple[int, SavedEntity]] = {}
    events: list[dict[str, Any]] = []
    changes_total = 0
    reobserved_unchanged = 0
    first_seen = 0
    http_ok_with_explicit_success = 0
    http_ok_with_success_unknown = 0
    for index, request in enumerate(requests):
        first: list[str] = []
        changes: list[dict[str, Any]] = []
        unchanged: list[str] = []
        if request.http_status == 200:
            if request.response_success is True:
                http_ok_with_explicit_success += 1
            elif request.response_success is None:
                http_ok_with_success_unknown += 1
        for entity_name, entity in sorted(request.entities.items()):
            previous = latest.get(entity_name)
            if previous is None:
                first.append(entity_name)
                first_seen += 1
            else:
                previous_index, old_entity = previous
                changed_fields = [
                    {"field": key, "before": old_entity.fields.get(key),
                     "after": entity.fields.get(key)}
                    for key in sorted(old_entity.fields.keys() | entity.fields.keys())
                    if old_entity.fields.get(key) != entity.fields.get(key)
                ]
                if not changed_fields:
                    unchanged.append(entity_name)
                    reobserved_unchanged += 1
                else:
                    changes.append({
                        "entity": entity_name,
                        "previous_observed_request_index": previous_index,
                        "fields": changed_fields,
                    })
                    changes_total += len(changed_fields)
            latest[entity_name] = (index, entity)
        events.append({
            "request_index_in_retained_window": index,
            "included_entities": sorted(request.entities.keys()),
            "first_observed_in_window_not_creation": first,
            "unchanged_since_previous_entity_observation": unchanged,
            "field_changes_since_previous_entity_observation": changes,
            "http_status": request.http_status,
            "response_success": request.response_success,
            "response_save_index": request.response_save_index,
            "keycount_matches_form_fields": True,  # checked only if keycount exists
        })
    totals = payload.get("route_counters")
    total = totals.get("save") if isinstance(totals, Mapping) else None
    dropped = (total - len(requests)) if type(total) is int and total >= len(requests) else None
    return {
        "schema": SCHEMA,
        "status": "OBSERVED_CLIENT_SAVE_FIELDS_NOT_NUHOST_ORDER_OR_HOST_VERIFIED",
        "summary": {
            "retained_saves": len(requests),
            "save_requests_counted_in_browser": total if type(total) is int else None,
            "earlier_saves_not_retained": dropped,
            "unique_entities_observed": len(latest),
            "newly_seen_baselines_not_entity_creations": first_seen,
            "field_changes_between_reobserved_entities": changes_total,
            "reobserved_unchanged_entities": reobserved_unchanged,
            "http_200_explicit_success_true": http_ok_with_explicit_success,
            "http_200_success_not_true_or_missing": http_ok_with_success_unknown,
            "NuHost_orders_accepted_verified": False,
            "NuHost_phase_order_verified": False,
            "snapshot_absence_means_deletion": False,
        },
        "events": events,
    }
