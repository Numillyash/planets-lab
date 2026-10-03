#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

# Standard THost VCR record layout (100 bytes) as independently documented by
# PlanetsCentral. AFSim's live in-memory battle record matches it exactly.
VCR_BASE = 0x323E
LEFT_OBJ = VCR_BASE + 12          # 0x324A
RIGHT_OBJ = VCR_BASE + 54         # 0x3274
LEFT_SHIELD = VCR_BASE + 96       # 0x329E
RIGHT_SHIELD = VCR_BASE + 98      # 0x32A0

OBJ_FIELDS = {
    "damage": 20,
    "crew": 22,
    "id": 24,
    "owner_word": 26,  # THost addresses owner byte + zero high byte as WORD
    "picture_word": 28,
    "beam_type": 30,
    "beam_count_word": 32,
    "fighter_bays": 34,
    "torp_type": 36,
    "ammo": 38,
    "torp_tubes": 40,
}

KNOWN_FUNCTIONS = {
    "planet_or_right_builder": 0x402D,
    "screen_result_parser": 0x4C4C,
    "outcome_handler": 0x4E2D,
    "battle_end_detector": 0x4F8B,
    "battle_end_isr": 0x50CE,
    "postcombat_candidate": 0x675A,
}


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def parse_mz(data: bytes) -> dict[str, int]:
    if len(data) < 0x1C or data[:2] not in {b"MZ", b"ZM"}:
        raise ValueError("not an MZ executable")
    pages = u16(data, 0x04)
    last = u16(data, 0x02)
    hdr = u16(data, 0x08) * 16
    size = (pages - 1) * 512 + (last or 512) if pages else len(data)
    return {
        "load_image_offset": hdr,
        "mz_file_size": min(size, len(data)),
    }


def disassemble(data: bytes, start: int, end: int, out: Path, stem: str) -> tuple[Path, str]:
    p = out / f"{stem}_{start:06x}_{end:06x}.bin"
    p.write_bytes(data[start:end])
    if shutil.which("ndisasm"):
        r = subprocess.run(
            ["ndisasm", "-b", "16", "-o", hex(start), str(p)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        text = r.stdout
    elif shutil.which("objdump"):
        r = subprocess.run(
            ["objdump", "-D", "-b", "binary", "-m", "i8086", "-M", "intel",
             f"--adjust-vma={start}", str(p)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        text = r.stdout
    else:
        text = "(no ndisasm/objdump installed)\n"
    d = out / f"{stem}_{start:06x}.disasm.txt"
    d.write_text(text, encoding="utf-8")
    return d, text


def find_pascal_prologue_before(data: bytes, anchor: int, floor: int, max_back: int = 0x3000) -> int | None:
    p = data.rfind(b"\x55\x89\xe5", max(floor, anchor - max_back), anchor + 1)
    return p if p >= 0 else None


def find_pascal_prologue_after(data: bytes, start: int, ceiling: int, max_forward: int = 0x5000) -> int | None:
    p = data.find(b"\x55\x89\xe5", start + 3, min(ceiling, start + max_forward))
    return p if p >= 0 else None


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


def classify_ref(data: bytes, pos: int, value: int) -> str:
    regs = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
    if pos >= 1:
        op = data[pos - 1]
        if 0xB8 <= op <= 0xBF:
            return f"mov {regs[op-0xB8]},0x{value:04x}"
        if op == 0x68:
            return f"push 0x{value:04x}"
        if op == 0xA1:
            return f"mov ax,[0x{value:04x}]"
        if op == 0xA3:
            return f"mov [0x{value:04x}],ax"
    if pos >= 2:
        op, modrm = data[pos-2], data[pos-1]
        if op == 0xC7 and modrm == 0x06:
            return f"mov word [0x{value:04x}],imm16"
        if op == 0xC6 and modrm == 0x06:
            return f"mov byte [0x{value:04x}],imm8"
        if op in {0x80,0x81,0x83,0x88,0x89,0x8A,0x8B,0xFF} and (modrm & 0xC7) == 0x06:
            return f"direct-mem opcode=0x{op:02x} modrm=0x{modrm:02x}"
    return "raw-word"


def function_owner(data: bytes, pos: int, floor: int) -> str:
    # The battle-end ISR intentionally does not use a Pascal 55/89/e5 prologue.
    if 0x50CE <= pos <= 0x513C:
        return "0x0050ce ISR"
    p = find_pascal_prologue_before(data, pos, floor, 0x3000)
    return f"0x{p:06x}" if p is not None else "UNKNOWN"


def emit_disasm(emit, data: bytes, out: Path, label: str, start: int, end: int, max_lines: int = 1600):
    dst, txt = disassemble(data, start, end, out, label)
    emit(f"{label}: 0x{start:06x}..0x{end:06x} bytes={end-start}")
    emit(f"disassembly={dst}")
    lines = txt.splitlines()
    for line in lines[:max_lines]:
        emit(line)
    if len(lines) > max_lines:
        emit(f"... truncated after {max_lines} lines; full copy saved locally")


def main() -> int:
    ap = argparse.ArgumentParser(description="Map AFSim's live VCR record and trace it back into OOB/queue code.")
    ap.add_argument("--exe", default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE")
    ap.add_argument("--out", default="artifacts/external-sources/independent-sims/afsim-vcr-queue-bridge")
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

    emit("===== AFSIM VCR -> OOB/QUEUE BRIDGE AUDIT =====")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit(f"scan:   0x{lo:06x}..0x{hi:06x}")
    emit()

    emit("===== EXACT VCR RECORD LAYOUT MATCH =====")
    emit(f"record_base       0x{VCR_BASE:04x}")
    emit(f"left_object       0x{LEFT_OBJ:04x} (= record + 12)")
    emit(f"right_object      0x{RIGHT_OBJ:04x} (= record + 54)")
    emit(f"object_stride     0x{RIGHT_OBJ-LEFT_OBJ:02x} ({RIGHT_OBJ-LEFT_OBJ} bytes)")
    emit(f"left_shield       0x{LEFT_SHIELD:04x} (= record + 96)")
    emit(f"right_shield      0x{RIGHT_SHIELD:04x} (= record + 98)")
    emit(f"record_size       100 bytes")
    emit()

    for side, base in [("left", LEFT_OBJ), ("right", RIGHT_OBJ)]:
        emit(f"{side} object @ 0x{base:04x}:")
        for name, off in OBJ_FIELDS.items():
            emit(f"  +{off:02d} 0x{base+off:04x} {name}")
    emit()

    emit("===== CAPTURE MUTATION FIELD IDENTITY =====")
    emit("Outcome handler 0x4e2d uses:")
    emit(f"  left crew  = 0x{LEFT_OBJ+22:04x}")
    emit(f"  right crew = 0x{RIGHT_OBJ+22:04x}")
    emit(f"  left owner = 0x{LEFT_OBJ+26:04x}")
    emit(f"  right owner= 0x{RIGHT_OBJ+26:04x}")
    emit("Therefore the already-observed symmetric mutation is:")
    emit("  if left crew reaches 0:  left.owner := right.owner; left.crew := 10")
    emit("  if right crew reaches 0: right.owner := left.owner; right.crew := 10")
    emit()

    emit("===== BATTLE-END CONTROL-FLOW CORRECTION =====")
    emit("0x4f8b is a battle-end detector/poller and returns with RET at 0x50cd.")
    emit("0x50ce is a separate interrupt-style routine ending in IRET at 0x513c.")
    emit("The ISR calls detector 0x4f8b and, when completion flags permit, calls:")
    emit("  parser  0x4c4c")
    emit("  outcome 0x4e2d")
    emit("Do not describe 0x4f8b itself as the parser/outcome shared caller.")
    emit()

    emit("===== VCR RECORD/OBJECT ADDRESS REFERENCES =====")
    addresses = {
        "record_base": VCR_BASE,
        "left_object": LEFT_OBJ,
        "right_object": RIGHT_OBJ,
        "left_damage": LEFT_OBJ+20,
        "left_crew": LEFT_OBJ+22,
        "left_id": LEFT_OBJ+24,
        "left_owner": LEFT_OBJ+26,
        "right_damage": RIGHT_OBJ+20,
        "right_crew": RIGHT_OBJ+22,
        "right_id": RIGHT_OBJ+24,
        "right_owner": RIGHT_OBJ+26,
        "left_shield": LEFT_SHIELD,
        "right_shield": RIGHT_SHIELD,
    }
    functions: dict[int, set[str]] = {}
    for name, addr in addresses.items():
        hits = []
        for p in word_hits(data, addr, lo, hi):
            cls = classify_ref(data, p, addr)
            if cls == "raw-word":
                continue
            owner = function_owner(data, p, lo)
            emit(f"{name:13s} addr=0x{addr:04x} file=0x{p:06x} class={cls} function={owner}")
            hits.append((p, owner))
            if owner.startswith("0x") and "ISR" not in owner:
                try:
                    fn = int(owner, 16)
                    functions.setdefault(fn, set()).add(name)
                except ValueError:
                    pass
        if not hits:
            emit(f"{name:13s} addr=0x{addr:04x} classified_refs=0")
    emit()

    emit("===== KNOWN FUNCTION CALLERS =====")
    for name, target in KNOWN_FUNCTIONS.items():
        refs = near_refs(data, target, lo, hi)
        emit(f"{name:24s} target=0x{target:06x} refs={len(refs)}")
        for p, kind in refs:
            emit(f"  file=0x{p:06x} {kind} owner={function_owner(data,p,lo)}")
    emit()

    emit("===== PLANET/RIGHT-OBJECT BUILDER 0x402d =====")
    end_402d = find_pascal_prologue_after(data, 0x402D, hi, 0x3000) or min(hi, 0x402D+0x1200)
    emit_disasm(emit, data, out, "function_00402d", 0x402D, end_402d, 1200)
    emit()

    emit("===== POSTCOMBAT CANDIDATE 0x675a =====")
    end_675a = find_pascal_prologue_after(data, 0x675A, hi, 0x5000) or min(hi, 0x675A+0x2000)
    emit_disasm(emit, data, out, "function_00675a", 0x675A, end_675a, 1800)
    emit()

    emit("===== FUNCTIONS WITH MULTIPLE VCR STATE REFERENCES =====")
    ranked = sorted(functions.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for fn, names in ranked:
        if len(names) < 2 or fn in {0x402D,0x4E2D,0x675A}:
            continue
        fn_end = find_pascal_prologue_after(data, fn, hi, 0x4000) or min(hi, fn+0x1000)
        emit()
        emit(f"function=0x{fn:06x} refs={','.join(sorted(names))}")
        emit_disasm(emit, data, out, f"multi_vcr_{fn:06x}", fn, fn_end, 1000)

    emit()
    emit("===== QUEUE-BRIDGE SEARCH TARGETS =====")
    emit("The next semantic bridge is any code which:")
    emit("  - copies a 42-byte left/right VCR object back into a persistent AFSim ship;")
    emit("  - reads owner/crew after outcome_handler and updates an OOB entry;")
    emit("  - invokes OOB sort/recalculation after capture;")
    emit("  - advances/restarts a battle-order cursor after the ISR marks completion.")
    emit("Prioritize 0x675a and callers before broad disassembly.")
    emit("External VCR format identity is useful for AFSim reverse engineering only;")
    emit("it is not NuHost evidence.")

    (out/"audit.txt").write_text("\n".join(report)+"\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
