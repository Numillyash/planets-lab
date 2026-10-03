#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ARRAYS = {
    "parallel_3d9d": 0x3D9D,
    "parallel_3dcf": 0x3DCF,
    "parallel_3e01": 0x3E01,
}

ENTRY_BASE = 0x32DC
ENTRY_STRIDE = 0x36
ENTRY_FC = 0x00
ENTRY_ATTACK_VALUE = 0x04
ENTRY_OWNER = 0x26
ENTRY_SHIP_ID = 0x24

PROMPTS = {
    "owner": b"Enter number of the race that owns the ship",
    "ship_id": b"Enter the id that you want the ship to be",
    "kill": b"Is the ship set to the kill mission",
    "fuel": b"Does the ship have fuel",
    "primary_enemy": b"What is the ships primary enemy",
    "friendly_code": b"What is this ships Friendly code",
}

KNOWN = {
    "ship_selector": 0x51C6,
    "sort_comparator": 0x5572,
    "resort": 0x5627,
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


def find_prologue_before(data: bytes, anchor: int, floor: int, max_back: int = 0x3000) -> int | None:
    p = data.rfind(b"\x55\x89\xe5", max(floor, anchor - max_back), anchor + 1)
    return p if p >= 0 else None


def find_prologue_after(data: bytes, start: int, ceiling: int, max_forward: int = 0x5000) -> int | None:
    p = data.find(b"\x55\x89\xe5", start + 3, min(ceiling, start + max_forward))
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


def classify_disp16_ref(data: bytes, pos: int, value: int) -> str:
    # pos points at the low byte of a 16-bit displacement.
    if pos >= 2:
        op, modrm = data[pos-2], data[pos-1]
        # mod=10 disp16 indexed form or mod=00 r/m=110 direct form.
        mod = (modrm >> 6) & 0x3
        rm = modrm & 0x7
        if op in {0x80,0x81,0x83,0x88,0x89,0x8A,0x8B,0xC6,0xC7,0xFF}:
            if mod == 2 or (mod == 0 and rm == 6):
                return f"mem opcode=0x{op:02x} modrm=0x{modrm:02x}"
    if pos >= 1:
        op = data[pos-1]
        if op == 0xA0:
            return f"mov al,[0x{value:04x}]"
        if op == 0xA1:
            return f"mov ax,[0x{value:04x}]"
        if op == 0xA2:
            return f"mov [0x{value:04x}],al"
        if op == 0xA3:
            return f"mov [0x{value:04x}],ax"
        if 0xB8 <= op <= 0xBF:
            regs = ["ax","cx","dx","bx","sp","bp","si","di"]
            return f"mov {regs[op-0xB8]},0x{value:04x}"
    return "raw-word"


def function_owner(data: bytes, pos: int, floor: int) -> int | None:
    return find_prologue_before(data, pos, floor, 0x3000)


def pascal_ptr(data: bytes, text_pos: int, text: bytes) -> tuple[int, bool]:
    # Prompt literals may be full strings embedded in a longer prompt, so accept
    # the exact preceding length only when it matches.
    if text_pos > 0 and data[text_pos-1] == len(text):
        return text_pos-1, True
    return text_pos, False


def literal_xrefs(data: bytes, cs_off: int, start: int, end: int) -> list[tuple[int,str]]:
    word = struct.pack("<H", cs_off & 0xFFFF)
    out = []
    for p in find_all(data, word, start, end):
        if p >= 1:
            op = data[p-1]
            if op == 0xBF:
                tail = data[p+2:p+4]
                if tail == b"\x0e\x57":
                    out.append((p-1, "STRONG mov di,off; push cs; push di"))
                else:
                    out.append((p-1, "mov di,off"))
            elif 0xB8 <= op <= 0xBE:
                out.append((p-1, f"mov reg,0x{cs_off:04x}"))
            elif op == 0x68:
                out.append((p-1, f"push 0x{cs_off:04x}"))
    return sorted(set(out))


def emit_function(emit, data: bytes, out: Path, start: int, hi: int, label: str, max_lines: int = 1600):
    end = find_prologue_after(data, start, hi, 0x5000)
    if end is None:
        end = min(hi, start + 0x1800)
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
        description="Map AFSim OOB parallel metadata arrays to Kill/Fuel/Primary Enemy/Friendly Code inputs."
    )
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-oob-metadata")
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
    def emit(s: str = ""):
        print(s)
        report.append(s)

    emit("===== AFSIM OOB METADATA FIELD AUDIT =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit(f"scan:   0x{lo:06x}..0x{hi:06x}")
    emit()

    emit("===== CURRENT BEHAVIORAL IDENTITIES TO VERIFY =====")
    emit("parallel 0x3d9d[index]  candidate: fuel/availability")
    emit("parallel 0x3dcf[index]  candidate: Kill/aggressive flag")
    emit("parallel 0x3e01[index]  candidate: Primary Enemy owner")
    emit("entry +0x00             candidate: 3-char friendly code")
    emit("entry +0x04             proven computed numeric OOB attack value")
    emit()

    emit("===== PARALLEL ARRAY REFERENCE INVENTORY =====")
    funcs: dict[int, set[str]] = collections.defaultdict(set)
    for name, addr in ARRAYS.items():
        emit(f"{name} base=0x{addr:04x}")
        hits = find_all(data, struct.pack("<H", addr), lo, hi)
        shown = 0
        for p in hits:
            cls = classify_disp16_ref(data, p, addr)
            if cls == "raw-word":
                continue
            owner = function_owner(data, p, lo)
            emit(f"  file=0x{p:06x} class={cls} owner={('0x%06x'%owner) if owner is not None else 'UNKNOWN'}")
            if owner is not None:
                funcs[owner].add(name)
            shown += 1
        if not shown:
            emit("  classified_refs=0")
    emit()

    emit("===== FRIENDLY-CODE ENTRY FIELD REFERENCES =====")
    for name, addr in {
        "entry_base": ENTRY_BASE,
        "entry_attack_value_base": ENTRY_BASE + ENTRY_ATTACK_VALUE,
        "entry_owner_base": ENTRY_BASE + ENTRY_OWNER,
        "entry_ship_id_base": ENTRY_BASE + ENTRY_SHIP_ID,
    }.items():
        emit(f"{name}=0x{addr:04x}")
        shown = 0
        for p in find_all(data, struct.pack("<H", addr), lo, hi):
            cls = classify_disp16_ref(data, p, addr)
            if cls == "raw-word":
                continue
            owner = function_owner(data, p, lo)
            emit(f"  file=0x{p:06x} class={cls} owner={('0x%06x'%owner) if owner is not None else 'UNKNOWN'}")
            shown += 1
        if not shown:
            emit("  classified_refs=0")
    emit()

    emit("===== INPUT PROMPT LOCATIONS / XREFS =====")
    prompt_funcs: dict[int, set[str]] = collections.defaultdict(set)
    for name, text in PROMPTS.items():
        positions = find_all(data, text, lo, hi)
        emit(f"{name}: text_hits={len(positions)}")
        for pos in positions:
            ptr, exact_pascal = pascal_ptr(data, pos, text)
            cs_off = ptr - mz["initial_cs_file_base"]
            emit(
                f"  text_file=0x{pos:06x} ptr_file=0x{ptr:06x} "
                f"exact_pascal_prefix={exact_pascal} cs_off=0x{cs_off & 0xffff:04x}"
            )
            refs = literal_xrefs(data, cs_off, lo, hi)
            for rp, cls in refs:
                owner = function_owner(data, rp, lo)
                emit(f"    xref=0x{rp:06x} {cls} owner={('0x%06x'%owner) if owner is not None else 'UNKNOWN'}")
                if owner is not None:
                    prompt_funcs[owner].add(name)
    emit()

    interesting = set(funcs) | set(prompt_funcs)
    # Keep known selector/sort users visible even if prompts are indirect.
    interesting.update(KNOWN.values())

    emit("===== FUNCTIONS CONNECTING INPUTS TO OOB METADATA =====")
    for fn in sorted(interesting):
        labels = sorted(funcs.get(fn,set()) | prompt_funcs.get(fn,set()))
        emit()
        emit(f"function=0x{fn:06x} evidence={','.join(labels) if labels else 'known-oob-user'}")
        emit_function(emit, data, out, fn, hi, f"metadata_user_{fn:06x}", 2000)

    emit()
    emit("===== EXPECTED PROOF =====")
    emit("Confirm concrete write paths:")
    emit("  Kill input          -> parallel 0x3dcf[index]")
    emit("  Fuel input          -> parallel 0x3d9d[index]")
    emit("  Primary Enemy input -> parallel 0x3e01[index]")
    emit("  Friendly code       -> entry[index]+0x00")
    emit()
    emit("Then AFSIM-R1 can be frozen as executable pseudocode:")
    emit("  sort by Kill-class desc, owner asc, attack-value asc, ship-id asc;")
    emit("  select Kill phase first, then Primary Enemy phase;")
    emit("  canonicalize selected pair by ship ID;")
    emit("  lower ship ID -> VCR LEFT, higher ship ID -> VCR RIGHT;")
    emit("  after every combat write back, re-sort and restart from index 1.")
    emit("Held-out remains closed.")

    (out / "audit.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
