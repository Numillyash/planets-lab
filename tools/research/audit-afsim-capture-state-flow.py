#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

CALLER = 0x4F8B
PARSER = 0x4C4C
OUTCOME = 0x4E2D

# Post-result paired state slots identified by the outcome formatter.
STATE_ADDRS = {
    "ship_a_result0": 0x325E,
    "ship_a_result2": 0x3260,
    "ship_a_field6":  0x3264,
    "ship_a_result12": 0x3270,
    "ship_b_result0": 0x3288,
    "ship_b_result2": 0x328A,
    "ship_b_field6":  0x328E,
    "ship_b_result12": 0x329A,
    "aux_a": 0x329E,
    "aux_b": 0x32A0,
}

LOCAL_RESULT_ADDRS = {
    "a0": 0x002E,
    "b0": 0x0030,
    "a2": 0x0032,
    "b2": 0x0034,
    "a12": 0x0036,
    "b12": 0x0038,
}

def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]

def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]

def parse_mz(data: bytes) -> dict[str, int]:
    if len(data) < 0x1C or data[:2] not in {b"MZ", b"ZM"}:
        raise ValueError("not MZ")
    f = {
        "pages": u16(data, 0x04),
        "bytes_last_page": u16(data, 0x02),
        "header_paragraphs": u16(data, 0x08),
    }
    f["load_image_offset"] = f["header_paragraphs"] * 16
    f["mz_file_size"] = (f["pages"] - 1) * 512 + (f["bytes_last_page"] or 512)
    return f

def find_prologue_before(data: bytes, anchor: int, floor: int, max_back: int = 0x1800) -> int | None:
    lo = max(floor, anchor - max_back)
    p = data.rfind(b"\x55\x89\xe5", lo, anchor + 1)
    return p if p >= 0 else None

def find_next_prologue(data: bytes, start: int, ceiling: int, max_forward: int = 0x4000) -> int | None:
    p = data.find(b"\x55\x89\xe5", start + 3, min(ceiling, start + max_forward))
    return p if p >= 0 else None

def disassemble(data: bytes, start: int, end: int, out: Path, stem: str) -> tuple[Path, str]:
    blob = out / f"{stem}_{start:06x}_{end:06x}.bin"
    blob.write_bytes(data[start:end])
    if shutil.which("ndisasm"):
        p = subprocess.run(
            ["ndisasm", "-b", "16", "-o", hex(start), str(blob)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        text = p.stdout
    elif shutil.which("objdump"):
        p = subprocess.run(
            ["objdump", "-D", "-b", "binary", "-m", "i8086", "-M", "intel",
             f"--adjust-vma={start}", str(blob)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        text = p.stdout
    else:
        text = "(no disassembler installed)\n"
    dst = out / f"{stem}_{start:06x}.disasm.txt"
    dst.write_text(text, encoding="utf-8")
    return dst, text

def near_refs(data: bytes, target: int, start: int, end: int) -> list[tuple[int, str]]:
    refs = []
    for p in range(start, max(start, end - 2)):
        if data[p] not in {0xE8, 0xE9}:
            continue
        t = p + 3 + s16(data, p + 1)
        if t == target:
            refs.append((p, "call" if data[p] == 0xE8 else "jmp"))
    return refs

def word_hits(data: bytes, value: int, start: int, end: int) -> list[int]:
    needle = struct.pack("<H", value)
    out = []
    p = start
    while True:
        p = data.find(needle, p, end)
        if p < 0:
            break
        out.append(p)
        p += 1
    return out

def classify_mem_ref(data: bytes, word_pos: int, value: int) -> str:
    # Direct-address forms common in 16-bit Turbo Pascal.
    if word_pos >= 1:
        op = data[word_pos - 1]
        if op == 0xA1:
            return f"mov ax,[0x{value:04x}]"
        if op == 0xA3:
            return f"mov [0x{value:04x}],ax"
    if word_pos >= 2:
        op, modrm = data[word_pos - 2], data[word_pos - 1]
        if op == 0xC7 and modrm == 0x06:
            return f"mov word [0x{value:04x}],imm16"
        if op == 0xC6 and modrm == 0x06:
            return f"mov byte [0x{value:04x}],imm8"
        if op in {0x80, 0x81, 0x83, 0x8A, 0x8B, 0x88, 0x89, 0xFF} and (modrm & 0xC7) == 0x06:
            return f"direct-mem opcode=0x{op:02x} modrm=0x{modrm:02x}"
    return "raw-word"

def context(data: bytes, pos: int, before: int = 24, after: int = 40) -> str:
    lo = max(0, pos - before)
    hi = min(len(data), pos + after)
    rows = []
    for off in range(lo, hi, 16):
        chunk = data[off:min(off+16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        rows.append(f"{off:06x}  {hx:<47}  {asc}")
    return "\n".join(rows)

def main() -> int:
    ap = argparse.ArgumentParser(description="Audit AFSim capture-state mutation and caller flow.")
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-capture-state-flow")
    args = ap.parse_args()

    exe = Path(args.exe)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not exe.is_file():
        print(f"ERROR: missing {exe}", file=sys.stderr)
        return 66

    data = exe.read_bytes()
    mz = parse_mz(data)
    start = mz["load_image_offset"]
    end = min(len(data), mz["mz_file_size"])

    report: list[str] = []
    def emit(s: str = "") -> None:
        print(s)
        report.append(s)

    emit("===== AFSIM CAPTURE STATE-FLOW AUDIT =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit(f"scan:   0x{start:06x}..0x{end:06x}")
    emit()

    emit("===== KNOWN RESULT FUNCTIONS =====")
    emit(f"screen/result parser: 0x{PARSER:06x}")
    emit(f"outcome formatter:    0x{OUTCOME:06x}")
    emit(f"shared caller:        0x{CALLER:06x}")
    emit()

    emit("===== SHARED CALLER DISASSEMBLY =====")
    caller_end = find_next_prologue(data, CALLER, end, 0x5000)
    if caller_end is None:
        caller_end = min(end, CALLER + 0x2000)
    dst, text = disassemble(data, CALLER, caller_end, out, "shared_caller")
    emit(f"caller_range=0x{CALLER:06x}..0x{caller_end:06x} bytes={caller_end-CALLER}")
    emit(f"disassembly={dst}")
    for line in text.splitlines()[:1200]:
        emit(line)
    if len(text.splitlines()) > 1200:
        emit("... caller disassembly truncated in report; full copy saved locally")

    emit()
    emit("===== CALL SITES INSIDE SHARED CALLER =====")
    for label, target in [("parser", PARSER), ("outcome", OUTCOME)]:
        refs = [(p,k) for p,k in near_refs(data, target, CALLER, caller_end)]
        emit(f"{label}: target=0x{target:06x} refs={len(refs)}")
        for p,k in refs:
            emit(f"  0x{p:06x} {k}")

    emit()
    emit("===== PAIRED POST-RESULT STATE LAYOUT =====")
    emit("Observed pair stride:")
    emit(f"  ship_b_result0 - ship_a_result0 = 0x{STATE_ADDRS['ship_b_result0']-STATE_ADDRS['ship_a_result0']:x}")
    emit(f"  ship_b_result2 - ship_a_result2 = 0x{STATE_ADDRS['ship_b_result2']-STATE_ADDRS['ship_a_result2']:x}")
    emit(f"  ship_b_field6  - ship_a_field6  = 0x{STATE_ADDRS['ship_b_field6']-STATE_ADDRS['ship_a_field6']:x}")
    emit(f"  ship_b_result12- ship_a_result12= 0x{STATE_ADDRS['ship_b_result12']-STATE_ADDRS['ship_a_result12']:x}")
    for name, addr in STATE_ADDRS.items():
        emit(f"{name:16s} 0x{addr:04x}")

    emit()
    emit("===== DIRECT REFERENCES TO PAIRED STATE =====")
    interesting_hits: list[tuple[int,str,int,str]] = []
    for name, addr in STATE_ADDRS.items():
        hits = word_hits(data, addr, start, end)
        classified = [(p, classify_mem_ref(data,p,addr)) for p in hits]
        strong = [(p,c) for p,c in classified if c != "raw-word"]
        emit(f"{name}: addr=0x{addr:04x} all_hits={len(hits)} classified={len(strong)}")
        for p,c in strong:
            owner = find_prologue_before(data, p, start, 0x1800)
            emit(f"  file=0x{p:06x} class={c} function={('0x%06x'%owner) if owner is not None else 'UNKNOWN'}")
            interesting_hits.append((p,name,addr,c))

    emit()
    emit("===== LOCAL RESULT VARIABLE REFERENCES =====")
    for name, addr in LOCAL_RESULT_ADDRS.items():
        hits = word_hits(data, addr, start, end)
        strong = [(p, classify_mem_ref(data,p,addr)) for p in hits]
        strong = [(p,c) for p,c in strong if c != "raw-word"]
        emit(f"{name}: addr=0x{addr:04x} classified={len(strong)}")
        for p,c in strong[:80]:
            owner = find_prologue_before(data, p, start, 0x1800)
            emit(f"  file=0x{p:06x} class={c} function={('0x%06x'%owner) if owner is not None else 'UNKNOWN'}")

    # Disassemble unique functions that strongly access owner/crew candidate slots.
    emit()
    emit("===== FUNCTIONS TOUCHING CAPTURE-MUTATED SLOTS =====")
    target_names = {"ship_a_result2","ship_a_field6","ship_b_result2","ship_b_field6"}
    funcs: dict[int, set[str]] = {}
    for p,name,addr,c in interesting_hits:
        if name not in target_names:
            continue
        owner = find_prologue_before(data, p, start, 0x1800)
        if owner is not None:
            funcs.setdefault(owner, set()).add(name)

    for fn, names in sorted(funcs.items()):
        fn_end = find_next_prologue(data, fn, end, 0x3000)
        if fn_end is None:
            fn_end = min(end, fn + 0x1000)
        emit()
        emit(f"function=0x{fn:06x} slots={','.join(sorted(names))} range=0x{fn:06x}..0x{fn_end:06x}")
        dst, text = disassemble(data, fn, fn_end, out, f"state_user_{fn:06x}")
        emit(f"disassembly={dst}")
        # Print only lines mentioning the paired addresses, plus small source context
        lines = text.splitlines()
        needles = tuple(f"{a:x}" for a in [0x3260,0x3264,0x328a,0x328e])
        selected = []
        for i,line in enumerate(lines):
            low = line.lower()
            if any(n in low for n in needles):
                lo = max(0,i-5); hi=min(len(lines),i+8)
                selected.extend(range(lo,hi))
        for i in sorted(set(selected))[:500]:
            emit(lines[i])

    emit()
    emit("===== RAW CONTEXT OF CAPTURE-MUTATED SLOT REFERENCES =====")
    for p,name,addr,c in interesting_hits:
        if name not in target_names:
            continue
        emit()
        emit(f"--- file=0x{p:06x} {name}=0x{addr:04x} {c} ---")
        emit(context(data,p))

    emit()
    emit("===== CURRENT STRUCTURAL HYPOTHESIS (NOT YET PROMOTED) =====")
    emit("The outcome formatter proves symmetric capture mutation:")
    emit("  if local result slot 0x32 == 0:")
    emit("      state[ship A,+6] := state[ship B,+6]")
    emit("      local slot 0x32 := 10")
    emit("  if local result slot 0x34 == 0:")
    emit("      state[ship B,+6] := state[ship A,+6]")
    emit("      local slot 0x34 := 10")
    emit("and then local result slots are copied into paired structures with stride 0x2A.")
    emit()
    emit("Candidate interpretation:")
    emit("  +6 may be owner/race; +2/local 0x32/0x34 may be crew.")
    emit("This must be proven from independent initialization/use sites before naming")
    emit("the fields. The next queue question is whether the mutated paired state is")
    emit("fed back into OOB construction/re-sort by the shared caller after outcome().")

    (out/"audit.txt").write_text("\n".join(report)+"\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
