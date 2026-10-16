"""Fail-closed operator-attested PRE-Host cargo order admission, research only.

HMAC authenticates an operator's *record*, not the Planets.nu server's
acceptance of the orders and not the truth of a self-reported timestamp.
For a historical comparison a separate, trustworthy Host-start boundary
and complete owner-scoped source capture must be supplied externally.
Never publish raw private order envelopes or HMAC keys as runtime evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
from typing import Any, Mapping

from planets_lab.core import GameState
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders,
)
from planets_lab.sim.planet_cargo_transfer_phase import TRANSFER_FIELDS
from planets_lab.sim.planetary_order_aware_slice import (
    PlanetaryOrderAwareSlice, PlanetarySliceOutcome,
)

SCHEMA = "planets-lab.prehost-order-capture.v1"
ADMITTED = "ADMITTED_OPERATOR_ATTESTED_NOT_NUHOST_VERIFIED"
ORIGIN = "operator_prehost_submission"
COVERAGE = "complete_declared_game_players"
UTC_PATTERN = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
PAYLOAD_KEYS = frozenset((
    "schema", "game_id", "turn", "captured_at_utc", "source",
    "coverage", "player_ids", "pre_state_sha256", "orders",
))
TRANSFER_KEYS = frozenset(("planet_id", "direction", *TRANSFER_FIELDS))


class OrderCaptureInvalid(ValueError):
    """Bad or unsupported capture; not a license to infer an order."""


def _exact_keys(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise OrderCaptureInvalid(f"{label}: exact keys required: {sorted(keys)}")
    return value


def _integer(value: Any, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise OrderCaptureInvalid(f"{label}: invalid nonnegative integer")
    return value


def _utc(raw: Any, label: str) -> datetime:
    if not isinstance(raw, str) or not UTC_PATTERN.fullmatch(raw):
        raise OrderCaptureInvalid(f"{label}: expected UTC seconds with Z suffix")
    try:
        when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OrderCaptureInvalid(f"{label}: invalid datetime") from exc
    if when.utcoffset().total_seconds() != 0:
        raise OrderCaptureInvalid(f"{label}: non-UTC datetime")
    return when


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        raise OrderCaptureInvalid("capture is not canonical JSON") from exc


def state_fingerprint(state: GameState) -> str:
    """Hash model-visible full state, excluding potentially private metadata."""
    state.validate()
    projection = {
        "game_id": state.game_id, "turn": state.turn,
        "players": {k: asdict(v) for k, v in sorted(state.players.items())},
        "planets": {k: asdict(v) for k, v in sorted(state.planets.items())},
        "ships": {k: asdict(v) for k, v in sorted(state.ships.items())},
        "starbases": {k: asdict(v) for k, v in sorted(state.starbases.items())},
        "ion_storms": {k: asdict(v) for k, v in sorted(state.ion_storms.items())},
    }
    return sha256(_canonical(projection)).hexdigest()


def _serialize_orders(state: GameState, orders: TurnOrders) -> list[dict[str, Any]]:
    # Merely omitting a player is NOT evidence of an empty submitted turn.
    if set(orders.by_player) != set(state.players):
        raise OrderCaptureInvalid("explicit orders required for every declared game player")
    rows: list[dict[str, Any]] = []
    globally_seen: set[int] = set()
    for player_id, owner_orders in sorted(orders.by_player.items()):
        _integer(player_id, "player id", positive=True)
        if type(owner_orders) is not PlayerOrders or owner_orders.player_id != player_id:
            raise OrderCaptureInvalid("player id mismatch")
        ships: list[dict[str, Any]] = []
        for entry in owner_orders.ship_orders:
            if type(entry) is not ShipOrder or entry.planet_transfer is None:
                raise OrderCaptureInvalid("only explicit cargo-transfer orders supported")
            if any(getattr(entry, name) is not None for name in (
                "waypoint_x", "waypoint_y", "warp", "mission",
                "primary_enemy_id", "friendly_code",
            )):
                raise OrderCaptureInvalid("unknown ship-order fields cannot be elided")
            ship_id = _integer(entry.ship_id, "ship id", positive=True)
            if ship_id in globally_seen:
                raise OrderCaptureInvalid("duplicate ship order across players")
            globally_seen.add(ship_id)
            ship = state.ships.get(ship_id)
            if ship is None or ship.owner_id != player_id:
                raise OrderCaptureInvalid("ship not owned by submitting player")
            transfer = entry.planet_transfer
            if type(transfer) is not PlanetCargoTransferOrder:
                raise OrderCaptureInvalid("unsupported transfer payload type")
            _integer(transfer.planet_id, "planet id", positive=True)
            if transfer.direction not in ("planet_to_ship", "ship_to_planet"):
                raise OrderCaptureInvalid("unsupported transfer direction")
            amounts = {}
            for name in TRANSFER_FIELDS:
                amounts[name] = _integer(getattr(transfer, name), name)
            ships.append({
                "ship_id": ship_id,
                "planet_transfer": {
                    "planet_id": transfer.planet_id,
                    "direction": transfer.direction,
                    **amounts,
                },
            })
        rows.append({"player_id": player_id, "ship_orders": ships})
    return rows


def _decode_orders(state: GameState, raw: Any) -> TurnOrders:
    if not isinstance(raw, list):
        raise OrderCaptureInvalid("orders must be a list, including empty player rows")
    by_player: dict[int, PlayerOrders] = {}
    for row in raw:
        owner = _exact_keys(row, frozenset(("player_id", "ship_orders")), "player")
        player_id = _integer(owner["player_id"], "player id", positive=True)
        if player_id in by_player:
            raise OrderCaptureInvalid("duplicate player capture")
        entries = owner["ship_orders"]
        if not isinstance(entries, list):
            raise OrderCaptureInvalid("ship orders must be a list")
        ship_orders = []
        for entry in entries:
            ship_row = _exact_keys(
                entry, frozenset(("ship_id", "planet_transfer")), "ship order",
            )
            transfer = _exact_keys(ship_row["planet_transfer"], TRANSFER_KEYS, "transfer")
            values = {
                name: _integer(transfer[name], name) for name in TRANSFER_FIELDS
            }
            planet_id = _integer(transfer["planet_id"], "planet id", positive=True)
            direction = transfer["direction"]
            if direction not in ("planet_to_ship", "ship_to_planet"):
                raise OrderCaptureInvalid("unknown cargo direction")
            ship_orders.append(ShipOrder(
                ship_id=_integer(ship_row["ship_id"], "ship id", positive=True),
                planet_transfer=PlanetCargoTransferOrder(
                    planet_id=planet_id, direction=direction, **values,
                ),
            ))
        by_player[player_id] = PlayerOrders(
            player_id=player_id, ship_orders=tuple(ship_orders),
        )
    decoded = TurnOrders(by_player=by_player)
    # Round-trip equality also checks ordering, ownership, duplicates and
    # unmodelled fields in one place; canonical capture serialization only.
    if raw != _serialize_orders(state, decoded):
        raise OrderCaptureInvalid("noncanonical, incomplete or reordered order capture")
    return decoded


def _key(key: bytes) -> bytes:
    if type(key) is not bytes or len(key) < 32:
        raise OrderCaptureInvalid("capture signing key must be 32+ bytes")
    return key


def seal_prehost_capture(
    state: GameState,
    orders: TurnOrders,
    *,
    captured_at_utc: str,
    key: bytes,
    key_id: str,
) -> dict[str, Any]:
    """Called by a trusted *pre-Host* order recorder; no network acquisition.

    This is a local attestation, not server acknowledgement or external
    timestamp proof. The user/capture process must independently establish
    that it captured submitted orders BEFORE NuHost executed the turn.
    """
    _key(key)
    _utc(captured_at_utc, "capture time")
    if not isinstance(key_id, str) or not 1 <= len(key_id) <= 64 or not re.fullmatch(
        r"[A-Za-z0-9._-]+", key_id
    ):
        raise OrderCaptureInvalid("invalid key identifier")
    payload = {
        "schema": SCHEMA, "game_id": state.game_id, "turn": state.turn,
        "captured_at_utc": captured_at_utc, "source": ORIGIN,
        "coverage": COVERAGE,
        "player_ids": sorted(state.players),
        "pre_state_sha256": state_fingerprint(state),
        "orders": _serialize_orders(state, orders),
    }
    tag = hmac.new(key, _canonical(payload), sha256).hexdigest()
    return {
        "payload": payload,
        "attestation": {
            "algorithm": "HMAC-SHA256", "key_id": key_id,
            "tag_hex": tag,
        },
    }


@dataclass(frozen=True, slots=True)
class CaptureAdmission:
    status: str
    orders: TurnOrders | None = None
    reason: str | None = None

    @property
    def admitted(self) -> bool:
        return self.status == ADMITTED and self.orders is not None


def admit_prehost_capture(
    envelope: Any,
    state: GameState,
    *,
    keyring: Mapping[str, bytes],
    observed_host_start_utc: str | None,
) -> CaptureAdmission:
    """Fail closed unless witnessed Host-start boundary and attested record match.

    observed_host_start_utc must come from independent trusted operations
    logging. Merely passing a string cannot certify that the clock is genuine.
    """
    try:
        root = _exact_keys(envelope, frozenset(("payload", "attestation")), "envelope")
        payload = _exact_keys(root["payload"], PAYLOAD_KEYS, "payload")
        auth = _exact_keys(
            root["attestation"],
            frozenset(("algorithm", "key_id", "tag_hex")), "attestation",
        )
        if auth["algorithm"] != "HMAC-SHA256":
            raise OrderCaptureInvalid("unrecognized attestation method")
        key_id, digest = auth["key_id"], auth["tag_hex"]
        if not isinstance(key_id, str) or key_id not in keyring:
            return CaptureAdmission("ABSTAIN_UNTRUSTED_KEY", reason="unknown signing key")
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            return CaptureAdmission("ABSTAIN_INVALID_ATTESTATION", reason="malformed digest")
        expected = hmac.new(_key(keyring[key_id]), _canonical(payload), sha256).hexdigest()
        if not hmac.compare_digest(expected, digest):
            return CaptureAdmission("ABSTAIN_INVALID_ATTESTATION", reason="signature mismatch")

        # Source and scope are independently checked against the supplied
        # full-information state, never inferred from post-Host resources.
        if payload["schema"] != SCHEMA or payload["source"] != ORIGIN:
            raise OrderCaptureInvalid("unsupported capture schema/source")
        if payload["coverage"] != COVERAGE:
            return CaptureAdmission("ABSTAIN_INCOMPLETE_SCOPE", reason="non-exhaustive scope")
        if (type(payload["game_id"]) is not type(state.game_id)
                or payload["game_id"] != state.game_id
                or type(payload["turn"]) is not int or payload["turn"] != state.turn
                or payload["pre_state_sha256"] != state_fingerprint(state)):
            return CaptureAdmission("ABSTAIN_STATE_IDENTITY", reason="pre-Host state mismatch")
        if payload["player_ids"] != sorted(state.players):
            return CaptureAdmission("ABSTAIN_INCOMPLETE_SCOPE", reason="game players not covered")
        if observed_host_start_utc is None:
            return CaptureAdmission("ABSTAIN_UNWITNESSED_TIME",
                                    reason="no independent Host-start boundary supplied")
        captured = _utc(payload["captured_at_utc"], "capture time")
        host_start = _utc(observed_host_start_utc, "witness Host start")
        if captured >= host_start:
            return CaptureAdmission("ABSTAIN_NOT_PREHOST", reason="capture not before Host")
        orders = _decode_orders(state, payload["orders"])
        return CaptureAdmission(ADMITTED, orders=orders)
    except (OrderCaptureInvalid, TypeError, ValueError, KeyError, AttributeError) as exc:
        return CaptureAdmission("ABSTAIN_INVALID_CAPTURE", reason=str(exc))


@dataclass(frozen=True, slots=True)
class CapturedSimulation:
    status: str
    outcome: PlanetarySliceOutcome | None
    reason: str | None = None


def simulate_admitted_capture(
    slice_: PlanetaryOrderAwareSlice,
    state: GameState,
    envelope: Any,
    *,
    keyring: Mapping[str, bytes],
    observed_host_start_utc: str | None,
    seed: int = 0,
) -> CapturedSimulation:
    """No simulation or leaked partial state when admission abstains."""
    admission = admit_prehost_capture(
        envelope, state, keyring=keyring,
        observed_host_start_utc=observed_host_start_utc,
    )
    if not admission.admitted:
        return CapturedSimulation(admission.status, None, admission.reason)
    assert admission.orders is not None
    outcome = slice_.attempt_step(state, admission.orders, seed=seed)
    if not outcome.supported:
        return CapturedSimulation("ABSTAIN_UNSUPPORTED_SIMULATION", None,
                                  outcome.abstain_reason)
    return CapturedSimulation(
        "MODELED_OPERATOR_ATTESTED_NOT_NUHOST_DIFFERENTIAL",
        outcome,
    )
