#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

TARGET = 0x2F14

LABELS = {
    "owner_label": b"Race of owner",
    "ship_id_label": b"Ship id",
    "kill_label": b"Ship missio kill",
    "fuel_label": b"Fuel on board",
    "primary_enemy_label": b"Primary enemy",
    "friendly_code_label": b"Friendly code value",
}

HELP_TEXT = {
    "kill_help": b"Is the ship set to the kill mission",
    "fuel_help": b"Does the ship have fuel",
    "primary_enemy_help": b"What is the ships primary enemy",
    "friendly_code_help": b"What is this ships Friendly code",
}

def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]

def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]

def parse_mz(data: bytes) -> dict[str, int]:
    if len(data) < 0x1C or data[:2] not in {b"MZ", b"ZM"}:
        raise ValueError("not MZ")
    pages = u16(data, 0x04)
    last = u16(data, 0x02)
    hdr = u16(data, 0x08) * 16
    cs = u16(data, 0x16)
    size = (pages - 1) * 512 + (last or 512) if pages else len(data)
    return {
        "load_image_offset": hdr,
        "initial_cs": cs,
        "initial_cs_file_base": hdr + cs * 16,
        "mz_file_size": min(size, len(data)),
    }

def find_all(data: bytes, needle: bytes, start: int, end: int) -> list[int]:
    out = []
    p = start
    while True:
        p = data.find(needle, p, end)
        if p < 0:
            return out
        out.append(p)
        p += 1

def find_prologue_after(data: bytes, start: int, ceiling: int, max_forward: int = 0x8000) -> int | None:
    p = data.find(b"\x55\x89\xe5", start + 3, min(ceiling, start + max_forward))
    return p if p >= 0 else None

def find_prologue_before(data: bytes, anchor: int, floor: int, max_back: int = 0x4000) -> int | None:
    p = data.rfind(b"\x55\x89\xe5", max(floor, anchor - max_back), anchor + 1)
    return p if p >= 0 else None

def function_owner(data: bytes, pos: int, floor: int) -> str:
    p = find_prologue_before(data, pos, floor)
    return f"0x{p:06x}" if p is not None else "UNKNOWN"

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

def pascal_start(data: bytes, text_pos: int) -> tuple[int, bool, int | None]:
    if text_pos <= 0:
        return text_pos, False, None
    n = data[text_pos - 1]
    if 0 < n <= 255 and text_pos - 1 + 1 + n <= len(data):
        raw = data[text_pos:text_pos+n]
        # prefix may describe a larger field label in which our needle is a prefix
        if raw.startswith(data[text_pos:text_pos+min(len(raw), 3)]):
            return text_pos - 1, True, n
    return text_pos, False, None

def cs_literal_refs(data: bytes, off16: int, start: int, end: int) -> list[tuple[int,str]]:
    needle = struct.pack("<H", off16 & 0xFFFF)
    out = []
    for p in find_all(data, needle, start, end):
        if p < 1:
            continue
        op = data[p-1]
        if op == 0xBF:
            if data[p+2:p+4] == b"\x0e\x57":
                out.append((p-1, "mov di,off; push cs; push di"))
            else:
                out.append((p-1, "mov di,off"))
        elif 0xB8 <= op <= 0xBE:
            out.append((p-1, f"mov reg,0x{off16 & 0xffff:04x}"))
        elif op == 0x68:
            out.append((p-1, f"push 0x{off16 & 0xffff:04x}"))
    return sorted(set(out))

def parameter_les_refs(data: bytes, start: int, end: int) -> list[tuple[int,int]]:
    # 16-bit LES DI,[BP+disp8] => C4 7E xx
    out = []
    p = start
    while p + 2 < end:
        if data[p:p+2] == b"\xc4\x7e":
            disp = struct.unpack("<b", data[p+2:p+3])[0]
            if disp >= 4:
                out.append((p, disp))
        p += 1
    return out

def bp_disp_refs_from_disasm(txt: str) -> dict[str,list[str]]:
    groups: dict[str,list[str]] = {}
    for line in txt.splitlines():
        m = re.search(r"\[bp\+0x([0-9a-f]+)\]", line, flags=re.I)
        if not m:
            continue
        k = f"bp+0x{int(m.group(1),16):x}"
        groups.setdefault(k, []).append(line)
    return groups

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Trace AFSim ship editor 0x2f14 metadata pointer arguments to Kill/Fuel/Primary Enemy fields."
    )
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-ship-editor-metadata")
    args = ap.parse_args()

    exe = Path(args.exe)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not exe.is_file():
        print(f"ERROR: missing {exe}", file=sys.stderr)
        return 66

    data = exe.read_bytes()
    mz = parse_mz(data)
    lo, hi = mz["load_image_offset"], mz["mz_file_size"]

    report: list[str] = []
    def emit(s: str = "") -> None:
        print(s)
        report.append(s)

    emit("===== AFSIM SHIP-EDITOR METADATA AUDIT =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit(f"scan:   0x{lo:06x}..0x{hi:06x}")
    emit()

    emit("===== PROVEN CALLER BRIDGE =====")
    emit("0x5883 initializes three locals: A=1, B=1, C=0")
    emit("and calls 0x2f14(entry, &A, &B, &C).")
    emit("On success:")
    emit("  A -> parallel 0x3d9d[index]")
    emit("  B -> parallel 0x3dcf[index]")
    emit("  C -> parallel 0x3e01[index]")
    emit("Selector behavior already proves C = Primary Enemy.")
    emit("This pass must distinguish A/B as Fuel vs KILL.")
    emit()

    emit("===== 0x2f14 CALLERS =====")
    refs = near_refs(data, TARGET, lo, hi)
    for p, kind in refs:
        emit(f"file=0x{p:06x} {kind} owner={function_owner(data,p,lo)}")
    if not refs:
        emit("no near callers found")
    emit()

    end = find_prologue_after(data, TARGET, hi, 0x9000)
    if end is None:
        end = min(hi, TARGET + 0x1800)
    dst, txt = disassemble(data, TARGET, end, out, "ship_editor_002f14")

    emit("===== 0x2f14 FUNCTION =====")
    emit(f"range=0x{TARGET:06x}..0x{end:06x} bytes={end-TARGET}")
    emit(f"disassembly={dst}")
    for line in txt.splitlines()[:5000]:
        emit(line)
    emit()

    emit("===== PARAMETER FAR-POINTER ACCESS SUMMARY =====")
    for p, disp in parameter_les_refs(data, TARGET, end):
        emit(f"file=0x{p:06x} LES DI,[BP+0x{disp:02x}]")
    emit()

    emit("===== PARAMETER REFERENCES FROM DISASSEMBLY =====")
    groups = bp_disp_refs_from_disasm(txt)
    for k in sorted(groups, key=lambda x:int(x.split("0x")[1],16)):
        emit(k + ":")
        for line in groups[k]:
            emit("  " + line)
    emit()

    emit("===== FORM LABEL LOCATIONS / XREFS =====")
    for name, needle in LABELS.items():
        poses = find_all(data, needle, lo, hi)
        emit(f"{name}: hits={len(poses)}")
        for pos in poses:
            ptr, pref, plen = pascal_start(data,pos)
            off = ptr - mz["initial_cs_file_base"]
            emit(
                f"  text_file=0x{pos:06x} ptr_file=0x{ptr:06x} "
                f"pascal_candidate={pref} len={plen} cs_off=0x{off & 0xffff:04x}"
            )
            for rp, cls in cs_literal_refs(data, off, TARGET, end):
                emit(f"    in_2f14 xref=0x{rp:06x} {cls}")
            for rp, cls in cs_literal_refs(data, off, lo, hi):
                if TARGET <= rp < end:
                    continue
                emit(f"    global xref=0x{rp:06x} {cls} owner={function_owner(data,rp,lo)}")
    emit()

    emit("===== HELP-TEXT LOCATIONS =====")
    emit("These strings may live in a separate data/resource segment, so absence")
    emit("of CS-relative xrefs is not negative evidence.")
    for name, needle in HELP_TEXT.items():
        poses = find_all(data, needle, lo, hi)
        emit(f"{name}: hits={len(poses)}")
        for pos in poses:
            emit(f"  text_file=0x{pos:06x}")
    emit()

    emit("===== DECISION GATE =====")
    emit("Required direct proof:")
    emit("  identify which caller pointer A/B is rendered/edited by")
    emit("  'Ship mission kill' versus 'Fuel on board'.")
    emit()
    emit("Once mapped:")
    emit("  parallel 0x3d9d = <Fuel or Kill>")
    emit("  parallel 0x3dcf = <Kill or Fuel>")
    emit("  parallel 0x3e01 = Primary Enemy")
    emit()
    emit("Then freeze executable AFSIM-R1 before any Nu discovery-corpus run.")
    emit("Held-out remains closed.")

    (out / "audit.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
