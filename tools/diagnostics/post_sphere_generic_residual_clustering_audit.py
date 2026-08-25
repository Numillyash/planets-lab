from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from typing import Any, Hashable

import duckdb


DEFAULT_DB = Path("validation/corpus/compiled/v1/corpus.duckdb")
DEFAULT_RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
RESIDUAL_VIEWS = (
    "movement_post_fuel_proration_residual",
    "movement_post_mine_strong_residual",
    "movement_post_horwasp_strong_residual",
)
HORWASP_HULL_IDS = frozenset(range(201, 214))
CLOSED_MITE_HULL_ID = 213


@dataclass(frozen=True, slots=True)
class ResidualRow:
    game_id: int
    hull_id: int | None
    ship_id: int
    turn: int
    warp: int | None
    baseline_category: str | None
    gravitonic: bool
    x: int
    y: int
    next_x: int
    next_y: int
    target_x: int
    target_y: int
    observed_distance: float
    nominal_max_distance: float

    @property
    def observed_vector(self) -> tuple[int, int]:
        return self.next_x - self.x, self.next_y - self.y

    @property
    def target_vector(self) -> tuple[int, int]:
        return self.target_x - self.x, self.target_y - self.y


@dataclass(slots=True)
class ClusterStats:
    rows: int = 0
    hulls: set[int] | None = None
    games: set[int] | None = None

    def __post_init__(self) -> None:
        if self.hulls is None:
            self.hulls = set()
        if self.games is None:
            self.games = set()

    def add(self, row: ResidualRow) -> None:
        self.rows += 1
        if row.hull_id is not None:
            self.hulls.add(row.hull_id)
        self.games.add(row.game_id)


def _distance_bucket(distance: float) -> str:
    if distance <= 1.5:
        return "<=1.5"
    if distance <= 10:
        return "1.5-10"
    if distance <= 50:
        return "10-50"
    if distance <= 90:
        return "50-90"
    if distance <= 150:
        return "90-150"
    if distance <= 500:
        return "150-500"
    if distance <= 1000:
        return "500-1000"
    return ">1000"


def _ratio_bucket(distance: float, nominal: float) -> str:
    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (
        ("~0.5x", 0.5),
        ("~1.0x", 1.0),
        ("~1.5x", 1.5),
        ("~2.0x", 2.0),
        ("~3.0x", 3.0),
    ):
        if abs(ratio - target) <= 0.08:
            return label
    if ratio < 0.5:
        return "<0.5x"
    if ratio < 1.0:
        return "0.5-1.0x"
    if ratio < 1.5:
        return "1.0-1.5x"
    if ratio < 2.0:
        return "1.5-2.0x"
    if ratio < 3.0:
        return "2.0-3.0x"
    return ">3.0x"


def _warp_bucket(warp: int | None) -> str:
    if warp is None:
        return "warp_unknown"
    if warp <= 0:
        return "warp0"
    if warp <= 3:
        return "warp1-3"
    if warp <= 6:
        return "warp4-6"
    if warp <= 9:
        return "warp7-9"
    return "warp>9"


def _target_relation(row: ResidualRow) -> str:
    origin = (row.x, row.y)
    observed = (row.next_x, row.next_y)
    target = (row.target_x, row.target_y)
    if observed == origin and target == origin:
        return "observed=origin,target=origin"
    if observed == origin:
        return "observed=origin"
    if target == origin:
        return "target=origin"
    if observed == target:
        return "observed=target"
    return "observed=other"


def _direction_bucket(row: ResidualRow) -> str:
    odx, ody = row.observed_vector
    tdx, tdy = row.target_vector
    observed_norm = hypot(odx, ody)
    target_norm = hypot(tdx, tdy)
    if observed_norm <= 1e-9:
        return "observed_stationary"
    if target_norm <= 1e-9:
        return "target_is_origin"
    cosine = (odx * tdx + ody * tdy) / (observed_norm * target_norm)
    if cosine >= 0.98:
        return "same_line_forward"
    if cosine >= 0.75:
        return "mostly_forward"
    if cosine <= -0.98:
        return "same_line_reverse"
    if cosine <= -0.75:
        return "mostly_reverse"
    if -0.25 <= cosine <= 0.25:
        return "roughly_perpendicular"
    return "oblique"


def _canonical_vector(vector: tuple[int, int]) -> tuple[int, int]:
    """Collapse sign, axis swap and mirror variants into one displacement shape."""
    a, b = abs(vector[0]), abs(vector[1])
    return (a, b) if a >= b else (b, a)


def _load_rows(
    db_path: Path,
    residual_view: str = DEFAULT_RESIDUAL_VIEW,
) -> list[ResidualRow]:
    if residual_view not in RESIDUAL_VIEWS:
        raise ValueError(f"unsupported residual view: {residual_view}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        raw_rows = con.execute(
            f"""
            SELECT
                game_id,
                hull_id,
                ship_id,
                before_archive_turn,
                warp,
                baseline_category,
                coalesce(is_gravitonic_hull, false),
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                coalesce(observed_distance, 0.0),
                coalesce(nominal_max_distance, 0.0)
            FROM {residual_view}
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    rows: list[ResidualRow] = []
    for raw in raw_rows:
        if any(raw[index] is None for index in (0, 2, 3, 7, 8, 9, 10, 11, 12)):
            continue
        rows.append(
            ResidualRow(
                game_id=int(raw[0]),
                hull_id=int(raw[1]) if raw[1] is not None else None,
                ship_id=int(raw[2]),
                turn=int(raw[3]),
                warp=int(raw[4]) if raw[4] is not None else None,
                baseline_category=str(raw[5]) if raw[5] is not None else None,
                gravitonic=bool(raw[6]),
                x=int(raw[7]),
                y=int(raw[8]),
                next_x=int(raw[9]),
                next_y=int(raw[10]),
                target_x=int(raw[11]),
                target_y=int(raw[12]),
                observed_distance=float(raw[13]),
                nominal_max_distance=float(raw[14]),
            )
        )
    return rows


def _cluster(
    rows: list[ResidualRow],
    key_fn,
) -> dict[Hashable, ClusterStats]:
    result: dict[Hashable, ClusterStats] = defaultdict(ClusterStats)
    for row in rows:
        result[key_fn(row)].add(row)
    return dict(result)


def _print_counter(title: str, counter: Counter[Any], *, limit: int) -> None:
    print(f"\n===== {title} =====")
    for key, count in counter.most_common(limit):
        print(key, count)


def _print_clusters(
    title: str,
    clusters: dict[Hashable, ClusterStats],
    *,
    limit: int,
    min_hulls: int = 1,
    min_games: int = 1,
) -> None:
    print(f"\n===== {title} =====")
    candidates = [
        (key, stats)
        for key, stats in clusters.items()
        if len(stats.hulls) >= min_hulls and len(stats.games) >= min_games
    ]
    candidates.sort(
        key=lambda item: (
            -item[1].rows,
            -len(item[1].hulls),
            -len(item[1].games),
            repr(item[0]),
        )
    )
    for key, stats in candidates[:limit]:
        print(
            key,
            "rows=", stats.rows,
            "hulls=", len(stats.hulls), sorted(stats.hulls),
            "games=", len(stats.games), sorted(stats.games),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cluster the selected final movement residual layer by generic geometry "
            "signatures shared across hulls and games. The default is the current "
            "post-fuel L2 v6 endpoint; post-mine and post-Horwasp stages remain "
            "available for explicit reproduction/overlap work."
        )
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument(
        "--residual-view",
        choices=RESIDUAL_VIEWS,
        default=DEFAULT_RESIDUAL_VIEW,
        help="DuckDB residual view to cluster (default: current post-fuel final layer).",
    )
    parser.add_argument(
        "--include-horwasp",
        action="store_true",
        help="Include hull ids 201-213 in the generic clustering population.",
    )
    args = parser.parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if not args.db.is_file():
        raise SystemExit(f"missing compiled corpus database: {args.db}")

    all_rows = _load_rows(args.db, args.residual_view)
    mite_rows = [row for row in all_rows if row.hull_id == CLOSED_MITE_HULL_ID]
    horwasp_rows = [row for row in all_rows if row.hull_id in HORWASP_HULL_IDS]
    generic_rows = (
        all_rows
        if args.include_horwasp
        else [row for row in all_rows if row.hull_id not in HORWASP_HULL_IDS]
    )

    print("===== GENERIC RESIDUAL CLUSTERING AUDIT =====")
    print("residual_view=", args.residual_view)
    print("final_residual_rows=", len(all_rows))
    print("closed_mite_rows=", len(mite_rows))
    print("known_horwasp_hull_rows=", len(horwasp_rows))
    print("generic_rows=", len(generic_rows))
    print("generic_games=", len({row.game_id for row in generic_rows}))
    print("generic_hulls=", len({row.hull_id for row in generic_rows if row.hull_id is not None}))

    _print_counter(
        "GENERIC HULL COUNTS",
        Counter(row.hull_id for row in generic_rows),
        limit=args.limit,
    )
    _print_counter(
        "GENERIC GAME COUNTS",
        Counter(row.game_id for row in generic_rows),
        limit=args.limit,
    )
    _print_counter(
        "BASELINE CATEGORIES",
        Counter(row.baseline_category for row in generic_rows),
        limit=args.limit,
    )
    _print_counter(
        "WARP BUCKETS",
        Counter(_warp_bucket(row.warp) for row in generic_rows),
        limit=args.limit,
    )
    _print_counter(
        "DISTANCE BUCKETS",
        Counter(_distance_bucket(row.observed_distance) for row in generic_rows),
        limit=args.limit,
    )
    _print_counter(
        "OBSERVED / NOMINAL RATIO",
        Counter(
            _ratio_bucket(row.observed_distance, row.nominal_max_distance)
            for row in generic_rows
        ),
        limit=args.limit,
    )
    _print_counter(
        "TARGET RELATION",
        Counter(_target_relation(row) for row in generic_rows),
        limit=args.limit,
    )
    _print_counter(
        "DIRECTION RELATIVE TO TARGET",
        Counter(_direction_bucket(row) for row in generic_rows),
        limit=args.limit,
    )

    exact_vectors = _cluster(generic_rows, lambda row: row.observed_vector)
    canonical_vectors = _cluster(generic_rows, lambda row: _canonical_vector(row.observed_vector))
    mechanic_signatures = _cluster(
        generic_rows,
        lambda row: (
            _warp_bucket(row.warp),
            row.baseline_category,
            _ratio_bucket(row.observed_distance, row.nominal_max_distance),
            _target_relation(row),
            _direction_bucket(row),
            row.gravitonic,
        ),
    )
    coarse_signatures = _cluster(
        generic_rows,
        lambda row: (
            _warp_bucket(row.warp),
            _ratio_bucket(row.observed_distance, row.nominal_max_distance),
            _target_relation(row),
            _direction_bucket(row),
        ),
    )

    _print_clusters(
        "EXACT DISPLACEMENTS SHARED BY >=2 HULLS / >=2 GAMES",
        exact_vectors,
        limit=args.limit,
        min_hulls=2,
        min_games=2,
    )
    _print_clusters(
        "CANONICAL DISPLACEMENT SHAPES SHARED BY >=2 HULLS / >=2 GAMES",
        canonical_vectors,
        limit=args.limit,
        min_hulls=2,
        min_games=2,
    )
    _print_clusters(
        "DETAILED MECHANIC SIGNATURES SHARED BY >=2 HULLS / >=2 GAMES",
        mechanic_signatures,
        limit=args.limit,
        min_hulls=2,
        min_games=2,
    )
    _print_clusters(
        "COARSE SIGNATURES SHARED BY >=3 HULLS / >=2 GAMES",
        coarse_signatures,
        limit=args.limit,
        min_hulls=3,
        min_games=2,
    )

    candidate_hulls = (23, 52, 56, 17, 46, 94, 29, 22, 16, 31)
    print("\n===== CANDIDATE HULL SIGNATURES =====")
    for hull_id in candidate_hulls:
        hull_rows = [row for row in generic_rows if row.hull_id == hull_id]
        if not hull_rows:
            continue
        signatures = Counter(
            (
                _warp_bucket(row.warp),
                _ratio_bucket(row.observed_distance, row.nominal_max_distance),
                _target_relation(row),
                _direction_bucket(row),
                row.baseline_category,
            )
            for row in hull_rows
        )
        print(
            "hull=", hull_id,
            "rows=", len(hull_rows),
            "games=", sorted({row.game_id for row in hull_rows}),
        )
        for signature, count in signatures.most_common(8):
            print("  ", signature, count)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Prefer clusters with multiple hulls and multiple games. Exact/canonical "
        "vector repetition is a lead, not a mechanic by itself. Do not reopen "
        "Red Mite or promote a hull-specific rule from this summary alone."
    )


if __name__ == "__main__":
    main()
