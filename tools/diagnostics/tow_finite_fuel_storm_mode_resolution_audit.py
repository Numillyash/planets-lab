from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from planets_lab.corpus.api import CorpusApiError, PlanetsNuPublicApi

from tow_finite_fuel_residual_shape_audit import _parse_clean_cases


TARGET_SETTING = "nuionstorms"
RELATED_SETTINGS = (
    "maxions",
    "maxioncloudsperstorm",
    "nebulas",
    "stars",
)


def _normalize_key(value: Any) -> str:
    return str(value).lower().replace("_", "").replace("-", "")


def _find_named_values(
    value: Any,
    normalized_name: str,
    *,
    path: str = "$",
) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _normalize_key(key) == normalized_name:
                found.append((child_path, child))
            if isinstance(child, (Mapping, list, tuple)):
                found.extend(
                    _find_named_values(
                        child,
                        normalized_name,
                        path=child_path,
                    )
                )
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            if isinstance(child, (Mapping, list, tuple)):
                found.extend(
                    _find_named_values(
                        child,
                        normalized_name,
                        path=child_path,
                    )
                )
    return found


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0"}:
            return False
    return None


def _resolve_mode(entries: Sequence[tuple[str, Any]]) -> tuple[bool | None, str]:
    if not entries:
        return None, "missing"

    parsed = [_boolish(value) for _, value in entries]
    if any(value is None for value in parsed):
        return None, "unparsed"

    unique = set(parsed)
    if unique == {True}:
        return True, "resolved_true"
    if unique == {False}:
        return False, "resolved_false"
    return None, "conflict"


def _repr_entries(entries: Sequence[tuple[str, Any]]) -> tuple[tuple[str, str], ...]:
    return tuple((path, repr(value)) for path, value in entries)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the historical nuionstorms game setting for finite-fuel Tow residual games "
            "using public game/loadinfo through the repository's proxy-only corpus client."
        )
    )
    parser.add_argument("--external-log", type=Path, required=True)
    args = parser.parse_args()

    expected, clean_cases = _parse_clean_cases(args.external_log)
    game_ids = sorted({int(case["game"]) for case in clean_cases})

    totals: Counter[str] = Counter()
    totals["clean_residual_input"] = expected
    totals["unique_games"] = len(game_ids)

    print("===== FINITE-FUEL TOW STORM-MODE RESOLUTION AUDIT =====")
    print("external_log=", args.external_log)
    print("clean_residual_input=", expected)
    print("game_ids=", game_ids)
    print("transport=proxy-only PlanetsNuPublicApi")

    try:
        api = PlanetsNuPublicApi()
    except CorpusApiError as exc:
        print("proxy_client_error=", repr(str(exc)))
        totals["proxy_client_error"] += 1
        print("\n===== SUMMARY =====")
        for key in (
            "clean_residual_input",
            "unique_games",
            "loadinfo_success",
            "loadinfo_error",
            "mode_true_games",
            "mode_false_games",
            "mode_unknown_games",
            "mode_missing_games",
            "mode_unparsed_games",
            "mode_conflict_games",
            "proxy_client_error",
        ):
            print(f"{key}= {totals[key]}")
        return 0

    for game_id in game_ids:
        totals["loadinfo_attempts"] += 1
        try:
            payload = api.load_info(game_id)
        except CorpusApiError as exc:
            totals["loadinfo_error"] += 1
            print(
                {
                    "game": game_id,
                    "loadinfo": "error",
                    "error": str(exc),
                },
                flush=True,
            )
            continue

        totals["loadinfo_success"] += 1
        mode_entries = _find_named_values(payload, TARGET_SETTING)
        mode, status = _resolve_mode(mode_entries)
        totals[f"mode_{status}_games"] += 1
        if mode is True:
            totals["mode_true_games"] += 1
        elif mode is False:
            totals["mode_false_games"] += 1
        else:
            totals["mode_unknown_games"] += 1

        related: dict[str, tuple[tuple[str, str], ...]] = {}
        for setting in RELATED_SETTINGS:
            entries = _find_named_values(payload, _normalize_key(setting))
            related[setting] = _repr_entries(entries)

        print(
            {
                "game": game_id,
                "loadinfo": "ok",
                "nuionstorms": mode,
                "mode_status": status,
                "nuionstorms_entries": _repr_entries(mode_entries),
                "related_settings": related,
                "top_level_keys": tuple(sorted(str(key) for key in payload.keys())),
            },
            flush=True,
        )

    if totals["loadinfo_success"] + totals["loadinfo_error"] != totals["unique_games"]:
        raise AssertionError("loadinfo accounting mismatch")
    if totals["mode_true_games"] + totals["mode_false_games"] + totals["mode_unknown_games"] != totals["loadinfo_success"]:
        raise AssertionError("mode accounting mismatch")

    print("\n===== SUMMARY =====")
    for key in (
        "clean_residual_input",
        "unique_games",
        "loadinfo_attempts",
        "loadinfo_success",
        "loadinfo_error",
        "mode_true_games",
        "mode_false_games",
        "mode_unknown_games",
        "mode_missing_games",
        "mode_unparsed_games",
        "mode_conflict_games",
        "proxy_client_error",
    ):
        print(f"{key}= {totals[key]}")

    print("Public loadinfo is used only to resolve historical game mode metadata.")
    print("No corpus acquisition, simulator rule, or planets-intel change is made here.")
    print("finite-fuel Tow remains OPEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
