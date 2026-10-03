#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys


TARGETS = {
    "both_destroyed": b"Both ships blew up",
    "won": b" won",
    "captured": b" captured",
    "timed_out": b"The battle timed out",
    "ending_damage": b"Ending damage :",
    "ending_shield": b"Ending shield :",
    "status_after_combat": b"Status after combat",
    "status_after_battle": b"Status after battle",
    "afsim_tmp": b"afsim.tmp",
    "afsim_log": b"afsim.log",
    "vcr11_dat": b"vcr11.dat",
}


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def parse_mz(data: bytes) -> dict[str, int]:
    if len(data) < 0x1C or data[:2] not in {b"MZ", b"ZM"}:
        raise ValueError("not an MZ executable")
    fields = {
        "bytes_last_page": u16(data, 0x02),
        "pages": u16(data, 0x04),
        "relocations": u16(data, 0x06),
        "header_paragraphs": u16(data, 0x08),
        "min_extra_paragraphs": u16(data, 0x0A),
        "max_extra_paragraphs": u16(data, 0x0C),
        "initial_ss": u16(data, 0x0E),
        "initial_sp": u16(data, 0x10),
        "checksum": u16(data, 0x12),
        "initial_ip": u16(data, 0x14),
        "initial_cs": u16(data, 0x16),
        "reloc_table_offset": u16(data, 0x18),
        "overlay_number": u16(data, 0x1A),
    }
    fields["load_image_offset"] = fields["header_paragraphs"] * 16
    return fields


def find_all(data: bytes, needle: bytes, start: int = 0, end: int | None = None) -> list[int]:
    if end is None:
        end = len(data)
    out = []
    pos = start
    while True:
        pos = data.find(needle, pos, end)
        if pos < 0:
            break
        out.append(pos)
        pos += 1
    return out


def shortstring_info(data: bytes, pos: int, text: bytes) -> tuple[int, bool]:
    if pos <= 0:
        return pos, False
    prefix = data[pos - 1]
    return pos - 1, prefix == len(text)


def hexdump(data: bytes, start: int, end: int) -> str:
    lines = []
    for off in range(start, end, 16):
        chunk = data[off:min(off + 16, end)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{off:06x}  {hx:<47}  {asc}")
    return "\n".join(lines)


def imm16_refs(data: bytes, value: int, start: int, end: int) -> list[tuple[int, str, int]]:
    """
    Return strong immediate references where we know the instruction boundary
    from the opcode itself.

    Common 16-bit forms used by Turbo/Borland code:
      B8..BF iw   mov reg, imm16
      68 iw       push imm16     (80186+)
      05/0D/15/1D/25/2D/35/3D iw arithmetic AX, imm16
    """
    word = struct.pack("<H", value)
    out: list[tuple[int, str, int]] = []
    names = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
    pos = start
    while True:
        pos = data.find(word, pos, end)
        if pos < 0:
            break
        if pos >= 1:
            op = data[pos - 1]
            if 0xB8 <= op <= 0xBF:
                out.append((pos - 1, f"mov {names[op - 0xB8]}, 0x{value:04x}", pos))
            elif op == 0x68:
                out.append((pos - 1, f"push 0x{value:04x}", pos))
            elif op in {0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D}:
                out.append((pos - 1, f"AX-immediate opcode 0x{op:02x} value 0x{value:04x}", pos))
        pos += 1
    return out


def rank_segment_bases(
    data: bytes,
    load_start: int,
    string_ptrs: dict[str, int],
    code_search_end: int,
) -> list[dict]:
    """
    A Turbo Pascal short-string literal is normally addressed by its length byte.
    Search paragraph-aligned candidate segment bases. A good base should make the
    relative offsets of several result strings appear as strong 16-bit immediates
    in generated code.
    """
    candidates = []
    first_string = min(string_ptrs.values())
    max_base = min(first_string, len(data))
    for base in range(load_start, max_base + 1, 16):
        distinct = 0
        strong_total = 0
        refs_by_target: dict[str, list[tuple[int, str, int]]] = {}
        for name, ptr in string_ptrs.items():
            rel = ptr - base
            if not (0 <= rel <= 0xFFFF):
                continue
            refs = imm16_refs(data, rel, load_start, code_search_end)
            if refs:
                distinct += 1
                strong_total += len(refs)
                refs_by_target[name] = refs
        if distinct:
            candidates.append(
                {
                    "base": base,
                    "distinct": distinct,
                    "strong_total": strong_total,
                    "refs": refs_by_target,
                }
            )
    candidates.sort(key=lambda x: (x["distinct"], x["strong_total"]), reverse=True)
    return candidates


def disassemble_window(exe: Path, data: bytes, anchor: int, out_dir: Path, label: str) -> str:
    start = anchor
    end = min(len(data), anchor + 160)
    blob = data[start:end]
    slice_path = out_dir / f"{label}_{anchor:06x}.bin"
    slice_path.write_bytes(blob)

    if shutil.which("ndisasm"):
        proc = subprocess.run(
            ["ndisasm", "-b", "16", "-o", hex(start), str(slice_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return proc.stdout

    if shutil.which("objdump"):
        proc = subprocess.run(
            [
                "objdump",
                "-D",
                "-b",
                "binary",
                "-m",
                "i8086",
                "-M",
                "intel",
                f"--adjust-vma={start}",
                str(slice_path),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return proc.stdout

    return "(no ndisasm or objdump available; raw slice was saved)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Locate the AFSim VCR outcome/capture result handler without broad disassembly."
    )
    parser.add_argument(
        "--exe",
        default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE",
    )
    parser.add_argument(
        "--out",
        default="artifacts/external-sources/independent-sims/afsim-result-handler",
    )
    args = parser.parse_args()

    exe = Path(args.exe)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not exe.is_file():
        print(f"ERROR: missing executable: {exe}", file=sys.stderr)
        return 66

    data = exe.read_bytes()
    try:
        mz = parse_mz(data)
    except ValueError as exc:
        print(f"ERROR: {exc}: {exe}", file=sys.stderr)
        return 65

    report_path = out / "audit.txt"
    lines: list[str] = []

    def emit(s: str = "") -> None:
        print(s)
        lines.append(s)

    emit("===== AFSIM RESULT-HANDLER LOCATOR =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit()
    emit("===== MZ HEADER =====")
    for k, v in mz.items():
        emit(f"{k}: 0x{v:x} ({v})")

    located: dict[str, tuple[int, int, bool]] = {}
    emit()
    emit("===== TARGET STRING LOCATIONS =====")
    for name, text in TARGETS.items():
        positions = find_all(data, text)
        if not positions:
            emit(f"{name}: NOT FOUND")
            continue
        for idx, pos in enumerate(positions):
            ptr, pascal_ok = shortstring_info(data, pos, text)
            emit(
                f"{name}[{idx}]: text_file=0x{pos:06x} "
                f"ptr_file=0x{ptr:06x} pascal_len_prefix={pascal_ok} "
                f"text_len={len(text)}"
            )
            if idx == 0:
                located[name] = (pos, ptr, pascal_ok)

    core_names = ["both_destroyed", "won", "captured", "timed_out"]
    missing = [n for n in core_names if n not in located]
    if missing:
        emit()
        emit(f"ERROR: missing core outcome strings: {missing}")
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 65

    # Use the Pascal short-string prefix where validated. Otherwise use the text
    # start as a weaker pointer candidate.
    core_ptrs = {
        name: (located[name][1] if located[name][2] else located[name][0])
        for name in core_names
    }

    code_search_end = min(core_ptrs.values())
    emit()
    emit("===== CANDIDATE SEGMENT-BASE RANKING =====")
    emit(f"code_search_range: 0x{mz['load_image_offset']:x}..0x{code_search_end:x}")
    ranked = rank_segment_bases(
        data,
        mz["load_image_offset"],
        core_ptrs,
        code_search_end,
    )
    for rank, cand in enumerate(ranked[:20], 1):
        emit(
            f"rank={rank:02d} base_file=0x{cand['base']:06x} "
            f"distinct_targets={cand['distinct']} strong_refs={cand['strong_total']}"
        )
        for name, refs in sorted(cand["refs"].items()):
            rel = core_ptrs[name] - cand["base"]
            emit(f"  {name}: rel=0x{rel:04x}")
            for ref in refs[:12]:
                emit(f"    code_file=0x{ref[0]:06x} {ref[1]}")

    if not ranked:
        emit()
        emit("No strong paragraph-aligned segment-base candidate was found.")
        emit("This does not prove absence of a handler; the compiler may use")
        emit("a pointer table, far pointer, or non-immediate addressing.")
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 0

    best = ranked[0]
    emit()
    emit("===== BEST CANDIDATE DETAIL =====")
    emit(
        f"base_file=0x{best['base']:06x} "
        f"distinct_targets={best['distinct']} strong_refs={best['strong_total']}"
    )

    all_refs: list[tuple[int, str, str]] = []
    for name, refs in best["refs"].items():
        for anchor, desc, _immpos in refs:
            all_refs.append((anchor, name, desc))
    all_refs.sort()

    # Cluster references that likely belong to one handler.
    clusters: list[list[tuple[int, str, str]]] = []
    for item in all_refs:
        if not clusters or item[0] - clusters[-1][-1][0] > 512:
            clusters.append([item])
        else:
            clusters[-1].append(item)

    emit()
    emit("===== STRONG-XREF CLUSTERS =====")
    for ci, cluster in enumerate(clusters, 1):
        names = sorted(set(x[1] for x in cluster))
        emit(
            f"cluster={ci} range=0x{cluster[0][0]:06x}..0x{cluster[-1][0]:06x} "
            f"targets={','.join(names)} refs={len(cluster)}"
        )
        for anchor, name, desc in cluster:
            emit(f"  0x{anchor:06x} {name}: {desc}")

    emit()
    emit("===== TARGETED DISASSEMBLY WINDOWS =====")
    seen_anchors = set()
    for anchor, name, desc in all_refs:
        if anchor in seen_anchors:
            continue
        seen_anchors.add(anchor)
        emit()
        emit(f"--- anchor 0x{anchor:06x} target={name} ({desc}) ---")
        emit(disassemble_window(exe, data, anchor, out, name).rstrip())

    emit()
    emit("===== RAW STRING-POOL CONTEXT =====")
    pool_start = max(0, min(core_ptrs.values()) - 32)
    pool_end = min(len(data), max(located[n][0] + len(TARGETS[n]) for n in core_names) + 32)
    emit(hexdump(data, pool_start, pool_end))

    emit()
    emit("===== NEXT INTERPRETATION GATE =====")
    emit("A compact code cluster referencing won/captured/destroyed/timeout is the")
    emit("preferred result-handler candidate. Inspect that cluster for:")
    emit("  result-code branch shape;")
    emit("  owner/crew mutation on capture;")
    emit("  removal or retention of either ship;")
    emit("  OOB cursor increment/restart/re-sort;")
    emit("  repeated-pair handling after timeout/capture.")
    emit("Do not infer NuHost semantics from AFSim alone.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
