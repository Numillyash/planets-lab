"""M2 client-side economic evidence from REAL /game/save payloads.

Offline, read-only witness extraction: not a TurnOrders decoder and never
a claim about order execution, Host phases, or true NuHost game state.
Partial save objects are compared to the most recent observed instance
of the SAME entity in the SAME game/player/turn. A missing object is
never a zero-value object or a deletion.

Cross-HAR overlapping game/player/turn windows are stitched by request
start timestamp only when all timestamps are present and unambiguous.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping

from planets_lab.data.nu_save_payload import (
    NuSavePayloadError, SavedEntity, SavedRequest, parse_capture,
)

SCHEMA = "planets-lab.client-economic-witnesses.v1"
EVIDENCE = "CLIENT_SAVE_COHANGE_ONLY_NOT_HOST_VERIFIED"
RESOURCE_NAMES = (
    "Neutronium", "Duranium", "Tritanium", "Molybdenum",
    "MegaCredits", "Supplies", "Clans", "Ammo",
)
BUILD_RESOURCE_NAMES = ("MegaCredits", "Duranium", "Tritanium", "Molybdenum")
TAX_NAMES = ("NativeTaxRate", "ColonistTaxRate")
MAX_WINDOWS = 10000
MAX_EVENTS = 200000


def _amount(value: Any) -> int | None:
    # Do not coerce booleans, fractional values, negative inventory or
    # noncanonical numbers into an observed resource quantity.
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    return None


def _delta(old: SavedEntity, new: SavedEntity, name: str) -> int | None:
    before, after = _amount(old.fields.get(name)), _amount(new.fields.get(name))
    return after - before if before is not None and after is not None else None


def _changed(old: SavedEntity, new: SavedEntity, name: str) -> bool:
    return old.fields.get(name) != new.fields.get(name)


def _timestamp(observation: Mapping[str, Any]) -> datetime | None:
    timing = observation.get("timing")
    text = timing.get("start_iso") if isinstance(timing, Mapping) else None
    if not isinstance(text, str):
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except ValueError:
        return None


def _build_event(
    *,
    kind: str,
    request_index: int,
    entity: str,
    previous_index: int | None,
    **details: Any,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "evidence": EVIDENCE,
        "save_index_in_window": request_index,
        "previous_entity_save_index": previous_index,
        "entity": entity,
        **details,
    }


def _analyze_window(
    game_id: int, player_id: int, turn: int,
    records: list[tuple[datetime | None, SavedRequest]],
    *,
    source_segments: int,
) -> dict[str, Any]:
    if len(records) > MAX_EVENTS:
        raise NuSavePayloadError("too many saves within one window")
    if source_segments > 1:
        if any(stamp is None for stamp, _ in records):
            return {
                "game_id": game_id, "player_id": player_id, "turn": turn,
                "source_segments": source_segments,
                "save_count": len(records),
                "status": "ABSTAIN_CROSS_HAR_ORDER_UNWITNESSED",
                "events": [],
            }
        # Equal timestamps across independent segments are not safely
        # ordered by HAR traversal order or body content.
        stamps = [stamp for stamp, _ in records]
        if len(stamps) != len(set(stamps)):
            return {
                "game_id": game_id, "player_id": player_id, "turn": turn,
                "source_segments": source_segments,
                "save_count": len(records),
                "status": "ABSTAIN_DUPLICATE_REQUEST_TIMESTAMPS",
                "events": [],
            }
        records = sorted(records, key=lambda pair: pair[0])

    latest: dict[str, tuple[int, SavedEntity]] = {}
    events: list[dict[str, Any]] = []
    first_seen = 0

    for index, (_, request) in enumerate(records):
        changed: dict[str, tuple[int, SavedEntity, SavedEntity]] = {}
        for name, entity in request.entities.items():
            previous = latest.get(name)
            if previous is None:
                first_seen += 1
            elif previous[1].fields != entity.fields:
                changed[name] = (previous[0], previous[1], entity)
            latest[name] = (index, entity)

        # An observed pending reservation can exist before our first
        # capture; first appearance is NOT a new transfer command.
        for name, (prior, old, new) in sorted(changed.items()):
            if new.kind != "Ship":
                continue
            field_names = (
                "TransferTargetId", "TransferTargetType",
                *(f"Transfer{resource}" for resource in RESOURCE_NAMES),
            )
            if not any(_changed(old, new, field) for field in field_names):
                continue
            balances: dict[str, dict[str, int]] = {}
            changed_resources: list[str] = []
            unknown = False
            for resource in RESOURCE_NAMES:
                tfield = f"Transfer{resource}"
                if not _changed(old, new, tfield):
                    continue
                changed_resources.append(resource)
                dc, dt = _delta(old, new, resource), _delta(old, new, tfield)
                if dc is None or dt is None:
                    unknown = True
                else:
                    balances[resource] = {
                        "available_delta": dc,
                        "reserved_delta": dt,
                        "total_delta": dc + dt,
                    }
            balanced = (
                bool(changed_resources) and not unknown
                and len(balances) == len(changed_resources)
                and all(x["total_delta"] == 0 for x in balances.values())
            )
            events.append(_build_event(
                kind="PENDING_TRANSFER_STATE_CHANGE", request_index=index,
                entity=name, previous_index=prior,
                status=(
                    "CLIENT_RESERVATION_BALANCED" if balanced else
                    "CLIENT_TRANSFER_STATE_CHANGED_UNATTRIBUTED"
                ),
                transfer_target_before={
                    field: old.fields.get(field)
                    for field in ("TransferTargetId", "TransferTargetType")
                },
                transfer_target_after={
                    field: new.fields.get(field)
                    for field in ("TransferTargetId", "TransferTargetType")
                },
                resource_deltas=balances,
                changed_reserved_resources=changed_resources,
                note="client stock/reservation cochange; not executed transfer",
            ))

        # Direct ship/planet resource cochange is a separate witness,
        # NEVER synthesized into an authenticated Host cargo order.
        ships = [
            (name, *info) for name, info in changed.items()
            if info[2].kind == "Ship"
        ]
        planets = [
            (name, *info) for name, info in changed.items()
            if info[2].kind == "Planet"
        ]
        for resource in RESOURCE_NAMES:
            ship_deltas = [
                (name, prior, amount) for name, prior, old, new in ships
                if (amount := _delta(old, new, resource)) not in (None, 0)
                and all(
                    old.fields.get(field) == new.fields.get(field)
                    for field in (
                        f"Transfer{resource}",
                        "TransferTargetId", "TransferTargetType",
                    )
                )
            ]
            planet_deltas = [
                (name, prior, amount) for name, prior, old, new in planets
                if (amount := _delta(old, new, resource)) not in (None, 0)
            ]
            # Exactly one changing Ship and one changing Planet is a
            # strict uniqueness gate. Changes on other entities or
            # simultaneous production may still be confounding causes.
            if (len(ship_deltas) == len(planet_deltas) == 1
                    and ship_deltas[0][2] + planet_deltas[0][2] == 0):
                ship_name, ship_prior, ship_delta = ship_deltas[0]
                planet_name, planet_prior, planet_delta = planet_deltas[0]
                events.append(_build_event(
                    kind="CO_SAVED_SHIP_PLANET_STOCK_BALANCE",
                    request_index=index, entity=ship_name,
                    previous_index=ship_prior,
                    planet_entity=planet_name,
                    previous_planet_save_index=planet_prior,
                    resource=resource, ship_delta=ship_delta,
                    planet_delta=planet_delta,
                    status="CLIENT_BALANCED_CHANGE_CANDIDATE",
                    note="co-saved available-stock change; action cause unwitnessed",
                ))

        # Build selection / resource costs. Numeric Starbase ID is NOT
        # the owning Planet ID; real Starbase1 co-saves with Planet8.
        for name, (prior, old, new) in sorted(changed.items()):
            if new.kind != "Starbase" or not (
                old.fields.get("IsBuilding") == "false"
                and new.fields.get("IsBuilding") == "true"
            ):
                continue
            candidates: list[tuple[str, int, dict[str, int]]] = []
            for planet_name, (planet_prior, pold, pnew) in planets:
                amounts = {
                    field: _delta(pold, pnew, field)
                    for field in BUILD_RESOURCE_NAMES
                }
                if all(amount is not None and amount < 0 for amount in amounts.values()):
                    candidates.append((
                        planet_name, planet_prior,
                        {resource: -amount for resource, amount in amounts.items()},
                    ))
            # A cost with several matching planets is not attributable.
            if len(candidates) != 1:
                events.append(_build_event(
                    kind="STARBASE_BUILD_COST_ABSTENTION",
                    request_index=index, entity=name,
                    previous_index=prior,
                    status=(
                        "ABSTAIN_AMBIGUOUS_SPENDING_PLANETS" if candidates
                        else "ABSTAIN_NO_COMPARABLE_PLANET_SPENDING"
                    ), candidate_planet_count=len(candidates),
                ))
                continue
            planet_name, planet_prior, costs = candidates[0]
            recipe_fields = (
                "BuildHullId", "BuildEngineId", "BuildBeamId",
                "BuildTorpedoId", "BuildBeamCount", "BuildTorpCount",
            )
            tech_fields = (
                "HullTechLevel", "EngineTechLevel", "BeamTechLevel",
                "TorpTechLevel", "HullTechUp", "EngineTechUp",
                "BeamTechUp", "TorpTechUp",
            )
            recipe = {f: new.fields.get(f) for f in recipe_fields}
            tech_changes = {
                field: {"before": old.fields.get(field),
                        "after": new.fields.get(field)}
                for field in tech_fields if _changed(old, new, field)
            }
            events.append(_build_event(
                kind="STARBASE_BUILD_SPENDING_COHANGE",
                request_index=index, entity=name,
                previous_index=prior,
                planet_entity=planet_name,
                previous_planet_save_index=planet_prior,
                recipe=recipe,
                observed_planet_spending=costs,
                tech_field_changes=tech_changes,
                status=(
                    "CLIENT_BUILD_SPENDING_WITH_TECH_CHANGE"
                    if tech_changes else "CLIENT_BUILD_SPENDING_NO_TECH_CHANGE_OBSERVED"
                ),
                note="within-save client spending, not isolated Host formula",
            ))

        for name, (prior, old, new) in sorted(changed.items()):
            if new.kind != "Planet":
                continue
            for tax_field in TAX_NAMES:
                if not _changed(old, new, tax_field):
                    continue
                before = _amount(old.fields.get(tax_field))
                after = _amount(new.fields.get(tax_field))
                if before is None or after is None:
                    continue
                forecast = (
                    "NativeHappyChange" if tax_field == "NativeTaxRate"
                    else "ColHappyChange"
                )
                events.append(_build_event(
                    kind="PLANET_TAX_PREVIEW_CHANGE",
                    request_index=index, entity=name,
                    previous_index=prior,
                    tax_field=tax_field,
                    tax_before=before, tax_after=after,
                    preview_field=forecast,
                    preview_before=old.fields.get(forecast),
                    preview_after=new.fields.get(forecast),
                    status="CLIENT_FORECAST_ONLY",
                ))

    return {
        "game_id": game_id, "player_id": player_id, "turn": turn,
        "source_segments": source_segments,
        "save_count": len(records),
        "status": "CLIENT_OBSERVATIONS_ORDERED_NOT_HOST_VERIFIED",
        "first_seen_entity_baselines_not_creations": first_seen,
        "events": events,
    }


def analyze_client_economic_evidence(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Safely stitch owner-HAR windows, extract typed client economic events.

    This output intentionally includes game/player identifiers and
    observed numeric game data. Keep output PRIVATE and review prior
    to external sharing. It has no API credentials or Note.Body text.
    """
    if not isinstance(bundle, Mapping) or bundle.get("schema") != (
        "planets-lab.har-save-capture-bundle.v1"
    ):
        raise NuSavePayloadError("not a local redacted HAR save bundle")
    sessions = bundle.get("sessions")
    if not isinstance(sessions, list) or len(sessions) > MAX_WINDOWS:
        raise NuSavePayloadError("missing or excessive sessions")

    groups: dict[tuple[int, int, int], list[tuple[datetime | None, SavedRequest]]] = defaultdict(list)
    segments: dict[tuple[int, int, int], int] = defaultdict(int)
    total = 0
    for session in sessions:
        parsed = parse_capture(session)
        rows = session["observations"]
        if not parsed:
            continue
        identity = (parsed[0].game_id, parsed[0].player_id, parsed[0].turn)
        segments[identity] += 1
        for row, request in zip(rows, parsed):
            groups[identity].append((_timestamp(row), request))
            total += 1
            if total > MAX_EVENTS:
                raise NuSavePayloadError("excessive observations")

    windows = [
        _analyze_window(*identity, records, source_segments=segments[identity])
        for identity, records in sorted(groups.items())
    ]
    counts: dict[str, int] = defaultdict(int)
    ordered_saves = 0
    for window in windows:
        if not window["status"].startswith("ABSTAIN"):
            ordered_saves += window["save_count"]
        for event in window["events"]:
            counts[event["kind"]] += 1
            if event["kind"] == "PENDING_TRANSFER_STATE_CHANGE":
                counts[event["status"]] += 1
            if event["kind"] == "STARBASE_BUILD_SPENDING_COHANGE":
                counts[event["status"]] += 1
    return {
        "schema": SCHEMA,
        "status": "CLIENT_SAVE_EVIDENCE_ONLY_NOT_NUHOST_VERIFIED",
        "summary": {
            "input_saves": total,
            "unique_game_player_turn_windows": len(windows),
            "overlap_windows": sum(1 for n in segments.values() if n > 1),
            "saves_with_witnessed_order": ordered_saves,
            "windows_abstained": sum(
                1 for w in windows if w["status"].startswith("ABSTAIN")
            ),
            "event_counts": dict(sorted(counts.items())),
            "NuHost_order_execution_verified": False,
            "NuHost_phase_order_verified": False,
        },
        "windows": windows,
    }
