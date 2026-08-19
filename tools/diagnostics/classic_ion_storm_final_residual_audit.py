from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import hypot
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import duckdb

from planets_lab.corpus.api import CorpusApiError, PlanetsNuPublicApi
from planets_lab.corpus.movement_chunnel_context import _effective_sample
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _planet_tuples_by_turn,
    _warp_well_destination,
)
from planets_lab.corpus.movement_residual_context import (
    StormRecord,
    _navigation_endpoint,
    _storm_consensus_by_turn,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.rules.ion_storm import integer_drag_delta
from planets_lab.validation.movement_geometry import MovementSample


DB = Path("validation/corpus/compiled/v1/corpus.duckdb")
ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared")
DIRECT_API_BASE_URL = "http://api.planets.nu"


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0"}:
            return False
    return None


def _find_setting(value: Any, normalized_name: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if normalized == normalized_name:
                found.append(child)
            if isinstance(child, (Mapping, list, tuple)):
                found.extend(_find_setting(child, normalized_name))
    elif isinstance(value, (list, tuple)):
        for child in value:
            if isinstance(child, (Mapping, list, tuple)):
                found.extend(_find_setting(child, normalized_name))
    return found


def _nuionstorms_consensus(snapshots: Sequence[Any]) -> tuple[bool | None, tuple[Any, ...]]:
    raw_values: list[Any] = []
    parsed: set[bool] = set()
    for snapshot in snapshots:
        values = _find_setting(snapshot.mechanics_payload, "nuionstorms")
        raw_values.extend(values)
        for value in values:
            flag = _boolish(value)
            if flag is not None:
                parsed.add(flag)
    consensus = next(iter(parsed)) if len(parsed) == 1 else None
    unique_raw = tuple(sorted({repr(value) for value in raw_values}))
    return consensus, unique_raw


def _settings_from_payload(payload: Any) -> tuple[bool | None, dict[str, Any], str | None]:
    if not isinstance(payload, dict):
        return None, {}, "loadinfo response is not an object"
    settings = payload.get("settings")
    if not isinstance(settings, dict):
        return None, {}, "loadinfo response has no settings object"
    return _boolish(settings.get("nuionstorms")), settings, None


def _official_settings_proxy(
    api: PlanetsNuPublicApi,
    game_id: int,
) -> tuple[bool | None, dict[str, Any], str | None]:
    try:
        payload = api.load_info(game_id)
    except CorpusApiError as exc:
        return None, {}, str(exc)
    return _settings_from_payload(payload)


def _official_settings_direct(
    game_id: int,
) -> tuple[bool | None, dict[str, Any], str | None]:
    """Fetch public loadinfo directly for an explicitly local diagnostic run.

    This helper is intentionally scoped to this diagnostic. The corpus API itself
    remains proxy-only so server-side acquisition cannot silently bypass the proxy.
    """

    url = f"{DIRECT_API_BASE_URL}/game/loadinfo?{urlencode({'gameid': game_id})}"
    request = Request(
        url,
        headers={
            "Accept-Encoding": "gzip",
            "User-Agent": "planets-lab-local-diagnostic/0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=30.0) as response:
            data = response.read()
            encoding = response.headers.get("Content-Encoding", "")
    except HTTPError as exc:
        return None, {}, f"Planets.nu returned HTTP {exc.code} for game/loadinfo"
    except URLError as exc:
        return None, {}, f"Planets.nu direct loadinfo failed: {exc.reason}"

    if encoding.lower() == "gzip" or data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except OSError as exc:
            return None, {}, f"Planets.nu returned invalid gzip data: {exc}"

    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, {}, f"Planets.nu returned invalid JSON: {exc}"

    if isinstance(payload, dict) and payload.get("success") is False:
        return None, {}, str(payload.get("error", "Planets.nu loadinfo failed"))
    return _settings_from_payload(payload)


def _classic_root_storms(storms: Sequence[StormRecord]) -> tuple[StormRecord, ...]:
    return tuple(
        sorted((storm for storm in storms if storm.parent_id == 0), key=lambda item: item.id)
    )


def _classic_constant_offset(
    storms: Sequence[StormRecord],
    *,
    x: int,
    y: int,
) -> tuple[tuple[int, int] | None, str, tuple[int, ...]]:
    """Documented classic-storm alternative: voltage is constant inside each circle.

    This deliberately reuses the currently validated integer drag vector and changes
    only the voltage/coverage model. Extreme (>=400 meV) transport stays fail-closed.
    """

    effective_x = x
    effective_y = y
    total_dx = 0
    total_dy = 0
    matched: list[int] = []

    for storm in _classic_root_storms(storms):
        if storm.radius <= 0:
            continue
        if hypot(effective_x - storm.x, effective_y - storm.y) >= storm.radius:
            continue
        if storm.voltage < 150.0:
            continue
        if storm.voltage >= 400.0:
            return None, "extreme_voltage", tuple(matched + [storm.id])
        dx, dy = integer_drag_delta(storm.warp, storm.heading)
        effective_x += dx
        effective_y += dy
        total_dx += dx
        total_dy += dy
        matched.append(storm.id)

    if not matched:
        return (0, 0), "not_affected", ()
    return (total_dx, total_dy), "resolved_drag", tuple(matched)


def _alternative_category(
    sample: MovementSample,
    *,
    storms: Sequence[StormRecord],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[str | None, str, tuple[int, ...], tuple[int, int] | None]:
    offset, status, storm_ids = _classic_constant_offset(
        storms,
        x=sample.x,
        y=sample.y,
    )
    if offset is None or offset == (0, 0):
        return None, status, storm_ids, offset

    base = _navigation_endpoint(sample)
    shifted = (base[0] + offset[0], base[1] + offset[1])
    if sample.observed_destination == shifted:
        return "classic_constant_ion_storm_drag", status, storm_ids, offset

    well, ambiguous = _warp_well_destination(
        sample=sample,
        endpoint=shifted,
        planets=planets,
    )
    if ambiguous:
        return None, "warp_well_ambiguous", storm_ids, offset
    if well is not None and sample.observed_destination == well:
        return "classic_constant_ion_storm_drag_warp_well_match", status, storm_ids, offset
    return None, status, storm_ids, offset


def _sample(row: Mapping[str, Any]) -> MovementSample:
    return MovementSample(
        turn=int(row["before_embedded_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        hull_id=int(row["hull_id"]) if row["hull_id"] is not None else None,
    )


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit classic constant-voltage ion-storm explanations in final movement residuals."
    )
    parser.add_argument(
        "--direct-loadinfo",
        action="store_true",
        help=(
            "Fetch public game/loadinfo directly. Intended for an explicitly local "
            "workstation run; server-side corpus acquisition remains proxy-only."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _args()

    con = duckdb.connect(str(DB), read_only=True)
    try:
        columns = [
            item[1]
            for item in con.execute(
                "PRAGMA table_info('movement_post_horwasp_strong_residual')"
            ).fetchall()
        ]
        rows_raw = con.execute(
            "SELECT * FROM movement_post_horwasp_strong_residual "
            "ORDER BY game_id, before_archive_turn, ship_id"
        ).fetchall()
    finally:
        con.close()
    rows = [dict(zip(columns, raw)) for raw in rows_raw]

    print("===== CLASSIC ION STORM FINAL RESIDUAL AUDIT =====")
    print("rows=", len(rows))
    print("loadinfo_transport=", "direct-explicit" if args.direct_loadinfo else "proxy-required")

    by_game_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game_rows[int(row["game_id"])].append(row)

    api = None if args.direct_loadinfo else PlanetsNuPublicApi()
    totals = Counter()
    by_hull: dict[int, Counter[str]] = defaultdict(Counter)
    by_game: dict[int, Counter[str]] = defaultdict(Counter)
    categories = Counter()
    offsets = Counter()
    examples: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(by_game_rows.items()):
        archive_path = ARCHIVE_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pkl",
        )
        snapshots = prepared.snapshots
        archive_mode, raw_setting_values = _nuionstorms_consensus(snapshots)
        if args.direct_loadinfo:
            official_mode, settings, loadinfo_error = _official_settings_direct(game_id)
        else:
            assert api is not None
            official_mode, settings, loadinfo_error = _official_settings_proxy(api, game_id)

        if official_mode is not None:
            nuionstorms = official_mode
            mode_source = "loadinfo-direct" if args.direct_loadinfo else "loadinfo-proxy"
        elif archive_mode is not None:
            nuionstorms = archive_mode
            mode_source = "archive"
        else:
            nuionstorms = None
            mode_source = "unknown"

        storms_by_turn, conflict_turns, invalid_turns = _storm_consensus_by_turn(snapshots)
        entities = _entity_map(snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)

        print(
            f"prepared game={game_id} cache_hit={cache_hit} rows={len(game_rows)} "
            f"nuionstorms={nuionstorms!r} source={mode_source} "
            f"loadinfo_nuionstorms={official_mode!r} "
            f"maxions={settings.get('maxions')!r} "
            f"maxioncloudsperstorm={settings.get('maxioncloudsperstorm')!r} "
            f"nebulas={settings.get('nebulas')!r} stars={settings.get('stars')!r} "
            f"archive_raw_values={raw_setting_values} "
            f"loadinfo_error={loadinfo_error!r}"
        )

        for row in game_rows:
            totals["rows"] += 1
            hull_id = int(row["hull_id"]) if row["hull_id"] is not None else -1
            by_hull[hull_id]["rows"] += 1
            by_game[game_id]["rows"] += 1
            if nuionstorms is False:
                totals["classic_game_rows"] += 1
                by_hull[hull_id]["classic_game_rows"] += 1
                by_game[game_id]["classic_game_rows"] += 1
            elif nuionstorms is True:
                totals["cloudy_game_rows"] += 1
                by_hull[hull_id]["cloudy_game_rows"] += 1
                by_game[game_id]["cloudy_game_rows"] += 1
            else:
                totals["unknown_mode_rows"] += 1
                by_hull[hull_id]["unknown_mode_rows"] += 1
                by_game[game_id]["unknown_mode_rows"] += 1

            after_turn = int(row["after_archive_turn"])
            if after_turn in conflict_turns:
                totals["storm_context_conflict"] += 1
                by_hull[hull_id]["storm_context_conflict"] += 1
                continue
            if after_turn in invalid_turns:
                totals["storm_context_invalid"] += 1
                by_hull[hull_id]["storm_context_invalid"] += 1
                continue

            storms = storms_by_turn.get(after_turn, ())
            if not storms:
                totals["no_storm_records"] += 1
                continue

            sample = _effective_sample(_sample(row))
            planets = planets_by_turn.get(int(row["before_archive_turn"]), ())
            category, status, storm_ids, offset = _alternative_category(
                sample,
                storms=storms,
                planets=planets,
            )
            if storm_ids:
                totals["inside_class4_constant_voltage"] += 1
                by_hull[hull_id]["inside_class4_constant_voltage"] += 1
                by_game[game_id]["inside_class4_constant_voltage"] += 1
            if status == "extreme_voltage":
                totals["classic_extreme_voltage"] += 1
                by_hull[hull_id]["classic_extreme_voltage"] += 1
            if category is None:
                continue

            totals["classic_constant_explains_all_modes"] += 1
            by_hull[hull_id]["classic_constant_explains_all_modes"] += 1
            by_game[game_id]["classic_constant_explains_all_modes"] += 1
            categories[category] += 1
            if offset is not None:
                offsets[offset] += 1
            if nuionstorms is False:
                totals["classic_constant_explains_scoped"] += 1
                by_hull[hull_id]["classic_constant_explains_scoped"] += 1
                by_game[game_id]["classic_constant_explains_scoped"] += 1
            elif nuionstorms is True:
                totals["constant_explains_cloudy_mode"] += 1
                by_hull[hull_id]["constant_explains_cloudy_mode"] += 1
                by_game[game_id]["constant_explains_cloudy_mode"] += 1
            else:
                totals["constant_explains_unknown_mode"] += 1
            if hull_id == 79 and nuionstorms is False:
                totals["hull79_classic_constant_explains"] += 1
            if len(examples) < 50:
                examples.append(
                    {
                        "game": game_id,
                        "turn": int(row["before_archive_turn"]),
                        "ship": int(row["ship_id"]),
                        "hull": hull_id,
                        "warp": int(row["warp"]),
                        "origin": (int(row["x_before"]), int(row["y_before"])),
                        "observed": (int(row["x_after"]), int(row["y_after"])),
                        "waypoint": (int(row["target_x"]), int(row["target_y"])),
                        "baseline": row.get("baseline_category"),
                        "nuionstorms": nuionstorms,
                        "mode_source": mode_source,
                        "storm_ids": storm_ids,
                        "offset": offset,
                        "category": category,
                    }
                )

    print("\n===== TOTAL =====")
    for key in (
        "rows",
        "classic_game_rows",
        "cloudy_game_rows",
        "unknown_mode_rows",
        "storm_context_conflict",
        "storm_context_invalid",
        "no_storm_records",
        "inside_class4_constant_voltage",
        "classic_extreme_voltage",
        "classic_constant_explains_all_modes",
        "classic_constant_explains_scoped",
        "constant_explains_cloudy_mode",
        "constant_explains_unknown_mode",
        "hull79_classic_constant_explains",
    ):
        print(f"{key}=", totals[key])

    print("\n===== CATEGORIES =====")
    print(categories)

    print("\n===== TOP OFFSETS =====")
    for offset, count in offsets.most_common(30):
        print(offset, count, "distance=", round(hypot(*offset), 3))

    print("\n===== BY GAME =====")
    for game_id, counts in sorted(
        by_game.items(), key=lambda item: (-item[1]["rows"], item[0])
    ):
        print(game_id, dict(counts))

    print("\n===== TOP HULLS =====")
    print(
        "hull | rows | classic_rows | cloudy_rows | inside_class4 | "
        "scoped_explains | cloudy_constant_matches | all_mode_explains | extreme"
    )
    for hull_id, counts in sorted(
        by_hull.items(), key=lambda item: (-item[1]["rows"], item[0])
    )[:60]:
        print(
            hull_id,
            counts["rows"],
            counts["classic_game_rows"],
            counts["cloudy_game_rows"],
            counts["inside_class4_constant_voltage"],
            counts["classic_constant_explains_scoped"],
            counts["constant_explains_cloudy_mode"],
            counts["classic_constant_explains_all_modes"],
            counts["classic_extreme_voltage"],
            sep=" | ",
        )

    print("\n===== EXPLAINED EXAMPLES =====")
    for item in examples:
        print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
