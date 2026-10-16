"""Owner-scoped pre-Host cargo observations and strict all-player aggregation.

A player can attest ONLY their own observation; another player's silence
must never be synthesized as an empty PlayerOrders in the final TurnOrders.
This is operator-authenticated data, NOT evidence of server-accepted orders
or independent clock provenance. Nothing here calls Planets.nu or reads a
private account, and no private envelope may enter public runtime evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import re
from typing import Any, Mapping, Sequence

from planets_lab.core import GameState
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_order_aware_slice import (
    PlanetaryOrderAwareSlice, PlanetarySliceOutcome,
)
from planets_lab.sim.planetary_order_capture import (
    OrderCaptureInvalid, _canonical, _decode_orders, _exact_keys, _key,
    _serialize_orders, _utc, state_fingerprint,
)

SCHEMA = "planets-lab.prehost-owner-observation.v1"
SCOPE = "one_player_orders_explicit"
ORIGIN = "owner_operator_local_observation_not_server_acknowledged"
ADMITTED = "ADMITTED_ALL_PLAYERS_OPERATOR_SIGNED_NOT_NUHOST_VERIFIED"
KEY_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}")
TAG_PATTERN = re.compile(r"[0-9a-f]{64}")
DOMAIN = b"planets-lab-owner-order-observation-v1\x00"

_PAYLOAD_FIELDS = frozenset({
    "schema", "scope", "source", "game_id", "turn", "player_id",
    "captured_at_utc", "pre_state_sha256", "owner_orders_complete",
    "server_submission_acknowledged", "player_orders",
})
_AUTH_FIELDS = frozenset({"algorithm", "key_id", "tag_hex"})
_ENVELOPE_FIELDS = frozenset({"payload", "attestation"})


def _owner_row(state: GameState, orders: PlayerOrders) -> dict[str, Any]:
    if type(orders) is not PlayerOrders or type(orders.player_id) is not int:
        raise OrderCaptureInvalid("owner order record must be a PlayerOrders")
    player_id = orders.player_id
    if player_id not in state.players:
        raise OrderCaptureInvalid("owner not present in prestate")
    # Use the existing canonical serialization guard to reject unsupported
    # ship-order fields and foreign ships. Other rows here are validation
    # scaffolding ONLY and are never persisted, attested, or reported.
    validation_orders = TurnOrders(by_player={
        pid: orders if pid == player_id else PlayerOrders(player_id=pid)
        for pid in state.players
    })
    rows = _serialize_orders(state, validation_orders)
    return next(row for row in rows if row["player_id"] == player_id)


def seal_owner_observation(
    state: GameState,
    player_orders: PlayerOrders,
    *,
    captured_at_utc: str,
    key: bytes,
    key_id: str,
) -> dict[str, Any]:
    """Attest one authorized owner's locally observed pre-Host orders.

    The caller—not this function—must establish account authority, the
    capture clock, and whether the server acknowledged the submission.
    Captures deliberately attest NO server acknowledgement in V1.
    """
    _key(key)
    _utc(captured_at_utc, "capture time")
    if type(key_id) is not str or KEY_PATTERN.fullmatch(key_id) is None:
        raise OrderCaptureInvalid("invalid signer key id")
    row = _owner_row(state, player_orders)
    payload = {
        "schema": SCHEMA,
        "scope": SCOPE,
        "source": ORIGIN,
        "game_id": state.game_id,
        "turn": state.turn,
        "player_id": row["player_id"],
        "captured_at_utc": captured_at_utc,
        "pre_state_sha256": state_fingerprint(state),
        "owner_orders_complete": True,
        "server_submission_acknowledged": False,
        "player_orders": row,
    }
    signature = hmac.new(key, DOMAIN + _canonical(payload), sha256).hexdigest()
    return {
        "payload": payload,
        "attestation": {
            "algorithm": "HMAC-SHA256",
            "key_id": key_id,
            "tag_hex": signature,
        },
    }


@dataclass(frozen=True, slots=True)
class OwnerBundleAdmission:
    status: str
    orders: TurnOrders | None = None
    reason: str | None = None
    covered_player_ids: tuple[int, ...] = ()
    missing_player_ids: tuple[int, ...] = ()

    @property
    def admitted(self) -> bool:
        return self.status == ADMITTED and self.orders is not None


def aggregate_owner_observations(
    envelopes: Sequence[Any],
    state: GameState,
    *,
    owner_keyrings: Mapping[int, Mapping[str, bytes]],
    observed_host_start_utc: str | None,
) -> OwnerBundleAdmission:
    """Admit complete, independently owner-scoped records only.

    Host start is a *caller-provided* boundary, not a verified signed
    witness. This may produce an internally supported simulation but
    never a NuHost factual order-acceptance or historical parity claim.
    """
    try:
        state_hash = state_fingerprint(state)
        if type(envelopes) not in (tuple, list) or not envelopes:
            return OwnerBundleAdmission(
                "ABSTAIN_NO_OWNER_OBSERVATIONS", reason="no owner records",
            )
        if observed_host_start_utc is None:
            return OwnerBundleAdmission(
                "ABSTAIN_UNWITNESSED_TIME", reason="Host start not witnessed",
            )
        host_start = _utc(observed_host_start_utc, "Host start")
        rows: dict[int, dict[str, Any]] = {}
        for envelope in envelopes:
            root = _exact_keys(envelope, _ENVELOPE_FIELDS, "owner envelope")
            payload = _exact_keys(root["payload"], _PAYLOAD_FIELDS, "owner payload")
            auth = _exact_keys(root["attestation"], _AUTH_FIELDS, "owner attestation")
            if (payload["schema"] != SCHEMA or payload["scope"] != SCOPE
                    or payload["source"] != ORIGIN
                    or payload["owner_orders_complete"] is not True
                    or payload["server_submission_acknowledged"] is not False):
                return OwnerBundleAdmission(
                    "ABSTAIN_INVALID_SCOPE", reason="unsupported owner evidence claim",
                )
            player_id = payload["player_id"]
            if type(player_id) is not int or player_id not in state.players:
                return OwnerBundleAdmission(
                    "ABSTAIN_FOREIGN_OWNER", reason="unknown owner in capture",
                )
            if player_id in rows:
                return OwnerBundleAdmission(
                    "ABSTAIN_DUPLICATE_OWNER", reason="duplicate owner capture",
                )
            if (type(payload["game_id"]) is not type(state.game_id)
                    or payload["game_id"] != state.game_id
                    or type(payload["turn"]) is not int
                    or payload["turn"] != state.turn
                    or payload["pre_state_sha256"] != state_hash):
                return OwnerBundleAdmission(
                    "ABSTAIN_STATE_IDENTITY", reason="game/turn/prestate mismatch",
                )
            if auth["algorithm"] != "HMAC-SHA256":
                return OwnerBundleAdmission(
                    "ABSTAIN_INVALID_ATTESTATION", reason="unknown signing algorithm",
                )
            key_id, tag = auth["key_id"], auth["tag_hex"]
            if (type(key_id) is not str or KEY_PATTERN.fullmatch(key_id) is None
                    or type(tag) is not str or TAG_PATTERN.fullmatch(tag) is None):
                return OwnerBundleAdmission(
                    "ABSTAIN_INVALID_ATTESTATION", reason="malformed signer metadata",
                )
            owner_keys = owner_keyrings.get(player_id)
            if not isinstance(owner_keys, Mapping) or key_id not in owner_keys:
                return OwnerBundleAdmission(
                    "ABSTAIN_UNTRUSTED_OWNER_KEY", reason="no trusted signer for owner",
                )
            key = _key(owner_keys[key_id])
            expected = hmac.new(key, DOMAIN + _canonical(payload), sha256).hexdigest()
            if not hmac.compare_digest(tag, expected):
                return OwnerBundleAdmission(
                    "ABSTAIN_INVALID_ATTESTATION", reason="owner signature mismatch",
                )
            if _utc(payload["captured_at_utc"], "capture time") >= host_start:
                return OwnerBundleAdmission(
                    "ABSTAIN_NOT_PREHOST", reason="owner capture not before Host",
                )
            record = _exact_keys(
                payload["player_orders"], frozenset({"player_id", "ship_orders"}),
                "player order record",
            )
            if type(record["player_id"]) is not int or record["player_id"] != player_id:
                return OwnerBundleAdmission(
                    "ABSTAIN_OWNER_MISMATCH", reason="player order/owner mismatch",
                )
            rows[player_id] = record

        all_players = set(state.players)
        missing = tuple(sorted(all_players - rows.keys()))
        if missing:
            return OwnerBundleAdmission(
                "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE",
                reason="at least one player's orders not captured",
                covered_player_ids=tuple(sorted(rows)),
                missing_player_ids=missing,
            )
        # Deterministic canonical replay catches unsupported, foreign
        # or duplicate ship orders even when a signer authenticated them.
        decoded = _decode_orders(state, [rows[pid] for pid in sorted(rows)])
        return OwnerBundleAdmission(
            ADMITTED, orders=decoded,
            covered_player_ids=tuple(sorted(rows)),
        )
    except (OrderCaptureInvalid, TypeError, ValueError, KeyError, AttributeError) as exc:
        return OwnerBundleAdmission("ABSTAIN_INVALID_OWNER_BUNDLE", reason=str(exc))


@dataclass(frozen=True, slots=True)
class OwnerBundleSimulation:
    status: str
    outcome: PlanetarySliceOutcome | None = None
    reason: str | None = None


def simulate_owner_bundle(
    slice_: PlanetaryOrderAwareSlice,
    state: GameState,
    envelopes: Sequence[Any],
    *,
    owner_keyrings: Mapping[int, Mapping[str, bytes]],
    observed_host_start_utc: str | None,
    seed: int = 0,
) -> OwnerBundleSimulation:
    admitted = aggregate_owner_observations(
        envelopes, state, owner_keyrings=owner_keyrings,
        observed_host_start_utc=observed_host_start_utc,
    )
    if not admitted.admitted:
        return OwnerBundleSimulation(admitted.status, reason=admitted.reason)
    assert admitted.orders is not None
    outcome = slice_.attempt_step(state, admitted.orders, seed=seed)
    if not outcome.supported:
        return OwnerBundleSimulation(
            "ABSTAIN_UNSUPPORTED_SIMULATION", reason=outcome.abstain_reason,
        )
    return OwnerBundleSimulation(
        "MODELED_OWNER_BUNDLE_NOT_NUHOST_DIFFERENTIAL", outcome=outcome,
    )
