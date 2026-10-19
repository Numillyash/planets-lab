"""Privacy-bound preflight for passive Planets.nu /game/save client captures.

The V1 DevTools observer captures *client-visible* request/response pairs,
NOT a NuHost execution receipt. This module produces only aggregate counts.
No source game/player IDs, payload paths, value excerpts, fingerprints,
secret material, capture records or destination URL are returned.

No network, API or DuckDB dependencies. Pure analysis is compatible with
unit tests and local-only use; raw private captures MUST NOT be committed or
passed as --include to public runtime-evidence scripts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any, Mapping

SCHEMA = "planets-lab.save-payload-capture.v1"
REPORT_STATUS = "CLIENT_PAYLOAD_CAPTURE_NOT_NUHOST_ORDER_ACK"
REDACTION_SCOPE = "KNOWN_CREDENTIAL_FIELD_NAMES_ONLY_REVIEW_BEFORE_SHARING"
MAX_EVENTS = 10
SECRET_FIELD = re.compile(
    r"(?:^key$|(?:^|[_-])(?:auth|token|secret|password|passwd|cookie|session|"
    r"credential|bearer|csrf|signature)(?:$|[_-])|api[_-]?key|save[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|authorization|authkey|account[_-]?password)",
    re.IGNORECASE,
)
REDACTED = "<REDACTED_CREDENTIAL>"


class SaveEvidenceInvalid(ValueError):
    """Unusable or unsafe client observation; deliberately no input in error."""


@dataclass(frozen=True, slots=True)
class SaveReadinessAggregate:
    schema: str = "planets-lab.m2-save-evidence-readiness.v1"
    status: str = "CLIENT_TRANSPORT_ONLY_NOT_NUHOST_VERIFIED"
    retained_save_events: int = 0
    total_save_route_calls: int = 0
    total_turnready_route_calls_unlinked: int = 0
    save_calls_not_retained: int = 0
    parseable_nontruncated_request_events: int = 0
    unavailable_or_truncated_request_events: int = 0
    explicit_http_and_app_success_events: int = 0
    http_failure_events: int = 0
    application_failure_events: int = 0
    ambiguous_or_missing_response_events: int = 0
    transport_error_events: int = 0
    any_known_field_redaction_marker_events: int = 0
    verified_order_payload_mapping: bool = False
    signed_all_owner_orders_verified: bool = False
    independent_server_order_acceptance_verified: bool = False
    independent_host_start_witness_verified: bool = False
    complete_pre_and_post_host_states_verified: bool = False
    nuhost_execution_verified: bool = False
    private_payload_content_returned: bool = False


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _scan_markers(value: Any) -> tuple[bool, bool]:
    """Return (redaction observed, omission/truncation observed).

    Known credential fields not masked cause unconditional rejection; no
    sensitive key/value is included in error messages or any result.
    """
    redacted = omitted = False
    stack = [value]
    nodes = 0
    while stack:
        item = stack.pop()
        nodes += 1
        if nodes > 300_000:
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        if isinstance(item, dict):
            for k, v in item.items():
                if type(k) is not str:
                    raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
                if SECRET_FIELD.search(k) and v != REDACTED:
                    raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
                stack.append(v)
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str):
            redacted |= item == REDACTED
            omitted |= item.startswith("<OMITTED_") or item in (
                "<REQUEST_BODY_UNAVAILABLE>", "<RESPONSE_UNREADABLE>",
                "<STREAM_OR_BINARY_NOT_DECODED>", "<PARSING_FAILED>",
            )
        elif item is not None and type(item) not in (int, float, bool):
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
    return redacted, omitted


def analyze_save_capture(report: Mapping[str, Any]) -> SaveReadinessAggregate:
    """Classify observations *without inferring accepted/Host-executed orders*.

    A 2xx HTTP code + JSON success:true only confirms a client-visible
    success-shaped response to /game/save. It does NOT confirm that a
    particular submitted order survived server validation or executed.
    The /game/turnready counter has no timestamp/event correspondence.
    """
    if (type(report) is not dict or report.get("schema") != SCHEMA
            or report.get("status") != REPORT_STATUS
            or report.get("redaction_scope") != REDACTION_SCOPE
            or report.get("no_extra_requests") is not True
            or report.get("verified_NuHost_order_mapping") is not False):
        raise SaveEvidenceInvalid("invalid_or_unsafe_capture")

    counts = report.get("route_counters")
    events = report.get("observations")
    retained = report.get("observed_save_calls_retained")
    if (not isinstance(counts, dict)
            or set(counts) != {"save", "turnready"}
            or not all(_nonnegative_int(n) for n in counts.values())
            or not isinstance(events, list) or len(events) > MAX_EVENTS
            or not _nonnegative_int(retained) or retained != len(events)
            or counts["save"] < retained):
        raise SaveEvidenceInvalid("invalid_or_unsafe_capture")

    metrics = {
        "parseable_nontruncated_request_events": 0,
        "unavailable_or_truncated_request_events": 0,
        "explicit_http_and_app_success_events": 0,
        "http_failure_events": 0,
        "application_failure_events": 0,
        "ambiguous_or_missing_response_events": 0,
        "transport_error_events": 0,
        "any_known_field_redaction_marker_events": 0,
    }
    for event in events:
        if (type(event) is not dict
                or event.get("transport") not in ("fetch", "xhr")
                or event.get("method") not in ("GET", "POST", "PUT", "PATCH", "DELETE")):
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        status_code = event.get("http_status")
        if status_code is not None and (
            type(status_code) is not int or not 100 <= status_code <= 599
        ):
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        request = event.get("request")
        response = event.get("response")
        if (type(request) is not dict
                or set(request) != {"encoding", "body"}
                or type(request["encoding"]) is not str
                or (response is not None and (
                    type(response) is not dict or set(response) != {"encoding", "body"}
                    or type(response["encoding"]) is not str
                ))):
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        # Never emit a key, field value, URL, game ID, secret or input path.
        redact_req, omitted_req = _scan_markers(request["body"])
        redact_resp, _ = _scan_markers(response["body"]) if response else (False, False)
        if redact_req or redact_resp:
            metrics["any_known_field_redaction_marker_events"] += 1
        parseable = (
            request["encoding"] in ("form", "json", "multipart-form")
            and type(request["body"]) in (dict, list)
            and not omitted_req
        )
        if parseable:
            metrics["parseable_nontruncated_request_events"] += 1
        else:
            metrics["unavailable_or_truncated_request_events"] += 1

        if event.get("transport_error") is True:
            metrics["transport_error_events"] += 1
            # Network error is not independently categorized as HTTP failure.
            if status_code is not None:
                raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
            continue
        if "transport_error" in event and event["transport_error"] is not False:
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")

        if status_code is not None and not 200 <= status_code < 300:
            metrics["http_failure_events"] += 1
            continue
        result = response["body"] if response and response["encoding"] == "json" else None
        if (status_code is not None and 200 <= status_code < 300
                and type(result) is dict and result.get("success") is True):
            metrics["explicit_http_and_app_success_events"] += 1
        elif (status_code is not None and 200 <= status_code < 300
                and type(result) is dict and result.get("success") is False):
            metrics["application_failure_events"] += 1
        else:
            metrics["ambiguous_or_missing_response_events"] += 1

    classified = sum(metrics[name] for name in (
        "explicit_http_and_app_success_events",
        "http_failure_events",
        "application_failure_events",
        "ambiguous_or_missing_response_events",
        "transport_error_events",
    ))
    if classified != retained:
        raise SaveEvidenceInvalid("invalid_or_unsafe_capture")

    return SaveReadinessAggregate(
        retained_save_events=retained,
        total_save_route_calls=counts["save"],
        total_turnready_route_calls_unlinked=counts["turnready"],
        save_calls_not_retained=counts["save"] - retained,
        **metrics,
    )


def public_aggregate(report: Mapping[str, Any]) -> dict[str, Any]:
    """Only fixed schema and integer/bool totals; never return source refs."""
    return asdict(analyze_save_capture(report))
