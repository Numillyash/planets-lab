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
    fields["initial_cs_file_base"] = (
        fields["load_image_offset"] + fields["initial_cs"] * 16
    )
    return fields


def find_all(data: bytes, needle: bytes) -> list[int]:
    out = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            break
        out.append(pos)
        pos += 1
    return out


def pascal_string_start(data: bytes, text_pos: int, text: bytes) -> tuple[int, bool]:
    if text_pos > 0 and data[text_pos - 1] == len(text):
        return text_pos - 1, True
    return text_pos, False


def nearest_prologue(data: bytes, anchor: int, floor: int, max_back: int = 0x800) -> int | None:
    start = max(floor, anchor - max_back)
    pos = anchor
    while pos >= start:
        p = data.rfind(b"\x55\x89\xe5", start, pos + 1)
        if p < 0:
            return None
        return p
    return None


def disassemble_blob(path: Path, base: int) -> str:
    if shutil.which("ndisasm"):
        proc = subprocess.run(
            ["ndisasm", "-b", "16", "-o", hex(base), str(path)],
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
                f"--adjust-vma={base}",
                str(path),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return proc.stdout
    return "(no ndisasm or objdump installed)"


def classify_offset_refs(
    data: bytes,
    offset: int,
    search_start: int,
    search_end: int,
) -> list[tuple[int, str]]:
    """
    Find references to a true CS-relative 16-bit offset.

    Strong forms are instruction shapes whose boundaries are unambiguous:
      BF iw        mov di, imm16
      B8..BF iw    mov reg, imm16
      68 iw        push imm16
      C7 /0 iw     mov r/m16, imm16 (reported only with context, not fully decoded)

    Turbo Pascal frequently emits:
      mov di, <shortstring offset>
      push cs
      push di
      call ...
    for code-segment string literals, so that exact shape gets highest value.
    """
    word = struct.pack("<H", offset)
    refs: list[tuple[int, str]] = []
    regs = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]

    pos = search_start
    while True:
        pos = data.find(word, pos, search_end)
        if pos < 0:
            break

        # Strong Turbo-Pascal string literal pattern.
        if pos >= 1 and data[pos - 1] == 0xBF:
            inst = pos - 1
            tail = data[pos + 2 : pos + 4]
            if tail == b"\x0e\x57":
                refs.append((inst, f"STRONG mov di,0x{offset:04x}; push cs; push di"))
            else:
                refs.append((inst, f"mov di,0x{offset:04x}"))

        if pos >= 1:
            op = data[pos - 1]
            if 0xB8 <= op <= 0xBE:
                refs.append((pos - 1, f"mov {regs[op-0xB8]},0x{offset:04x}"))
            elif op == 0x68:
                refs.append((pos - 1, f"push 0x{offset:04x}"))
            elif op == 0xC7:
                refs.append((pos - 1, f"possible mov r/m16,0x{offset:04x}"))

        pos += 1

    # De-duplicate same anchor+description.
    return sorted(set(refs))


def emit_context(data: bytes, anchor: int, before: int = 16, after: int = 32) -> str:
    start = max(0, anchor - before)
    end = min(len(data), anchor + after)
    out = []
    for off in range(start, end, 16):
        chunk = data[off : min(off + 16, end)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{off:06x}  {hx:<47}  {asc}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Locate true AFSim VCR result-handler xrefs using MZ load-image offsets."
    )
    ap.add_argument(
        "--exe",
        default="artifacts/external-sources/independent-sims/extracted/afsim/AFSIM.EXE",
    )
    ap.add_argument(
        "--out",
        default="artifacts/external-sources/independent-sims/afsim-result-handler-v2",
    )
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

    report: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        report.append(line)

    emit("===== AFSIM RESULT-HANDLER LOCATOR V2 =====")
    emit("method: fixed MZ load-image / CS-relative short-string offsets")
    emit(f"exe:    {exe}")
    emit(f"size:   {len(data)}")
    emit(f"sha256: {hashlib.sha256(data).hexdigest()}")
    emit()

    emit("===== MZ HEADER =====")
    for k, v in mz.items():
        emit(f"{k}: 0x{v:x} ({v})")

    emit()
    emit("===== TRUE SHORT-STRING OFFSETS =====")
    target_info: dict[str, dict[str, int | bool | bytes]] = {}
    for name, text in TARGETS.items():
        hits = find_all(data, text)
        if not hits:
            emit(f"{name}: NOT FOUND")
            continue
        pos = hits[0]
        ptr_file, pascal_ok = pascal_string_start(data, pos, text)

        # The string pool sits in the same initial CS segment in this executable.
        # initial_cs is currently 0, so segment offset is file - load image base.
        cs_off = ptr_file - mz["initial_cs_file_base"]

        target_info[name] = {
            "text_pos": pos,
            "ptr_file": ptr_file,
            "pascal_ok": pascal_ok,
            "cs_off": cs_off,
            "text": text,
        }
        emit(
            f"{name}: text_file=0x{pos:06x} ptr_file=0x{ptr_file:06x} "
            f"pascal_len_prefix={pascal_ok} cs_off=0x{cs_off:04x}"
        )

    if len(target_info) != len(TARGETS):
        emit("ERROR: one or more target strings missing")
        (out / "audit.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return 65

    # Search code before the string pool first. This avoids treating literal bytes
    # inside the pool or later data tables as xrefs.
    pool_start = min(int(v["ptr_file"]) for v in target_info.values())
    search_start = mz["initial_cs_file_base"]
    search_end = pool_start

    emit()
    emit("===== TRUE OFFSET XREFS =====")
    emit(f"search_range_file=0x{search_start:06x}..0x{search_end:06x}")
    all_refs: list[tuple[int, str, str]] = []

    for name, info in target_info.items():
        off = int(info["cs_off"])
        refs = classify_offset_refs(data, off, search_start, search_end)
        emit(f"{name}: cs_off=0x{off:04x} refs={len(refs)}")
        for anchor, desc in refs:
            emit(f"  file=0x{anchor:06x} {desc}")
            all_refs.append((anchor, name, desc))

    all_refs.sort()

    emit()
    emit("===== XREF CLUSTERS =====")
    clusters: list[list[tuple[int, str, str]]] = []
    for item in all_refs:
        if not clusters or item[0] - clusters[-1][-1][0] > 0x300:
            clusters.append([item])
        else:
            clusters[-1].append(item)

    if not clusters:
        emit("No true immediate xrefs found before the string pool.")
        emit("Fallback interpretation:")
        emit("  the compiler may reference the pool through a pointer table or")
        emit("  a helper returning one of the adjacent strings.")
    else:
        for i, cluster in enumerate(clusters, 1):
            names = sorted(set(x[1] for x in cluster))
            emit(
                f"cluster={i} file_range=0x{cluster[0][0]:06x}..0x{cluster[-1][0]:06x} "
                f"targets={','.join(names)} refs={len(cluster)}"
            )
            for anchor, name, desc in cluster:
                emit(f"  0x{anchor:06x} {name}: {desc}")

    emit()
    emit("===== STRING-POOL BOUNDARIES =====")
    pool_end = max(
        int(v["text_pos"]) + len(v["text"]) for v in target_info.values()
    )
    emit(f"pool_file=0x{pool_start:06x}..0x{pool_end:06x}")
    after = data[pool_end : pool_end + 16]
    emit(f"bytes_after_pool={after.hex(' ')}")
    if after.startswith(b"\x55\x89\xe5"):
        emit(f"next_function_prologue_file=0x{pool_end:06x}")
    else:
        # Search a very small distance because Pascal pools are commonly placed
        # directly between procedures.
        p = data.find(b"\x55\x89\xe5", pool_end, min(len(data), pool_end + 64))
        if p >= 0:
            emit(f"next_function_prologue_file=0x{p:06x}")
        else:
            emit("next_function_prologue_file=NOT_FOUND_WITHIN_64")

    emit()
    emit("===== PRECEDING FUNCTION CANDIDATE =====")
    pre = nearest_prologue(data, pool_start - 1, search_start, max_back=0x1000)
    if pre is None:
        emit("preceding_prologue=NOT_FOUND")
    else:
        emit(f"preceding_prologue_file=0x{pre:06x}")
        # Include through the string pool so references and trailing return are visible.
        end = min(len(data), pool_end + 8)
        blob = data[pre:end]
        blob_path = out / f"preceding_function_{pre:06x}_{end:06x}.bin"
        blob_path.write_bytes(blob)
        dis = disassemble_blob(blob_path, pre)
        (out / "preceding_function.disasm.txt").write_text(dis, encoding="utf-8")
        emit(f"preceding_disassembly={out / 'preceding_function.disasm.txt'}")

    emit()
    emit("===== XREF FUNCTION DISASSEMBLIES =====")
    emitted_starts: set[int] = set()
    for anchor, name, desc in all_refs:
        start = nearest_prologue(data, anchor, search_start, max_back=0x800)
        if start is None or start in emitted_starts:
            continue
        emitted_starts.add(start)
        end = min(len(data), max(anchor + 0x300, start + 0x600))
        blob = data[start:end]
        p = out / f"xref_function_{start:06x}_{end:06x}.bin"
        p.write_bytes(blob)
        dis = disassemble_blob(p, start)
        dp = out / f"xref_function_{start:06x}.disasm.txt"
        dp.write_text(dis, encoding="utf-8")
        emit(
            f"function_start=0x{start:06x} anchor=0x{anchor:06x} "
            f"target={name} detail={desc}"
        )
        emit(f"  disassembly={dp}")

    emit()
    emit("===== RAW CONTEXT FOR TRUE XREFS =====")
    for anchor, name, desc in all_refs:
        emit()
        emit(f"--- 0x{anchor:06x} {name}: {desc} ---")
        emit(emit_context(data, anchor))

    emit()
    emit("===== INTERPRETATION =====")
    emit("The previous V1 ranking was invalid for semantic inference because it")
    emit("allowed arbitrary paragraph bases and therefore matched unrelated small")
    emit("immediates such as 0x001e/0x0028. This V2 pass fixes the base to the")
    emit("actual MZ load image and initial CS, so only references to the true")
    emit("short-string offsets are eligible.")
    emit()
    emit("Desired next evidence:")
    emit("  a procedure referencing multiple result strings; or")
    emit("  a helper/table immediately before the result-string pool that maps")
    emit("  result codes to those strings.")
    emit("Only after that mapping is established should owner/crew/OOB mutation")
    emit("around the caller be interpreted.")

    (out / "audit.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
