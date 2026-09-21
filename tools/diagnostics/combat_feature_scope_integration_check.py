from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "planets-lab.combat-feature-scope-integration-check.v1"
PROFILE = "combat-planar-no-horwasp"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: report must be a JSON object")
    return payload


def _expect(actual: Any, expected: Any, label: str, failures: list[str]) -> None:
    if actual != expected:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def _scope(report: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    scopes = report.get("scopes")
    if not isinstance(scopes, Mapping):
        raise ValueError("report has no scopes object")
    value = scopes.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"report has no scope {name!r}")
    return value


def check(
    planet: Mapping[str, Any],
    phase: Mapping[str, Any],
    cluster: Mapping[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []

    selections: list[Mapping[str, Any]] = []
    for name, report in (
        ("planet", planet),
        ("phase", phase),
        ("cluster", cluster),
    ):
        selection = report.get("scope_selection")
        if not isinstance(selection, Mapping):
            failures.append(f"{name}: missing scope_selection")
            continue
        selections.append(selection)
        _expect(selection.get("profile"), PROFILE, f"{name}.profile", failures)
        _expect(selection.get("predicate_count"), 3, f"{name}.predicate_count", failures)
        _expect(selection.get("unknown_game_ids"), [], f"{name}.unknown_game_ids", failures)

    if selections:
        canonical = {
            "included_game_ids": selections[0].get("included_game_ids"),
            "excluded_game_ids": selections[0].get("excluded_game_ids"),
            "unknown_game_ids": selections[0].get("unknown_game_ids"),
        }
        for index, selection in enumerate(selections[1:], start=1):
            for key, expected in canonical.items():
                _expect(
                    selection.get(key),
                    expected,
                    f"selection[{index}].{key}",
                    failures,
                )

        included = selections[0].get("included_game_ids")
        excluded = selections[0].get("excluded_game_ids")
        _expect(len(included or []), 11, "selected game count", failures)
        _expect(len(excluded or []), 1, "excluded game count", failures)

    # C4 checkpoint continuity: selector-backed scope must preserve the exact
    # historical 11-game population previously defined by an ad-hoc game-id
    # exclusion.
    planet_selected = _scope(planet, "profile_selected_all")
    _expect(planet_selected.get("transitions"), 103, "planet.transitions", failures)
    _expect(
        planet_selected.get("status"),
        {"match": 102, "not_comparable": 1},
        "planet.status",
        failures,
    )
    _expect(
        planet_selected.get("base_kind"),
        {"starbase": 92, "no_starbase": 11},
        "planet.base_kind",
        failures,
    )
    _expect(
        planet_selected.get("shield_carry"),
        {"match": 103},
        "planet.shield_carry",
        failures,
    )

    # C3 checkpoint continuity.
    phase_all = _scope(phase, "profile_selected_all")
    _expect(phase_all.get("transitions"), 1169, "phase.all.transitions", failures)
    _expect(
        phase_all.get("status"),
        {
            "match": 1138,
            "reappearance_after_capture": 23,
            "mismatch": 8,
        },
        "phase.all.status",
        failures,
    )

    ship_ship = _scope(phase, "profile_selected_ship_vs_ship_survivors")
    _expect(ship_ship.get("transitions"), 764, "phase.ship_ship.transitions", failures)
    _expect(ship_ship.get("status"), {"match": 764}, "phase.ship_ship.status", failures)

    ship_ship_gap1 = _scope(
        phase,
        "profile_selected_ship_vs_ship_survivors_gap1",
    )
    _expect(
        ship_ship_gap1.get("transitions"),
        751,
        "phase.ship_ship_gap1.transitions",
        failures,
    )
    _expect(
        ship_ship_gap1.get("status"),
        {"match": 751},
        "phase.ship_ship_gap1.status",
        failures,
    )

    boundary = _scope(phase, "profile_selected_ship_to_planet_boundary")
    _expect(boundary.get("transitions"), 397, "phase.boundary.transitions", failures)
    _expect(
        boundary.get("status"),
        {
            "match": 374,
            "reappearance_after_capture": 15,
            "mismatch": 8,
        },
        "phase.boundary.status",
        failures,
    )

    # The descriptive cluster diagnostic must use the same selector-backed
    # partition; mechanics assertions remain in the phase/planet diagnostics.
    cluster_selected = _scope(cluster, "profile_selected")
    cluster_excluded = _scope(cluster, "profile_excluded")
    _expect(
        cluster_selected.get("status", {}).get("same_location_transitions"),
        1169,
        "cluster.selected.same_location_transitions",
        failures,
    )
    _expect(
        cluster_excluded.get("status", {}).get("same_location_transitions"),
        316,
        "cluster.excluded.same_location_transitions",
        failures,
    )

    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "exact": not failures,
        "failures": failures,
        "checks": {
            "selector_partition_shared": True if selections and not any(
                failure.startswith("selection[") for failure in failures
            ) else False,
            "planet_c4_checkpoint_preserved": not any(
                failure.startswith("planet.") for failure in failures
            ),
            "ship_c3_checkpoint_preserved": not any(
                failure.startswith("phase.") for failure in failures
            ),
            "cluster_partition_preserved": not any(
                failure.startswith("cluster.") for failure in failures
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that feature-index combat scoping preserves the established "
            "C3/C4 historical checkpoint populations."
        )
    )
    parser.add_argument("planet", type=Path)
    parser.add_argument("phase", type=Path)
    parser.add_argument("cluster", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        report = check(
            _load(args.planet),
            _load(args.phase),
            _load(args.cluster),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
