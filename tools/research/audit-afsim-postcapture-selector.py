#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

# Persistent AFSim combat-entry layout recovered from 0x675a.
ENTRY_BASE = 0x32DC
ENTRY_STRIDE = 0x36
ENTRY_SHIELD = 0x06
ENTRY_VCR_OBJECT = 0x0C
ENTRY_SHIP_ID = 0x24

# High-value procedures on the post-combat -> next-pair path.
TARGETS = {
    "entry_recalc": 0x2C68,
    "ship_pair_selector": 0x51C6,
    "planet_pair_selector": 0x53C6,
    "preselect_or_oob_refresh": 0x5627,
    "battle_setup": 0x497E,
    "battle_loop_owner": 0x675A,
    "battle_loop_caller": 0x7225,
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
        if data[p] not in {0xE8, 0xE9}:
            continue
        t = p + 3 + s16(data, p + 1)
        if t == target:
            out.append((p, "call" if data[p] == 0xE8 else "jmp"))
    return out

def word_hits(data: bytes, value: int, start: int, end: int) -> list[int]:
    needle = struct.pack("<H", value)
    out = []
    p = start
    while True:
        p = data.find(needle, p, end)
        if p < 0:
            return out
        out.append(p)
        p += 1

def classify(data: bytes, pos: int, value: int) -> str:
    if pos >= 1:
        op = data[pos-1]
        if op == 0xA1:
            return f"mov ax,[0x{value:04x}]"
        if op == 0xA3:
            return f"mov [0x{value:04x}],ax"
        if op == 0x68:
            return f"push 0x{value:04x}"
        if 0xB8 <= op <= 0xBF:
            regs = ["ax","cx","dx","bx","sp","bp","si","di"]
            return f"mov {regs[op-0xB8]},0x{value:04x}"
    if pos >= 2:
        op, modrm = data[pos-2], data[pos-1]
        if op in {0x80,0x81,0x83,0x88,0x89,0x8A,0x8B,0xFF} and (modrm & 0xC7) == 0x06:
            return f"direct-mem opcode=0x{op:02x} modrm=0x{modrm:02x}"
        if op == 0xC7 and modrm == 0x06:
            return f"mov word [0x{value:04x}],imm16"
    return "raw-word"

def function_owner(data: bytes, pos: int, floor: int) -> str:
    p = find_prologue_before(data, pos, floor, 0x3000)
    return f"0x{p:06x}" if p is not None else "UNKNOWN"

def print_disasm(emit, data: bytes, out: Path, label: str, start: int, end: int, max_lines: int = 1800):
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
        description="Audit AFSim post-capture persistent-state writeback and next-pair selection."
    )
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-postcapture-selector")
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

    emit("===== AFSIM POST-CAPTURE SELECTOR AUDIT =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit(f"scan:   0x{lo:06x}..0x{hi:06x}")
    emit()

    emit("===== PERSISTENT COMBAT ENTRY LAYOUT =====")
    emit(f"entry_base      = 0x{ENTRY_BASE:04x}")
    emit(f"entry_stride    = 0x{ENTRY_STRIDE:02x} ({ENTRY_STRIDE} bytes)")
    emit(f"shield_offset   = +0x{ENTRY_SHIELD:02x}")
    emit(f"vcr_object      = +0x{ENTRY_VCR_OBJECT:02x}")
    emit(f"ship_id         = +0x{ENTRY_SHIP_ID:02x}")
    emit(f"persistent vcr object base expression: 0x{ENTRY_BASE+ENTRY_VCR_OBJECT:04x} + index*0x36")
    emit(f"persistent shield expression:          0x{ENTRY_BASE+ENTRY_SHIELD:04x} + index*0x36")
    emit(f"persistent ship-id expression:         0x{ENTRY_BASE+ENTRY_SHIP_ID:04x} + index*0x36")
    emit()

    emit("===== PROVEN POST-COMBAT BRIDGE IN 0x675a =====")
    emit("Observed sequence:")
    emit("  VCR left object 0x324a -> persistent entry[index 0x313a] object")
    emit("  VCR right object 0x3274 -> persistent entry[index 0x313c] object")
    emit("  VCR left shield 0x329e -> persistent entry[index 0x313a] +6")
    emit("  VCR right shield 0x32a0 -> persistent entry[index 0x313c] +6")
    emit("  entry_recalc( entry[index 0x313a] )")
    emit("  entry_recalc( entry[index 0x313c] )")
    emit("The 42-byte object-copy direction is corroborated by the immediately")
    emit("following explicit shield writeback from VCR state into the same two")
    emit("persistent entries.")
    emit()

    emit("===== PRE-COMBAT ROLE NORMALIZATION =====")
    emit("Before battle_setup(), indices 0x313a and 0x313c are compared by")
    emit("persistent entry ship-id (+0x24 / absolute base 0x3300).")
    emit("If first ID > second ID, the indices are swapped.")
    emit("This proves AFSim canonicalizes the selected pair by ship ID before")
    emit("building/launching the VCR battle. LEFT/RIGHT interpretation still")
    emit("depends on battle_setup() and must not be assigned from this alone.")
    emit()

    emit("===== TARGET CALL GRAPH =====")
    for name, target in TARGETS.items():
        refs = near_refs(data, target, lo, hi)
        emit(f"{name:24s} target=0x{target:06x} refs={len(refs)}")
        for p, kind in refs:
            emit(f"  file=0x{p:06x} {kind} owner={function_owner(data,p,lo)}")
    emit()

    emit("===== PERSISTENT-LAYOUT CONSTANT USERS =====")
    constants = {
        "entry_base": ENTRY_BASE,
        "entry_shield_base": ENTRY_BASE + ENTRY_SHIELD,
        "entry_object_base": ENTRY_BASE + ENTRY_VCR_OBJECT,
        "entry_ship_id_base": ENTRY_BASE + ENTRY_SHIP_ID,
        "current_index_a": 0x313A,
        "current_index_b": 0x313C,
    }
    for name, value in constants.items():
        emit(f"{name}: 0x{value:04x}")
        shown = 0
        for p in word_hits(data, value, lo, hi):
            cls = classify(data,p,value)
            if cls == "raw-word":
                continue
            emit(f"  file=0x{p:06x} class={cls} owner={function_owner(data,p,lo)}")
            shown += 1
        if not shown:
            emit("  classified_refs=0")
    emit()

    emit("===== HIGH-VALUE FUNCTION DISASSEMBLIES =====")
    for name in [
        "entry_recalc",
        "preselect_or_oob_refresh",
        "ship_pair_selector",
        "planet_pair_selector",
        "battle_setup",
        "battle_loop_caller",
    ]:
        start = TARGETS[name]
        end = find_prologue_after(data, start, hi, 0x6000)
        if end is None:
            end = min(hi, start + 0x2000)
        emit()
        print_disasm(emit, data, out, name, start, end, 2200)

    emit()
    emit("===== SEMANTIC DISCRIMINATORS =====")
    emit("Classify entry_recalc(0x2c68):")
    emit("  - attack-value/OOB-key recomputation?")
    emit("  - status normalization only?")
    emit("  - removal/dead flag update?")
    emit()
    emit("Classify preselect_or_oob_refresh(0x5627):")
    emit("  - full sort/rebuild of OOB?")
    emit("  - cursor advance/reset?")
    emit("  - UI/status-only?")
    emit()
    emit("Classify ship_pair_selector(0x51c6):")
    emit("  - scans persistent entries from start?")
    emit("  - advances saved cursor?")
    emit("  - filters by current owner after capture?")
    emit("  - chooses aggressor/opponent independently?")
    emit()
    emit("Only after these are resolved freeze an AFSim O/C candidate.")
    emit("Do not promote the candidate into NuHost without discovery-corpus testing.")

    (out/"audit.txt").write_text("\n".join(report)+"\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
