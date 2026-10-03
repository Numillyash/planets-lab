#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

TARGETS = {
    "sort_comparator": 0x5572,
    "ship_eligibility": 0x513D,
    "planet_aux_eligibility": 0x5199,
    "vcr_side_builder": 0x3EB9,
    "persistent_remove_or_kill": 0x46BE,
    "full_resort": 0x5627,
    "ship_pair_selector": 0x51C6,
    "battle_setup": 0x497E,
}

ENTRY_BASE = 0x32DC
ENTRY_STRIDE = 0x36
ENTRY_OFFSETS = {
    "aux0": 0x00,
    "aux4": 0x04,
    "shield": 0x06,
    "vcr_object": 0x0C,
    "damage": 0x0C + 20,
    "crew": 0x0C + 22,
    "ship_id": 0x0C + 24,
    "owner": 0x0C + 26,
    "picture": 0x0C + 28,
    "beam_type": 0x0C + 30,
    "beam_count": 0x0C + 32,
    "fighter_bays": 0x0C + 34,
    "torp_type": 0x0C + 36,
    "ammo": 0x0C + 38,
    "torp_tubes": 0x0C + 40,
}

def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]

def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]

def parse_mz(data: bytes) -> tuple[int, int]:
    if len(data) < 0x1C or data[:2] not in {b"MZ", b"ZM"}:
        raise ValueError("not MZ")
    hdr = u16(data, 0x08) * 16
    pages = u16(data, 0x04)
    last = u16(data, 0x02)
    size = (pages - 1) * 512 + (last or 512) if pages else len(data)
    return hdr, min(size, len(data))

def find_prologue_after(data: bytes, start: int, ceiling: int, max_forward: int = 0x5000) -> int | None:
    p = data.find(b"\x55\x89\xe5", start + 3, min(ceiling, start + max_forward))
    return p if p >= 0 else None

def find_prologue_before(data: bytes, anchor: int, floor: int, max_back: int = 0x3000) -> int | None:
    p = data.rfind(b"\x55\x89\xe5", max(floor, anchor - max_back), anchor + 1)
    return p if p >= 0 else None

def disassemble(data: bytes, start: int, end: int, out: Path, stem: str) -> tuple[Path, str]:
    blob = out / f"{stem}_{start:06x}_{end:06x}.bin"
    blob.write_bytes(data[start:end])
    if shutil.which("ndisasm"):
        r = subprocess.run(
            ["ndisasm", "-b", "16", "-o", hex(start), str(blob)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        txt = r.stdout
    elif shutil.which("objdump"):
        r = subprocess.run(
            ["objdump", "-D", "-b", "binary", "-m", "i8086", "-M", "intel",
             f"--adjust-vma={start}", str(blob)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        txt = r.stdout
    else:
        txt = "(no ndisasm/objdump installed)\n"
    dst = out / f"{stem}_{start:06x}.disasm.txt"
    dst.write_text(txt, encoding="utf-8")
    return dst, txt

def near_refs(data: bytes, target: int, start: int, end: int) -> list[tuple[int, str]]:
    out = []
    for p in range(start, max(start, end - 2)):
        op = data[p]
        if op not in {0xE8, 0xE9}:
            continue
        t = p + 3 + s16(data, p + 1)
        if t == target:
            out.append((p, "call" if op == 0xE8 else "jmp"))
    return out

def function_owner(data: bytes, pos: int, floor: int) -> str:
    p = find_prologue_before(data, pos, floor, 0x3000)
    return f"0x{p:06x}" if p is not None else "UNKNOWN"

def emit_disasm(emit, data: bytes, out: Path, label: str, start: int, end: int, max_lines: int = 1800):
    dst, txt = disassemble(data, start, end, out, label)
    emit(f"{label}: 0x{start:06x}..0x{end:06x} bytes={end-start}")
    emit(f"disassembly={dst}")
    lines = txt.splitlines()
    for line in lines[:max_lines]:
        emit(line)
    if len(lines) > max_lines:
        emit(f"... truncated after {max_lines} lines; full copy saved locally")

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recover AFSim sort comparator, ship eligibility, and VCR side mapping."
    )
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-sort-eligibility-sides")
    args = ap.parse_args()

    exe = Path(args.exe)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not exe.is_file():
        print(f"ERROR: missing {exe}", file=sys.stderr)
        return 66

    data = exe.read_bytes()
    lo, hi = parse_mz(data)

    report: list[str] = []
    def emit(s: str = "") -> None:
        print(s)
        report.append(s)

    emit("===== AFSIM SORT / ELIGIBILITY / SIDE-MAPPING AUDIT =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit(f"scan:   0x{lo:06x}..0x{hi:06x}")
    emit()

    emit("===== FROZEN STRUCTURAL CANDIDATE =====")
    emit("AFSIM-R1 (already frozen before this pass):")
    emit("  battle result")
    emit("    -> VCR owner/crew capture mutation")
    emit("    -> writeback to persistent 54-byte entries")
    emit("    -> per-entry normalization 0x2c68")
    emit("    -> full persistent-array sort/rebuild 0x5627")
    emit("    -> selector 0x51c6 resets indices to 1/1")
    emit("    -> traversal restarts from beginning")
    emit()
    emit("This pass may refine the comparator/eligibility/side mapping, but must not")
    emit("silently change AFSIM-R1. Any contradiction must be reported explicitly.")
    emit()

    emit("===== PERSISTENT ENTRY FIELD MAP =====")
    emit(f"entry[index] = 0x{ENTRY_BASE:04x} + index*0x{ENTRY_STRIDE:02x}")
    for name, off in ENTRY_OFFSETS.items():
        emit(f"  +0x{off:02x}  {name}")
    emit()

    emit("===== TARGET CALLERS =====")
    for name, target in TARGETS.items():
        refs = near_refs(data, target, lo, hi)
        emit(f"{name:26s} target=0x{target:06x} refs={len(refs)}")
        for p, kind in refs:
            emit(f"  file=0x{p:06x} {kind} owner={function_owner(data,p,lo)}")
    emit()

    emit("===== TARGET DISASSEMBLIES =====")
    for name in [
        "sort_comparator",
        "ship_eligibility",
        "planet_aux_eligibility",
        "vcr_side_builder",
        "persistent_remove_or_kill",
    ]:
        start = TARGETS[name]
        end = find_prologue_after(data, start, hi, 0x5000)
        if end is None:
            end = min(hi, start + 0x1800)
        emit()
        emit_disasm(emit, data, out, name, start, end, 2200)

    emit()
    emit("===== LOCAL CALL GRAPH FROM TARGETS =====")
    target_ranges = {}
    for name in [
        "sort_comparator",
        "ship_eligibility",
        "planet_aux_eligibility",
        "vcr_side_builder",
        "persistent_remove_or_kill",
    ]:
        start = TARGETS[name]
        end = find_prologue_after(data, start, hi, 0x5000) or min(hi, start + 0x1800)
        target_ranges[name] = (start,end)

    # Report near-call destinations so follow-up can focus only on helpers actually
    # used by the comparator/eligibility/side mapping.
    for name,(start,end) in target_ranges.items():
        emit(f"{name}:")
        seen = []
        for p in range(start, max(start,end-2)):
            if data[p] != 0xE8:
                continue
            dest = p + 3 + s16(data,p+1)
            if lo <= dest < hi:
                seen.append((p,dest))
        for p,dest in seen:
            emit(f"  0x{p:06x} -> 0x{dest:06x} owner={function_owner(data,dest,lo)}")
        if not seen:
            emit("  no near calls")
    emit()

    emit("===== INTERPRETATION CHECKLIST =====")
    emit("sort_comparator 0x5572:")
    emit("  - identify compared entry fields")
    emit("  - identify ascending/descending direction")
    emit("  - identify tie-breaks")
    emit("  - determine whether owner/PE/mission/friendly-code affect order")
    emit()
    emit("ship_eligibility 0x513d:")
    emit("  - identify destroyed/disabled/dead rejection")
    emit("  - identify owner/relation/PE/mission checks")
    emit("  - identify any captured-state special case")
    emit()
    emit("vcr_side_builder 0x3eb9:")
    emit("  - map function argument to VCR left/right object")
    emit("  - map lower ship-ID canonicalization to actual VCR LEFT/RIGHT")
    emit()
    emit("persistent_remove_or_kill 0x46be:")
    emit("  - determine whether removal compacts/reorders the array")
    emit("  - determine whether captured ships bypass removal")
    emit()
    emit("Desired output: deterministic AFSim pseudocode suitable for a discovery")
    emit("Corpus DB comparator. Held-out remains closed.")

    (out/"audit.txt").write_text("\n".join(report)+"\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
