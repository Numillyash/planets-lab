#!/usr/bin/env python3
"""Local, standard-library HAR -> credential-redacted Nu /game/save captures.

No proxy, MITM, browser extension, API key, network access, or account login
is required. It reads an existing Chrome/Edge DevTools Network HAR file,
extracts ONLY authorized Planets.nu XHR/fetch POST /game/save payloads,
and writes one redacted bundle suitable for offline last-seen field analysis.

Usage (Windows):
    py nu_har_save_extract_v1.py --input "C:\capture\session.har" \
       --output "C:\capture\save_bundle_clean.json"

CRITICAL: the ORIGINAL HAR may contain cookies, apikey, savekey, auth
headers and all other network traffic. Keep it on your own device.
The transformed output preserves GAME ORDER DATA for owner-approved
reverse engineering. Review it for unexpected credential fields before
sharing. Do not commit either capture to GitHub.
"""
from __future__ import annotations

import argparse
import base64
from collections import OrderedDict
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit

BUNDLE_SCHEMA = "planets-lab.har-save-capture-bundle.v1"
CAPTURE_SCHEMA = "planets-lab.save-payload-capture.v1"
REDACTED = "<REDACTED_CREDENTIAL>"
MAX_FIELD_COUNT = 10000
MAX_BODY_CHARS = 4_000_000
ENTITY_NAME = re.compile(r"^(?:Ship|Planet|Starbase)[1-9][0-9]*$")
CREDENTIAL_NAME = re.compile(
    r"(?:api.?key|save.?key|access.?token|refresh.?token|"
    r"^key$|^auth$|auth(?:entication|orization)?|bearer|"
    r"password|passwd|cookie|session|jwt|credential|csrf|"
    r"secret|private.?key|email|username|signature)",
    re.I,
)
EMBEDDED_SECRET = re.compile(
    r"(?:api.?key|save.?key|access.?token|refresh.?token|"
    r"authorization|password|cookie|session|jwt)\s*[:=]",
    re.I,
)


class HarExtractError(ValueError):
    pass


def route_kind(url: Any) -> str | None:
    """Return only coarse, known categories; never expose full URLs."""
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("https", "http"):
            return None
        if host != "planets.nu" and not host.endswith(".planets.nu"):
            return None
        path = parsed.path.rstrip("/").lower()
        if path == "/game/save":
            return "save"
        if path == "/game/turnready":
            return "turnready"
    except ValueError:
        return None
    return None


def _redact_legacy_record(value: str) -> str:
    """Preserve actual planet/ship numeric data but mask named secret fields."""
    if len(value) > MAX_BODY_CHARS:
        return "<OMITTED_LARGE_GAME_FIELD>"
    tokens = value.split("|||")
    if len(tokens) <= 1 or not all(":::" in p for p in tokens):
        return REDACTED if EMBEDDED_SECRET.search(value) else value
    output = []
    for token in tokens:
        name, sep, raw = token.partition(":::")
        output.append(name + sep + (REDACTED if CREDENTIAL_NAME.search(name) or
                                    EMBEDDED_SECRET.search(raw) else raw))
    return "|||".join(output)


def redact_values(value: Any, *, depth: int = 0) -> Any:
    """Recursively scrub credential NAMES while preserving game-data values."""
    if depth > 32:
        return "<OMITTED_NESTING_LIMIT>"
    if isinstance(value, Mapping):
        return {
            key: (REDACTED if CREDENTIAL_NAME.search(str(key))
                  else redact_values(item, depth=depth + 1))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_values(item, depth=depth + 1) for item in value]
    if isinstance(value, str):
        if len(value) > MAX_BODY_CHARS:
            return "<OMITTED_LARGE_GAME_FIELD>"
        if "|||" in value and ":::" in value:
            return _redact_legacy_record(value)
        # Preserve arbitrary actual game strings, unless they appear to
        # contain an inline credential assignment. Not foolproof:
        # the owner MUST review unexpected free-text before sharing.
        if EMBEDDED_SECRET.search(value):
            return REDACTED
        stripped = value.strip()
        if (stripped.startswith("{") or stripped.startswith("[")) and len(value) <= MAX_BODY_CHARS:
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (dict, list)):
                    return redact_values(parsed, depth=depth + 1)
            except (ValueError, RecursionError):
                pass
        return value
    return value if value is None or isinstance(value, (bool, int, float)) else "<UNSUPPORTED_VALUE>"


def form_fields(post_data: Any) -> tuple[str, dict[str, Any]] | None:
    """Read POST params from HAR, without ever carrying request headers."""
    if not isinstance(post_data, Mapping):
        return None
    raw = post_data.get("text")
    pairs: list[tuple[Any, Any]]
    if isinstance(raw, str) and len(raw) <= MAX_BODY_CHARS and raw.strip():
        if raw.lstrip().startswith(("{", "[")):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return "json", redact_values(parsed)
            except ValueError:
                return None
        try:
            pairs = parse_qsl(
                raw, keep_blank_values=True, max_num_fields=MAX_FIELD_COUNT,
                errors="replace",
            )
        except ValueError:
            return None
    elif isinstance(post_data.get("params"), list):
        pairs = [(param.get("name"), param.get("value", ""))
                 for param in post_data["params"] if isinstance(param, Mapping)]
    else:
        return None
    if len(pairs) > MAX_FIELD_COUNT:
        return None
    fields: dict[str, Any] = {}
    for key, value in pairs:
        if not isinstance(key, str) or not key or key in fields:
            # Repeated/ambiguous keys cannot be represented by our
            # existing strict per-entity form parser; fail closed.
            return None
        fields[key] = REDACTED if CREDENTIAL_NAME.search(key) else redact_values(value)
    return ("form", fields) if fields else None


def safe_response(response: Any) -> tuple[int | None, dict[str, Any]]:
    """Sanitize JSON response bodies; NEVER include headers or raw HTML."""
    if not isinstance(response, Mapping):
        return None, {"encoding": "unavailable", "body": None}
    raw_status = response.get("status")
    status = raw_status if type(raw_status) is int and 0 <= raw_status <= 599 else None
    content = response.get("content")
    if not isinstance(content, Mapping):
        return status, {"encoding": "unavailable", "body": None}
    text = content.get("text")
    if not isinstance(text, str):
        return status, {"encoding": "unavailable", "body": None}
    if content.get("encoding") == "base64":
        try:
            text = base64.b64decode(text, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return status, {"encoding": "unavailable", "body": None}
    if len(text) > MAX_BODY_CHARS:
        return status, {"encoding": "oversize", "body": None}
    try:
        payload = json.loads(text)
    except ValueError:
        return status, {"encoding": "not_json", "body": None}
    return status, {"encoding": "json", "body": redact_values(payload)}


def extract_har(doc: Mapping[str, Any]) -> dict[str, Any]:
    """One HTML-free bundle, partitioned by (game, player, turn)."""
    if not isinstance(doc, Mapping) or not isinstance(doc.get("log"), Mapping):
        raise HarExtractError("HAR must have a log object")
    entries = doc["log"].get("entries")
    if not isinstance(entries, list):
        raise HarExtractError("HAR log.entries is missing or not an array")

    sessions: dict[tuple[str, str, str], dict[str, Any]] = OrderedDict()
    observed_save_calls = 0
    turnready_calls = 0
    ignored_saves = 0
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        request = entry.get("request")
        if not isinstance(request, Mapping) or request.get("method") != "POST":
            continue
        kind = route_kind(request.get("url"))
        if kind is None:
            continue
        if kind == "turnready":
            turnready_calls += 1
            continue
        observed_save_calls += 1
        parsed = form_fields(request.get("postData"))
        if parsed is None:
            ignored_saves += 1
            continue
        encoding, fields = parsed
        game_id, player_id, turn = (
            fields.get("gameid"), fields.get("playerid"), fields.get("turn")
        )
        if not all(isinstance(x, str) and x.isdecimal() for x in
                   (game_id, player_id, turn)):
            ignored_saves += 1
            continue
        identity = (game_id, player_id, turn)
        if identity not in sessions:
            sessions[identity] = {
                "schema": CAPTURE_SCHEMA,
                "status": "CLIENT_HAR_PAYLOAD_CAPTURE_NOT_NUHOST_ORDER_ACK",
                "observations": [],
                "route_counters": {"save": 0, "turnready": 0},
                "redaction_scope": "KNOWN_CREDENTIAL_FIELD_NAMES_REVIEW_BEFORE_SHARING",
                "no_extra_requests": True,
                "verified_NuHost_order_mapping": False,
            }
        session = sessions[identity]
        session["route_counters"]["save"] += 1
        response_status, response_body = safe_response(entry.get("response"))
        timing = {
            "start_iso": entry.get("startedDateTime") if isinstance(entry.get("startedDateTime"), str) else None,
            "network_duration_ms": entry.get("time") if type(entry.get("time")) in (int, float) else None,
        }
        session["observations"].append({
            "transport": "har",
            "method": "POST",
            "request": {"encoding": encoding, "body": fields},
            "http_status": response_status,
            "response": response_body,
            "timing": timing,
        })

    for session in sessions.values():
        session["observed_save_calls_retained"] = len(session["observations"])

    return {
        "schema": BUNDLE_SCHEMA,
        "status": "LOCAL_HAR_GAME_DATA_REDACTED_CLIENT_REQUESTS_NOT_NUHOST_ORDERS",
        "counts": {
            "har_entries": len(entries),
            "save_posts_seen": observed_save_calls,
            "save_posts_extract_failed": ignored_saves,
            "save_posts_extracted": observed_save_calls - ignored_saves,
            "turnready_posts_seen": turnready_calls,
            "grouped_sessions": len(sessions),
        },
        "sessions": list(sessions.values()),
        "credentials_not_guaranteed_absent_review_before_sharing": True,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path,
                   help="LOCAL DevTools HAR file; do not share the original")
    p.add_argument("--output", required=True, type=Path,
                   help="Credential-redacted JSON bundle for private review")
    p.add_argument("--overwrite", action="store_true",
                   help="Permit replacing a previous generated bundle")
    args = p.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        p.error("input and output cannot be the same path")
    with args.input.open(encoding="utf-8-sig") as handle:
        bundle = extract_har(json.load(handle))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "x"
    with args.output.open(mode, encoding="utf-8") as output:
        json.dump(bundle, output, ensure_ascii=False, indent=2)
        output.write("\n")
    counts = bundle["counts"]
    print(f"save_posts_seen: {counts['save_posts_seen']}")
    print(f"save_posts_extracted: {counts['save_posts_extracted']}")
    print(f"save_posts_extract_failed: {counts['save_posts_extract_failed']}")
    print(f"turnready_posts_seen: {counts['turnready_posts_seen']}")
    print(f"grouped_sessions: {counts['grouped_sessions']}")
    print("NuHost_order_mapping_verified: False")
    print("Review output for UNEXPECTED credential content before sharing.")
    print(f"Redacted bundle: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, HarExtractError, json.JSONDecodeError) as exc:
        print(f"HAR extraction failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
