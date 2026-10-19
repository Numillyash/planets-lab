"""Strict V2 owner-scoped order observations: ship cargo AND starbase tech.

This is an opt-in *operator-signed* local observation format, not proof of
NuHost accepting or executing orders. No HTTP collection, token handling,
clock validation beyond an externally supplied boundary, or private uploads.

V1 is intentionally unchanged: no v1 envelope is interpreted as v2 and
no tech order may be silently stripped during canonical serialization.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
from typing import Any, Mapping, Sequence

from planets_lab.core import GameState
from planets_lab.sim.orders import (
    PlayerOrders, StarbaseTechUpgradeOrder, TurnOrders,
)
from planets_lab.sim.planetary_owner_capture import (
    KEY_PATTERN, TAG_PATTERN, ORIGIN, SCOPE, _AUTH_FIELDS,
    _ENVELOPE_FIELDS, _PAYLOAD_FIELDS, _owner_row,
)
from planets_lab.sim.planetary_order_capture import (
    OrderCaptureInvalid, _canonical, _decode_orders, _exact_keys, _key,
    _utc, state_fingerprint,
)

SCHEMA_V2 = "planets-lab.prehost-owner-observation.v2"
DOMAIN_V2 = b"planets-lab-owner-order-observation-v2\x00"
ADMITTED_V2 = "ADMITTED_ALL_PLAYERS_OPERATOR_SIGNED_V2_NOT_NUHOST_VERIFIED"
TECH_FIELDS = ("hull", "engine", "beam", "torpedo")
STATE_FIELDS = ("tech_hull", "tech_engine", "tech_beam", "tech_torpedo")
TECH_ORDER_KEYS = frozenset(("planet_id", *TECH_FIELDS))
OWNER_ROW_KEYS_V2 = frozenset(("player_id", "ship_orders", "starbase_tech_orders"))


def _serialize_owner_v2(state: GameState, owner: PlayerOrders) -> dict[str, Any]:
    if type(owner) is not PlayerOrders or type(owner.player_id) is not int:
        raise OrderCaptureInvalid("expected owner-scoped explicit PlayerOrders")
    # Reuse the V1 canonical cargo guard with the V2-only technology
    # field removed *from the temporary V1 validation record only*.
    stripped = PlayerOrders(player_id=owner.player_id, ship_orders=owner.ship_orders)
    ships = _owner_row(state, stripped)
    seen: set[int] = set()
    tech_rows: list[dict[str, Any]] = []
    for upgrade in owner.starbase_tech_orders:
        if type(upgrade) is not StarbaseTechUpgradeOrder:
            raise OrderCaptureInvalid("invalid starbase technology order type")
        pid = upgrade.planet_id
        if type(pid) is not int or pid <= 0 or pid in seen:
            raise OrderCaptureInvalid("invalid or repeated technology order planet")
        seen.add(pid)
        base = state.starbases.get(pid)
        planet = state.planets.get(pid)
        if (base is None or planet is None or base.owner_id != owner.player_id
                or planet.owner_id != owner.player_id):
            raise OrderCaptureInvalid("technology order requires known owned base and planet")
        record: dict[str, Any] = {"planet_id": pid}
        changed = False
        for label, state_field in zip(TECH_FIELDS, STATE_FIELDS):
            target = getattr(upgrade, label)
            existing = getattr(base, state_field)
            if type(existing) is not int or not 1 <= existing <= 10:
                raise OrderCaptureInvalid("invalid complete prestate technology")
            if target is None:
                record[label] = None
                continue
            if type(target) is not int or not existing <= target <= 10:
                raise OrderCaptureInvalid("invalid upgrade target or downgrade")
            record[label] = target
            changed |= target > existing
        if not changed:
            raise OrderCaptureInvalid("technology order has no positive upgrade")
        tech_rows.append(record)
    return {
        "player_id": owner.player_id,
        "ship_orders": ships["ship_orders"],
        "starbase_tech_orders": sorted(tech_rows, key=lambda x: x["planet_id"]),
    }


def _decode_all_v2(
    state: GameState, rows: Mapping[int, Mapping[str, Any]],
) -> TurnOrders:
    if set(rows) != set(state.players):
        raise OrderCaptureInvalid("one signed order row required for every game player")
    # Reuse old canonical ship decoder; this is only temporary validation,
    # not a V1-signed record, and retains each explicitly empty owner.
    cargo_rows: list[dict[str, Any]] = []
    for pid in sorted(rows):
        record = _exact_keys(rows[pid], OWNER_ROW_KEYS_V2, "V2 owner row")
        if type(record["player_id"]) is not int or record["player_id"] != pid:
            raise OrderCaptureInvalid("V2 owner id mismatch")
        cargo_rows.append({"player_id": pid, "ship_orders": record["ship_orders"]})
    decoded_cargo = _decode_orders(state, cargo_rows)
    by_player = {}
    for pid in sorted(rows):
        raw_tech = rows[pid]["starbase_tech_orders"]
        if not isinstance(raw_tech, list):
            raise OrderCaptureInvalid("V2 technology order list required, including empty")
        upgrades: list[StarbaseTechUpgradeOrder] = []
        for raw in raw_tech:
            record = _exact_keys(raw, TECH_ORDER_KEYS, "V2 technology order")
            planet_id = record["planet_id"]
            if type(planet_id) is not int:
                raise OrderCaptureInvalid("invalid V2 planet ID")
            upgrades.append(StarbaseTechUpgradeOrder(
                planet_id=planet_id, **{name: record[name] for name in TECH_FIELDS},
            ))
        owner = PlayerOrders(
            player_id=pid,
            ship_orders=decoded_cargo.by_player[pid].ship_orders,
            starbase_tech_orders=tuple(upgrades),
        )
        if _serialize_owner_v2(state, owner) != rows[pid]:
            raise OrderCaptureInvalid("noncanonical, invalid or reordered V2 order record")
        by_player[pid] = owner
    return TurnOrders(by_player=by_player)


def seal_owner_observation_v2(
    state: GameState, player_orders: PlayerOrders, *,
    captured_at_utc: str, key: bytes, key_id: str,
) -> dict[str, Any]:
    """Attest a single owner's *local* complete-order assertion, not receipt."""
    _key(key)
    _utc(captured_at_utc, "owner capture time")
    if type(key_id) is not str or KEY_PATTERN.fullmatch(key_id) is None:
        raise OrderCaptureInvalid("invalid V2 signer key identifier")
    row = _serialize_owner_v2(state, player_orders)
    payload = {
        "schema": SCHEMA_V2, "scope": SCOPE, "source": ORIGIN,
        "game_id": state.game_id, "turn": state.turn,
        "player_id": row["player_id"], "captured_at_utc": captured_at_utc,
        "pre_state_sha256": state_fingerprint(state),
        "owner_orders_complete": True,
        "server_submission_acknowledged": False,
        "player_orders": row,
    }
    return {
        "payload": payload,
        "attestation": {
            "algorithm": "HMAC-SHA256", "key_id": key_id,
            "tag_hex": hmac.new(key, DOMAIN_V2 + _canonical(payload), sha256).hexdigest(),
        },
    }


@dataclass(frozen=True, slots=True)
class OwnerBundleAdmissionV2:
    status: str
    orders: TurnOrders | None = None
    reason: str | None = None
    covered_player_ids: tuple[int, ...] = ()
    missing_player_ids: tuple[int, ...] = ()

    @property
    def admitted(self) -> bool:
        return self.status == ADMITTED_V2 and self.orders is not None


def aggregate_owner_observations_v2(
    envelopes: Sequence[Any], state: GameState, *,
    owner_keyrings: Mapping[int, Mapping[str, bytes]],
    observed_host_start_utc: str | None,
) -> OwnerBundleAdmissionV2:
    """Strict all-player aggregation; signatures ≠ server receipt/clock witness."""
    try:
        if type(envelopes) not in (list, tuple) or not envelopes:
            return OwnerBundleAdmissionV2(
                "ABSTAIN_NO_OWNER_OBSERVATIONS", reason="missing owner records",
            )
        if observed_host_start_utc is None:
            return OwnerBundleAdmissionV2(
                "ABSTAIN_UNWITNESSED_TIME", reason="no externally witnessed Host-start boundary",
            )
        host_start = _utc(observed_host_start_utc, "Host start")
        expected_state = state_fingerprint(state)
        rows: dict[int, Mapping[str, Any]] = {}
        for envelope in envelopes:
            root = _exact_keys(envelope, _ENVELOPE_FIELDS, "V2 envelope")
            payload = _exact_keys(root["payload"], _PAYLOAD_FIELDS, "V2 payload")
            auth = _exact_keys(root["attestation"], _AUTH_FIELDS, "V2 attestation")
            if (payload["schema"] != SCHEMA_V2 or payload["scope"] != SCOPE
                    or payload["source"] != ORIGIN
                    or payload["owner_orders_complete"] is not True
                    or payload["server_submission_acknowledged"] is not False):
                return OwnerBundleAdmissionV2(
                    "ABSTAIN_INVALID_SCOPE", reason="unsupported V2 capture assertions",
                )
            pid = payload["player_id"]
            if type(pid) is not int or pid not in state.players:
                return OwnerBundleAdmissionV2("ABSTAIN_FOREIGN_OWNER")
            if pid in rows:
                return OwnerBundleAdmissionV2("ABSTAIN_DUPLICATE_OWNER")
            if auth["algorithm"] != "HMAC-SHA256":
                return OwnerBundleAdmissionV2("ABSTAIN_INVALID_ATTESTATION")
            kid, tag = auth["key_id"], auth["tag_hex"]
            if (type(kid) is not str or KEY_PATTERN.fullmatch(kid) is None
                    or type(tag) is not str or TAG_PATTERN.fullmatch(tag) is None):
                return OwnerBundleAdmissionV2("ABSTAIN_INVALID_ATTESTATION")
            keys = owner_keyrings.get(pid)
            if not isinstance(keys, Mapping) or kid not in keys:
                return OwnerBundleAdmissionV2("ABSTAIN_UNTRUSTED_OWNER_KEY")
            expected_mac = hmac.new(
                _key(keys[kid]), DOMAIN_V2 + _canonical(payload), sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_mac, tag):
                return OwnerBundleAdmissionV2("ABSTAIN_INVALID_ATTESTATION")
            if (type(payload["game_id"]) is not type(state.game_id)
                    or payload["game_id"] != state.game_id
                    or type(payload["turn"]) is not int or payload["turn"] != state.turn
                    or payload["pre_state_sha256"] != expected_state):
                return OwnerBundleAdmissionV2("ABSTAIN_STATE_IDENTITY")
            if _utc(payload["captured_at_utc"], "capture time") >= host_start:
                return OwnerBundleAdmissionV2("ABSTAIN_NOT_PREHOST")
            row = _exact_keys(payload["player_orders"], OWNER_ROW_KEYS_V2, "V2 owner row")
            if type(row["player_id"]) is not int or row["player_id"] != pid:
                return OwnerBundleAdmissionV2("ABSTAIN_OWNER_MISMATCH")
            rows[pid] = row
        missing = tuple(sorted(set(state.players) - set(rows)))
        if missing:
            return OwnerBundleAdmissionV2(
                "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE",
                reason="missing explicitly attested owner order rows",
                covered_player_ids=tuple(sorted(rows)),
                missing_player_ids=missing,
            )
        return OwnerBundleAdmissionV2(
            ADMITTED_V2, orders=_decode_all_v2(state, rows),
            covered_player_ids=tuple(sorted(rows)),
        )
    except (OrderCaptureInvalid, ValueError, TypeError, KeyError, AttributeError) as exc:
        return OwnerBundleAdmissionV2("ABSTAIN_INVALID_OWNER_BUNDLE", reason=str(exc))
