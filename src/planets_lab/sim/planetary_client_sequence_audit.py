"""Strict replay of metadata-only client save → ready chronology.

This validates one atomic, client-authored (report, trace) bundle and
recomputes aggregate counters. It is NOT an independent clock witness,
HTTP server order receipt, or proof of NuHost execution. It never uses
game/player/ship IDs, request/response bodies, headers or URLs.

Both the input trace and all client time values are untrusted; accepting
a self-consistent report does not authenticate it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

BUNDLE_SCHEMA = "planets-lab.client-save-ready-bundle.v1"
SCHEMA = "planets-lab.client-save-ready-metadata.v1"
TRACE_STATUS = "LOCAL_CLIENT_TIMELINE_NOT_HOST_PROOF"
REPORT_STATUS = "CLIENT_SEQUENCE_OBSERVED_NOT_NUHOST_ORDER_RECEIPT"
REPORT_FIELDS = frozenset((
    "schema", "status", "local_clock_provenance",
    "total_save_calls", "total_turnready_calls",
    "retained_metadata_events", "dropped_metadata_events", "pending_events",
    "transport_error_events", "client_visible_save_success_events",
    "client_visible_ready_success_events",
    "candidate_ordered_client_sequences_not_host_verified",
    "ambiguous_or_unconfirmed_ready_events",
    "repeated_ready_without_fresh_save_events",
    "failed_or_overlapping_save_window_events",
    "verified_server_order_acceptance",
    "independently_witnessed_host_start",
    "nuhost_execution_verified", "no_extra_network_requests",
    "request_or_response_payloads_retained",
))
EVENT_FIELDS = frozenset((
    "id", "route", "transport", "method", "started_ms", "settled_ms",
    "http_status", "app_success", "outcome",
))
COUNT_FIELDS = frozenset((
    "total_save_calls", "total_turnready_calls", "retained_metadata_events",
    "dropped_metadata_events", "pending_events", "transport_error_events",
    "client_visible_save_success_events", "client_visible_ready_success_events",
    "candidate_ordered_client_sequences_not_host_verified",
    "ambiguous_or_unconfirmed_ready_events",
    "repeated_ready_without_fresh_save_events",
    "failed_or_overlapping_save_window_events",
))
MAX_EVENTS = 64


class ClientSequenceInvalid(ValueError):
    """Generic failure: never echo untrusted content or private paths."""


def _fail() -> None:
    raise ClientSequenceInvalid("ABSTAIN_INVALID_OR_UNTRUSTED_CLIENT_METADATA")


def _exact(value: Any, fields: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail()
    return value


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _time(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _success(event: Mapping[str, Any]) -> bool:
    status = event["http_status"]
    return (event["outcome"] == "HTTP_RESPONSE"
            and type(status) is int and 200 <= status < 300
            and event["app_success"] is True)


@dataclass(frozen=True, slots=True)
class ClientSequenceAudit:
    schema: str = "planets-lab.client-sequence-audit.v1"
    status: str = "SELF_CONSISTENT_CLIENT_METADATA_NOT_NUHOST_VERIFIED"
    retained_metadata_events: int = 0
    total_save_calls: int = 0
    total_turnready_calls: int = 0
    dropped_metadata_events: int = 0
    candidate_ordered_client_sequences_not_host_verified: int = 0
    ambiguous_or_unconfirmed_ready_events: int = 0
    repeated_ready_without_fresh_save_events: int = 0
    failed_or_overlapping_save_window_events: int = 0
    independently_witnessed_host_start: bool = False
    independent_server_order_acceptance_verified: bool = False
    nuhost_execution_verified: bool = False
    raw_client_metadata_returned: bool = False


def audit_atomic_metadata_bundle(bundle: Any) -> ClientSequenceAudit:
    """Recompute all declared report counts; reject unknown/private fields.

    No actual evidence verification takes place: this is purely a logical
    consistency check of bounded client metadata captured at one instant.
    """
    root = _exact(bundle, frozenset(("schema", "report", "trace")))
    if root["schema"] != BUNDLE_SCHEMA:
        _fail()
    report = _exact(root["report"], REPORT_FIELDS)
    trace = _exact(root["trace"], frozenset(("schema", "status", "events")))
    if (report["schema"] != SCHEMA or trace["schema"] != SCHEMA
            or report["status"] != REPORT_STATUS or trace["status"] != TRACE_STATUS
            or report["local_clock_provenance"] != "UNWITNESSED_CLIENT_PERFORMANCE_CLOCK"
            or report["verified_server_order_acceptance"] is not False
            or report["independently_witnessed_host_start"] is not False
            or report["nuhost_execution_verified"] is not False
            or report["no_extra_network_requests"] is not True
            or report["request_or_response_payloads_retained"] is not False):
        _fail()
    if not all(_nonnegative_int(report[key]) for key in COUNT_FIELDS):
        _fail()
    raw = trace["events"]
    if type(raw) is not list or len(raw) > MAX_EVENTS:
        _fail()
    total = report["total_save_calls"] + report["total_turnready_calls"]
    dropped = report["dropped_metadata_events"]
    if total != len(raw) + dropped or report["retained_metadata_events"] != len(raw):
        _fail()
    if raw and (type(raw[0]) is not dict or type(raw[-1]) is not dict
                or raw[0].get("id") != dropped + 1
                or raw[-1].get("id") != total):
        _fail()

    events: list[dict[str, Any]] = []
    last_id = dropped
    last_started: float = -1
    for source in raw:
        event = _exact(source, EVENT_FIELDS)
        event_id = event["id"]
        if (type(event_id) is not int or event_id != last_id + 1
                or event["route"] not in ("save", "turnready")
                or event["transport"] not in ("fetch", "xhr")
                or event["method"] not in ("GET", "POST", "PUT", "PATCH", "DELETE", "OTHER")
                or not _time(event["started_ms"])
                or event["started_ms"] < last_started
                or event["outcome"] not in ("PENDING", "TRANSPORT_ERROR", "HTTP_RESPONSE")):
            _fail()
        last_id = event_id
        last_started = event["started_ms"]
        status = event["http_status"]
        success = event["app_success"]
        end = event["settled_ms"]
        if event["outcome"] == "PENDING":
            if end is not None or status is not None or success is not None:
                _fail()
        elif event["outcome"] == "TRANSPORT_ERROR":
            if (not _time(end) or end < event["started_ms"]
                    or status is not None or success is not None):
                _fail()
        else:
            if (not _time(end) or end < event["started_ms"]
                    or (status is not None and
                        (type(status) is not int or not 100 <= status <= 599))
                    or success not in (None, True, False)
                    or (success is not None and type(success) is not bool)):
                _fail()
        events.append(event)
    if sum(e["route"] == "save" for e in events) > report["total_save_calls"]:
        _fail()
    if sum(e["route"] == "turnready" for e in events) > report["total_turnready_calls"]:
        _fail()

    ready = [e for e in events if e["route"] == "turnready"]
    candidate = ambiguous = no_fresh = overlap = 0
    previous = None
    for item in ready:
        window = [e for e in events if e["route"] == "save" and
                  (previous is None or e["id"] > previous["id"])
                  and e["id"] < item["id"]]
        prior = previous
        previous = item
        if not window:
            no_fresh += 1
        clock_valid = _time(item["started_ms"]) and _time(item["settled_ms"]) and (
            item["settled_ms"] >= item["started_ms"])
        prior_inflight = prior is not None and (
            not _time(prior["settled_ms"])
            or prior["settled_ms"] > item["started_ms"])
        saves_success = bool(window) and all(
            _success(e) and _time(e["settled_ms"])
            and e["settled_ms"] >= e["started_ms"]
            and e["settled_ms"] <= item["started_ms"]
            for e in window)
        crossing = clock_valid and any(
            e["route"] == "save" and e["id"] > item["id"]
            and e["started_ms"] <= item["settled_ms"] for e in events)
        if (dropped or not _success(item) or not clock_valid
                or prior_inflight or not saves_success or crossing):
            ambiguous += 1
            if window and (prior_inflight or not saves_success
                           or crossing or not clock_valid):
                overlap += 1
        else:
            candidate += 1

    expected = {
        "pending_events": sum(e["outcome"] == "PENDING" for e in events),
        "transport_error_events": sum(
            e["outcome"] == "TRANSPORT_ERROR" for e in events
        ),
        "client_visible_save_success_events": sum(
            e["route"] == "save" and _success(e) for e in events
        ),
        "client_visible_ready_success_events": sum(
            e["route"] == "turnready" and _success(e) for e in events
        ),
        "candidate_ordered_client_sequences_not_host_verified": candidate,
        "ambiguous_or_unconfirmed_ready_events": ambiguous,
        "repeated_ready_without_fresh_save_events": no_fresh,
        "failed_or_overlapping_save_window_events": overlap,
    }
    if any(report[k] != v for k, v in expected.items()):
        _fail()
    return ClientSequenceAudit(
        retained_metadata_events=len(events),
        total_save_calls=report["total_save_calls"],
        total_turnready_calls=report["total_turnready_calls"],
        dropped_metadata_events=dropped,
        candidate_ordered_client_sequences_not_host_verified=candidate,
        ambiguous_or_unconfirmed_ready_events=ambiguous,
        repeated_ready_without_fresh_save_events=no_fresh,
        failed_or_overlapping_save_window_events=overlap,
    )


def safe_metadata_summary(bundle: Any) -> dict[str, Any]:
    return asdict(audit_atomic_metadata_bundle(bundle))
