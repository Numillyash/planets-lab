from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_TOOL = REPO_ROOT / "tools" / "diagnostics" / "combat_host_single_battle_side_order_audit.py"
DEFAULT_BASELINE = Path("logs/combat-host-single-battle-side-order.json")

spec = importlib.util.spec_from_file_location("combat_host_single_battle_side_order_audit_base", BASE_TOOL)
assert spec is not None and spec.loader is not None
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

_ORIGINAL_FC_KIND = base._fc_kind


def _signed_fc_kind(value: Any) -> tuple[str, int | None]:
    """Hypothesis only: treat exactly three-character +/-NN FCs as signed numeric battle values."""
    if isinstance(value, str) and len(value) == 3 and value[0] in "+-" and value[1:].isdigit():
        return "strict_numeric", int(value)
    return _ORIGINAL_FC_KIND(value)


def _load_baseline(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "planets-lab.combat-host-single-battle-side-order-audit.v1":
        raise ValueError(f"unexpected baseline schema: {raw.get('schema')!r}")
    return raw


def _delta_counts(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
    keys = sorted(set(before) | set(after))
    return {key: int(after.get(key, 0)) - int(before.get(key, 0)) for key in keys}


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline = _load_baseline(args.baseline)
    original = base._fc_kind
    try:
        base._fc_kind = _signed_fc_kind
        alternate = base.run(args)
    finally:
        base._fc_kind = original

    scopes: dict[str, Any] = {}
    for name in ("ordinary", "game_591478", "all"):
        before = baseline["scopes"][name]
        after = alternate["scopes"][name]
        scopes[name] = {
            "baseline_comparable": before["comparable"],
            "signed_comparable": after["comparable"],
            "baseline_side_priority": before["side_priority"],
            "signed_side_priority": after["side_priority"],
            "side_priority_delta": _delta_counts(before["side_priority"], after["side_priority"]),
            "baseline_exclusions": before["exclusions"],
            "signed_exclusions": after["exclusions"],
            "signed_priority_slices": after["priority_slices"],
            "signed_examples": after["examples"],
        }

    return {
        "schema": "planets-lab.combat-host-signed-numeric-fc-hypothesis-audit.v1",
        "read_only": True,
        "hypothesis": "exact three-character Friendly Codes matching [+/-][0-9][0-9] are parsed as signed numeric combat priority values",
        "baseline": str(args.baseline),
        "scopes": scopes,
        "evidence_boundary": (
            "This is an alternative parser differential, not a production rule. The hypothesis is supported only if it removes existing ordinary side-order residuals without creating new residuals. Official Planets.nu documentation describes numeric combat FCs as 001..999, so signed parsing would be an undocumented NuHost behavior if corpus-supported."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare documented numeric-FC parsing against a signed three-character FC hypothesis.")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--archive-dir", type=Path, default=base.RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=base.PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=60)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST SIGNED NUMERIC FC HYPOTHESIS AUDIT =====")
    print(f"hypothesis: {report['hypothesis']}")
    for name, scope in report["scopes"].items():
        print()
        print(f"===== {name} =====")
        for key in (
            "baseline_comparable",
            "signed_comparable",
            "baseline_side_priority",
            "signed_side_priority",
            "side_priority_delta",
            "signed_exclusions",
            "signed_priority_slices",
        ):
            print(f"{key}: {scope[key]}")
        residuals = [row for row in scope["signed_examples"] if row.get("priority_relation") == "left_higher_priority"]
        print(f"signed_left_higher_examples: {len(residuals)}")
        for row in residuals:
            print(
                f"  game={row['game_id']} turn={row['turn']} vcr={row['vcr_id']} "
                f"left_ship={row['left_ship_id']} left_fc={row['left_fc']!r} left_priority={row['left_priority']} "
                f"right_ship={row['right_ship_id']} right_fc={row['right_fc']!r} right_priority={row['right_priority']} "
                f"slice={row['slice']} initiative={row['initiative']}"
            )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: signed numeric FC handling remains a hypothesis until the differential is accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
