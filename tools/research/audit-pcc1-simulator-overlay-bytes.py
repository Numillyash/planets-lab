#!/usr/bin/env python3
"""
Audit the exact Turbo/Borland Pascal overlay bytes for the historical PCC1
ccSim unit.

This is intentionally a local archaeology tool. It does not copy any external
binary into Git; it reads the already-downloaded PCC packages under
artifacts/external-sources/pcc1-lineage and writes only local derived reports.

The key trick is that Turbo Pascal keeps a small resident overlay thunk/control
segment in CC.EXE. Its header starts with INT 3F (bytes CD 3F) and contains the
file offset, code size and relocation-table size for the corresponding unit in
CC.OVR. The .MAP gives us the ccSim segment selector and exact routine offsets
inside the overlaid code image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = ROOT / "artifacts" / "external-sources" / "pcc1-lineage"
DEFAULT_VERSIONS = ("1120", "1121", "1122")

SYMBOL_RE = re.compile(r"^\s*([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\S+)")
SEGMENT_TABLE_RE = re.compile(
    r"^\s*([0-9A-Fa-f]+)H\s+([0-9A-Fa-f]+)H\s+([0-9A-Fa-f]+)H\s+(\S+)\s+CODE\s*$"
)

TARGETS = (
    "SetShipOwner",
    "SortFCBO",
    "CalcBattleOrder",
    "Attacking",
    "KeepVCR",
    "MakeVCR",
    "MakePlanetVCR",
    "FillInPlanetAggressiveness",
    "SimulateOnce",
    "Simulate",
)


@dataclass
class MapInfo:
    version: str
    path: str
    segment: int
    segment_name: Optional[str]
    resident_start: Optional[int]
    resident_stop: Optional[int]
    resident_length: Optional[int]
    symbols: list[tuple[int, str]]

    @property
    def max_symbol_offset(self) -> int:
        return max(off for off, _ in self.symbols)


@dataclass
class OvrHead:
    exe_file_offset: int
    source: str
    signature: int
    ret_ofs: int
    ovr_offset: int
    code_bytes: int
    reloc_bytes: int
    entry_count: int
    next_seg: int
    load_seg: int
    reprieve: int
    next_loaded: int

    @property
    def reloc_count(self) -> Optional[int]:
        if self.reloc_bytes % 2:
            return None
        return self.reloc_bytes // 2


@dataclass
class ExtractedUnit:
    version: str
    map_info: MapInfo
    head: OvrHead
    exe_path: str
    ovr_path: str
    code_raw: bytes
    code_normalized: bytes
    relocation_offsets: list[int]
    invalid_relocation_offsets: list[int]

    def summary(self) -> dict:
        return {
            "version": self.version,
            "map": self.map_info.path,
            "map_segment": f"{self.map_info.segment:04X}",
            "resident_start": None
            if self.map_info.resident_start is None
            else f"0x{self.map_info.resident_start:X}",
            "resident_length": None
            if self.map_info.resident_length is None
            else f"0x{self.map_info.resident_length:X}",
            "overlay_header": {
                **asdict(self.head),
                "signature_hex": f"0x{self.head.signature:04X}",
                "ovr_offset_hex": f"0x{self.head.ovr_offset:X}",
                "code_bytes_hex": f"0x{self.head.code_bytes:X}",
                "reloc_bytes_hex": f"0x{self.head.reloc_bytes:X}",
            },
            "raw_sha256": sha256(self.code_raw),
            "normalized_sha256": sha256(self.code_normalized),
            "relocation_offsets": len(self.relocation_offsets),
            "invalid_relocation_offsets": self.invalid_relocation_offsets,
        }


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def find_one(root: Path, name: str) -> Path:
    hits = [p for p in root.rglob("*") if p.is_file() and p.name.lower() == name.lower()]
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one {name} under {root}, got {len(hits)}: {hits}")
    return hits[0]


def parse_map(version: str, path: Path) -> MapInfo:
    lines = path.read_text(errors="replace").splitlines()

    raw_symbols: list[tuple[int, int, str]] = []
    for line in lines:
        m = SYMBOL_RE.match(line)
        if m:
            raw_symbols.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3)))

    calc = [(seg, off) for seg, off, name in raw_symbols if name.lower() == "calcbattleorder"]
    if len(calc) != 1:
        raise RuntimeError(f"{path}: expected exactly one CalcBattleOrder, got {calc}")
    segment = calc[0][0]

    dedup: dict[tuple[int, str], None] = {}
    for seg, off, name in raw_symbols:
        if seg == segment:
            dedup[(off, name)] = None
    symbols = sorted(dedup)

    resident_start = resident_stop = resident_length = None
    segment_name = None
    wanted_start = segment << 4
    for line in lines:
        m = SEGMENT_TABLE_RE.match(line)
        if not m:
            continue
        start = int(m.group(1), 16)
        stop = int(m.group(2), 16)
        length = int(m.group(3), 16)
        name = m.group(4)
        if start == wanted_start:
            resident_start, resident_stop, resident_length, segment_name = start, stop, length, name
            break

    return MapInfo(
        version=version,
        path=str(path),
        segment=segment,
        segment_name=segment_name,
        resident_start=resident_start,
        resident_stop=resident_stop,
        resident_length=resident_length,
        symbols=symbols,
    )


def parse_ovrhead(exe: bytes, off: int, source: str) -> Optional[OvrHead]:
    # Turbo Pascal overlay control header, 22 bytes.
    if off < 0 or off + 22 > len(exe):
        return None
    signature, ret_ofs = struct.unpack_from("<HH", exe, off)
    ovr_offset = u32(exe, off + 4)
    code_bytes, reloc_bytes, entry_count, next_seg, load_seg, reprieve, next_loaded = struct.unpack_from(
        "<HHHHHHH", exe, off + 8
    )
    return OvrHead(
        exe_file_offset=off,
        source=source,
        signature=signature,
        ret_ofs=ret_ofs,
        ovr_offset=ovr_offset,
        code_bytes=code_bytes,
        reloc_bytes=reloc_bytes,
        entry_count=entry_count,
        next_seg=next_seg,
        load_seg=load_seg,
        reprieve=reprieve,
        next_loaded=next_loaded,
    )


def plausible(head: OvrHead, ovr_size: int, min_code_bytes: int) -> bool:
    if head.signature != 0x3FCD:  # bytes CD 3F == INT 3F
        return False
    if head.code_bytes <= min_code_bytes:
        return False
    if head.code_bytes > 0x10000:
        return False
    if head.reloc_bytes > 0x10000:
        return False
    if head.entry_count == 0 or head.entry_count > 4096:
        return False
    if head.ovr_offset >= ovr_size:
        return False
    end = head.ovr_offset + head.code_bytes + head.reloc_bytes
    if end > ovr_size:
        return False
    return True


def find_overlay_header(exe: bytes, ovr: bytes, mi: MapInfo) -> OvrHead:
    if len(exe) < 0x1C or exe[:2] not in (b"MZ", b"ZM"):
        raise RuntimeError("CC.EXE is not a recognizable MZ executable")

    header_bytes = u16(exe, 8) * 16
    candidates: list[OvrHead] = []

    exact_offsets = [
        ("mz_header_plus_map_segment", header_bytes + (mi.segment << 4)),
        ("map_segment_raw", mi.segment << 4),
    ]
    seen = set()
    for source, off in exact_offsets:
        if off in seen:
            continue
        seen.add(off)
        h = parse_ovrhead(exe, off, source)
        if h and plausible(h, len(ovr), mi.max_symbol_offset):
            candidates.append(h)

    # If the direct map conversion is not enough, scan every INT 3F signature
    # and validate the overlay metadata around it.
    pos = 0
    while True:
        pos = exe.find(b"\xCD\x3F", pos)
        if pos < 0:
            break
        if pos not in seen:
            h = parse_ovrhead(exe, pos, "signature_scan")
            if h and plausible(h, len(ovr), mi.max_symbol_offset):
                candidates.append(h)
        pos += 1

    if not candidates:
        diag = {
            "mz_header_bytes": header_bytes,
            "map_segment": f"{mi.segment:04X}",
            "map_linear": mi.segment << 4,
            "max_symbol_offset": f"0x{mi.max_symbol_offset:X}",
            "exe_size": len(exe),
            "ovr_size": len(ovr),
        }
        raise RuntimeError("no plausible ccSim overlay header found: " + json.dumps(diag, indent=2))

    # Prefer the exact map-derived candidate; otherwise choose the smallest
    # fitting code image (the ccSim overlay should fit the last symbol tightly).
    def score(h: OvrHead) -> tuple[int, int, int]:
        exact_rank = 0 if h.source == "mz_header_plus_map_segment" else 1 if h.source == "map_segment_raw" else 2
        slack = h.code_bytes - mi.max_symbol_offset
        return (exact_rank, slack, h.exe_file_offset)

    candidates.sort(key=score)
    best = candidates[0]

    # Avoid silently picking among equally plausible scan-only candidates.
    if best.source == "signature_scan":
        same = [h for h in candidates if score(h)[:2] == score(best)[:2]]
        if len(same) > 1:
            raise RuntimeError(
                "ambiguous overlay headers: "
                + json.dumps([asdict(h) for h in candidates[:10]], indent=2)
            )
    return best


def extract_unit(version: str, base: Path) -> ExtractedUnit:
    main_dir = base / "extracted" / f"cc{version}"
    db_dir = base / "extracted" / f"cc{version}db"

    exe_path = find_one(main_dir, "CC.EXE")
    ovr_path = find_one(main_dir, "CC.OVR")
    maps = sorted(p for p in db_dir.rglob("*.MAP") if p.is_file())
    if len(maps) != 1:
        raise RuntimeError(f"expected one MAP under {db_dir}, got {maps}")
    map_path = maps[0]

    mi = parse_map(version, map_path)
    exe = exe_path.read_bytes()
    ovr = ovr_path.read_bytes()
    head = find_overlay_header(exe, ovr, mi)

    code_start = head.ovr_offset
    code_end = code_start + head.code_bytes
    reloc_end = code_end + head.reloc_bytes
    code_raw = ovr[code_start:code_end]
    reloc_blob = ovr[code_end:reloc_end]

    relocation_offsets: list[int] = []
    invalid: list[int] = []
    if len(reloc_blob) % 2 == 0:
        for i in range(0, len(reloc_blob), 2):
            roff = u16(reloc_blob, i)
            if roff + 1 < len(code_raw):
                relocation_offsets.append(roff)
            else:
                invalid.append(roff)
    else:
        invalid.append(-1)

    normalized = bytearray(code_raw)
    for roff in relocation_offsets:
        # Segment relocation patches a 16-bit word.
        normalized[roff : roff + 2] = b"\x00\x00"

    return ExtractedUnit(
        version=version,
        map_info=mi,
        head=head,
        exe_path=str(exe_path),
        ovr_path=str(ovr_path),
        code_raw=code_raw,
        code_normalized=bytes(normalized),
        relocation_offsets=relocation_offsets,
        invalid_relocation_offsets=invalid,
    )


def symbol_ranges(mi: MapInfo) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    syms = mi.symbols
    for i, (off, name) in enumerate(syms):
        end = syms[i + 1][0] if i + 1 < len(syms) else 0x10000
        out[name] = (off, end)
    return out


def changed_ranges(a: bytes, b: bytes) -> list[tuple[int, int]]:
    n = min(len(a), len(b))
    ranges: list[tuple[int, int]] = []
    start: Optional[int] = None
    for i in range(n):
        different = a[i] != b[i]
        if different and start is None:
            start = i
        elif not different and start is not None:
            ranges.append((start, i))
            start = None
    if start is not None:
        ranges.append((start, n))
    if len(a) != len(b):
        ranges.append((n, max(len(a), len(b))))
    return ranges


def changed_count(a: bytes, b: bytes) -> int:
    n = min(len(a), len(b))
    return sum(x != y for x, y in zip(a[:n], b[:n])) + abs(len(a) - len(b))


def containing_symbols(mi: MapInfo, start: int, end: int) -> list[str]:
    syms = mi.symbols
    names = []
    for i, (off, name) in enumerate(syms):
        next_off = syms[i + 1][0] if i + 1 < len(syms) else 0x10000
        if start < next_off and end > off:
            names.append(name)
    return names


def compare_units(a: ExtractedUnit, b: ExtractedUnit) -> dict:
    result: dict = {
        "versions": [a.version, b.version],
        "raw": {
            "same_length": len(a.code_raw) == len(b.code_raw),
            "changed_bytes": changed_count(a.code_raw, b.code_raw),
            "sha256_equal": sha256(a.code_raw) == sha256(b.code_raw),
        },
        "normalized": {
            "same_length": len(a.code_normalized) == len(b.code_normalized),
            "changed_bytes": changed_count(a.code_normalized, b.code_normalized),
            "sha256_equal": sha256(a.code_normalized) == sha256(b.code_normalized),
        },
        "targets": {},
        "changed_ranges": [],
    }

    for start, end in changed_ranges(a.code_normalized, b.code_normalized):
        result["changed_ranges"].append(
            {
                "start": f"0x{start:X}",
                "end_exclusive": f"0x{end:X}",
                "length": end - start,
                "symbols_a": containing_symbols(a.map_info, start, end),
                "symbols_b": containing_symbols(b.map_info, start, end),
            }
        )

    ar = symbol_ranges(a.map_info)
    br = symbol_ranges(b.map_info)
    for target in TARGETS:
        if target not in ar or target not in br:
            result["targets"][target] = {"status": "missing"}
            continue
        a0, a1 = ar[target]
        b0, b1 = br[target]
        aa_raw = a.code_raw[a0:min(a1, len(a.code_raw))]
        bb_raw = b.code_raw[b0:min(b1, len(b.code_raw))]
        aa = a.code_normalized[a0:min(a1, len(a.code_normalized))]
        bb = b.code_normalized[b0:min(b1, len(b.code_normalized))]
        result["targets"][target] = {
            "range_a": [f"0x{a0:X}", f"0x{a1:X}"],
            "range_b": [f"0x{b0:X}", f"0x{b1:X}"],
            "length_a": len(aa),
            "length_b": len(bb),
            "raw_sha256_a": sha256(aa_raw),
            "raw_sha256_b": sha256(bb_raw),
            "normalized_sha256_a": sha256(aa),
            "normalized_sha256_b": sha256(bb),
            "raw_equal": aa_raw == bb_raw,
            "normalized_equal": aa == bb,
            "normalized_changed_bytes": changed_count(aa, bb),
        }
    return result


def write_unit_artifacts(unit: ExtractedUnit, derived: Path) -> None:
    derived.mkdir(parents=True, exist_ok=True)
    (derived / f"cc{unit.version}-ccsim-overlay.raw.bin").write_bytes(unit.code_raw)
    (derived / f"cc{unit.version}-ccsim-overlay.reloc-normalized.bin").write_bytes(unit.code_normalized)
    (derived / f"cc{unit.version}-ccsim-overlay.json").write_text(
        json.dumps(unit.summary(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--versions", nargs="+", default=list(DEFAULT_VERSIONS))
    args = ap.parse_args()

    base = args.base
    derived = base / "derived" / "overlay-byte-audit"
    report_path = base / "pcc1-simulator-overlay-byte-audit.json"

    units: dict[str, ExtractedUnit] = {}
    for version in args.versions:
        unit = extract_unit(version, base)
        units[version] = unit
        write_unit_artifacts(unit, derived)

    comparisons = []
    for i in range(len(args.versions) - 1):
        comparisons.append(compare_units(units[args.versions[i]], units[args.versions[i + 1]]))

    report = {
        "schema": "planets-lab.pcc1-simulator-overlay-byte-audit.v1",
        "base": str(base),
        "units": {v: units[v].summary() for v in args.versions},
        "comparisons": comparisons,
        "interpretation_guardrail": (
            "PCC1/CCBSim is the same implementation lineage as PCC2/c2ng. "
            "Binary equality or deltas here are source-lineage archaeology, not independent NuHost evidence."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("===== PCC1 CCSIM OVERLAY BYTE AUDIT =====")
    for version in args.versions:
        s = units[version].summary()
        h = s["overlay_header"]
        print(
            f"{version}: map_segment={s['map_segment']} "
            f"head_source={h['source']} exe_off=0x{h['exe_file_offset']:X} "
            f"ovr_off={h['ovr_offset_hex']} code={h['code_bytes_hex']} "
            f"reloc={h['reloc_bytes_hex']} entries={h['entry_count']} "
            f"norm_sha256={s['normalized_sha256']}"
        )
        if s["invalid_relocation_offsets"]:
            print(f"  WARNING invalid relocation offsets: {s['invalid_relocation_offsets'][:20]}")

    for cmp_result in comparisons:
        va, vb = cmp_result["versions"]
        print()
        print(f"===== COMPARE {va} -> {vb} =====")
        print(
            "raw: "
            f"equal={cmp_result['raw']['sha256_equal']} "
            f"changed_bytes={cmp_result['raw']['changed_bytes']}"
        )
        print(
            "reloc-normalized: "
            f"equal={cmp_result['normalized']['sha256_equal']} "
            f"changed_bytes={cmp_result['normalized']['changed_bytes']}"
        )
        print("--- target routines ---")
        for target, info in cmp_result["targets"].items():
            if info.get("status") == "missing":
                print(f"{target}: missing")
                continue
            print(
                f"{target}: len={info['length_a']}->{info['length_b']} "
                f"raw_equal={info['raw_equal']} "
                f"normalized_equal={info['normalized_equal']} "
                f"normalized_changed_bytes={info['normalized_changed_bytes']}"
            )
        if cmp_result["changed_ranges"]:
            print("--- normalized changed ranges ---")
            for row in cmp_result["changed_ranges"][:100]:
                print(
                    f"{row['start']}..{row['end_exclusive']} len={row['length']} "
                    f"symbols_a={','.join(row['symbols_a']) or '-'} "
                    f"symbols_b={','.join(row['symbols_b']) or '-'}"
                )
            if len(cmp_result["changed_ranges"]) > 100:
                print(f"... {len(cmp_result['changed_ranges']) - 100} more ranges in JSON report")
        else:
            print("normalized changed ranges: none")

    print()
    print("===== OVERLAY BYTE AUDIT COMPLETE =====")
    print(f"report:  {report_path}")
    print(f"derived: {derived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
