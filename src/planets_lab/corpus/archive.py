from __future__ import annotations

import gzip
import io
import json
import re
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


TURN_MEMBER_RE = re.compile(r"^player(?P<player>\d+)-turn(?P<turn>\d+)\.trn$")


@dataclass(frozen=True, order=True)
class TurnMember:
    player: int
    turn: int
    name: str


def _open_archive(data: bytes, *, validate: bool = True) -> zipfile.ZipFile:
    buffer = io.BytesIO(data)
    if not zipfile.is_zipfile(buffer):
        raise ValueError("response is not a ZIP archive")
    buffer.seek(0)
    archive = zipfile.ZipFile(buffer)
    if validate:
        bad = archive.testzip()
        if bad is not None:
            archive.close()
            raise ValueError(f"ZIP CRC failure at {bad!r}")
    return archive


def archive_members(data: bytes) -> tuple[str, ...]:
    with _open_archive(data) as archive:
        return tuple(archive.namelist())


def turn_members_from_names(names: Iterable[str]) -> tuple[TurnMember, ...]:
    result: list[TurnMember] = []
    for name in names:
        match = TURN_MEMBER_RE.fullmatch(name)
        if match is None:
            continue
        result.append(
            TurnMember(
                player=int(match.group("player")),
                turn=int(match.group("turn")),
                name=name,
            )
        )
    return tuple(sorted(result))


def turn_members(data: bytes) -> tuple[TurnMember, ...]:
    return turn_members_from_names(archive_members(data))


def visit_archive_turn_members(
    data: bytes,
    visitor: Callable[[TurnMember, bytes], None],
) -> tuple[str, ...]:
    """Read and CRC-check an archive in one pass while visiting turn members.

    ``ZipFile.testzip()`` decompresses every member. Calling it before separately
    reading every ``.trn`` therefore doubles decompression work. This helper opens
    the ZIP without a preliminary ``testzip`` and relies on ``ZipFile.read`` to
    perform each member CRC check while its payload is consumed. Non-turn members
    are also read once so a successful visit validates the complete archive.
    """

    with _open_archive(data, validate=False) as archive:
        infos = tuple(archive.infolist())
        names = tuple(info.filename for info in infos)
        turns = turn_members_from_names(names)
        turn_names = {member.name for member in turns}

        for member in turns:
            try:
                raw = archive.read(member.name)
            except KeyError as exc:
                raise ValueError(f"archive member not found: {member.name}") from exc
            visitor(member, raw)

        for info in infos:
            if info.is_dir() or info.filename in turn_names:
                continue
            archive.read(info)

    return names


def read_archive_member(data: bytes, name: str) -> bytes:
    with _open_archive(data) as archive:
        try:
            return archive.read(name)
        except KeyError as exc:
            raise ValueError(f"archive member not found: {name}") from exc


def read_archive_members(
    data: bytes,
    names: tuple[str, ...] | list[str],
) -> dict[str, bytes]:
    """Read many ZIP members after one archive validation/open cycle.

    Historical /game/loadall archives can contain thousands of .trn members.
    Re-opening and CRC-testing the whole ZIP for every member makes normalization
    effectively quadratic in archive size. Bulk reading keeps validation linear.
    """

    result: dict[str, bytes] = {}
    with _open_archive(data) as archive:
        for name in names:
            try:
                result[name] = archive.read(name)
            except KeyError as exc:
                raise ValueError(f"archive member not found: {name}") from exc
    return result


def inspect_turn_member(data: bytes, member: TurnMember | str) -> dict[str, Any]:
    name = member.name if isinstance(member, TurnMember) else member
    raw = read_archive_member(data, name)
    payload = raw
    transport = "plain"

    if payload[:2] == b"\x1f\x8b":
        try:
            payload = gzip.decompress(payload)
        except OSError as exc:
            raise ValueError(f"invalid gzip payload in {name}") from exc
        transport = "gzip"

    report: dict[str, Any] = {
        "member": name,
        "archive_bytes": len(raw),
        "decoded_bytes": len(payload),
        "magic_hex": raw[:16].hex(),
        "transport": transport,
    }

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        report["format"] = "binary"
        return report

    report["format"] = "utf8-text"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        report["text_prefix"] = text[:80].replace("\n", "\\n").replace("\r", "\\r")
        return report

    report["format"] = "json"
    report["json_type"] = type(parsed).__name__
    if isinstance(parsed, dict):
        report["top_level_keys"] = sorted(parsed.keys())
        shapes: dict[str, Any] = {}
        for key, value in parsed.items():
            if isinstance(value, list):
                shapes[key] = {"type": "list", "len": len(value)}
            elif isinstance(value, dict):
                shapes[key] = {
                    "type": "dict",
                    "keys": sorted(value.keys())[:80],
                }
            else:
                shapes[key] = {"type": type(value).__name__}
        report["top_level_shapes"] = shapes
    elif isinstance(parsed, list):
        report["length"] = len(parsed)
        if parsed:
            report["item_type"] = type(parsed[0]).__name__
            if isinstance(parsed[0], dict):
                report["item_keys"] = sorted(parsed[0].keys())[:80]
    return report
