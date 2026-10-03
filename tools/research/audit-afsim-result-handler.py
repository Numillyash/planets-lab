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
    "both_destroyed": b"Both ships blew up",
    "won": b" won ",
    "captured": b" captured ",
    "timed_out": b"The battle timed out",
}

def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]

def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]

def parse_mz(data: bytes) -> dict[str, int]:
    if len(data) < 0x1C or data[:2] not in {b"MZ", b"ZM"}:
        raise ValueError("not an MZ executable")
    f = {
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
    f["load_image_offset"] = f["header_paragraphs"] * 16
    f["initial_cs_file_base"] = f["load_image_offset"] + f["initial_cs"] * 16
    if f["pages"]:
        f["mz_file_size"] = (f["pages"] - 1) * 512 + (f["bytes_last_page"] or 512)
    else:
        f["mz_file_size"] = len(data)
    return f

def find_all(data: bytes, needle: bytes, start: int = 0, end: int | None = None) -> list[int]:
    if end is None:
        end = len(data)
    out: list[int] = []
    pos = start
    while True:
        pos = data.find(needle, pos, end)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1

def pascal_ptr(data: bytes, text_pos: int, text: bytes) -> tuple[int, bool]:
    if text_pos > 0 and data[text_pos - 1] == len(text):
        return text_pos - 1, True
    return text_pos, False

def find_prologue_before(data: bytes, anchor: int, floor: int, max_back: int = 0x2000) -> int | None:
    lo = max(floor, anchor - max_back)
    p = data.rfind(b"\x55\x89\xe5", lo, anchor + 1)
    return p if p >= 0 else None

def find_prologue_after(data: bytes, anchor: int, ceiling: int, max_forward: int = 0x2000) -> int | None:
    hi = min(ceiling, anchor + max_forward)
    p = data.find(b"\x55\x89\xe5", anchor, hi)
    return p if p >= 0 else None

def disassemble(blob_path: Path, base: int) -> str:
    if shutil.which("ndisasm"):
        p = subprocess.run(
            ["ndisasm", "-b", "16", "-o", hex(base), str(blob_path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        return p.stdout
    if shutil.which("objdump"):
        p = subprocess.run(
            ["objdump", "-D", "-b", "binary", "-m", "i8086", "-M", "intel",
             f"--adjust-vma={base}", str(blob_path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        return p.stdout
    return "(no ndisasm or objdump installed)\n"

def classify_word_hit(data: bytes, pos: int, value: int) -> str:
    regs = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
    if pos >= 1:
        op = data[pos - 1]
        if 0xB8 <= op <= 0xBF:
            reg = regs[op - 0xB8]
            if op == 0xBF and data[pos + 2:pos + 4] == b"\x0e\x57":
                return f"STRONG mov di,0x{value:04x}; push cs; push di"
            return f"mov {reg},0x{value:04x}"
        if op == 0x68:
            return f"push 0x{value:04x}"
    if pos >= 4 and data[pos - 4] == 0xC7:
        return f"possible C7-immediate 0x{value:04x}"
    return "raw-word"

def raw_word_hits(data: bytes, value: int, start: int, end: int, excluded: list[tuple[int, int]]) -> list[tuple[int, str]]:
    needle = struct.pack("<H", value)
    out: list[tuple[int, str]] = []
    for pos in find_all(data, needle, start, end):
        if any(lo <= pos < hi for lo, hi in excluded):
            continue
        out.append((pos, classify_word_hit(data, pos, value)))
    return out

def near_refs(data: bytes, target_file: int, start: int, end: int) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for p in range(start, max(start, end - 2)):
        op = data[p]
        if op not in {0xE8, 0xE9} or p + 2 >= end:
            continue
        target = p + 3 + s16(data, p + 1)
        if target == target_file:
            out.append((p, "call-near" if op == 0xE8 else "jmp-near"))
    return out

def hex_context(data: bytes, anchor: int, before: int = 24, after: int = 40) -> str:
    lo = max(0, anchor - before)
    hi = min(len(data), anchor + after)
    rows = []
    for off in range(lo, hi, 16):
        chunk = data[off:min(off + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        rows.append(f"{off:06x}  {hx:<47}  {asc}")
    return "\n".join(rows)

def emit_function(data: bytes, start: int, end: int, out: Path, stem: str, emit) -> None:
    if end <= start:
        return
    blob_path = out / f"{stem}_{start:06x}_{end:06x}.bin"
    blob_path.write_bytes(data[start:end])
    dis = disassemble(blob_path, start)
    dis_path = out / f"{stem}_{start:06x}.disasm.txt"
    dis_path.write_text(dis, encoding="utf-8")
    emit(f"{stem}: file=0x{start:06x}..0x{end:06x} bytes={end-start}")
    emit(f"  disassembly={dis_path}")
    emit("  --- disassembly ---")
    dis_lines = dis.splitlines()
    for line in dis_lines[:500]:
        emit(line)
    if len(dis_lines) > 500:
        emit("  ... truncated after 500 lines; full disassembly saved locally")

def main() -> int:
    ap = argparse.ArgumentParser(description="Locate AFSim outcome decoder/result handler using true MZ/CS offsets.")
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-result-handler-v3")
    args = ap.parse_args()

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

    mz_end = min(len(data), mz["mz_file_size"])
    report: list[str] = []
    def emit(s: str = "") -> None:
        print(s)
        report.append(s)

    emit("===== AFSIM RESULT-HANDLER LOCATOR V3 =====")
    emit("method: whole-load-image CS-offset scan + adjacent-function/caller audit")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit()
    emit("===== MZ HEADER =====")
    for k, v in mz.items():
        emit(f"{k}: 0x{v:x} ({v})")
    emit(f"scan_file_range=0x{mz['load_image_offset']:06x}..0x{mz_end:06x}")
    emit()

    info: dict[str, dict[str, int | bool | bytes]] = {}
    emit("===== TRUE SHORT-STRING OFFSETS =====")
    for name, text in TARGETS.items():
        hits = find_all(data, text)
        if not hits:
            emit(f"{name}: NOT FOUND")
            continue
        text_pos = hits[0]
        ptr_file, ok = pascal_ptr(data, text_pos, text)
        cs_off = ptr_file - mz["initial_cs_file_base"]
        info[name] = {"text_pos": text_pos, "ptr_file": ptr_file, "pascal": ok, "cs_off": cs_off, "text": text}
        emit(f"{name}: text_file=0x{text_pos:06x} ptr_file=0x{ptr_file:06x} pascal_len_prefix={ok} cs_off=0x{cs_off:04x}")

    if len(info) != len(TARGETS):
        emit("ERROR: not all result strings found")
        (out / "audit.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return 65

    pool_start = min(int(v["ptr_file"]) for v in info.values())
    pool_end = max(int(v["text_pos"]) + len(v["text"]) for v in info.values())
    excluded = [(pool_start, pool_end)]

    emit()
    emit("===== WHOLE-IMAGE TRUE-OFFSET HITS =====")
    all_hits: list[tuple[int, str, str]] = []
    for name, v in info.items():
        value = int(v["cs_off"])
        hits = raw_word_hits(data, value, mz["load_image_offset"], mz_end, excluded)
        emit(f"{name}: cs_off=0x{value:04x} hits={len(hits)}")
        for pos, cls in hits:
            region = "before-pool" if pos < pool_start else "after-pool"
            emit(f"  file=0x{pos:06x} region={region} class={cls}")
            all_hits.append((pos, name, cls))

    emit()
    emit("===== ADJACENT FUNCTION BOUNDARIES =====")
    pre_start = find_prologue_before(data, pool_start - 1, mz["load_image_offset"], 0x2000)
    post_start = pool_end if data[pool_end:pool_end+3] == b"\x55\x89\xe5" else find_prologue_after(data, pool_end, mz_end, 0x100)
    next_after_post = find_prologue_after(data, post_start + 3, mz_end, 0x3000) if post_start is not None else None
    emit(f"pool_file=0x{pool_start:06x}..0x{pool_end:06x}")
    emit(f"preceding_prologue={('0x%06x' % pre_start) if pre_start is not None else 'NOT_FOUND'}")
    emit(f"following_prologue={('0x%06x' % post_start) if post_start is not None else 'NOT_FOUND'}")
    emit(f"next_prologue={('0x%06x' % next_after_post) if next_after_post is not None else 'NOT_FOUND'}")

    emit()
    emit("===== ADJACENT FUNCTION DISASSEMBLY =====")
    if pre_start is not None:
        emit_function(data, pre_start, pool_start, out, "preceding_function", emit)
    if post_start is not None:
        post_end = next_after_post if next_after_post is not None else min(mz_end, post_start + 0x1000)
        emit_function(data, post_start, post_end, out, "following_function", emit)

    emit()
    emit("===== CALLERS / JUMPERS OF ADJACENT FUNCTIONS =====")
    for label, target in [("preceding", pre_start), ("following", post_start)]:
        if target is None:
            continue
        refs = near_refs(data, target, mz["load_image_offset"], mz_end)
        emit(f"{label}_target=0x{target:06x} refs={len(refs)}")
        for p, kind in refs:
            owner = find_prologue_before(data, p, mz["load_image_offset"], 0x1000)
            emit(f"  file=0x{p:06x} kind={kind} caller_prologue={('0x%06x' % owner) if owner is not None else 'UNKNOWN'}")

    emit()
    emit("===== RAW TRUE-OFFSET HIT CONTEXT =====")
    for pos, name, cls in all_hits:
        emit()
        emit(f"--- file=0x{pos:06x} target={name} class={cls} ---")
        emit(hex_context(data, pos))

    emit()
    emit("===== STRING POOL / NEXT FUNCTION CONTEXT =====")
    emit(hex_context(data, pool_start, before=32, after=(pool_end-pool_start)+96))

    emit()
    emit("===== INTERPRETATION GATE =====")
    emit("V2 searched only before the pool; V3 scans the entire MZ load image.")
    emit("Priority evidence is:")
    emit("  1. strong post-pool literal xrefs from the following procedure;")
    emit("  2. a result-code formatter immediately preceding the pool;")
    emit("  3. callers of either adjacent procedure showing VCR-result state flow.")
    emit("If literal xrefs are still absent, inspect adjacent procedures/callers before")
    emit("attempting broad disassembly; the compiler may index the compact pool.")
    emit("No AFSim rule is NuHost evidence without an independent Nu discriminator.")

    (out / "audit.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
