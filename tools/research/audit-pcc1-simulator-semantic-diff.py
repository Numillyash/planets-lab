#!/usr/bin/env python3
"""
Instruction-level semantic triage for PCC1 ccSim 1.1.21 -> 1.1.22.

Consumes local artifacts produced by:
  tools/research/audit-pcc1-simulator-lineage.sh
  tools/research/audit-pcc1-simulator-overlay-bytes.py

Goal: distinguish widespread link/layout address churn from an actual change in
capture/battle-order logic without blindly disassembling the whole program.

External PCC behaviour remains source-lineage archaeology, not NuHost evidence.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = ROOT / "artifacts" / "external-sources" / "pcc1-lineage"

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
)

SYMBOL_RE = re.compile(r"^\s*([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\S+)")
OBJDUMP_RE = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+"
    r"((?:(?:[0-9a-fA-F]{2})\s+)+)"
    r"\s*(\S+)"
    r"(?:\s+(.*?))?\s*$"
)
HEX_RE = re.compile(r"(?<![A-Za-z0-9_])(-?0x[0-9a-fA-F]+)")
HEX_UNSIGNED_RE = re.compile(r"0x[0-9a-fA-F]+")


@dataclass
class Symbol:
    segment: int
    offset: int
    name: str


@dataclass
class Insn:
    addr: int
    raw: bytes
    mnemonic: str
    operands: str

    @property
    def size(self) -> int:
        return len(self.raw)

    @property
    def text(self) -> str:
        return self.mnemonic + ((" " + self.operands) if self.operands else "")


def find_one(root: Path, name_glob: str) -> Path:
    hits = sorted(root.rglob(name_glob))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name_glob} under {root}, got {hits}")
    return hits[0]


def parse_map(path: Path) -> list[Symbol]:
    out: dict[tuple[int, int, str], Symbol] = {}
    for line in path.read_text(errors="replace").splitlines():
        m = SYMBOL_RE.match(line)
        if m:
            seg = int(m.group(1), 16)
            off = int(m.group(2), 16)
            name = m.group(3)
            out[(seg, off, name)] = Symbol(seg, off, name)
    return sorted(out.values(), key=lambda s: (s.segment, s.offset, s.name))


def simulator_segment(symbols: list[Symbol]) -> int:
    xs = [s.segment for s in symbols if s.name.lower() == "calcbattleorder"]
    if len(xs) != 1:
        raise RuntimeError(f"expected exactly one CalcBattleOrder, got {xs}")
    return xs[0]


def segment_symbols(symbols: list[Symbol], seg: int) -> list[Symbol]:
    # Same symbol can appear twice in MAP public/detail listings. Deduplicate.
    d = {(s.offset, s.name): s for s in symbols if s.segment == seg}
    return sorted(d.values(), key=lambda s: (s.offset, s.name))


def routine_ranges(symbols: list[Symbol], seg: int) -> dict[str, tuple[int, int]]:
    ss = segment_symbols(symbols, seg)
    out: dict[str, tuple[int, int]] = {}
    for i, s in enumerate(ss):
        end = ss[i + 1].offset if i + 1 < len(ss) else 0x10000
        out[s.name] = (s.offset, end)
    return out


def disassemble(blob: bytes, start: int, end: int) -> list[Insn]:
    objdump = shutil.which("objdump")
    if not objdump:
        raise RuntimeError("GNU objdump is required (package binutils)")

    import tempfile

    piece = blob[start:end]
    with tempfile.NamedTemporaryFile(prefix="pcc1-ccsim-", suffix=".bin") as tf:
        tf.write(piece)
        tf.flush()
        proc = subprocess.run(
            [
                objdump,
                "-D",
                "-b",
                "binary",
                "-m",
                "i8086",
                "-M",
                "intel",
                f"--adjust-vma=0x{start:X}",
                tf.name,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    out: list[Insn] = []
    for line in proc.stdout.splitlines():
        m = OBJDUMP_RE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        raw = bytes.fromhex(m.group(2))
        mnemonic = m.group(3).lower()
        operands = (m.group(4) or "").strip().lower()
        out.append(Insn(addr, raw, mnemonic, operands))
    return out


def operand_skeleton(s: str) -> str:
    # Keep registers/operators/addressing shape, erase only numeric literals.
    return HEX_RE.sub("<n>", s)


def numbers(s: str) -> list[int]:
    vals = []
    for m in HEX_RE.finditer(s):
        token = m.group(1)
        sign = -1 if token.startswith("-") else 1
        if sign < 0:
            token = token[1:]
        vals.append(sign * int(token, 16))
    return vals


def symbol_indexes(symbols: list[Symbol]) -> dict[str, dict[int, set[str]]]:
    by_offset: dict[int, set[str]] = collections.defaultdict(set)
    by_segment: dict[int, set[str]] = collections.defaultdict(set)
    by_linear: dict[int, set[str]] = collections.defaultdict(set)
    for s in symbols:
        by_offset[s.offset].add(s.name)
        by_segment[s.segment].add(s.name)
        by_linear[(s.segment << 4) + s.offset].add(s.name)
    return {
        "offset": dict(by_offset),
        "segment": dict(by_segment),
        "linear": dict(by_linear),
    }


def same_symbol_reference(
    old: int,
    new: int,
    idx_a: dict[str, dict[int, set[str]]],
    idx_b: dict[str, dict[int, set[str]]],
) -> tuple[bool, list[str]]:
    hits: set[str] = set()
    for domain in ("offset", "segment", "linear"):
        aa = idx_a[domain].get(old, set())
        bb = idx_b[domain].get(new, set())
        hits |= aa & bb
    return (bool(hits), sorted(hits))


def classify_pair(
    a: Insn,
    b: Insn,
    idx_a: dict[str, dict[int, set[str]]],
    idx_b: dict[str, dict[int, set[str]]],
) -> tuple[str, dict]:
    if a.raw == b.raw and a.text == b.text:
        return "equal", {}

    if a.mnemonic != b.mnemonic:
        return "mnemonic_change", {}

    if operand_skeleton(a.operands) != operand_skeleton(b.operands):
        return "operand_shape_change", {
            "skeleton_a": operand_skeleton(a.operands),
            "skeleton_b": operand_skeleton(b.operands),
        }

    na = numbers(a.operands)
    nb = numbers(b.operands)
    mapped = []
    unresolved = []
    if len(na) == len(nb):
        for x, y in zip(na, nb):
            if x == y:
                continue
            ok, names = same_symbol_reference(x, y, idx_a, idx_b)
            row = {"old": x, "new": y, "delta": y - x, "symbols": names}
            if ok:
                mapped.append(row)
            else:
                unresolved.append(row)
    else:
        unresolved.append({"old_numbers": na, "new_numbers": nb})

    if unresolved:
        return "operand_value_change", {"mapped": mapped, "unresolved": unresolved}
    if mapped:
        return "mapped_symbol_relocation", {"mapped": mapped}

    # The text can differ only in formatting while numeric values are equal.
    return "text_only", {}


def align_by_address(a: list[Insn], b: list[Insn]) -> list[tuple[Optional[Insn], Optional[Insn]]]:
    da = {x.addr: x for x in a}
    db = {x.addr: x for x in b}
    return [(da.get(addr), db.get(addr)) for addr in sorted(set(da) | set(db))]


def compact_insn(x: Optional[Insn]) -> Optional[dict]:
    if x is None:
        return None
    return {
        "addr": f"0x{x.addr:X}",
        "size": x.size,
        "bytes": x.raw.hex(),
        "text": x.text,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--old", default="1121")
    ap.add_argument("--new", default="1122")
    ap.add_argument("--targets", nargs="*", default=list(TARGETS))
    args = ap.parse_args()

    base = args.base
    derived = base / "derived" / "overlay-byte-audit"
    report_path = base / f"pcc1-simulator-semantic-diff-{args.old}-{args.new}.json"
    text_path = base / f"pcc1-simulator-semantic-diff-{args.old}-{args.new}.txt"

    raw_a_path = derived / f"cc{args.old}-ccsim-overlay.raw.bin"
    raw_b_path = derived / f"cc{args.new}-ccsim-overlay.raw.bin"
    if not raw_a_path.is_file() or not raw_b_path.is_file():
        raise RuntimeError(
            "overlay byte artifacts missing; run audit-pcc1-simulator-overlay-bytes.py first"
        )

    db_a = base / "extracted" / f"cc{args.old}db"
    db_b = base / "extracted" / f"cc{args.new}db"
    map_a = find_one(db_a, "*.MAP")
    map_b = find_one(db_b, "*.MAP")

    syms_a = parse_map(map_a)
    syms_b = parse_map(map_b)
    seg_a = simulator_segment(syms_a)
    seg_b = simulator_segment(syms_b)
    ranges_a = routine_ranges(syms_a, seg_a)
    ranges_b = routine_ranges(syms_b, seg_b)
    idx_a = symbol_indexes(syms_a)
    idx_b = symbol_indexes(syms_b)

    blob_a = raw_a_path.read_bytes()
    blob_b = raw_b_path.read_bytes()

    report = {
        "schema": "planets-lab.pcc1-simulator-semantic-diff.v1",
        "versions": [args.old, args.new],
        "map_segments": [f"{seg_a:04X}", f"{seg_b:04X}"],
        "targets": {},
        "guardrail": (
            "Instruction-shape equality here only characterizes the PCC1/PCC2/c2ng "
            "source lineage. It is not independent NuHost evidence."
        ),
    }

    text_lines = [
        "===== PCC1 CCSIM INSTRUCTION-LEVEL SEMANTIC TRIAGE =====",
        f"old={args.old} segment={seg_a:04X}",
        f"new={args.new} segment={seg_b:04X}",
        "",
    ]

    total_counts = collections.Counter()
    global_delta_hist = collections.Counter()

    for target in args.targets:
        if target not in ranges_a or target not in ranges_b:
            report["targets"][target] = {"status": "missing"}
            text_lines += [f"===== {target} =====", "status=missing", ""]
            continue

        a0, a1 = ranges_a[target]
        b0, b1 = ranges_b[target]
        ins_a = disassemble(blob_a, a0, min(a1, len(blob_a)))
        ins_b = disassemble(blob_b, b0, min(b1, len(blob_b)))

        pairs = align_by_address(ins_a, ins_b)
        counts = collections.Counter()
        details = []
        delta_hist = collections.Counter()

        for ia, ib in pairs:
            if ia is None or ib is None:
                cls = "instruction_boundary_change"
                meta = {}
            elif ia.size != ib.size:
                cls = "instruction_size_change"
                meta = {}
            else:
                cls, meta = classify_pair(ia, ib, idx_a, idx_b)

            counts[cls] += 1
            total_counts[cls] += 1

            if cls != "equal":
                row = {
                    "class": cls,
                    "old": compact_insn(ia),
                    "new": compact_insn(ib),
                    "meta": meta,
                }
                details.append(row)
                for section in ("mapped", "unresolved"):
                    for item in meta.get(section, []):
                        if isinstance(item, dict) and "delta" in item:
                            delta_hist[item["delta"]] += 1
                            global_delta_hist[item["delta"]] += 1

        report["targets"][target] = {
            "status": "ok",
            "range_old": [f"0x{a0:X}", f"0x{a1:X}"],
            "range_new": [f"0x{b0:X}", f"0x{b1:X}"],
            "instructions_old": len(ins_a),
            "instructions_new": len(ins_b),
            "classes": dict(sorted(counts.items())),
            "operand_delta_histogram": [
                {"delta": delta, "count": count}
                for delta, count in delta_hist.most_common(20)
            ],
            "differences": details,
        }

        text_lines.append(f"===== {target} =====")
        text_lines.append(
            f"range=0x{a0:X}..0x{a1:X} -> 0x{b0:X}..0x{b1:X} "
            f"insns={len(ins_a)}->{len(ins_b)}"
        )
        for key in (
            "equal",
            "mapped_symbol_relocation",
            "operand_value_change",
            "text_only",
            "operand_shape_change",
            "mnemonic_change",
            "instruction_size_change",
            "instruction_boundary_change",
        ):
            if counts[key]:
                text_lines.append(f"{key}: {counts[key]}")

        serious = {
            "operand_value_change",
            "operand_shape_change",
            "mnemonic_change",
            "instruction_size_change",
            "instruction_boundary_change",
        }
        interesting = [d for d in details if d["class"] in serious]
        if interesting:
            text_lines.append("--- unresolved / shape differences ---")
            for d in interesting[:120]:
                old = d["old"]
                new = d["new"]
                text_lines.append(
                    f"{d['class']}: "
                    f"{old['addr'] if old else '<none>'} "
                    f"{old['text'] if old else '<none>'}  ==>  "
                    f"{new['text'] if new else '<none>'}"
                )
                if d["meta"]:
                    text_lines.append("  meta=" + json.dumps(d["meta"], sort_keys=True))
            if len(interesting) > 120:
                text_lines.append(f"... {len(interesting) - 120} more in JSON")
        else:
            text_lines.append("unresolved / shape differences: none")

        mapped = [d for d in details if d["class"] == "mapped_symbol_relocation"]
        if mapped:
            text_lines.append("--- mapped symbol relocations (first 20) ---")
            for d in mapped[:20]:
                text_lines.append(
                    f"{d['old']['addr']} {d['old']['text']} ==> {d['new']['text']} "
                    f"{json.dumps(d['meta'], sort_keys=True)}"
                )
        text_lines.append("")

    report["totals"] = {
        "classes": dict(sorted(total_counts.items())),
        "operand_delta_histogram": [
            {"delta": delta, "count": count}
            for delta, count in global_delta_hist.most_common(50)
        ],
    }

    text_lines += [
        "===== TOTALS =====",
        *(f"{k}: {v}" for k, v in sorted(total_counts.items())),
        "",
        "===== INTERPRETATION =====",
        "mapped_symbol_relocation = changed operand resolves to same MAP symbol across builds",
        "operand_value_change     = same instruction shape, but numeric change not explained by MAP",
        "operand_shape/mnemonic/boundary change = potential actual generated-code change",
        "",
        f"json_report: {report_path}",
        f"text_report: {text_path}",
    ]

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")
    print("\n".join(text_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
